"""POST /api/generate — submit a lecture generation task."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks

from ..models import GenerateRequest, GenerateResponse
from ..pipeline.task_runner import create_task, run_pipeline

router = APIRouter()


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    lecture_id = uuid.uuid4().hex[:8]
    create_task(lecture_id)
    background_tasks.add_task(
        run_pipeline,
        lecture_id,
        req.problem,
        req.answer,
        req.problem_type,
        req.enable_tts,
    )
    return GenerateResponse(lecture_id=lecture_id)
