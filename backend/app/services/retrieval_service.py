from __future__ import annotations

import re
from collections import Counter
from typing import Any

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "with", "without",
    "from", "into", "onto", "over", "under", "about", "after", "before", "while", "when",
    "that", "this", "these", "those", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "at", "by", "it", "its", "as", "so", "not", "no", "yes",
    "how", "why", "what", "which", "who", "where", "when", "can", "could", "should",
    "would", "may", "might", "do", "does", "did", "have", "has", "had", "we", "you",
    "your", "our", "us", "they", "them", "their", "his", "her", "he", "she", "i", "me",
    "my", "our", "their", "there", "here", "much", "more", "most", "some", "any",
}


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", (text or "").lower())
    cleaned = cleaned.replace("-", " ")
    tokens = [token for token in cleaned.split() if token and token not in STOP_WORDS]
    return tokens


def _phrase_bonus(text: str, query_tokens: list[str]) -> float:
    lowered = (text or "").lower()
    bonus = 0.0
    for phrase in [" ".join(query_tokens[i : i + 2]) for i in range(max(0, len(query_tokens) - 1))]:
        if phrase and phrase in lowered:
            bonus += 2.0
    if len(query_tokens) >= 2:
        joined = " ".join(query_tokens[:2])
        if joined in lowered:
            bonus += 4.0
    return bonus


def score_segment(query: str, segment_text: str) -> float:
    query_tokens = _tokenize(query)
    segment_tokens = _tokenize(segment_text)
    if not query_tokens or not segment_tokens:
        return 0.0

    query_counter = Counter(query_tokens)
    segment_counter = Counter(segment_tokens)

    term_overlap = sum(min(query_counter.get(term, 0), segment_counter.get(term, 0)) for term in query_counter)
    unique_overlap = len(set(query_tokens) & set(segment_tokens))
    phrase_bonus = _phrase_bonus(segment_text, query_tokens)
    if not term_overlap and not unique_overlap:
        return 0.0

    return float(term_overlap * 3 + unique_overlap * 2 + phrase_bonus)


def retrieve_segments(query: str, segments: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    if not query or not segments:
        return []

    scored = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "") or "")
        if not text.strip():
            continue
        score = score_segment(query, text)
        if score <= 0:
            continue
        scored.append(
            {
                "text": text,
                "start": float(segment.get("start", 0) or 0),
                "end": float(segment.get("end", segment.get("start", 0) or 0) or 0),
                "score": score,
                "index": index,
            }
        )

    scored.sort(key=lambda item: (-item["score"], item["start"]))
    return scored[:limit]
