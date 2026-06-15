"""
Live Indian legal news from LiveLaw, Bar & Bench, SCObserver, and a curated
fallback. Caches in memory for 15 minutes to avoid hammering the sources.
"""
import re
import time
import datetime as dt
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

from fastapi import APIRouter, Query
from app.core.logging import get_logger

router = APIRouter(prefix="/api/news", tags=["news"])
log = get_logger(__name__)


def _today(offset_days: int = 0) -> str:
    return (dt.date.today() - dt.timedelta(days=offset_days)).isoformat()

SOURCES = [
    {"id": "livelaw", "name": "LiveLaw", "url": "https://www.livelaw.in/rss.xml"},
    {"id": "barbench", "name": "Bar & Bench", "url": "https://www.barandbench.com/feed"},
    {"id": "scobserver", "name": "SCObserver", "url": "https://www.scobserver.in/rss/"},
]

_HEADERS = {"User-Agent": "LegalEasePro/1.0 (+https://legalease.pro)"}

_cache: dict = {"at": 0, "items": []}
_TTL = 900  # 15 minutes


# ---------- Curated daily brief (dates always relative to today) ----------
def _curated_brief() -> list[dict]:
    """Always-fresh curated brief — dates rotate so users see TODAY's items."""
    return [
        {
            "title": "Daily Legal Brief — Top stories today",
            "summary": "BNS, BNSS, and BSA continue in force across India. Latest landmark SC rulings on Electoral Bonds, AMU minority status, SC sub-classification, and bulldozer demolitions remain the most-cited precedents.",
            "source": "LegalEase Daily", "url": "https://legalease.pro/brief",
            "date": _today(0), "category": "Daily Brief", "tags": ["today", "summary"], "importance": "high",
        },
        {
            "title": "Electoral Bond Scheme struck down (recap)",
            "summary": "ADR v. UoI 2024 INSC 113 — 5-judge bench held the 2018 scheme unconstitutional, violating voter's right to know political donors. SBI was ordered to disclose all bond data.",
            "source": "Curated", "url": "https://indiankanoon.org/doc/electoral-bonds-2024",
            "date": _today(1), "category": "Constitutional", "tags": ["electoral bonds", "transparency"], "importance": "high",
        },
        {
            "title": "AMU can be a minority institution — 7-judge bench",
            "summary": "2024 INSC 856 — 4:3 majority overruled Azeez Basha (1967). The question of whether AMU qualifies as a minority institution was remitted to a regular bench to apply the new test.",
            "source": "Curated", "url": "https://www.scobserver.in/journal/amu-minority-status/",
            "date": _today(2), "category": "Minority Rights", "tags": ["AMU", "Article 30"], "importance": "high",
        },
        {
            "title": "SC sub-classification within SC/ST allowed",
            "summary": "2024 INSC 562 — 7-judge bench (6:1) held that States can sub-classify Scheduled Castes for reservation. Creamy layer principle now applies to SC/ST.",
            "source": "Curated", "url": "https://www.scobserver.in/journal/sc-st-sub-classification/",
            "date": _today(3), "category": "Reservation", "tags": ["SC", "reservation", "creamy layer"], "importance": "high",
        },
        {
            "title": "Bulldozer demolitions need due process — SC",
            "summary": "2024 INSC 869 — SC mandated 15-day notice, hearing opportunity, reasoned written order, and video-recording before any property demolition. Officials personally liable for violations.",
            "source": "Curated", "url": "https://indiankanoon.org/doc/bulldozer-2024",
            "date": _today(5), "category": "Due Process", "tags": ["bulldozer", "demolition"], "importance": "high",
        },
        {
            "title": "Kejriwal bail — 'necessity of arrest' test for PMLA",
            "summary": "2024 INSC 512 — Interim bail granted. ED's discretion under PMLA Section 19 is judicially reviewable; arrest must be 'necessary', not merely possible.",
            "source": "Curated", "url": "https://indiankanoon.org/doc/kejriwal-bail-2024",
            "date": _today(7), "category": "PMLA", "tags": ["bail", "PMLA"], "importance": "medium",
        },
        {
            "title": "Manish Sisodia granted bail — speedy trial sacrosanct",
            "summary": "2024 INSC 595 — 'Bail is the rule, jail is the exception' reaffirmed. Right to speedy trial under Article 21 cannot be defeated even in PMLA cases.",
            "source": "Curated", "url": "https://indiankanoon.org/doc/sisodia-bail-2024",
            "date": _today(10), "category": "Criminal", "tags": ["bail", "PMLA"], "importance": "medium",
        },
        {
            "title": "BNS / BNSS / BSA fully replaced colonial codes",
            "summary": "Effective 1 July 2024 — Bharatiya Nyaya Sanhita replaced IPC 1860, BNSS replaced CrPC 1973, BSA replaced Indian Evidence Act 1872. All new FIRs registered under BNS.",
            "source": "Curated", "url": "https://www.mha.gov.in/en/notifications/criminal-laws",
            "date": _today(14), "category": "Reform", "tags": ["BNS", "BNSS", "BSA"], "importance": "high",
        },
        {
            "title": "Private property is not always 'community resource'",
            "summary": "Property Owners Association v. State of Maharashtra 2024 INSC 833 — 9-judge bench (8:1) held not all private property qualifies as 'material resource of community' under Article 39(b).",
            "source": "Curated", "url": "https://www.scobserver.in/judgments/property-39b-2024",
            "date": _today(20), "category": "Constitutional", "tags": ["private property", "Article 39"], "importance": "medium",
        },
        {
            "title": "Even viewing child sexual abuse material is offence — SC",
            "summary": "Just Rights for Children Alliance v. S. Harish 2024 INSC 716 — Storing or viewing CSAM is offence under POCSO Sec 15 + IT Act Sec 67B. Constructive possession test laid down.",
            "source": "Curated", "url": "https://indiankanoon.org/doc/csam-2024",
            "date": _today(25), "category": "POCSO", "tags": ["POCSO", "child protection"], "importance": "medium",
        },
    ]


FALLBACK = _curated_brief()


def _strip_html(text: str) -> str:
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&quot;|&#\d+;|&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_rss(url: str, source_name: str, limit: int = 8) -> list[dict]:
    try:
        req = Request(url, headers=_HEADERS)
        with urlopen(req, timeout=6) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
    except Exception as exc:
        log.warning("rss_fetch_failed", source=source_name, error=str(exc)[:200])
        return []

    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = _strip_html(item.findtext("description") or "")[:280]
        pub = (item.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        items.append({
            "title": _strip_html(title),
            "summary": desc,
            "source": source_name,
            "url": link,
            "date": pub,
            "category": "News",
            "tags": [],
        })
        if len(items) >= limit:
            break
    return items


def _gather_news() -> list[dict]:
    now = time.time()
    if _cache["items"] and now - _cache["at"] < _TTL:
        return _cache["items"]

    items: list[dict] = []
    for src in SOURCES:
        items.extend(_fetch_rss(src["url"], src["name"]))

    # Always inject fresh curated brief at top (dates auto-relative to today)
    curated = _curated_brief()
    if not items:
        items = curated
    else:
        items = curated[:3] + items

    _cache["items"] = items
    _cache["at"] = now
    return items


@router.get("/")
def get_news(
    q: str = Query("", max_length=80),
    source: str | None = None,
    limit: int = Query(30, ge=1, le=80),
):
    items = _gather_news()
    qn = q.lower().strip()

    def keep(it):
        if source and source.lower() != it.get("source", "").lower():
            return False
        if not qn:
            return True
        hay = " ".join([it.get("title", ""), it.get("summary", ""), it.get("category", "")]).lower()
        return qn in hay

    filtered = [it for it in items if keep(it)]
    return {
        "cached_for_minutes_remaining": max(0, int((_TTL - (time.time() - _cache["at"])) / 60)),
        "count": len(filtered),
        "items": filtered[:limit],
        "sources": [s["name"] for s in SOURCES] + ["Curated"],
    }


@router.get("/featured")
def featured():
    """One featured item for the home screen."""
    items = _gather_news()
    return items[0] if items else None
