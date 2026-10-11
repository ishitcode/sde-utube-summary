from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.history import router as history_router
from app.api.routes.tutor import router as tutor_router
from app.api.routes.videos import router as videos_router
from app.db import init_db

app = FastAPI(
    title="YouTube Summary Studio",
    description="AI-powered lecture summarizer with multilingual tutoring and RAG-inspired retrieval.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "youtube-summary-studio"}


app.include_router(videos_router, prefix="/api")
app.include_router(tutor_router, prefix="/api")
app.include_router(history_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
