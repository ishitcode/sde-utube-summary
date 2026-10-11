from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.deep_dive_service import build_deep_dive, follow_up, get_session
from app.schemas import TutorRequest, TutorResponse

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/deep-dive", response_model=TutorResponse)
def deep_dive(payload: TutorRequest) -> TutorResponse:
    result = build_deep_dive(
        topic=payload.topic,
        learning_level=payload.learning_level,
        language=payload.language,
        explanation_style=payload.explanation_style,
        transcript=[],
    )
    return TutorResponse(
        session_id=result["session_id"],
        topic=result["topic"],
        language=result["language"],
        learning_level=result["learning_level"],
        explanation=result["explanation"],
        sections=result["sections"],
        sources=result["sources"],
        evidence_sufficiency=result["evidence_sufficiency"],
        explanation_language=result["language"],
    )


@router.post("/follow-up")
def deep_dive_follow_up(session_id: str, question: str) -> dict:
    try:
        return follow_up(session_id, question)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Tutor session not found") from exc


@router.get("/sessions/{session_id}")
def get_tutor_session(session_id: str) -> dict:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Tutor session not found")
    return session


@router.get("/sessions/{session_id}/history")
def get_tutor_history(session_id: str) -> dict:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Tutor session not found")
    return {"session_id": session_id, "history": session.get("follow_ups", [])}
