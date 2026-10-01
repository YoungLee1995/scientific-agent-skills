"""Local teaching API for ACL-first knowledge retrieval."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.services.knowledge import KnowledgeAnswer, KnowledgeService
from app.services.local_archive import LocalArchive

app = FastAPI(title="Lab Agent Knowledge API")


class KnowledgeQuery(BaseModel):
    project_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=4_000)


def _service() -> KnowledgeService:
    return KnowledgeService(
        LocalArchive(Path(os.getenv("LOCAL_ARCHIVE_PATH", "data/local-archive")))
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/knowledge/query", response_model=KnowledgeAnswer)
def query_knowledge(
    request: KnowledgeQuery, x_user_id: str | None = Header(default=None)
) -> KnowledgeAnswer:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id is required")
    return _service().answer_question(x_user_id, request.question, request.project_id)
