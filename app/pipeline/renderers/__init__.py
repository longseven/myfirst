"""Renderer abstraction layer — pluggable backends for different subjects.

Each renderer implements three methods:
  - get_prompt_schema()  → LLM prompt schema string
  - parse_llm_output()   → raw LLM text → structured dict
  - render()             → structured dict → final HTML/video output
"""

from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

log = logging.getLogger("renderers")


class RendererBase(abc.ABC):
    """Abstract base for all renderers."""

    name: str = "base"

    @abc.abstractmethod
    def get_prompt_schema(self) -> str:
        """Return the LLM prompt schema doc (tells LLM what JSON to output)."""
        ...

    @abc.abstractmethod
    def get_system_prompt(self, teaching_data: str) -> str:
        """Return the full system prompt for the LLM call."""
        ...

    @abc.abstractmethod
    async def parse_llm_output(self, raw: str) -> dict:
        """Parse raw LLM text output into structured intermediate data."""
        ...

    @abc.abstractmethod
    async def render(self, data: dict, output_dir: str) -> str:
        """Render intermediate data to final output. Returns path to index.html."""
        ...


# Subject → renderer mapping (lazy-loaded)
_registry: dict[str, RendererBase] = {}


def register(subject: str, renderer: RendererBase):
    """Register a renderer for a subject."""
    _registry[subject] = renderer
    log.info("注册渲染器: %s → %s", subject, renderer.name)


def get_renderer(subject: str) -> RendererBase:
    """Get the renderer for a subject. Falls back to ThreeJS renderer."""
    if subject in _registry:
        return _registry[subject]
    # Fallback: check if there's a default
    if "_default" in _registry:
        return _registry["_default"]
    raise KeyError(f"未找到学科 '{subject}' 的渲染器，也没有默认渲染器")


def init_renderers():
    """Initialize and register all renderers. Called once at startup."""
    from .threejs import ThreeJSRenderer
    from .manim_ import ManimRenderer
    from .video import VideoRenderer

    threejs = ThreeJSRenderer()
    manim = ManimRenderer()
    video = VideoRenderer()

    # Three.js: 立体几何
    register("立体几何", threejs)
    register("_default", threejs)  # fallback

    # Manim: 大部分计算类学科
    for subj in ["解三角形", "三角函数", "函数", "导数", "数列",
                 "排列组合概率统计", "集合与不等式", "解析几何",
                 "复数", "平面向量"]:
        register(subj, manim)

    log.info("渲染器初始化完成: %d 个学科已注册", len(_registry) - 1)  # -1 for _default
