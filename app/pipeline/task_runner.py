"""Background task orchestrator — runs the full pipeline with renderer routing."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import OrderedDict
from typing import Optional

from ..config import settings
from ..models import LectureStatus
from .detector import detect_problem_type, detect_subject_and_types
from .teaching import load_teaching_data
from .llm import call_llm, ModelPurpose
from . import tts

log = logging.getLogger("pipeline.runner")

# In-memory task store with LRU eviction (max 100 tasks)
# Using OrderedDict to maintain access order for cleanup
_tasks: OrderedDict[str, dict] = OrderedDict()
_MAX_TASKS = 100
_TASK_TTL = 3600  # Task TTL in seconds (1 hour)

# Limit concurrent generations
_semaphore: Optional[asyncio.Semaphore] = None

# Renderer registry (lazy init)
_renderers_initialized = False


def _sem() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.max_concurrent)
    return _semaphore


def _ensure_renderers():
    """Initialize renderers once."""
    global _renderers_initialized
    if not _renderers_initialized:
        from .renderers import init_renderers
        init_renderers()
        _renderers_initialized = True


def _update(task_id: str, **kw):
    """Update task status with timestamp."""
    if task_id in _tasks:
        _tasks[task_id].update(kw)
        _tasks[task_id]["updated_at"] = time.time()
        # Move to end for LRU ordering
        _tasks.move_to_end(task_id)


def _evict_old_tasks():
    """Remove tasks that exceed max count or have expired."""
    now = time.time()
    # Remove tasks exceeding TTL
    expired = [
        tid for tid, t in _tasks.items()
        if now - t.get("created_at", now) > _TASK_TTL
    ]
    for tid in expired:
        del _tasks[tid]
        log.debug("清理过期任务：%s", tid)

    # Remove oldest tasks if exceeding max count
    while len(_tasks) > _MAX_TASKS:
        oldest_id = next(iter(_tasks))
        del _tasks[oldest_id]
        log.debug("清理最旧任务：%s", oldest_id)


def get_task(task_id: str) -> Optional[dict]:
    """Get task by ID, or None if not found."""
    if task_id in _tasks:
        _tasks.move_to_end(task_id)  # Update LRU order
        return _tasks[task_id]
    return None


def list_all_tasks() -> list[dict]:
    """Return all tasks sorted by recency (most recent first)."""
    _evict_old_tasks()
    return list(reversed(list(_tasks.values())))


def create_task(task_id: str) -> dict:
    """Create a new task entry."""
    _evict_old_tasks()
    task = {
        "lecture_id": task_id,
        "status": "queued",
        "progress": 0,
        "message": "任务已创建",
        "url": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _tasks[task_id] = task
    return task


# Backward-compatible alias
tasks = _tasks


async def run_pipeline(
    task_id: str,
    problem: str,
    answer: Optional[str] = None,
    problem_type: str = "auto",
    enable_tts: bool = True,
):
    """Full async pipeline: detect → teach → route renderer → LLM → render → TTS."""
    async with _sem():
        lecture_dir = os.path.join(settings.lectures_dir, task_id)
        os.makedirs(lecture_dir, exist_ok=True)

        try:
            # 0. Ensure renderers are initialized
            _ensure_renderers()
            from .renderers import get_renderer

            # 1. Detect problem type (5%)
            _update(task_id, status="detecting", progress=5, message="检测题型...")
            if problem_type == "auto":
                detected = detect_subject_and_types(problem)
            else:
                detected = [(problem_type, [])]

            types_desc = "; ".join(
                f"{s}[{','.join(ts)}]" if ts else s for s, ts in detected
            )
            log.info("题型检测: %s", types_desc)

            # Primary subject (first detected)
            primary_subject = detected[0][0] if detected else "立体几何"

            # 2. Load teaching data (10%)
            _update(task_id, status="loading_teaching", progress=10, message="加载教学数据...")
            teaching_data = load_teaching_data(detected, settings.teaching_data_dir)

            # 3. Route to renderer based on subject
            renderer = get_renderer(primary_subject)
            renderer_name = renderer.name
            log.info("渲染器路由: %s → %s", primary_subject, renderer_name)
            _update(task_id, status="generating", progress=15,
                    message=f"AI 正在分析题目（{renderer_name}渲染器）...")

            # 4. Build LLM prompt using renderer's schema
            system_prompt = renderer.get_system_prompt(teaching_data)
            user_content = f"题目：\n{problem}"
            if answer:
                user_content += f"\n\n参考答案：\n{answer}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            # 5. Call LLM (15% → 60%)
            # Use Claude Opus for problem solving/diagram generation
            _update(task_id, progress=20, message="AI 正在生成讲解内容...")
            raw_output = await call_llm(
                messages,
                temperature=0.1,
                max_tokens=16000,
                purpose=ModelPurpose.PROBLEM_SOLVING,
            )
            _update(task_id, progress=55, message="LLM 输出完成，解析中...")

            # 6. Parse LLM output (60%)
            parsed_data = await renderer.parse_llm_output(raw_output)

            # Save intermediate data
            data_path = os.path.join(lecture_dir, f"{renderer_name}_data.json")
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=2)
            _update(task_id, progress=65, message="数据解析完成")

            # 7. Render (65% → 85%)
            _update(task_id, status="rendering", progress=70,
                    message=f"正在渲染（{renderer_name}）...")
            await renderer.render(parsed_data, lecture_dir)
            _update(task_id, progress=85, message="渲染完成")

            # 8. TTS (85% → 95%)
            if enable_tts and settings.tts_enabled:
                _update(task_id, status="generating_tts", progress=85, message="生成语音讲解...")
                audio_dir = os.path.join(lecture_dir, "audio")

                # Extract speech texts from parsed data (renderer-agnostic)
                tts_data = _extract_tts_data(parsed_data, renderer_name)
                if tts_data:
                    count = await tts.generate_all(tts_data, audio_dir)
                    log.info("TTS 完成: %d 段语音", count)

            # Done
            url = f"/lectures/{task_id}/index.html"
            _update(
                task_id,
                status="done",
                progress=100,
                message="生成完成！",
                url=url,
                renderer=renderer_name,
            )
            log.info("Pipeline 完成: %s (renderer=%s)", url, renderer_name)

        except Exception as e:
            log.exception("Pipeline 失败: %s", e)
            _update(task_id, status="failed", message=f"生成失败: {e}")


def _extract_tts_data(parsed_data: dict, renderer_name: str) -> Optional[dict]:
    """Extract TTS-compatible data from different renderer outputs.

    Returns a dict with 'solution_script' key containing speech texts,
    compatible with the existing tts.generate_all() interface.
    """
    if renderer_name == "threejs":
        # Three.js data already has solution_script
        if "solution_script" in parsed_data:
            return parsed_data
        return None

    elif renderer_name == "manim":
        # Convert manim scenes to solution_script format
        scenes = parsed_data.get("scenes", [])
        if not scenes:
            return None
        script = []
        for scene in scenes:
            speech = scene.get("speech", "")
            if speech:
                script.append({"speech": speech})
        return {"solution_script": script} if script else None

    elif renderer_name == "video":
        # Convert video solution_steps to solution_script format
        steps = parsed_data.get("solution_steps", [])
        if not steps:
            return None
        script = []
        for step in steps:
            speech = step.get("speech", "")
            if speech:
                script.append({"speech": speech})
        return {"solution_script": script} if script else None

    return None
