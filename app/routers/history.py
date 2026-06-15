from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc
from app.db.database import get_db
from app.db.models import Session as ChatSession, Message
from app.schemas.chat import SessionOut, MessageOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    device_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: DBSession = Depends(get_db),
):
    q = db.query(ChatSession)
    if device_id:
        q = q.filter(ChatSession.device_id == device_id)
    return q.order_by(desc(ChatSession.updated_at)).limit(limit).all()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: str,
    db: DBSession = Depends(get_db),
):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: DBSession = Depends(get_db),
):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"status": "success"}
