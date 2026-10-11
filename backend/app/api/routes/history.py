from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import VideoRecord

router = APIRouter(tags=["history"])


@router.get("/history")
def list_history(db: Session = Depends(get_db)) -> dict:
    videos = db.scalars(select(VideoRecord)).all()
    return {
        "items": [
            {
                "video_id": video.video_id,
                "title": video.title,
                "channel_name": video.channel_name,
                "status": video.status,
            }
            for video in videos
        ]
    }


@router.get("/history/{video_id}")
def get_history_for_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    record = db.scalar(select(VideoRecord).where(VideoRecord.video_id == video_id))
    if not record:
        raise HTTPException(status_code=404, detail="Video not found")
    return {
        "video_id": record.video_id,
        "title": record.title,
        "channel_name": record.channel_name,
        "status": record.status,
    }
