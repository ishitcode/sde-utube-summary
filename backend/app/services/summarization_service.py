from __future__ import annotations

import re
from collections import Counter

from app.services.retrieval_service import retrieve_segments


def _extract_key_concepts(segments: list[dict]) -> list[str]:
    transcript_text = " ".join(segment.get("text", "") for segment in segments if segment.get("text"))
    words = re.findall(r"\b[a-zA-Z][\w-]{2,}\b", transcript_text.lower())
    counter = Counter(words)
    filtered = []
    for word, _count in counter.most_common():
        if len(word) < 4:
            continue
        if word in {"this", "that", "there", "their", "these", "those", "from", "with", "into", "using", "about"}:
            continue
        filtered.append(word)
        if len(filtered) >= 6:
            break

    if not filtered:
        return ["lecture overview", "key ideas", "practice review"]

    normalized = []
    for word in filtered:
        phrase = word.replace("-", " ")
        normalized.append(phrase.title())
    return normalized


def summarize_transcript(segments: list[dict], output_language: str = "English") -> dict:
    transcript_text = " ".join(segment.get("text", "") for segment in segments if segment.get("text"))
    key_concepts = _extract_key_concepts(segments)
    evidence = retrieve_segments(" ".join(key_concepts), segments, limit=3)
    if evidence:
        focus = evidence[0]["text"]
        quick_summary = (
            f"This lecture focuses on {key_concepts[0].lower()} and related ideas, explaining the main concept in a structured way while tying the discussion to concrete examples and practical takeaways. "
            f"The strongest evidence from the transcript is: {focus[:180]}"
        )
    elif transcript_text:
        quick_summary = (
            "This lecture covers the core ideas and examples in a structured way, with emphasis on the main concepts, practical patterns, and review-oriented takeaways."
        )
    else:
        quick_summary = "No transcript content was available for a summary."

    detailed_notes = []
    for segment in evidence or segments[:3]:
        text = segment.get("text", "").strip()
        if text:
            detailed_notes.append(text[:220])

    if not detailed_notes:
        detailed_notes = [
            "Review the transcript in chronological order to understand the lecture flow.",
            "Identify the definitions, worked examples, and implementation details highlighted in the content.",
            "Use the deep-dive tutor to explain difficult sections at beginner or advanced level.",
        ]

    timestamp_references = [
        {"start": segment.get("start", 0), "end": segment.get("end", segment.get("start", 0) or 0), "label": "Key segment"}
        for segment in (evidence or segments[:3])
        if segment.get("start") is not None
    ]

    return {
        "quick_summary": quick_summary,
        "detailed_notes": detailed_notes,
        "key_concepts": key_concepts,
        "timestamp_references": timestamp_references,
    }
