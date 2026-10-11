from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com"}
VIDEO_ID_PATTERN = re.compile(r"(?:v=|/shorts/|youtu\.be/|embed/)([A-Za-z0-9_-]{9,12})")


def validate_youtube_url(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError("YouTube URL is required.")

    parsed = urlparse(candidate)
    hostname = (parsed.netloc or "").lower().replace("www.", "")

    if hostname not in YOUTUBE_HOSTS and not hostname.endswith("youtube.com"):
        raise ValueError("This is not a supported YouTube URL.")

    match = VIDEO_ID_PATTERN.search(candidate)
    if not match:
        raise ValueError("Could not find a valid video ID in the provided URL.")

    video_id = match.group(1)
    if len(video_id) < 9 or len(video_id) > 12:
        raise ValueError("Video ID length is invalid.")
    return video_id


def extract_video_id(url: str) -> str:
    return validate_youtube_url(url)


def fetch_video_metadata(video_id: str) -> dict[str, Any]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return {
        "video_id": video_id,
        "title": info.get("title"),
        "channel_name": info.get("channel") or info.get("uploader"),
        "thumbnail_url": (info.get("thumbnail") or info.get("thumbnails", [{}])[-1].get("url")),
        "duration": info.get("duration"),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "caption_languages": [
            caption.get("language") for caption in info.get("captions", {}).values() if caption.get("language")
        ],
    }


def fetch_transcript(video_id: str, preferred_language: str | None = None) -> list[dict[str, Any]]:
    api = YouTubeTranscriptApi()
    transcript = None
    try:
        if preferred_language and preferred_language.lower() != "auto":
            transcript = api.fetch(video_id, languages=[preferred_language])
        else:
            transcript = api.fetch(video_id)
    except Exception:
        try:
            transcript = api.fetch(video_id)
        except Exception as exc:  # pragma: no cover - real network-call behavior
            raise ValueError(f"No transcript is available for this video: {exc}") from exc

    normalized = []
    for index, item in enumerate(transcript):
        normalized.append(
            {
                "text": item.text,
                "start": float(item.start),
                "end": float(item.start + item.duration),
                "language": getattr(item, "language", preferred_language or "unknown"),
                "source": "auto-generated",
                "index": index,
            }
        )
    return normalized


def analyze_video_url(url: str, transcript_language: str | None = "auto", output_language: str = "English") -> dict[str, Any]:
    video_id = validate_youtube_url(url)
    metadata = fetch_video_metadata(video_id)
    transcript = fetch_transcript(video_id, preferred_language=transcript_language)
    summary = {
        "quick_summary": "Lecture imported successfully. The transcript is available for study and retrieval.",
        "detailed_notes": [
            "The lecture has been indexed for structured notes and revision.",
            "Use the deep-dive tutor to explain difficult concepts at different levels.",
        ],
        "key_concepts": ["lecture overview", "key takeaways", "practice review"],
        "timestamp_references": [{"start": transcript[0]["start"], "end": transcript[-1]["end"], "label": "Full lecture"}] if transcript else [],
    }
    return {
        "video_id": video_id,
        "title": metadata.get("title"),
        "channel_name": metadata.get("channel_name"),
        "thumbnail_url": metadata.get("thumbnail_url"),
        "duration": metadata.get("duration"),
        "url": metadata.get("url"),
        "status": "ready",
        "transcript_language": transcript_language,
        "caption_languages": metadata.get("caption_languages", []),
        "summary": summary,
        "transcript": transcript,
        "message": "Video was validated and processed successfully.",
        "output_language": output_language,
    }
