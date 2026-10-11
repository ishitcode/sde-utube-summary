from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VideoAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=5)
    transcript_language: str | None = "auto"
    output_language: str = "English"


class VideoMetadata(BaseModel):
    video_id: str
    title: str | None = None
    channel_name: str | None = None
    thumbnail_url: str | None = None
    duration: float | None = None
    url: str
    status: str = "ready"
    caption_languages: list[str] = Field(default_factory=list)
    error_message: str | None = None


class TranscriptSegmentSchema(BaseModel):
    text: str
    start: float
    end: float
    language: str | None = None
    source: str | None = None


class SummaryResponse(BaseModel):
    quick_summary: str
    detailed_notes: list[str]
    key_concepts: list[str]
    timestamp_references: list[dict[str, Any]]


class VideoAnalyzeResponse(BaseModel):
    video_id: str
    title: str | None
    channel_name: str | None
    thumbnail_url: str | None
    duration: float | None
    url: str
    status: str
    transcript_language: str | None
    caption_languages: list[str]
    summary: SummaryResponse
    transcript: list[TranscriptSegmentSchema]
    message: str


class TutorRequest(BaseModel):
    video_id: str | None = None
    topic: str = Field(..., min_length=2)
    learning_level: Literal["Beginner", "Intermediate", "Advanced", "Interview Preparation"] = "Beginner"
    language: Literal["English", "Hinglish", "Hindi"] = "English"
    explanation_style: Literal[
        "step-by-step teaching",
        "real-world analogy",
        "code walkthrough",
        "mathematical explanation",
        "interview-oriented explanation",
        "compare and contrast",
        "practical implementation",
    ] = "step-by-step teaching"


class TutorResponse(BaseModel):
    session_id: str
    topic: str
    language: str
    learning_level: str
    explanation: str
    sections: list[str]
    sources: list[dict[str, Any]]
    evidence_sufficiency: str
    explanation_language: str
