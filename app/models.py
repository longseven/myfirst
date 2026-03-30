"""Pydantic request / response schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    problem: str
    answer: Optional[str] = None
    problem_type: str = "auto"
    enable_tts: bool = True


class GenerateResponse(BaseModel):
    lecture_id: str


class LectureStatus(BaseModel):
    lecture_id: str
    status: str  # queued | detecting | generating_scene | assembling | generating_tts | done | failed
    progress: int  # 0-100
    message: str
    url: Optional[str] = None
