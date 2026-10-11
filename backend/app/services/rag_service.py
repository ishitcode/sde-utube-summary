from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.services.retrieval_service import retrieve_segments


class RAGService:
    def __init__(self, storage_path: str = "./.rag") -> None:
        self.storage_path = Path(storage_path)
        if self.storage_path == Path(':memory:'):
            self.storage_path = None
        elif str(self.storage_path) != ':memory:':
            self.storage_path.mkdir(parents=True, exist_ok=True)

        self._index: dict[str, list[dict[str, Any]]] = {}
        self._persist_path = None if self.storage_path is None else self.storage_path / 'index.json'
        self._load()

    def _load(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            with self._persist_path.open('r', encoding='utf-8') as handle:
                self._index = json.load(handle)
        except (json.JSONDecodeError, OSError):
            self._index = {}

    def _save(self) -> None:
        if self._persist_path is None:
            return
        with self._persist_path.open('w', encoding='utf-8') as handle:
            json.dump(self._index, handle, ensure_ascii=False)

    def index_video(self, video_id: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._index[video_id] = []
        for idx, segment in enumerate(segments):
            text = str(segment.get('text', '') or '').strip()
            if not text:
                continue
            record = {
                'text': text,
                'start': float(segment.get('start', 0) or 0),
                'end': float(segment.get('end', segment.get('start', 0) or 0) or 0),
                'index': idx,
                'video_id': video_id,
            }
            self._index[video_id].append(record)
        self._save()
        return self._index[video_id]

    def search(self, query: str, video_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        candidates = []
        if video_id:
            candidates = self._index.get(video_id, [])
        else:
            for items in self._index.values():
                candidates.extend(items)

        if not candidates:
            return []

        hits = retrieve_segments(query, candidates, limit=limit)
        for hit in hits:
            hit['video_id'] = video_id or candidates[hit['index']]['video_id'] if hit.get('index') is not None else None
        return hits
