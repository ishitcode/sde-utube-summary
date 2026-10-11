from __future__ import annotations

import uuid
from typing import Any

from app.services.retrieval_service import retrieve_segments


SESSION_STORE: dict[str, dict[str, Any]] = {}


def build_deep_dive(topic: str, learning_level: str, language: str, explanation_style: str, transcript: list[dict] | None = None) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    transcript_hint = retrieve_segments(topic, transcript or [], limit=3) if transcript else []
    sources = [
        {"video_id": "lecture", "start": segment.get("start", 0), "end": segment.get("end", 0), "label": segment.get("text", "")[:80]}
        for segment in transcript_hint
    ]

    if transcript_hint:
        anchor = transcript_hint[0]["text"]
        explanation = (
            f"{topic} is best understood by anchoring it in the lecture evidence. The transcript highlights: \"{anchor[:180]}\". "
            f"At the {learning_level.lower()} level, the key idea is to connect that statement to the core mechanism, then reason through examples and trade-offs. "
            f"This explanation follows a {explanation_style.lower()} approach and uses the lecture as the primary source of grounding."
        )
        evidence_sufficiency = "Strong: the lecture includes direct evidence and examples related to the topic."
    else:
        explanation = (
            f"{topic} is a foundational concept that becomes easier to understand when we break it into intuition, core mechanics, and a worked example. "
            f"At the {learning_level.lower()} level, the key idea is to connect the concept to what the lecture is explaining and then study the practical trade-offs. "
            f"This explanation follows a {explanation_style.lower()} approach and stays grounded in the lecture evidence where available."
        )
        evidence_sufficiency = "Partial: the lecture provides context and examples; additional explanation is provided as supplemental teaching material."

    sections = [
        "Concept Overview",
        "Why the Concept Matters",
        "Intuition",
        "Step-by-Step Explanation",
        "Worked Example",
        "Trade-offs",
        "Interview Questions",
    ]

    payload = {
        "session_id": session_id,
        "topic": topic,
        "learning_level": learning_level,
        "language": language,
        "explanation_style": explanation_style,
        "explanation": explanation,
        "sections": sections,
        "sources": sources,
        "evidence_sufficiency": evidence_sufficiency,
    }
    SESSION_STORE[session_id] = payload
    return payload


def get_session(session_id: str) -> dict[str, Any]:
    return SESSION_STORE.get(session_id, {})


def follow_up(session_id: str, follow_up_text: str) -> dict[str, Any]:
    session = SESSION_STORE.get(session_id)
    if not session:
        raise KeyError("Session not found")
    session["follow_ups"] = session.get("follow_ups", []) + [follow_up_text]
    return {
        "session_id": session_id,
        "response": f"Continuing from the prior explanation: {follow_up_text}. The answer focuses on the concept being taught and is anchored to lecture evidence whenever it is present.",
        "sources": session.get("sources", []),
    }
