from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')

if os.getenv('LANGSMITH_API_KEY'):
    os.environ.setdefault('LANGSMITH_TRACING', 'true')
    os.environ.setdefault('LANGSMITH_PROJECT', 'youtube-summary-studio')

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


class SummaryRequest(BaseModel):
    segments: list[dict[str, Any]] = Field(default_factory=list)
    output_language: str = 'English'
    summary_start: float | None = Field(default=None, ge=0)
    summary_end: float | None = Field(default=None, ge=0)
    request_id: str | None = None

    @model_validator(mode='after')
    def validate_summary_range(self):
        if (self.summary_start is None) != (self.summary_end is None):
            raise ValueError('Both summary start and end times are required.')
        if self.summary_start is not None and self.summary_end <= self.summary_start:
            raise ValueError('Summary end time must be greater than the start time.')
        return self


class SummaryOutput(BaseModel):
    quick_summary: str
    detailed_notes: list[str]
    key_concepts: list[str]
    timestamp_references: list[dict[str, Any]]


class SummaryState(TypedDict):
    segments: list[dict[str, Any]]
    output_language: str
    request_id: str | None
    summary: dict[str, Any]


def _summarize_node(state: SummaryState) -> dict[str, Any]:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=503, detail='Set GEMINI_API_KEY to enable LangChain summaries.')

    model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    logger.info(
        'MODEL_INVOKE_START agent=lecture_summary provider=google model=%s request_id=%s segments=%s',
        model_name,
        state.get('request_id'),
        len(state['segments']),
    )
    transcript = '\n'.join(
        f"[{float(segment.get('start', 0) or 0):.2f}s - {float(segment.get('end', 0) or 0):.2f}s] {str(segment.get('text', '')).strip()}"
        for segment in state['segments']
        if str(segment.get('text', '')).strip()
    )
    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
    ).with_structured_output(SummaryOutput)

    try:
        result = model.invoke(
            [
                ('system', 'You are an expert tutor. Summarize only facts supported by the transcript. Keep timestamps aligned to the source.'),
                (
                    'human',
                    f'Write in {state["output_language"]}. Include 2-4 detailed notes and 3-6 key concepts. '
                    f'Use the provided timestamps for timestamp references.\n\nTranscript:\n{transcript}',
                ),
            ]
        )
    except Exception:
        logger.exception(
            'MODEL_INVOKE_FAILED agent=lecture_summary provider=google model=%s request_id=%s',
            model_name,
            state.get('request_id'),
        )
        raise

    logger.info(
        'MODEL_INVOKE_SUCCESS agent=lecture_summary provider=google model=%s request_id=%s',
        model_name,
        state.get('request_id'),
    )
    return {'summary': result.model_dump()}


summary_graph = StateGraph(SummaryState)
summary_graph.add_node('summarize', _summarize_node)
summary_graph.add_edge(START, 'summarize')
summary_graph.add_edge('summarize', END)
summary_agent = summary_graph.compile()


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


@app.post('/api/summarize')
def summarize_segments(payload: SummaryRequest, request: Request) -> dict:
    segments = [
        segment
        for segment in payload.segments
        if str(segment.get('text', '')).strip()
        and (
            payload.summary_start is None
            or (
                float(segment.get('end', segment.get('start', 0)) or 0) > payload.summary_start
                and float(segment.get('start', 0) or 0) < payload.summary_end
            )
        )
    ]
    if not segments:
        raise HTTPException(status_code=422, detail='No transcript is available in the selected time range.')

    request_id = payload.request_id or request.headers.get('x-request-id') or uuid.uuid4().hex
    logger.info(
        'SUMMARY_AGENT_START agent=lecture_summary request_id=%s segments=%s output_language=%s range=%s',
        request_id,
        len(segments),
        payload.output_language,
        (payload.summary_start, payload.summary_end),
    )
    state = summary_agent.invoke(
        {
            'segments': segments,
            'output_language': payload.output_language,
            'request_id': request_id,
        },
        config={
            'run_name': 'youtube_lecture_summary',
            'metadata': {'agent': 'lecture_summary', 'request_id': request_id},
            'tags': ['youtube-summary', 'langgraph'],
        },
    )
    summary = state['summary']
    summary['summary_range'] = (
        {'start': payload.summary_start, 'end': payload.summary_end}
        if payload.summary_start is not None
        else None
    )
    logger.info('SUMMARY_AGENT_SUCCESS agent=lecture_summary request_id=%s', request_id)
    return summary
