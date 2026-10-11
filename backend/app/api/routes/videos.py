from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import LectureSummary, TranscriptSegment, VideoRecord
from app.schemas import VideoAnalyzeRequest, VideoAnalyzeResponse, VideoMetadata
from app.services.summarization_service import summarize_transcript
from app.services.video_service import analyze_video_url, fetch_transcript, fetch_video_metadata

router = APIRouter(prefix="/videos", tags=["videos"])


def get_video_by_id(db: Session, video_id: str) -> VideoRecord | None:
    return db.scalar(select(VideoRecord).where(VideoRecord.video_id == video_id))


@router.post("/analyze", response_model=VideoAnalyzeResponse)
def analyze_video(payload: VideoAnalyzeRequest, db: Session = Depends(get_db)) -> VideoAnalyzeResponse:
    try:
        result = analyze_video_url(payload.url, payload.transcript_language, payload.output_language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    video = db.scalar(select(VideoRecord).where(VideoRecord.video_id == result["video_id"]))
    if video is None:
        video = VideoRecord(
            video_id=result["video_id"],
            url=result["url"],
            title=result["title"],
            channel_name=result["channel_name"],
            thumbnail_url=result["thumbnail_url"],
            duration=result["duration"],
            transcript_language=result["transcript_language"],
            output_language=result["output_language"],
            status=result["status"],
        )
        db.add(video)
        db.commit()
        db.refresh(video)

    db.query(TranscriptSegment).filter(TranscriptSegment.video_id == video.id).delete()
    for idx, segment in enumerate(result["transcript"]):
        db.add(
            TranscriptSegment(
                video_id=video.id,
                segment_index=idx,
                start_time=segment["start"],
                end_time=segment["end"],
                text=segment["text"],
                language=segment.get("language"),
                source_caption=segment.get("source"),
            )
        )

    db.query(LectureSummary).filter(LectureSummary.video_id == video.id).delete()
    summary_payload = summarize_transcript(result["transcript"], payload.output_language)
    db.add(
        LectureSummary(
            video_id=video.id,
            summary_type="quick",
            quick_summary=summary_payload["quick_summary"],
            detailed_notes="\n".join(summary_payload["detailed_notes"]),
            key_concepts=",".join(summary_payload["key_concepts"]),
        )
    )
    db.commit()

    return VideoAnalyzeResponse(
        video_id=result["video_id"],
        title=result["title"],
        channel_name=result["channel_name"],
        thumbnail_url=result["thumbnail_url"],
        duration=result["duration"],
        url=result["url"],
        status=result["status"],
        transcript_language=result["transcript_language"],
        caption_languages=result["caption_languages"],
        summary={
            "quick_summary": summary_payload["quick_summary"],
            "detailed_notes": summary_payload["detailed_notes"],
            "key_concepts": summary_payload["key_concepts"],
            "timestamp_references": summary_payload["timestamp_references"],
        },
        transcript=[
            {
                "text": segment["text"],
                "start": segment["start"],
                "end": segment["end"],
                "language": segment.get("language"),
                "source": segment.get("source"),
            }
            for segment in result["transcript"]
        ],
        message=result["message"],
    )


@router.get("/{video_id}")
def get_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    record = get_video_by_id(db, video_id)
    if not record:
        raise HTTPException(status_code=404, detail="Video not found")
    return {
        "video_id": record.video_id,
        "title": record.title,
        "channel_name": record.channel_name,
        "thumbnail_url": record.thumbnail_url,
        "duration": record.duration,
        "status": record.status,
        "transcript_language": record.transcript_language,
    }


@router.get("/{video_id}/transcript")
def get_transcript(video_id: str, db: Session = Depends(get_db)) -> dict:
    record = get_video_by_id(db, video_id)
    if not record:
        raise HTTPException(status_code=404, detail="Video not found")
    segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.video_id == record.id)).all()
    return {
        "video_id": video_id,
        "transcript_language": record.transcript_language,
        "segments": [
            {
                "text": segment.text,
                "start": segment.start_time,
                "end": segment.end_time,
                "language": segment.language,
                "source": segment.source_caption,
            }
            for segment in segments
        ],
    }


@router.get("/{video_id}/summary")
def get_summary(video_id: str, db: Session = Depends(get_db)) -> dict:
    record = get_video_by_id(db, video_id)
    if not record:
        raise HTTPException(status_code=404, detail="Video not found")
    summary = db.scalar(select(LectureSummary).where(LectureSummary.video_id == record.id))
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {
        "video_id": video_id,
        "quick_summary": summary.quick_summary,
        "detailed_notes": summary.detailed_notes.split("\n"),
        "key_concepts": summary.key_concepts.split(","),
    }


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    record = get_video_by_id(db, video_id)
    if not record:
        raise HTTPException(status_code=404, detail="Video not found")
    db.query(TranscriptSegment).filter(TranscriptSegment.video_id == record.id).delete()
    db.query(LectureSummary).filter(LectureSummary.video_id == record.id).delete()
    db.delete(record)
    db.commit()
    return {"video_id": video_id, "status": "deleted"}
