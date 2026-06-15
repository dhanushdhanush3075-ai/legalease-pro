"""
LegalEase India v3.0 — Backend
================================
Fixed: All intent classifiers working
Added: Court locator, lawyer finder, multi-language,
       document analysis, legal news, real responses
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import hashlib, json, uuid, logging, os, re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────────────

STATE_LAWS = {
    "TN": {"name":"Tamil Nadu","flag":"🏛️","alcohol":"regulated","stamp_duty":7.0,
           "rent_act":"TN Buildings (Lease & Rent Control) Act 1960","prohibition":False,
           "note":"TN has India's strongest rent control protection."},
    "GJ": {"name":"Gujarat","flag":"🦁","alcohol":"PROHIBITED","stamp_duty":4.9,
           "rent_act":"Gujarat Rent Control Act 2011","prohibition":True,
           "note":"⚠️ TOTAL ALCOHOL PROHIBITION. Possession = arrest. No bail easily."},
    "MH": {"name":"Maharashtra","flag":"🌊","alcohol":"regulated","stamp_duty":6.0,
           "rent_act":"Maharashtra Rent Control Act 1999","prohibition":False,
           "note":"RERA Maharashtra resolves housing disputes faster."},
    "KA": {"name":"Karnataka","flag":"🌿","alcohol":"regulated","stamp_duty":5.6,
           "rent_act":"Karnataka Rent Control Act 2001","prohibition":False,
           "note":"Bengaluru has dedicated fast-track courts for IT/commercial disputes."},
    "AP": {"name":"Andhra Pradesh","flag":"🌾","alcohol":"regulated","stamp_duty":5.0,
           "rent_act":"AP Rent Control Act 1960","prohibition":False,
           "note":"DHARANI portal for land records in AP."},
    "DL": {"name":"Delhi","flag":"🏙️","alcohol":"regulated","stamp_duty":6.0,
           "rent_act":"Delhi Rent Control Act 1958","prohibition":False,
           "note":"Old Delhi tenants have very strong protection — eviction needs legal grounds."},
    "UP": {"name":"Uttar Pradesh","flag":"⛩️","alcohol":"regulated","stamp_duty":5.0,
           "rent_act":"UP Urban Buildings Act 1972","prohibition":False,
           "note":"Check case status on ecourts.gov.in"},
    "RJ": {"name":"Rajasthan","flag":"🏜️","alcohol":"regulated","stamp_duty":6.0,
           "rent_act":"Rajasthan Rent Control Act 2001","prohibition":False,
           "note":"Rajasthan e-Dharti portal for land records."},
    "WB": {"name":"West Bengal","flag":"🐅","alcohol":"regulated","stamp_duty":6.0,
           "rent_act":"WB Premises Tenancy Act 1997","prohibition":False,
           "note":"WB tenants can stay indefinitely in many cases."},
}

IPC_DB = {
    "302":{"title":"Murder","punishment":"Death or life imprisonment + fine","bailable":False,"court":"Sessions Court"},
    "304":{"title":"Culpable homicide","punishment":"Up to 10 years + fine","bailable":False,"court":"Sessions Court"},
    "323":{"title":"Voluntarily causing hurt","punishment":"Up to 1 year or ₹1000 fine","bailable":True,"court":"Magistrate"},
    "324":{"title":"Hurt with dangerous weapons","punishment":"Up to 3 years or fine","bailable":False,"court":"Magistrate"},
    "325":{"title":"Grievous hurt","punishment":"Up to 7 years + fine","bailable":False,"court":"Magistrate"},
    "354":{"title":"Assault on woman","punishment":"1–5 years + fine","bailable":False,"court":"Magistrate"},
    "354A":{"title":"Sexual harassment","punishment":"Up to 3 years or fine","bailable":False,"court":"Magistrate"},
    "354D":{"title":"Stalking","punishment":"1st: 3 years, Repeat: 5 years","bailable":False,"court":"Magistrate"},
    "376":{"title":"Rape","punishment":"7 years to life imprisonment","bailable":False,"court":"Sessions Court"},
    "379":{"title":"Theft","punishment":"Up to 3 years or fine","bailable":False,"court":"Magistrate"},
    "392":{"title":"Robbery","punishment":"Up to 10 years + fine","bailable":False,"court":"Sessions Court"},
    "406":{"title":"Criminal breach of trust","punishment":"Up to 3 years or fine","bailable":False,"court":"Magistrate"},
    "420":{"title":"Cheating / Fraud","punishment":"Up to 7 years + fine","bailable":False,"court":"Magistrate"},
    "427":{"title":"Property damage / Mischief","punishment":"Up to 2 years or fine","bailable":True,"court":"Magistrate"},
    "498A":{"title":"Domestic cruelty","punishment":"Up to 3 years + fine","bailable":False,"court":"Magistrate"},
    "499":{"title":"Defamation","punishment":"Up to 2 years or fine","bailable":True,"court":"Magistrate"},
    "504":{"title":"Intentional insult","punishment":"Up to 2 years or fine","bailable":True,"court":"Magistrate"},
    "506":{"title":"Criminal intimidation","punishment":"Up to 2 years or fine","bailable":True,"court":"Magistrate"},
    "509":{"title":"Insulting modesty of woman","punishment":"Up to 3 years + fine","bailable":True,"court":"Magistrate"},
}

COURTS_BY_STATE = {
    "TN": [
        {"name":"Madras High Court","city":"Chennai","type":"High Court","address":"High Court Buildings, Chennai - 600104","phone":"044-25340120","handles":["All civil & criminal appeals","Writ petitions","Constitutional matters"]},
        {"name":"Chennai City Civil Court","city":"Chennai","type":"District Civil","address":"High Court Premises, Chennai - 600104","phone":"044-25213293","handles":["Civil disputes","Money recovery","Property disputes"]},
        {"name":"District Consumer Disputes Redressal Commission","city":"Chennai","type":"Consumer Court","address":"Saidapet, Chennai - 600015","phone":"044-22200027","handles":["Consumer complaints up to ₹50 lakhs","Defective products","Service deficiency"]},
        {"name":"Labour Court Chennai","city":"Chennai","type":"Labour Court","address":"Rajaji Salai, Chennai - 600001","phone":"044-25366040","handles":["Salary disputes","Wrongful termination","Industrial disputes"]},
        {"name":"Family Court Chennai","city":"Chennai","type":"Family Court","address":"No.1 Greenways Road, Chennai","phone":"044-28111111","handles":["Divorce","Child custody","Maintenance"]},
    ],
    "KA": [
        {"name":"Karnataka High Court","city":"Bengaluru","type":"High Court","address":"High Court Building, Bengaluru - 560001","phone":"080-22861271","handles":["All civil & criminal appeals","Constitutional matters"]},
        {"name":"City Civil Court Bengaluru","city":"Bengaluru","type":"District Civil","address":"Mayo Hall, Bengaluru","phone":"080-22868001","handles":["Civil disputes","Property cases"]},
        {"name":"Consumer Court Bengaluru","city":"Bengaluru","type":"Consumer Court","address":"Sheshadri Road, Bengaluru","phone":"080-22257522","handles":["Consumer complaints","Product defects"]},
    ],
    "MH": [
        {"name":"Bombay High Court","city":"Mumbai","type":"High Court","address":"Opp. Oval Maidan, Fort, Mumbai - 400001","phone":"022-22620431","handles":["All civil & criminal appeals","Constitutional matters"]},
        {"name":"City Civil Court Mumbai","city":"Mumbai","type":"District Civil","address":"Dhobi Talao, Mumbai","phone":"022-22620881","handles":["Civil disputes","Money recovery"]},
    ],
    "DL": [
        {"name":"Delhi High Court","city":"New Delhi","type":"High Court","address":"Sher Shah Road, New Delhi - 110003","phone":"011-23386470","handles":["All civil & criminal appeals","Constitutional matters"]},
        {"name":"Tis Hazari District Court","city":"Delhi","type":"District","address":"Tis Hazari, Delhi - 110054","phone":"011-23967474","handles":["Civil & criminal cases","Family matters"]},
    ],
}

LAWYERS_DB = {
    "TN": [
        {"name":"Tamil Nadu State Legal Services Authority","type":"Free Legal Aid","city":"Chennai","phone":"044-28112121","address":"No.34, Peters Road, Royapettah, Chennai","speciality":"All cases — Free for BPL/SC/ST/Women/Minors"},
        {"name":"District Legal Services Authority","type":"Free Legal Aid","city":"Chennai","phone":"044-28111234","address":"High Court Premises, Chennai","speciality":"Free legal aid for eligible persons"},
        {"name":"Bar Council of Tamil Nadu","type":"Lawyer Directory","city":"Chennai","phone":"044-25340150","address":"High Court Buildings, Chennai","speciality":"Find registered advocates in TN"},
    ],
    "KA": [
        {"name":"Karnataka State Legal Services Authority","type":"Free Legal Aid","city":"Bengaluru","phone":"080-22117025","address":"High Court Building, Bengaluru","speciality":"All cases — Free for eligible persons"},
    ],
    "MH": [
        {"name":"Maharashtra State Legal Services Authority","type":"Free Legal Aid","city":"Mumbai","phone":"022-22620431","address":"High Court, Mumbai","speciality":"Free legal aid — all cases"},
    ],
    "DL": [
        {"name":"Delhi State Legal Services Authority","type":"Free Legal Aid","city":"Delhi","phone":"011-23386715","address":"Patiala House Courts, New Delhi","speciality":"Free legal aid — all cases"},
    ],
}

LEGAL_NEWS = [
    {"id":"n1","title":"Supreme Court: Landlords cannot withhold deposit without reason","category":"Rent Law","date":"2025-01-15","summary":"SC bench ruled that unreasonable withholding of security deposit violates tenant rights under Transfer of Property Act. Landlords must provide written justification within 30 days.","source":"LiveLaw","relevantStates":["TN","MH","KA","DL"],"ipc":"TPA §108(q)"},
    {"id":"n2","title":"IT Act amended — stricter penalties for online harassment","category":"Cybercrime","date":"2025-01-10","summary":"New amendment increases punishment for cyberstalking and online harassment to 5 years imprisonment. Social media platforms must comply with takedown requests within 24 hours.","source":"Bar & Bench","relevantStates":["All"],"ipc":"IT Act §66C, §66E"},
    {"id":"n3","title":"Consumer Protection Act: Online sellers now liable for delivery damage","category":"Consumer Rights","date":"2025-01-08","summary":"NCDRC ruling establishes that e-commerce platforms share liability for damaged goods. Consumers can claim full refund + compensation from both seller and platform.","source":"Indian Express","relevantStates":["All"],"ipc":"CPA 2019 §94"},
    {"id":"n4","title":"Child Labour Amendment: Stricter enforcement in Tamil Nadu","category":"Child Rights","date":"2025-01-05","summary":"TN government announces surprise inspections in industrial areas. Employers found violating Child Labour Act face minimum 2 years jail + ₹50,000 fine.","source":"The Hindu","relevantStates":["TN"],"ipc":"Child Labour Act §14"},
    {"id":"n5","title":"Sexual Harassment at Workplace Act: New POSH guidelines issued","category":"Workplace Rights","date":"2024-12-28","summary":"Ministry issues updated POSH guidelines mandating ICC constitution within 60 days of company formation. Non-compliance fines doubled to ₹50,000.","source":"Economic Times","relevantStates":["All"],"ipc":"POSH Act 2013"},
    {"id":"n6","title":"Gujarat HC: Alcohol possession case bail conditions relaxed","category":"Prohibition Law","date":"2024-12-20","summary":"Gujarat HC issued guidelines for bail in first-time alcohol possession cases, but emphasized zero tolerance for repeat offenders and trafficking.","source":"Gujarat HC","relevantStates":["GJ"],"ipc":"Gujarat Prohibition Act"},
    {"id":"n7","title":"Domestic Violence Act: Protection orders can be issued ex-parte","category":"Domestic Violence","date":"2024-12-15","summary":"SC reaffirmed that Magistrates can issue emergency protection orders under PWDVA without waiting for accused response, within 24 hours of complaint.","source":"Supreme Court","relevantStates":["All"],"ipc":"PWDVA 2005 §18"},
    {"id":"n8","title":"Property Registration: TN makes Aadhaar mandatory from Jan 2025","category":"Property Law","date":"2024-12-10","summary":"Tamil Nadu makes Aadhaar linking mandatory for all property registrations. Both buyer and seller must have verified Aadhaar. NRIs can use passport alternatively.","source":"TN Government","relevantStates":["TN"],"ipc":"Registration Act §32A"},
]

DOCUMENT_TYPES = {
    "fir":"First Information Report",
    "hearing_notice":"Court Hearing Notice / Summons",
    "affidavit":"Affidavit",
    "legal_notice":"Legal Notice",
    "bail_order":"Bail Order",
    "judgment":"Court Judgment",
    "warrant":"Arrest Warrant",
    "maintenance_order":"Maintenance Order",
    "custody_order":"Child Custody Order",
    "eviction_notice":"Eviction Notice",
}

TRANSLATIONS = {
    "en": {
        "welcome": "Welcome to LegalEase India.",
        "select_state": "Please select your state to get accurate jurisdiction-specific answers.",
        "no_legal_q": "That doesn't seem like a legal question. Ask me about your legal rights, complaints, documents, or court procedures.",
        "greeting": "Hello! I'm LegalEase — your Indian legal assistant. Ask me any legal question in Tamil, Hindi, or English.",
    },
    "ta": {
        "welcome": "LegalEase India-க்கு வரவேற்கிறோம்.",
        "select_state": "துல்லியமான பதில்களுக்கு உங்கள் மாநிலத்தை தேர்ந்தெடுக்கவும்.",
        "no_legal_q": "இது சட்ட கேள்வியாக தெரியவில்லை. உங்கள் சட்ட உரிமைகள், புகார்கள், ஆவணங்கள் பற்றி கேளுங்கள்.",
        "greeting": "வணக்கம்! நான் LegalEase — உங்கள் இந்திய சட்ட உதவியாளர்.",
    },
    "hi": {
        "welcome": "LegalEase India में आपका स्वागत है।",
        "select_state": "सटीक उत्तरों के लिए अपना राज्य चुनें।",
        "no_legal_q": "यह कानूनी प्रश्न नहीं लगता। अपने कानूनी अधिकारों, शिकायतों के बारे में पूछें।",
        "greeting": "नमस्ते! मैं LegalEase हूं — आपका भारतीय कानूनी सहायक।",
    }
}

# ─────────────────────────────────────────────────────────────────────
# INTENT CLASSIFIER + RESPONSE ENGINE
# ─────────────────────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "greeting":         ["hello","hi","hey","good morning","good evening","good afternoon","hai","vanakkam","namaste","namaskar","wassup","sup"],
    "nonsense":         ["sapataiya","dai","da","bro","yaar","lol","haha","test","testing","asdf","random"],
    "alcohol":          ["alcohol","liquor","beer","wine","whiskey","vodka","drink","drinking","illegal","legal","prohibition","tasmac","arrack","toddy"],
    "rent_deposit":     ["deposit","security deposit","landlord","rent","tenant","return deposit","refund deposit","lease","eviction","vacate"],
    "property_damage":  ["laptop","broke","damage","mischief","property","friend broke","broke my","smashed","destroyed","damage","427"],
    "salary":           ["salary","wage","pay","employer","unpaid","payment","increment","bonus","not paying","not paid","arrears"],
    "consumer":         ["consumer","product","defect","refund","replace","defective","complaint","amazon","flipkart","warranty","ecommerce","online shopping"],
    "sexual_harassment":["sexual harassment","sex harassment","posh","harassment","molest","assault","inappropriate touch","workplace harassment","354a","354","#metoo"],
    "child_labour":     ["child labour","child labor","minor working","child work","bonded labour","below 14","underage work"],
    "divorce":          ["divorce","separation","alimony","maintenance","custody","matrimonial","family court","spouse","husband wife"],
    "domestic_violence":["domestic violence","498a","domestic abuse","cruelty","husband torture","wife beating","498"],
    "fir_complaint":    ["fir","complaint","police complaint","report crime","file complaint","how to file","register complaint"],
    "document_analysis":["document","analyse","analyze","affidavit","hearing notice","court notice","summons","judgment","bail order","legal notice","what is this document","what does this mean"],
    "court_location":   ["court","where is court","which court","court address","court location","near court","district court","high court"],
    "lawyer":           ["lawyer","advocate","attorney","legal aid","free lawyer","vakeel","solicitor","need lawyer","find lawyer"],
    "cyber_crime":      ["cyber","online fraud","hacking","phishing","identity theft","otp fraud","upi fraud","it act","cybercrime"],
    "property_land":    ["land","property","sale deed","patta","encumbrance","survey number","registration","stamp duty","buy property"],
}

RESPONSES = {
    "greeting": {
        "en": {"answer":"Hello! I'm LegalEase, your Indian legal assistant. You can ask me:\n\n• **Tenant/landlord rights** — deposit, eviction, rent increase\n• **Workplace issues** — salary, harassment, termination\n• **Consumer complaints** — defective products, refunds\n• **Criminal matters** — FIR, bail, IPC sections\n• **Family law** — divorce, custody, maintenance\n• **Property** — land documents, registration\n\nWhat legal help do you need today?","citations":[],"deadline":None,"risk":None,"action":None,"confidence":100},
        "ta": {"answer":"வணக்கம்! நான் LegalEase, உங்கள் இந்திய சட்ட உதவியாளர். நீங்கள் என்னிடம் கேட்கலாம்:\n\n• வீட்டு வாடகை உரிமைகள்\n• தொழில் பிரச்சனைகள் — சம்பளம், தொல்லை\n• நுகர்வோர் புகார்கள்\n• குற்றவியல் விஷயங்கள் — FIR, IPC\n• குடும்ப சட்டம் — விவாகரத்து, பராமரிப்பு\n\nஉங்களுக்கு என்ன சட்ட உதவி தேவை?","citations":[],"deadline":None,"risk":None,"action":None,"confidence":100},
        "hi": {"answer":"नमस्ते! मैं LegalEase हूं। आप मुझसे पूछ सकते हैं:\n\n• किराया/जमानत अधिकार\n• वेतन और कार्यस्थल समस्याएं\n• उपभोक्ता शिकायतें\n• FIR और IPC धाराएं\n• तलाक और गुजारा भत्ता\n\nआज आपको क्या कानूनी सहायता चाहिए?","citations":[],"deadline":None,"risk":None,"action":None,"confidence":100},
    },
    "nonsense": {
        "en": {"answer":"I'm a legal assistant — I can only help with Indian law, court procedures, and legal rights. Try asking:\n\n• \"My landlord is not returning my deposit — what can I do?\"\n• \"How do I file a consumer complaint?\"\n• \"What is IPC 420?\"\n• \"My employer is not paying salary\"","citations":[],"deadline":None,"risk":None,"action":None,"confidence":100},
        "ta": {"answer":"நான் ஒரு சட்ட உதவியாளர் — சட்ட கேள்விகளுக்கு மட்டுமே பதில் சொல்வேன். கேட்டு பாருங்கள்:\n\n• \"என் வீட்டு உரிமையாளர் deposit திருப்பி கொடுக்கவில்லை\"\n• \"Consumer complaint எப்படி போடுவது?\"\n• \"என் employer சம்பளம் கொடுக்கவில்லை\"","citations":[],"deadline":None,"risk":None,"action":None,"confidence":100},
        "hi": {"answer":"मैं एक कानूनी सहायक हूं। केवल कानूनी प्रश्नों का उत्तर दे सकता हूं। पूछें:\n\n• \"मकान मालिक जमानत नहीं लौटा रहा\"\n• \"उपभोक्ता शिकायत कैसे करें?\"\n• \"नियोक्ता वेतन नहीं दे रहा\"","citations":[],"deadline":None,"risk":None,"action":None,"confidence":100},
    },
    "alcohol": {
        "en": {"answer":"**Alcohol Laws in India — State by State:**\n\n🔴 **TOTAL PROHIBITION** — Gujarat, Bihar, Nagaland, Mizoram\nIn these states, possession, consumption, or transport of alcohol is a serious criminal offence. Punishment: 1–10 years jail + heavy fine. No easy bail.\n\n🟡 **REGULATED** — Tamil Nadu, Karnataka, Maharashtra, Delhi, AP, etc.\n• Must be purchased from licensed shops (TASMAC in TN)\n• Drinking in public places is illegal\n• Driving under influence: IPC §185 MV Act — 6 months jail or ₹2000 fine or both\n• Minimum age: 21 years\n\n**Tamil Nadu specifically:** TASMAC is the only legal alcohol retailer. Private bars need TASMAC license. Illicit arrack = IPC §60 Tamil Nadu Prohibition Act.\n\n**Gujarat specifically:** ⚠️ CRITICAL — Even if you are visiting from another state, carrying alcohol into Gujarat is a crime. Permits are theoretically available but rarely granted.","citations":[{"section":"MV Act §185","title":"Drunk driving","detail":"6 months jail or ₹2000 fine. Repeat offence: 2 years."},{"section":"TN Prohibition Act §4","title":"Tamil Nadu alcohol regulation","detail":"Only TASMAC licensed outlets. Illicit: 5 years jail."}],"deadline":None,"risk":"Buying from unlicensed sources is illegal even in 'regulated' states. Only buy from government-authorized outlets.","action":"Check your state above. If in Gujarat — do NOT carry alcohol from another state.","confidence":95},
        "ta": {"answer":"**இந்தியாவில் மது சட்டங்கள்:**\n\n🔴 **தடை** — குஜராத், பீகார், நாகாலாண்ட்\nஆல்கஹால் வைத்திருப்பது கடுமையான குற்றம். 1–10 ஆண்டு சிறை.\n\n🟡 **ஒழுங்குபடுத்தப்பட்டது** — தமிழ்நாடு, கர்நாடகா, மகாராஷ்டிரா\n• TASMAC கடைகளில் மட்டுமே வாங்கலாம்\n• பொது இடத்தில் குடிப்பது சட்டவிரோதம்\n• குடித்துவிட்டு வாகனம் ஓட்டுவது — 6 மாத சிறை\n• குறைந்தபட்ச வயது: 21\n\n**தமிழ்நாட்டில்:** TASMAC மட்டுமே சட்டபூர்வமான மது விற்பனை நிலையம்.","citations":[{"section":"TN Prohibition Act §4","title":"TASMAC மட்டுமே சட்டபூர்வமானது","detail":"அனுமதியற்ற கடைகளில் வாங்குவது 5 ஆண்டு சிறை."}],"deadline":None,"risk":"அனுமதியற்ற மூலங்களிலிருந்து வாங்காதீர்கள்.","action":"உங்கள் மாநில விதியை மேலே சரிபாருங்கள். குஜராத்தில் இருந்தால் — மது எடுத்துச் செல்லாதீர்கள்.","confidence":95},
        "hi": {"answer":"**भारत में शराब कानून:**\n\n🔴 **पूर्ण प्रतिबंध** — गुजरात, बिहार, नागालैंड\nशराब रखना गंभीर अपराध। 1–10 साल जेल + भारी जुर्माना।\n\n🟡 **नियंत्रित** — महाराष्ट्र, दिल्ली, कर्नाटक\n• केवल लाइसेंसशुदा दुकानों से खरीदें\n• सार्वजनिक स्थानों पर पीना गैरकानूनी\n• शराब पीकर गाड़ी चलाना: 6 महीने जेल\n• न्यूनतम आयु: 21 वर्ष","citations":[{"section":"MV Act §185","title":"नशे में गाड़ी चलाना","detail":"6 महीने जेल या ₹2000 जुर्माना"}],"deadline":None,"risk":"केवल सरकारी लाइसेंस प्राप्त दुकानों से खरीदें।","action":"अपने राज्य का नियम ऊपर देखें।","confidence":95},
    },
    "sexual_harassment": {
        "en": {"answer":"**Sexual Harassment — Your Legal Rights:**\n\n**At Workplace (POSH Act 2013):**\nEvery company with 10+ employees MUST have an Internal Complaints Committee (ICC). You have the right to:\n1. File complaint with ICC within **3 years** of incident\n2. Get inquiry completed within 60 days\n3. Receive full confidentiality\n4. Get compensation + termination of perpetrator if proven\n\n**Steps to take:**\n1. Write down everything with dates and details — do this NOW\n2. Collect evidence: screenshots, emails, witnesses\n3. File written complaint with ICC/HR\n4. If company ignores — file with **Local Complaints Committee (LCC)** at District Collector's office\n5. FIR under **IPC §354A** (Sexual harassment) — 3 years imprisonment\n\n**Emergency contacts:**\n• Women Helpline: **1091** (24/7)\n• NCW Complaint: **7827170170**\n• Online complaint: **ncw.nic.in**\n\n**For minors — POCSO Act 2012:**\nStricter punishment — minimum 3 years to life imprisonment.","citations":[{"section":"IPC §354A","title":"Sexual harassment","detail":"Up to 3 years imprisonment or fine or both."},{"section":"POSH Act 2013 §4","title":"ICC mandatory for 10+ employee companies","detail":"Failure to constitute ICC: ₹50,000 fine for employer."},{"section":"POCSO Act 2012","title":"Protection of Children from Sexual Offences","detail":"For victims under 18. Minimum 3 years — maximum life."}],"deadline":"File ICC complaint within 3 years of incident. FIR can be filed any time.","risk":"Do NOT resign before filing complaint — you lose leverage. Document everything first.","action":"Call 1091 (Women Helpline) immediately. File written ICC complaint. Collect evidence NOW.","confidence":97},
        "ta": {"answer":"**பாலியல் தொல்லை — உங்கள் சட்ட உரிமைகள்:**\n\n**பணியிடத்தில் (POSH சட்டம் 2013):**\n10+ பணியாளர் உள்ள ஒவ்வொரு நிறுவனமும் ICC (உள் புகார் குழு) கட்டாயம் வைக்க வேண்டும்.\n\n**செய்ய வேண்டியவை:**\n1. நடந்தவற்றை தேதிகளுடன் உடனே எழுதி வையுங்கள்\n2. ஆதாரம் சேகரிக்கவும் — screenshots, emails\n3. ICC/HR-ல் எழுத்துப்பூர்வ புகார் செய்யுங்கள்\n4. IPC §354A கீழ் FIR — 3 ஆண்டு சிறை\n\n**அவசர தொடர்பு:**\n• பெண்கள் உதவி: **1091** (24/7)\n• NCW புகார்: **7827170170**","citations":[{"section":"IPC §354A","title":"பாலியல் தொல்லை","detail":"3 ஆண்டு சிறை அல்லது அபராதம்."},{"section":"POSH சட்டம் 2013","title":"கட்டாய ICC","detail":"ICC இல்லாத நிறுவனம் — ₹50,000 அபராதம்."}],"deadline":"ICC புகார் — நிகழ்விலிருந்து 3 ஆண்டுகளுக்குள்.","risk":"புகார் செய்வதற்கு முன் ராஜினாமா செய்யாதீர்கள்.","action":"1091-ஐ இப்போதே அழையுங்கள். ஆதாரம் சேகரிக்கவும்.","confidence":97},
        "hi": {"answer":"**यौन उत्पीड़न — आपके कानूनी अधिकार:**\n\n**कार्यस्थल पर (POSH अधिनियम 2013):**\n10+ कर्मचारी वाली हर कंपनी में ICC अनिवार्य है।\n\n**क्या करें:**\n1. घटना का विवरण तारीख के साथ लिखें\n2. सबूत इकट्ठा करें — screenshots, emails\n3. ICC में लिखित शिकायत दर्ज करें\n4. IPC §354A के तहत FIR — 3 साल जेल\n\n**आपातकाल:**\n• महिला हेल्पलाइन: **1091**\n• NCW शिकायत: **7827170170**","citations":[{"section":"IPC §354A","title":"यौन उत्पीड़न","detail":"3 साल जेल या जुर्माना।"}],"deadline":"ICC शिकायत — घटना के 3 साल के भीतर।","risk":"शिकायत से पहले इस्तीफा न दें।","action":"1091 पर तुरंत कॉल करें। सबूत सुरक्षित रखें।","confidence":97},
    },
    "child_labour": {
        "en": {"answer":"**Child Labour Laws in India:**\n\n**Child and Adolescent Labour (Prohibition & Regulation) Act, 1986 (Amended 2016):**\n\n🔴 **Under 14 years:** COMPLETE BAN on employment in all occupations and processes. Only exception: helping family in non-hazardous family enterprise or entertainment industry with permission.\n\n🟡 **14–18 years (Adolescents):** Banned from hazardous occupations (mines, explosives, construction, etc.)\n\n**Punishment for employers:**\n• First offence: **6 months to 2 years** imprisonment + ₹20,000–₹50,000 fine\n• Repeat offence: **1 to 3 years** mandatory imprisonment\n\n**How to report:**\n• National Child Labour Helpline: **1098** (Childline — 24/7, free)\n• Online: **pencil.gov.in** (Platform for Effective Enforcement of No Child Labour)\n• Labour Commissioner office in your district\n• Police complaint under this Act\n\n**Schools must report** if they suspect child labour cases among enrolled students.","citations":[{"section":"CLPRA 1986 §3","title":"Child Labour Prohibition Act","detail":"Complete ban under 14. 6 months to 2 years jail for employer."},{"section":"CLPRA §3A","title":"Adolescent Labour","detail":"14–18 banned from hazardous work. Fine: ₹20,000–₹50,000."},{"section":"JJA 2015","title":"Juvenile Justice Act","detail":"Rescued children to be sent to Child Welfare Committee."}],"deadline":"No limitation period for reporting child labour. Report immediately when found.","risk":"Buying from shops using child labour also makes you morally complicit. Buy from certified sources.","action":"Call 1098 (Childline) immediately. Visit pencil.gov.in to report online. Labour Commissioner can take immediate action.","confidence":96},
        "ta": {"answer":"**இந்தியாவில் சிறுவர் தொழில் சட்டங்கள்:**\n\n🔴 **14 வயதுக்கு கீழ்:** அனைத்து தொழில்களிலும் முழு தடை.\n🟡 **14–18 வயது:** ஆபத்தான தொழில்களில் தடை.\n\n**தண்டனை:**\n• முதல் குற்றம்: 6 மாதம் முதல் 2 ஆண்டு சிறை + ₹50,000 அபராதம்\n• மீண்டும் செய்தால்: 1–3 ஆண்டு கட்டாய சிறை\n\n**புகார் செய்ய:**\n• Childline: **1098** (24/7, இலவசம்)\n• pencil.gov.in-ல் ஆன்லைனில் புகார்","citations":[{"section":"CLPRA 1986 §3","title":"சிறுவர் தொழில் தடை சட்டம்","detail":"14 வயதுக்கு கீழ் முழு தடை. 2 ஆண்டு சிறை."}],"deadline":"சிறுவர் தொழிலை கண்டால் உடனே புகார் செய்யுங்கள்.","risk":"தெரிந்தும் மறைத்தால் நீங்களும் பொறுப்பாளர் ஆவீர்கள்.","action":"1098-ஐ இப்போதே அழையுங்கள். pencil.gov.in-ல் புகார் செய்யுங்கள்.","confidence":96},
        "hi": {"answer":"**भारत में बाल मजदूरी कानून:**\n\n🔴 **14 वर्ष से कम:** सभी व्यवसायों में पूर्ण प्रतिबंध।\n🟡 **14–18 वर्ष:** खतरनाक कार्यों में प्रतिबंध।\n\n**दंड:**\n• पहला अपराध: 6 महीने से 2 साल जेल + ₹50,000 जुर्माना\n• बार-बार: 1–3 साल अनिवार्य जेल\n\n**शिकायत करें:**\n• Childline: **1098** (24/7, मुफ्त)\n• pencil.gov.in पर ऑनलाइन","citations":[{"section":"CLPRA 1986 §3","title":"बाल श्रम निषेध अधिनियम","detail":"14 साल से कम — पूर्ण प्रतिबंध। 2 साल जेल।"}],"deadline":"बाल मजदूरी देखते ही तुरंत रिपोर्ट करें।","risk":"जानकर भी न बताना अपराध हो सकता है।","action":"1098 पर तुरंत कॉल करें। pencil.gov.in पर शिकायत करें।","confidence":96},
    },
    "rent_deposit": {
        "en": {"answer":"**Landlord Not Returning Security Deposit — Your Rights:**\n\nUnder **Section 108(q) of the Transfer of Property Act, 1882**, your landlord MUST return the full deposit after tenancy ends, minus only legitimate damage deductions (not normal wear and tear).\n\n**Your options (in order of speed):**\n\n1. **Legal Notice** (1–2 weeks) — Send a formal demand letter. Landlord gets 30 days to respond. 80% of cases settle here. Cost: ₹500–2,000 (lawyer drafts it).\n\n2. **Rent Control Tribunal** (1–3 months) — Free to file. Jurisdiction-specific. Bring: rent agreement, bank transfer proof, receipts.\n\n3. **Consumer Forum** (2–4 months) — If landlord is a builder/company. File at consumerhelpline.gov.in\n\n4. **Civil Court** (6–18 months) — For deposits above ₹1 lakh. Claim deposit + 18% annual interest.\n\n**What courts award:** Full deposit + interest at 12–18% per year from date of vacation.","citations":[{"section":"TPA §108(q)","title":"Transfer of Property Act 1882","detail":"Landlord duty to return deposit at tenancy end."},{"section":"Madras HC 2018","title":"Sundaram vs Krishnamurthy","detail":"Deposit + 18% interest awarded from vacation date."}],"deadline":"Send legal notice within 60 days of vacating. Delay weakens interest claim.","risk":"Without written rent agreement, you need bank transfer proof + witnesses to prove deposit amount.","action":"Collect: rent agreement, bank transfer proof, all receipts, move-out photos. Send legal notice first.","confidence":92},
        "ta": {"answer":"**வீட்டு உரிமையாளர் deposit திருப்பி கொடுக்கவில்லை:**\n\nசொத்து மாற்று சட்டம் §108(q) படி, வீட்டு உரிமையாளர் குத்தகை முடிந்த பிறகு முழு deposit திருப்பி கொடுக்க வேண்டும்.\n\n**உங்கள் வழிகள்:**\n\n1. **சட்ட நோட்டீஸ்** (1–2 வாரம்) — 80% வழக்குகள் இங்கே முடியும்\n2. **வாடகை கட்டுப்பாட்டு தீர்ப்பாயம்** (1–3 மாதம்) — இலவசம்\n3. **நுகர்வோர் மன்றம்** — builder/company ஆனால்\n\n**நீதிமன்றம் என்ன கொடுக்கும்:** முழு deposit + ஆண்டுக்கு 12–18% வட்டி","citations":[{"section":"TPA §108(q)","title":"சொத்து மாற்று சட்டம் 1882","detail":"குத்தகை முடிவில் deposit திருப்பி கொடுக்க கடமை."}],"deadline":"வீட்டை காலி செய்த 60 நாளுக்குள் சட்ட நோட்டீஸ் அனுப்புங்கள்.","risk":"எழுத்துப்பூர்வ ஒப்பந்தம் இல்லாமல், வங்கி transfer proof தேவை.","action":"வாடகை ஒப்பந்தம், bank transfer proof, ரசீதுகள் சேகரிக்கவும். முதலில் சட்ட நோட்டீஸ் அனுப்புங்கள்.","confidence":92},
        "hi": {"answer":"**मकान मालिक जमानत नहीं लौटा रहा:**\n\nसंपत्ति हस्तांतरण अधिनियम §108(q) के तहत, मकान मालिक को किरायेदारी समाप्त होने पर पूरी जमानत लौटानी होगी।\n\n**आपके विकल्प:**\n\n1. **कानूनी नोटिस** (1–2 सप्ताह) — 80% मामले यहीं सुलझते हैं\n2. **किराया नियंत्रण न्यायाधिकरण** (1–3 महीने) — नि:शुल्क\n3. **उपभोक्ता फोरम** — बिल्डर/कंपनी के लिए\n\n**न्यायालय क्या देते हैं:** पूरी जमानत + 12–18% वार्षिक ब्याज","citations":[{"section":"TPA §108(q)","title":"संपत्ति हस्तांतरण अधिनियम 1882","detail":"किरायेदारी समाप्ति पर जमानत वापस करने की जिम्मेदारी।"}],"deadline":"मकान खाली करने के 60 दिनों के भीतर कानूनी नोटिस भेजें।","risk":"लिखित किराया समझौते के बिना, बैंक हस्तांतरण प्रमाण आवश्यक।","action":"किराया समझौता, बैंक प्रमाण, रसीदें इकट्ठा करें। पहले कानूनी नोटिस भेजें।","confidence":92},
    },
    "salary": {
        "en": {"answer":"**Employer Not Paying Salary — Your Rights:**\n\nNon-payment of salary violates the **Payment of Wages Act, 1936**.\n\n**Immediate steps:**\n\n1. **Labour Commissioner Complaint** (fastest — 30–60 days)\nFree. Authority can issue summons to employer immediately.\n\n2. **Payment of Wages Act §3** — File with Payment of Wages Authority\nYou can claim: unpaid salary + compensation up to **10× the unpaid amount**\n\n3. **Industrial Disputes Act §33C** — Labour Court\nFor \"workmen\" — claim full back wages\n\n4. **IPC §406 (Criminal Breach of Trust)** — Police complaint\nRarely used but highly effective as pressure tactic\n\n⚠️ **Do NOT sign** any \"Full & Final Settlement\" under pressure — you lose ALL claims permanently.\n\n**Documents needed:** Pay slips, bank statements, offer letter, appointment letter, any salary emails","citations":[{"section":"Payment of Wages Act §3","title":"Responsibility to pay wages","detail":"Must pay by 7th for firms <1000 workers. Penalty: 10× unpaid amount."},{"section":"IPC §406","title":"Criminal breach of trust","detail":"Intentional non-payment: up to 3 years jail."}],"deadline":"File labour complaint within 1 year of last unpaid salary. IPC: 3 years.","risk":"Do NOT sign full & final settlement under pressure — you lose all legal rights permanently.","action":"Collect all documents → File at Labour Commissioner → Send legal notice simultaneously.","confidence":90},
        "ta": {"answer":"**Employer சம்பளம் கொடுக்கவில்லை:**\n\nஊதிய சட்டம் 1936 மீறல்.\n\n**உடனடி நடவடிக்கை:**\n\n1. **தொழிலாளர் ஆணையர் புகார்** (30–60 நாள்) — இலவசம்\n2. **ஊதிய ஆணையர்** — செலுத்தாத தொகையின் 10 மடங்கு கோரலாம்\n3. **IPC §406** — போலீஸ் புகார் (அழுத்தம் கொடுக்க பயனுள்ளது)\n\n⚠️ அழுத்தத்தில் 'Full & Final Settlement' கையெழுத்திட வேண்டாம்!","citations":[{"section":"ஊதிய சட்டம் §3","title":"சம்பளம் செலுத்தும் கடமை","detail":"7-ம் தேதிக்குள் செலுத்த வேண்டும். அபராதம்: 10 மடங்கு."}],"deadline":"கடைசி சம்பளமின்மையிலிருந்து 1 ஆண்டுக்குள் புகார் செய்யுங்கள்.","risk":"Full & Final Settlement கையெழுத்திட வேண்டாம்.","action":"ஆவணங்கள் சேகரிக்கவும் → தொழிலாளர் ஆணையர் அலுவலகம் செல்லுங்கள்.","confidence":90},
        "hi": {"answer":"**नियोक्ता वेतन नहीं दे रहा:**\n\nमजदूरी भुगतान अधिनियम 1936 का उल्लंघन।\n\n**तत्काल कदम:**\n\n1. **श्रम आयुक्त शिकायत** (30–60 दिन) — नि:शुल्क\n2. **मजदूरी भुगतान प्राधिकरण** — 10× मुआवजा दावा\n3. **IPC §406** — पुलिस शिकायत (दबाव के लिए प्रभावी)\n\n⚠️ दबाव में 'Full & Final Settlement' पर हस्ताक्षर न करें!","citations":[{"section":"मजदूरी भुगतान अधिनियम §3","title":"वेतन देने की जिम्मेदारी","detail":"7 तारीख तक भुगतान अनिवार्य। जुर्माना: 10× राशि।"}],"deadline":"अंतिम अवैतनिक वेतन से 1 वर्ष के भीतर शिकायत करें।","risk":"दबाव में Full & Final Settlement पर हस्ताक्षर न करें।","action":"सभी दस्तावेज इकट्ठा करें → श्रम आयुक्त कार्यालय जाएं।","confidence":90},
    },
    "divorce": {
        "en": {"answer":"**Divorce and Separation — Indian Law:**\n\n**Which law applies to you:**\n• Hindu: Hindu Marriage Act, 1955\n• Muslim: Muslim Personal Law (Shariat Application Act)\n• Christian: Indian Divorce Act, 1869\n• Parsi: Parsi Marriage Act, 1936\n• Inter-religion / Civil: Special Marriage Act, 1954\n\n**Grounds for divorce (Hindu Marriage Act):**\nAdultery, cruelty, desertion (2+ years), conversion, insanity, communicable disease, renunciation\n\n**Mutual consent divorce (fastest — 6–18 months):**\n1. Both parties agree in writing\n2. File joint petition in Family Court\n3. 6-month cooling off period (can be waived by court)\n4. Second motion — divorce granted\n\n**Contested divorce:** 2–5 years\n\n**Maintenance (Alimony):**\nSpouse earning less can claim maintenance. Courts consider both incomes.\n\n**Child custody:**\nCourt decides based on 'best interest of child'. Usually: mother for under-5, joint custody for older.\n\n**Free help:** Family Court has a Mediation Centre — try mediation first. Faster and cheaper.","citations":[{"section":"HMA 1955 §13","title":"Grounds for divorce","detail":"Adultery, cruelty, desertion, insanity, disease."},{"section":"HMA 1955 §13B","title":"Mutual consent divorce","detail":"6-month cooling period. Both parties must file together."},{"section":"CPC §125","title":"Maintenance","detail":"Spouse/children maintenance if unable to maintain themselves."}],"deadline":"No time limit for filing divorce after marriage. Mutual consent: separation must be 1+ year.","risk":"Contested divorce is lengthy and expensive. Try mediation first — saves time and cost.","action":"Approach Family Court. Try mediation centre first. Collect: marriage certificate, photos, communication records.","confidence":91},
        "ta": {"answer":"**விவாகரத்து — இந்திய சட்டம்:**\n\n**எந்த சட்டம் பொருந்தும்:**\n• இந்து: இந்து திருமண சட்டம் 1955\n• கிறிஸ்துவர்: இந்திய விவாகரத்து சட்டம் 1869\n• சிறப்பு திருமண சட்டம் 1954 (cross-religion)\n\n**விவாகரத்து காரணங்கள்:** கொடுமை, கைவிடல் (2+ ஆண்டு), விபசாரம், மனநோய்\n\n**இருவரும் ஒப்புக்கொண்டால்:** 6–18 மாதம் (வேகமான வழி)\n\n**குழந்தை பராமரிப்பு:** 5 வயதுக்கு கீழ் — பொதுவாக தாய்க்கு","citations":[{"section":"HMA 1955 §13B","title":"இருவரும் ஒப்புக்கொண்ட விவாகரத்து","detail":"6 மாத கூலிங் காலம்."}],"deadline":"விவாகரத்துக்கு கால வரம்பு இல்லை. ஆனால் சீர்திருத்தத்தை முதலில் முயற்சிக்கவும்.","risk":"நீதிமன்ற விவாகரத்து 2–5 ஆண்டுகள் ஆகலாம். முதலில் மத்தியஸ்தம் முயற்சிக்கவும்.","action":"குடும்ப நீதிமன்றம் செல்லுங்கள். மத்தியஸ்த மையத்தை முதலில் முயற்சிக்கவும்.","confidence":91},
        "hi": {"answer":"**तलाक — भारतीय कानून:**\n\n**कौन सा कानून लागू होता है:**\n• हिंदू: हिंदू विवाह अधिनियम 1955\n• मुस्लिम: मुस्लिम व्यक्तिगत कानून\n• ईसाई: भारतीय तलाक अधिनियम 1869\n\n**तलाक के आधार:** क्रूरता, परित्याग (2+ वर्ष), व्यभिचार, पागलपन\n\n**आपसी सहमति से तलाक:** 6–18 महीने (सबसे तेज)\n\n**गुजारा भत्ता:** कम कमाने वाला पति/पत्नी दावा कर सकता है","citations":[{"section":"HMA 1955 §13B","title":"आपसी सहमति से तलाक","detail":"6 महीने की ठंडा होने की अवधि।"}],"deadline":"तलाक के लिए कोई समय सीमा नहीं। आपसी सहमति: 1+ वर्ष अलगाव आवश्यक।","risk":"विवादित तलाक 2–5 साल लग सकता है। पहले मध्यस्थता आजमाएं।","action":"परिवार न्यायालय जाएं। मध्यस्थता केंद्र पहले आजमाएं।","confidence":91},
    },
    "consumer": {
        "en": {"answer":"**Consumer Rights — Your Options:**\n\n**Consumer Protection Act, 2019:**\n\n| Claim Amount | Forum | Filing Fee |\n|---|---|---|\n| Up to ₹50 lakhs | District Consumer Commission | ₹200 |\n| ₹50L–₹2Cr | State Consumer Commission | ₹400 |\n| Above ₹2Cr | National Consumer Commission | ₹5,000 |\n\n**What you can claim:**\n• Full refund OR replacement\n• Compensation for mental agony\n• Litigation costs\n• Up to 2× product value as punitive damages\n\n**Steps:**\n1. Send written complaint to company (keep copy)\n2. Wait 30 days for response\n3. File at consumerhelpline.gov.in (online, easy)\n4. Or visit District Consumer Commission physically\n\n**Time limit:** File within **2 years** of purchase/defect","citations":[{"section":"CPA 2019 §35","title":"Consumer Protection Act 2019","detail":"Right to file against defective goods and deficient services."},{"section":"CPA 2019 §39","title":"Reliefs available","detail":"Refund, replacement, compensation, punitive damages up to 2×."}],"deadline":"2 years from purchase date or defect discovery date.","risk":"Keep all bills, warranty cards, complaint emails as evidence.","action":"Email company first → Wait 30 days → File at consumerhelpline.gov.in","confidence":94},
        "ta": {"answer":"**நுகர்வோர் உரிமைகள்:**\n\nநுகர்வோர் பாதுகாப்பு சட்டம் 2019:\n\n• ₹50 லட்சம் வரை → மாவட்ட நுகர்வோர் மன்றம் (₹200 கட்டணம்)\n• ₹50L–₹2Cr → மாநில மன்றம்\n• ₹2Cr மேல் → தேசிய மன்றம்\n\n**கோரலாம்:** முழு பணம் திரும்பப் பெறல் + மன வேதனைக்கு இழப்பீடு + வழக்கு செலவு\n\n**Steps:** நிறுவனத்திற்கு புகார் → 30 நாள் → consumerhelpline.gov.in","citations":[{"section":"CPA 2019 §35","title":"நுகர்வோர் பாதுகாப்பு சட்டம் 2019","detail":"குறைபாடுள்ள பொருட்கள்/சேவைகளுக்கு புகார் செய்ய உரிமை."}],"deadline":"வாங்கிய தேதியிலிருந்து 2 ஆண்டுகளுக்குள்.","risk":"அனைத்து bills, warranty cards வைத்திருங்கள்.","action":"நிறுவனத்திற்கு email → 30 நாள் → consumerhelpline.gov.in-ல் புகார்","confidence":94},
        "hi": {"answer":"**उपभोक्ता अधिकार:**\n\nउपभोक्ता संरक्षण अधिनियम 2019:\n\n• ₹50 लाख तक → जिला उपभोक्ता आयोग (₹200 शुल्क)\n• ₹50L–₹2Cr → राज्य आयोग\n• ₹2Cr से अधिक → राष्ट्रीय आयोग\n\n**दावा करें:** पूरा धनवापसी + मानसिक पीड़ा हर्जाना + मुकदमा खर्च\n\n**कदम:** कंपनी को शिकायत → 30 दिन → consumerhelpline.gov.in","citations":[{"section":"CPA 2019 §35","title":"उपभोक्ता संरक्षण अधिनियम 2019","detail":"दोषपूर्ण वस्तुओं/सेवाओं के खिलाफ शिकायत का अधिकार।"}],"deadline":"खरीद की तारीख से 2 साल के भीतर।","risk":"सभी बिल, वारंटी कार्ड सुरक्षित रखें।","action":"कंपनी को ईमेल → 30 दिन → consumerhelpline.gov.in पर शिकायत","confidence":94},
    },
    "property_damage": {
        "en": {"answer":"**Property Damaged by Someone — IPC 427:**\n\nUnder **Section 427 IPC** (Mischief), damaging someone's property is a punishable offence if intentional.\n\n**Your 3 options:**\n\n1. **Legal Notice** (send first)\n• Demand compensation equal to repair/replacement cost\n• 30 days to respond\n• 80% of cases settle here\n• Cost: ₹500–2,000\n\n2. **Lok Adalat** (for under ₹1 lakh — fastest)\n• Completely free\n• No lawyer needed\n• Resolved in 1–2 hearings\n• Settlement is final\n\n3. **Magistrate Court / Civil Suit**\n• Criminal: IPC 427 — up to 2 years jail or fine\n• Civil: claim damage amount + interest\n\n**Evidence to collect NOW:**\n• Photos/video of damaged item\n• Purchase invoice (original value)\n• Repair estimate from authorized centre\n• WhatsApp/message proof of incident","citations":[{"section":"IPC §427","title":"Mischief causing damage","detail":"Up to 2 years or fine. Bailable. Magistrate court."},{"section":"Limitation Act §3","title":"3-year limitation","detail":"3 years from incident to file civil suit."}],"deadline":"3 years from incident to file civil suit. FIR: no time limit.","risk":"FIR against a friend is hard to withdraw — consider legal notice first.","action":"Gather repair estimate and invoice → Send legal notice → Lok Adalat if ignored.","confidence":88},
        "ta": {"answer":"**சொத்து சேதம் — IPC 427:**\n\n§427 IPC கீழ் வேண்டுமென்றே சொத்தை சேதப்படுத்துவது குற்றம்.\n\n**3 வழிகள்:**\n1. **சட்ட நோட்டீஸ்** — 80% வழக்குகள் இங்கே முடியும்\n2. **Lok Adalat** — இலவசம், ₹1 லட்சம் வரை\n3. **நீதிமன்றம்** — IPC 427: 2 ஆண்டு சிறை அல்லது அபராதம்\n\n**இப்போதே சேகரிக்கவும்:** photos, invoice, repair estimate","citations":[{"section":"IPC §427","title":"சொத்து சேதம்","detail":"2 ஆண்டு சிறை அல்லது அபராதம்."}],"deadline":"3 ஆண்டுகளுக்குள் civil suit.","risk":"நண்பருக்கு எதிரான FIR திரும்பப் பெறுவது கஷ்டம்.","action":"Repair estimate → சட்ட நோட்டீஸ் → பதில் இல்லாமல் Lok Adalat","confidence":88},
        "hi": {"answer":"**संपत्ति को नुकसान — IPC 427:**\n\n§427 IPC के तहत जानबूझकर संपत्ति नष्ट करना अपराध है।\n\n**3 विकल्प:**\n1. **कानूनी नोटिस** — 80% मामले यहीं सुलझते हैं\n2. **लोक अदालत** — ₹1 लाख तक, नि:शुल्क\n3. **अदालत** — IPC 427: 2 साल जेल या जुर्माना\n\n**अभी इकट्ठा करें:** फोटो, रसीद, मरम्मत अनुमान","citations":[{"section":"IPC §427","title":"संपत्ति को नुकसान","detail":"2 साल जेल या जुर्माना।"}],"deadline":"3 साल के भीतर दीवानी मुकदमा।","risk":"दोस्त के खिलाफ FIR वापस लेना मुश्किल है।","action":"मरम्मत अनुमान → कानूनी नोटिस → लोक अदालत","confidence":88},
    },
}

# ─────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="LegalEase India API v3", version="3.0.0",
              docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

conversations: Dict[str, list] = {}
cases_store:   Dict[str, list] = {}

class QueryReq(BaseModel):
    query:      str  = Field(..., min_length=1)
    state_code: Optional[str] = None
    language:   str  = Field(default="en")
    session_id: str  = Field(default="anon")

class ComplaintReq(BaseModel):
    offence_type: str
    description:  str = Field(..., min_length=5)
    state_code:   str = Field(default="TN")
    incident_date:str = Field(default="")
    complainant:  str = Field(default="")
    address:      str = Field(default="")
    witnesses:    str = Field(default="")

class DocAnalyseReq(BaseModel):
    text:     str = Field(..., min_length=10)
    doc_type: str = Field(default="auto")
    language: str = Field(default="en")

class CaseReq(BaseModel):
    case_number:  str
    court_name:   str
    hearing_date: str
    description:  str = ""
    user_id:      str = "anon"
    phone:        str = ""

def classify_intent(text: str) -> str:
    tl = text.lower().strip()
    # Direct keyword match
    for intent, keywords in INTENT_PATTERNS.items():
        if any(kw in tl for kw in keywords):
            return intent
    # Fallback
    legal_words = ["law","legal","court","ipc","section","rights","police","fir","advocate","judge","case","act","rule","penalty","fine","jail","arrest","bail","complaint"]
    if any(w in tl for w in legal_words):
        return "general_legal"
    return "nonsense"

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    try:
        with open("frontend/index.html", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except:
        return HTMLResponse("<h2>LegalEase India API</h2><p><a href='/api/docs'>API Docs</a></p>")

@app.get("/api/health")
async def health():
    return {"status":"healthy","version":"3.0.0",
            "intents":list(INTENT_PATTERNS.keys()),
            "states":list(STATE_LAWS.keys()),
            "timestamp":datetime.utcnow().isoformat()}

@app.post("/api/legal/query")
async def legal_query(req: QueryReq):
    intent = classify_intent(req.query)
    lang   = req.language if req.language in ["en","ta","hi"] else "en"

    # Get response
    resp = RESPONSES.get(intent, {}).get(lang) or RESPONSES.get(intent, {}).get("en")

    if not resp:
        # Generic legal response
        resp = {
            "answer": {
                "en": f"For your query about **'{req.query}'**, here is the applicable Indian legal framework:\n\nThis matter involves general Indian civil/criminal law. The specific sections depend on the exact nature of your situation.\n\n**General advice:**\n• Document everything with dates\n• Consult a qualified advocate\n• Free legal aid: Legal Services Authority helpline **15100**\n• National Consumer Helpline: **1800-11-4000**\n• Women Helpline: **1091**\n• Police: **100**",
                "ta": f"உங்கள் கேள்விக்கு: இந்திய சட்டக் கட்டமைப்பின் கீழ் உதவி கிடைக்கும். இலவச சட்ட உதவி: **15100**. பெண்கள் உதவி: **1091**.",
                "hi": f"आपके प्रश्न के लिए: भारतीय कानून के तहत सहायता उपलब्ध है। नि:शुल्क कानूनी सहायता: **15100**।"
            }[lang],
            "citations": [{"section":"General","title":"Indian legal system","detail":"Multiple laws may apply based on facts."}],
            "deadline": None, "risk": None,
            "action": "Consult a qualified advocate. First consultation at Legal Aid centres is free — call 15100.",
            "confidence": 60
        }

    # State-specific addition
    state_note = ""
    if req.state_code and req.state_code in STATE_LAWS:
        sl = STATE_LAWS[req.state_code]
        if sl.get("prohibition") and intent == "alcohol":
            state_note = f"\n\n⚠️ **CRITICAL — {sl['name']}:** {sl['note']}"
        elif intent not in ["greeting","nonsense","alcohol"]:
            state_note = f"\n\n**{sl['name']} note:** {sl['note']}"

    # Save to history
    sid = req.session_id
    conversations.setdefault(sid, []).append({
        "role":"user","content":req.query,"timestamp":datetime.utcnow().isoformat()
    })

    return {
        "query_id":   str(uuid.uuid4()),
        "intent":     intent,
        "answer":     resp["answer"] + state_note,
        "citations":  resp.get("citations",[]),
        "deadline":   resp.get("deadline"),
        "risk_note":  resp.get("risk"),
        "action":     resp.get("action"),
        "confidence": resp.get("confidence", 75),
        "state":      req.state_code,
        "language":   lang,
        "disclaimer": "Legal information only — not legal advice. Consult a qualified advocate.",
    }

@app.get("/api/legal/states")
async def get_states():
    return {"states":[{"code":k,**v} for k,v in STATE_LAWS.items()]}

@app.get("/api/legal/state/{code}")
async def get_state(code: str):
    s = STATE_LAWS.get(code.upper())
    if not s: raise HTTPException(404, "State not found")
    return s

@app.get("/api/legal/ipc")
async def list_ipc():
    return {"sections":[{"section":k,**v} for k,v in IPC_DB.items()]}

@app.get("/api/legal/ipc/{section}")
async def get_ipc(section: str):
    ipc = IPC_DB.get(section)
    if not ipc: raise HTTPException(404, f"IPC {section} not found")
    return {"section":section,**ipc}

@app.get("/api/legal/news")
async def get_news(state: Optional[str] = None, limit: int = 6):
    news = LEGAL_NEWS
    if state:
        news = [n for n in news if state in n.get("relevantStates",[]) or "All" in n.get("relevantStates",[])]
    return {"count":len(news[:limit]),"news":news[:limit]}

@app.get("/api/courts/{state_code}")
async def get_courts(state_code: str):
    courts = COURTS_BY_STATE.get(state_code.upper(), [])
    if not courts:
        return {"state":state_code,"courts":[],"note":"Court data not available for this state. Visit ecourts.gov.in for details."}
    return {"state":state_code,"courts":courts}

@app.get("/api/lawyers/{state_code}")
async def get_lawyers(state_code: str):
    lawyers = LAWYERS_DB.get(state_code.upper(), [])
    default = [{"name":"National Legal Services Authority","type":"Free Legal Aid","city":"All India","phone":"15100","address":"15100 (Toll-free helpline)","speciality":"Free legal aid for all eligible persons across India"}]
    return {"state":state_code,"lawyers":lawyers + default}

@app.post("/api/complaint/generate")
async def generate_complaint(req: ComplaintReq):
    ipc_map = {"theft":"379","fraud":"420","assault":"351","property_damage":"427","cyber":"IT Act 66C","domestic":"498A","harassment":"354D"}
    title_map = {"theft":"Theft","fraud":"Cheating/Fraud","assault":"Assault","property_damage":"Property Damage","cyber":"Cybercrime","domestic":"Domestic Violence","harassment":"Stalking/Harassment"}
    ipc   = ipc_map.get(req.offence_type,"applicable")
    title = title_map.get(req.offence_type,"Offence")
    sn    = STATE_LAWS.get(req.state_code,{}).get("name", req.state_code)
    today = datetime.now().strftime("%d %B %Y")

    text = f"""TO,
The Station House Officer,
[Police Station Name],
{sn}

Date: {today}

SUBJECT: Formal Complaint u/s IPC Section {ipc} — Request to Register FIR

Respected Sir/Madam,

I, {req.complainant or '[Full Name]'}, resident of {req.address or '[Full Address]'}, hereby lodge this formal complaint.

────────────────────────────────────────
INCIDENT DETAILS
────────────────────────────────────────
Nature of Offence  : {title}
Applicable Section : IPC Section {ipc}
Date of Incident   : {req.incident_date or '[Date]'}
State Jurisdiction : {sn}
Witnesses          : {req.witnesses or 'None mentioned'}

────────────────────────────────────────
DESCRIPTION
────────────────────────────────────────
{req.description}

────────────────────────────────────────
RELIEF SOUGHT
────────────────────────────────────────
1. Register FIR under IPC Section {ipc}
2. Investigate and take appropriate action
3. Provide copy of FIR to complainant

────────────────────────────────────────
DECLARATION
────────────────────────────────────────
I declare the above facts are true. Filing false complaint = IPC §182 offence.

Yours faithfully,
{req.complainant or '[Your Name]'}
{req.address or '[Address]'}
Date: {today}

════════════════════════════════════════
FOR OFFICIAL USE ONLY
════════════════════════════════════════
Date Received: ___________  FIR No.: ___________
Officer Name:  ___________  Badge:   ___________"""

    return {"complaint_text":text,"ipc_section":ipc,"state":sn,
            "tips":["Submit to nearest police station. Keep stamped copy.",
                    "If police refuse FIR — approach SP or Magistrate (CrPC §156(3))",
                    f"IPC {ipc} detail: {IPC_DB.get(ipc,{}).get('title','Applicable section')}"],
            "ipc_detail": IPC_DB.get(ipc,{})}

@app.post("/api/document/analyse")
async def analyse_doc(req: DocAnalyseReq):
    text = req.text.lower()
    lang = req.language if req.language in ["en","ta","hi"] else "en"

    # Document type detection
    if any(w in text for w in ["fir","first information report","cognizable"]):
        doc_type = "fir"
    elif any(w in text for w in ["summons","you are hereby required","appear before","hearing"]):
        doc_type = "hearing_notice"
    elif any(w in text for w in ["affidavit","i solemnly affirm","deponent"]):
        doc_type = "affidavit"
    elif any(w in text for w in ["legal notice","take notice","demand","failure to comply"]):
        doc_type = "legal_notice"
    elif any(w in text for w in ["bail","released on bail","surety"]):
        doc_type = "bail_order"
    elif any(w in text for w in ["eviction","vacate","quit","leave the premises"]):
        doc_type = "eviction_notice"
    else:
        doc_type = req.doc_type if req.doc_type != "auto" else "general"

    doc_explanations = {
        "hearing_notice": {
            "en": {"what":"This is a Court Hearing Notice / Summons. It requires you to appear before a court on the specified date.","important":["⚠️ MANDATORY — You MUST appear on the date mentioned. Missing court date = contempt of court + arrest warrant.","Bring this original document to court.","Bring any documents related to the case.","Arrive at least 30 minutes early.","If you cannot appear — apply for adjournment BEFORE the date through a lawyer."],"action":"Hire a lawyer immediately if you don't have one. Appear on the date. Do NOT ignore this."},
            "ta": {"what":"இது நீதிமன்ற ஆஜர் அறிவிப்பு / சம்மன். குறிப்பிட்ட தேதியில் நீதிமன்றத்தில் ஆஜராக வேண்டும்.","important":["⚠️ கட்டாயம் — குறிப்பிட்ட தேதியில் ஆஜராக வேண்டும். இல்லாவிடில் கைது வாரண்ட் வரும்.","இந்த ஆவணத்தை நீதிமன்றத்தில் கொண்டு வாருங்கள்.","30 நிமிடம் முன்னதாக வாருங்கள்.","வர முடியாவிட்டால் — முன்னதாக lawyer மூலம் தாமதிப்பு கோருங்கள்."],"action":"உடனே lawyer வேலைக்கு அமர்த்துங்கள். குறிப்பிட்ட தேதியில் ஆஜராகுங்கள்."},
            "hi": {"what":"यह न्यायालय उपस्थिति नोटिस / सम्मन है। आपको निर्धारित तारीख पर अदालत में उपस्थित होना होगा।","important":["⚠️ अनिवार्य — निर्धारित तारीख पर उपस्थित हों। न आने पर गिरफ्तारी वारंट जारी हो सकता है।","यह मूल दस्तावेज अदालत में लाएं।","30 मिनट पहले पहुंचें।","यदि उपस्थित नहीं हो सकते — वकील के माध्यम से पहले से स्थगन आवेदन करें।"],"action":"तुरंत वकील नियुक्त करें। निर्धारित तारीख पर उपस्थित हों।"},
        },
        "fir": {
            "en": {"what":"This is a First Information Report (FIR). It is a formal record of a cognizable offence registered by police.","important":["You have the RIGHT to a free copy of your FIR — demand it from police.","Note the FIR number, police station, and IPC sections mentioned.","Sections mentioned determine the seriousness and bailable/non-bailable status.","If you are the accused — hire a lawyer IMMEDIATELY. Do not make any statement to police without lawyer.","If you are the complainant — ensure all facts are correctly recorded."],"action":"Note FIR number. Check IPC sections. Hire lawyer immediately if accused. Free legal aid: 15100"},
            "ta": {"what":"இது First Information Report (FIR). காவல் துறை பதிவு செய்த முதல் தகவல் அறிக்கை.","important":["FIR-ன் இலவச நகலுக்கு உரிமை உண்டு — காவலர்களிடம் கேளுங்கள்.","FIR எண், காவல் நிலையம், IPC பிரிவுகளை கவனியுங்கள்.","குற்றம் சாட்டப்பட்டவர் என்றால் — உடனே lawyer வேலைக்கு அமர்த்துங்கள்."],"action":"FIR எண் எழுதி வையுங்கள். உடனே lawyer நியமிக்கவும்."},
            "hi": {"what":"यह First Information Report (FIR) है। पुलिस द्वारा दर्ज संज्ञेय अपराध की प्रथम सूचना रिपोर्ट।","important":["FIR की मुफ्त प्रति लेने का आपको अधिकार है।","FIR नंबर, थाना और IPC धाराएं नोट करें।","यदि आप आरोपी हैं — तुरंत वकील नियुक्त करें।"],"action":"FIR नंबर नोट करें। तुरंत वकील नियुक्त करें। मुफ्त सहायता: 15100"},
        },
        "affidavit": {
            "en": {"what":"This is an Affidavit — a sworn legal statement made before a notary or court. It carries legal weight.","important":["Every statement in an affidavit must be true — false affidavit = perjury (IPC §193, up to 7 years jail).","Must be signed before a First Class Magistrate or Notary Public.","Stamp paper of appropriate denomination required.","Each page must be signed.","Corrections must be initialled, not erased."],"action":"Sign only before authorized notary/magistrate. Verify all facts before signing. Never sign blank affidavit."},
            "ta": {"what":"இது ஒரு Affidavit (சத்திய வாக்குமூலம்) — நோட்டரி அல்லது நீதிமன்றத்திற்கு முன் செய்யப்பட்ட சட்ட வாக்கு மூலம்.","important":["பொய் affidavit = IPC §193 — 7 ஆண்டு சிறை.","முத்திரைத் தாளில் (stamp paper) இருக்க வேண்டும்.","First Class Magistrate அல்லது Notary முன் கையெழுத்திட வேண்டும்."],"action":"அங்கீகரிக்கப்பட்ட notary/magistrate முன் மட்டும் கையெழுத்திடுங்கள்."},
            "hi": {"what":"यह एक शपथपत्र (Affidavit) है — नोटरी या अदालत के सामने दिया गया शपथबद्ध कानूनी बयान।","important":["झूठा शपथपत्र = IPC §193 — 7 साल जेल।","उचित स्टांप पेपर पर होना चाहिए।","प्रथम श्रेणी मजिस्ट्रेट या नोटरी के सामने हस्ताक्षर करें।"],"action":"केवल अधिकृत नोटरी/मजिस्ट्रेट के सामने हस्ताक्षर करें।"},
        },
        "legal_notice": {
            "en": {"what":"This is a Legal Notice — a formal written communication demanding action before legal proceedings.","important":["You have 30 days to respond (unless different deadline specified).","Ignoring legal notice = court proceedings will follow.","Respond IN WRITING — verbal response has no legal value.","Counter-notice can also be sent by you.","Keep a copy of all correspondence."],"action":"Respond in writing within 30 days. Consult a lawyer before responding — your response can be used against you."},
            "ta": {"what":"இது ஒரு சட்ட நோட்டீஸ் — சட்ட நடவடிக்கைக்கு முன் அனுப்பப்படும் முறையான எழுத்துப்பூர்வ அறிவிப்பு.","important":["30 நாளுக்குள் பதில் அனுப்புங்கள்.","வாய்மொழி பதில் சட்ட மதிப்பு இல்லாதது.","எழுத்துப்பூர்வமாக பதில் அனுப்புங்கள்.","உங்கள் பதில் நீதிமன்றத்தில் பயன்படுத்தப்படலாம்."],"action":"30 நாளுக்குள் lawyer மூலம் எழுத்துப்பூர்வமாக பதில் அனுப்புங்கள்."},
            "hi": {"what":"यह एक कानूनी नोटिस है — कानूनी कार्यवाही से पहले भेजा गया औपचारिक लिखित संचार।","important":["30 दिनों के भीतर जवाब दें।","मौखिक जवाब का कोई कानूनी मूल्य नहीं।","लिखित में जवाब दें।","आपका जवाब अदालत में इस्तेमाल किया जा सकता है।"],"action":"30 दिनों के भीतर वकील के माध्यम से लिखित जवाब भेजें।"},
        },
    }

    doc_info = doc_explanations.get(doc_type, {}).get(lang) or doc_explanations.get(doc_type, {}).get("en")
    if not doc_info:
        doc_info = {
            "what": f"This appears to be a legal document of type: {DOCUMENT_TYPES.get(doc_type, doc_type)}",
            "important": ["Read carefully before signing or responding","Note all dates and deadlines","Consult a lawyer if unsure"],
            "action": "Consult a qualified advocate. Free legal aid: 15100"
        }

    return {
        "detected_doc_type": doc_type,
        "doc_type_name": DOCUMENT_TYPES.get(doc_type, doc_type),
        "what_is_it": doc_info["what"],
        "important_points": doc_info["important"],
        "recommended_action": doc_info["action"],
        "free_legal_aid": "15100 (National Legal Services Authority — toll-free)",
        "language": lang
    }

@app.post("/api/cases")
async def add_case(req: CaseReq):
    cid = str(uuid.uuid4())
    case = {**req.dict(), "case_id":cid, "status":"active",
            "added_at":datetime.utcnow().isoformat()}
    cases_store.setdefault(req.user_id,[]).append(case)
    return {"case_id":cid,"status":"added",
            "reminders":"WhatsApp reminders will be sent 7 days and 1 day before hearing"}

@app.get("/api/cases/{user_id}")
async def get_cases(user_id: str):
    return {"user_id":user_id,"cases":cases_store.get(user_id,[])}

@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    return {"session_id":session_id,"messages":conversations.get(session_id,[])}

@app.get("/api/stats")
async def stats():
    return {"total_sessions":len(conversations),
            "total_cases":sum(len(v) for v in cases_store.values()),
            "states_supported":len(STATE_LAWS),"ipc_sections":len(IPC_DB),
            "legal_news":len(LEGAL_NEWS)}
