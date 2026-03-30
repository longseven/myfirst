"""Manim renderer — generates math animation videos from LLM output.

Pipeline: problem → LLM → manim_data.json → Manim Python script → render → MP4 → player HTML
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import textwrap
from typing import Optional

from . import RendererBase
from ..llm import call_llm
from .manim_instructions import init_handlers, get_handler

log = logging.getLogger("renderers.manim")


# ============================================================
# Manim scene_data JSON schema
# ============================================================

MANIM_SCHEMA_DOC = r"""
你必须输出**严格合法的 JSON**，用于生成数学教学动画视频。

```json
{
  "title": "题目简短标题",
  "problem_tex": "题目 LaTeX 表示",
  "scenes": [
    {
      "phase": "审题/分析/求解/验证/总结",
      "speech": "这一步的讲解文本（口语化，30-80 字）",
      "instructions": [...]
    }
  ],
  "summary": {
    "key_formula": "$核心公式$",
    "method_name": "方法名称",
    "tips": ["注意点 1", "注意点 2"]
  }
}
```

### 指令类型：write_tex, transform_tex, draw_axes, plot_function, mark_point,
           highlight_interval, draw_line, draw_triangle, draw_table, fade_out,
           pause, write_text, draw_number_line

### 约束：
- scenes 必须 8-20 个步骤
- speech 要口语化
- 只输出 JSON
"""


MANIM_SYSTEM_PROMPT = textwrap.dedent("""\
你是一位高中数学名师 + 数学动画制作专家。

任务：根据给定的数学题目，生成结构化 JSON 数据，用于自动生成 Manim 教学动画视频。

=== 教学方法论 ===
{teaching_data}

=== 输出 JSON 格式说明 ===
{schema_doc}

=== 重要约束 ===
1. 动画必须完整展示解题全过程，不能跳步。
2. 每个 scene 的 speech 文本要口语化，像老师自然讲课。
3. 公式推导要逐步展示（write_tex → transform_tex）。
4. 函数题必须画图（draw_axes + plot_function）。
5. 表格（单调性表、分布列表）用 draw_table。
6. 三角形题用 draw_triangle + draw_angle。
7. 概率题用 draw_tree。
8. 每步动画不超过 5 个指令。
9. 只输出 JSON，不要任何解释。
""")


class ManimRenderer(RendererBase):
    """Renderer for math subjects — generates Manim animation videos."""

    name = "manim"

    def __init__(self):
        """Initialize renderer with instruction handlers."""
        init_handlers()

    def get_prompt_schema(self) -> str:
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "prompts", "manim_schema.md"
        )
        schema_path = os.path.normpath(schema_path)
        if os.path.isfile(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                return f.read()
        return MANIM_SCHEMA_DOC

    def get_system_prompt(self, teaching_data: str) -> str:
        return MANIM_SYSTEM_PROMPT.format(
            teaching_data=teaching_data or "（暂无教学数据）",
            schema_doc=self.get_prompt_schema(),
        )

    async def parse_llm_output(self, raw: str) -> dict:
        """Extract manim_data JSON from LLM output."""
        from ..scene import _extract_json
        data = _extract_json(raw)

        if "scenes" not in data:
            raise ValueError("LLM 返回的 JSON 缺少 'scenes' 字段")

        n_scenes = len(data.get("scenes", []))
        total_anims = sum(len(s.get("instructions") or s.get("animations", [])) for s in data["scenes"])
        log.info("Manim 数据：%d 个场景，%d 个动画指令", n_scenes, total_anims)
        return data

    async def render(self, data: dict, output_dir: str) -> str:
        """Convert manim_data → Python script → render → HTML player."""
        os.makedirs(output_dir, exist_ok=True)

        # Save manim_data.json
        json_path = os.path.join(output_dir, "manim_data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Generate Manim Python script
        script_path = os.path.join(output_dir, "scene.py")
        script = self._generate_manim_script(data)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        # Try to render with Manim
        video_path = None
        try:
            video_path = await self._run_manim(script_path, output_dir)
        except Exception as e:
            log.warning("Manim 渲染失败，回退到静态 HTML: %s", e)

        # Generate HTML player
        html_path = os.path.join(output_dir, "index.html")
        html = self._generate_player_html(data, video_path)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        log.info("Manim 渲染完成：%s", html_path)
        return html_path

    def _generate_manim_script(self, data: dict) -> str:
        """Convert manim_data JSON to a Manim Community Edition Python script."""
        title = data.get("title", "MathLecture")
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', title)[:30] or "Lecture"

        lines = [
            '"""Auto-generated Manim script."""',
            'from manim import *',
            '',
            f'class {safe_name}(Scene):',
            '    def construct(self):',
        ]

        prev_tex_var = None
        for i, scene in enumerate(data.get("scenes", [])):
            phase = scene.get("phase") or scene.get("title", "")
            speech = scene.get("speech", "")
            lines.append('')
            lines.append(f'        # === {phase} ===')
            lines.append(f'        # {speech[:60]}...')

            axes_var = None
            # Use instructions or animations field
            anims = scene.get("instructions") or scene.get("animations", [])

            for j, anim in enumerate(anims):
                atype = anim.get("type", "")
                var = f"obj_{i}_{j}"

                handler = get_handler(atype)
                if handler:
                    code_lines = handler.generate(anim, var, axes_var)
                    lines.extend(code_lines)

                    # Track variables for transforms and axes
                    if atype == "write_tex":
                        prev_tex_var = var
                    elif atype == "draw_axes":
                        axes_var = var

            lines.append('        self.wait(1)')

        lines.append('')
        return '\n'.join(lines)

    async def _run_manim(self, script_path: str, output_dir: str) -> Optional[str]:
        """Execute manim render command. Returns video path or None."""
        with open(script_path, "r") as f:
            content = f.read()
        m = re.search(r'class (\w+)\(Scene\)', content)
        if not m:
            raise RuntimeError("Manim script 中未找到 Scene 类")
        class_name = m.group(1)

        cmd = [
            "manim", "render", "-qm",
            "--media_dir", output_dir,
            script_path, class_name,
        ]

        log.info("执行 Manim: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if proc.returncode != 0:
            log.error("Manim stderr: %s", proc.stderr[:1000])
            raise RuntimeError(f"Manim 渲染失败：{proc.stderr[:500]}")

        # Find the output video
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if f.endswith(".mp4"):
                    return os.path.join(root, f)

        raise RuntimeError("Manim 渲染完成但未找到 MP4 文件")

    def _generate_player_html(self, data: dict, video_path: Optional[str]) -> str:
        """Generate HTML player page with video (or fallback to step-by-step display)."""
        title = data.get("title", "数学讲解")
        scenes = data.get("scenes", [])
        summary = data.get("summary", {})

        steps_html = self._build_steps_html(scenes)
        summary_html = self._build_summary_html(summary)
        video_html = self._build_video_html(video_path)

        return self._assemble_html(title, steps_html, summary_html, video_html)

    def _build_steps_html(self, scenes: list) -> str:
        """Build HTML for step cards."""
        steps = []
        for i, scene in enumerate(scenes):
            phase = scene.get("phase") or scene.get("title", "")
            speech = scene.get("speech", "")
            anims = scene.get("instructions") or scene.get("animations", [])

            # Extract formulas
            formulas = [
                a.get("tex") or a.get("to_tex", "")
                for a in anims
                if a.get("type") in ("write_tex", "transform_tex")
                and (a.get("tex") or a.get("to_tex"))
            ]
            formulas_html = "".join(
                f'<div class="formula">$${f}$$</div>' for f in formulas
            )

            steps.append(f"""
            <div class="step-card" data-step="{i}">
                <div class="step-header">
                    <span class="step-num">Step {i+1}</span>
                    <span class="step-phase">{phase}</span>
                </div>
                <p class="step-speech">{speech}</p>
                {formulas_html}
            </div>""")
        return "".join(steps)

    def _build_summary_html(self, summary: dict) -> str:
        """Build HTML for summary card."""
        if not summary:
            return ""

        key_formula = summary.get("key_formula", "")
        method = summary.get("method_name", "")
        tips = summary.get("tips", [])
        tips_html = "".join(f"<li>{t}</li>" for t in tips)

        return f"""
            <div class="summary-card">
                <h3>总结</h3>
                <p><strong>方法</strong>: {method}</p>
                <div class="formula">$${key_formula}$$</div>
                <ul>{tips_html}</ul>
            </div>"""

    def _build_video_html(self, video_path: Optional[str]) -> str:
        """Build video section HTML."""
        if video_path:
            video_rel = os.path.basename(video_path)
            return f'<video id="lecture-video" controls><source src="{video_rel}" type="video/mp4"></video>'
        return '<div class="no-video">动画视频暂未生成（需安装 Manim）<br>下方展示解题步骤</div>'

    def _assemble_html(self, title: str, steps_html: str, summary_html: str, video_html: str) -> str:
        """Assemble final HTML page."""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, 'PingFang SC', sans-serif; background:#0a0a0f; color:#e0e0e0; }}
.container {{ max-width:1200px; margin:0 auto; padding:20px; }}
h1 {{ font-size:1.5rem; color:#64ffda; margin-bottom:20px; text-align:center; }}
.video-section {{ background:#111; border-radius:12px; overflow:hidden; margin-bottom:24px; }}
video {{ width:100%; display:block; }}
.no-video {{ padding:60px 20px; text-align:center; color:#666; font-size:1.1rem; line-height:1.8; }}
.steps-section {{ display:grid; gap:16px; }}
.step-card {{ background:#1a1a2e; border-radius:10px; padding:16px 20px; border-left:3px solid #333; transition:border-color .2s; }}
.step-card:hover {{ border-left-color:#64ffda; }}
.step-header {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; }}
.step-num {{ background:#64ffda; color:#0a0a0f; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; }}
.step-phase {{ color:#888; font-size:0.85rem; }}
.step-speech {{ font-size:0.95rem; line-height:1.6; color:#ccc; }}
.formula {{ margin:8px 0; padding:8px 12px; background:#111; border-radius:6px; overflow-x:auto; }}
.summary-card {{ background:#1a2a1a; border:1px solid #2a4a2a; border-radius:10px; padding:20px; margin-top:24px; }}
.summary-card h3 {{ color:#64ffda; margin-bottom:12px; }}
.summary-card ul {{ padding-left:20px; }}
.summary-card li {{ margin:4px 0; color:#aaa; }}
</style>
</head>
<body>
<div class="container">
    <h1>{title}</h1>
    <div class="video-section">{video_html}</div>
    <div class="steps-section">{steps_html}</div>
    {summary_html}
</div>
<script>
document.addEventListener("DOMContentLoaded", function() {{
    renderMathInElement(document.body, {{
        delimiters: [
            {{left: "$$", right: "$$", display: true}},
            {{left: "$", right: "$", display: false}}
        ]
    }});
}});
</script>
</body>
</html>"""
