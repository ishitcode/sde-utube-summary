from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class VideoRecord(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(512))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transcript_language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    output_language: Mapped[str] = mapped_column(String(50), default="English")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    caption_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="video")
    summaries: Mapped[list["LectureSummary"]] = relationship(back_populates="video")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    segment_index: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, default=0.0)
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_caption: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    video: Mapped[VideoRecord] = relationship(back_populates="transcript_segments")


class LectureSummary(Base):
    __tablename__ = "lecture_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    summary_type: Mapped[str] = mapped_column(String(50), default="quick")
    quick_summary: Mapped[str] = mapped_column(Text)
    detailed_notes: Mapped[str] = mapped_column(Text, default="")
    key_concepts: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    video: Mapped[VideoRecord] = relationship(back_populates="summaries")


class DeepDiveSession(Base):
    __tablename__ = "deep_dive_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    video_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    topic: Mapped[str] = mapped_column(String(255))
    learning_level: Mapped[str] = mapped_column(String(50), default="Beginner")
    language: Mapped[str] = mapped_column(String(50), default="English")
    explanation_style: Mapped[str] = mapped_column(String(100), default="step-by-step")
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
