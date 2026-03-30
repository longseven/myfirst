"""Three.js renderer — wraps existing scene.py + assembler.py for 3D geometry."""

from __future__ import annotations

import json
import logging
import os
import re

from . import RendererBase
from ..llm import call_llm
from ...config import settings

log = logging.getLogger("renderers.threejs")


class ThreeJSRenderer(RendererBase):
    """Renderer for 立体几何 — generates interactive 3D HTML via Three.js."""

    name = "threejs"

    def get_prompt_schema(self) -> str:
        """Return the Three.js scene_data JSON schema."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "prompts", "threejs_schema.md"
        )
        schema_path = os.path.normpath(schema_path)
        if os.path.isfile(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                return f.read()
        # Fallback: use inline schema from scene.py
        from ..scene import SCENE_DATA_SCHEMA_DOC
        return SCENE_DATA_SCHEMA_DOC

    def get_system_prompt(self, teaching_data: str) -> str:
        """Build system prompt for Three.js scene generation."""
        from ..scene import SYSTEM_PROMPT_TEMPLATE
        return SYSTEM_PROMPT_TEMPLATE.format(
            teaching_data=teaching_data or "（暂无教学数据）",
            schema_doc=self.get_prompt_schema(),
        )

    async def parse_llm_output(self, raw: str) -> dict:
        """Extract JSON from LLM output with repair logic."""
        from ..scene import _extract_json
        scene = _extract_json(raw)

        for required in ("vertices", "solution_script"):
            if required not in scene:
                raise ValueError(f"LLM 返回的 JSON 缺少必要字段: {required}")

        n_verts = len(scene.get("vertices", {}))
        n_steps = len(scene.get("solution_script", []))
        log.info("Three.js 场景: %d 个顶点, %d 个教学步骤", n_verts, n_steps)
        return scene

    async def render(self, data: dict, output_dir: str) -> str:
        """Inject scene_data into Three.js template, save index.html."""
        from ..assembler import assemble_html

        html = assemble_html(data)
        os.makedirs(output_dir, exist_ok=True)

        html_path = os.path.join(output_dir, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # Also save scene_data.json for debugging
        json_path = os.path.join(output_dir, "scene_data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        log.info("Three.js 渲染完成: %s", html_path)
        return html_path
