"""GET /api/status/{lecture_id} — poll task progress."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..pipeline.task_runner import get_task, list_all_tasks

router = APIRouter()


@router.get("/api/status/{lecture_id}")
async def get_status(lecture_id: str):
    task = get_task(lecture_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/api/tasks")
async def list_tasks():
    """Return all tasks (most recent first)."""
    return list_all_tasks()
