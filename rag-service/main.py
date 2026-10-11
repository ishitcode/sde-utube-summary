from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title='Youtube Summary RAG Service', version='1.0.0')

LOG_DIR = Path(__file__).resolve().parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'rag.log'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()],
)
logger = logging.getLogger('rag_service')

INDEX_DIR = Path(__file__).resolve().parent / '.index'
INDEX_DIR.mkdir(exist_ok=True)
INDEX_FILE = INDEX_DIR / 'segments.json'


class IndexRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    segments: list[dict[str, Any]] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    video_id: str | None = None
    limit: int = 3


@app.middleware('http')
async def log_requests(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or uuid.uuid4().hex
    start = time.perf_counter()
    logger.info('REQUEST START %s %s request_id=%s', request.method, request.url.path, request_id)

    try:
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            'REQUEST END %s %s status=%s duration_ms=%s request_id=%s',
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        response.headers['X-Request-Id'] = request_id
        return response
    except Exception as exc:  # pragma: no cover - logging fallback
        logger.exception('REQUEST ERROR %s %s request_id=%s', request.method, request.url.path, request_id)
        raise exc


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception('UNHANDLED_EXCEPTION %s %s', request.method, request.url.path)
    return JSONResponse(status_code=500, content={'detail': 'Internal server error'})


def _load_index() -> dict[str, list[dict[str, Any]]]:
    if not INDEX_FILE.exists():
        return {}
    try:
        return json.loads(INDEX_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        logger.warning('INDEX_FILE_CORRUPT path=%s', INDEX_FILE)
        return {}


def _save_index(index: dict[str, list[dict[str, Any]]]) -> None:
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False), encoding='utf-8')


@app.get('/health')
def health() -> dict:
    logger.info('HEALTHCHECK_OK service=rag-service')
    return {'status': 'ok', 'service': 'rag-service'}


@app.post('/api/index')
def index_segments(payload: IndexRequest) -> dict:
    logger.info('INDEX_START video_id=%s segments=%s', payload.video_id, len(payload.segments))

    try:
        index = _load_index()
        stored = []
        for idx, segment in enumerate(payload.segments):
            text = str(segment.get('text', '') or '').strip()
            if not text:
                continue
            stored.append(
                {
                    'video_id': payload.video_id,
                    'text': text,
                    'start': float(segment.get('start', 0) or 0),
                    'end': float(segment.get('end', segment.get('start', 0) or 0) or 0),
                    'index': idx,
                }
            )

        index[payload.video_id] = stored
        _save_index(index)
        logger.info('INDEX_SUCCESS video_id=%s indexed=%s', payload.video_id, len(stored))
        return {'video_id': payload.video_id, 'indexed': len(stored)}
    except Exception as exc:
        logger.exception('INDEX_FAILED video_id=%s', payload.video_id)
        raise exc


@app.post('/api/search')
def search_segments(payload: SearchRequest) -> dict:
    logger.info('SEARCH_START video_id=%s query=%s limit=%s', payload.video_id, payload.query[:120], payload.limit)

    try:
        index = _load_index()
        candidates = index.get(payload.video_id, []) if payload.video_id else [item for items in index.values() for item in items]

        scored = []
        for item in candidates:
            text = str(item.get('text', '') or '').lower()
            query = payload.query.lower()
            score = 0
            if query in text:
                score += 5
            for term in query.split():
                if term and term in text:
                    score += 2
            if score > 0:
                scored.append({**item, 'score': score})

        scored = sorted(scored, key=lambda item: (-item['score'], item.get('start', 0)))[: payload.limit]
        logger.info('SEARCH_SUCCESS video_id=%s hits=%s', payload.video_id, len(scored))
        return {'hits': scored}
    except Exception as exc:
        logger.exception('SEARCH_FAILED video_id=%s query=%s', payload.video_id, payload.query[:120])
        raise exc
