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

log = logging.getLogger("renderers.manim")


# ============================================================
# Manim scene_data JSON schema (tells LLM what to output)
# ============================================================

MANIM_SCHEMA_DOC = r"""
你必须输出**严格合法的 JSON**，用于生成数学教学动画视频。顶层结构：

```json
{
  "title": "题目简短标题",
  "problem_tex": "题目 LaTeX 表示",
  "scenes": [
    {
      "phase": "审题/分析/求解/验证/总结",
      "speech": "这一步的讲解文本（口语化，30-80字）",
      "animations": [
        // 动画指令列表，按顺序执行
      ]
    }
  ],
  "summary": {
    "key_formula": "$核心公式$",
    "method_name": "方法名称",
    "tips": ["注意点1", "注意点2"]
  }
}
```

### animations 指令类型：

1. **write_tex** — 书写公式
   `{"type": "write_tex", "tex": "f(x) = x^3 - 3x + 1", "position": "UP", "color": "BLUE"}`

2. **transform_tex** — 公式变换（上一行 → 下一行）
   `{"type": "transform_tex", "from_tex": "f'(x) = 3x^2 - 3", "to_tex": "3x^2 - 3 = 0"}`

3. **draw_axes** — 绘制坐标轴
   `{"type": "draw_axes", "x_range": [-3, 3, 1], "y_range": [-5, 5, 1], "x_label": "x", "y_label": "y"}`

4. **plot_function** — 绘制函数图像
   `{"type": "plot_function", "expr": "x**3 - 3*x + 1", "x_range": [-2.5, 2.5], "color": "BLUE"}`

5. **mark_point** — 标注点
   `{"type": "mark_point", "x": 1, "y": -1, "label": "极小值(-1)", "color": "RED"}`

6. **highlight_interval** — 高亮区间
   `{"type": "highlight_interval", "x_from": -1, "x_to": 1, "label": "递减区间", "color": "YELLOW"}`

7. **draw_line** — 绘制直线/线段
   `{"type": "draw_line", "start": [0, 0], "end": [3, 4], "color": "GREEN", "label": "AB"}`

8. **draw_triangle** — 绘制三角形
   `{"type": "draw_triangle", "vertices": [[0,0], [3,0], [1.5, 2.6]], "labels": ["A", "B", "C"], "color": "WHITE"}`

9. **draw_angle** — 标注角
   `{"type": "draw_angle", "vertex": [0,0], "p1": [3,0], "p2": [1.5, 2.6], "label": "60°", "color": "YELLOW"}`

10. **draw_table** — 绘制表格
    `{"type": "draw_table", "headers": ["x", "f'(x)", "f(x)"], "rows": [["(-∞,-1)", "+", "↑"], ["(-1,1)", "-", "↓"]], "title": "单调性表"}`

11. **fade_out** — 淡出当前所有元素
    `{"type": "fade_out"}`

12. **pause** — 暂停
    `{"type": "pause", "duration": 1.0}`

13. **write_text** — 书写普通文本
    `{"type": "write_text", "text": "关键结论", "position": "DOWN", "color": "YELLOW"}`

14. **draw_number_line** — 数轴标根法
    `{"type": "draw_number_line", "range": [-5, 5], "marks": [{"x": -1, "label": "-1"}, {"x": 1, "label": "1"}], "signs": [{"interval": "(-∞,-1)", "sign": "+"}, {"interval": "(-1,1)", "sign": "-"}]}`

15. **draw_tree** — 树形图（概率）
    `{"type": "draw_tree", "root": "开始", "branches": [{"label": "A(0.6)", "children": [{"label": "B(0.3)"}, {"label": "B̄(0.7)"}]}, {"label": "Ā(0.4)", "children": []}]}`

### 约束：
- scenes 必须 8-20 个步骤
- phase 标签: 审题(1-2步)、分析(1-2步)、求解(4-10步)、验证(0-2步)、总结(1-2步)
- speech 要口语化，像老师讲课
- 公式用标准 LaTeX
- 只基于题目内容生成，不编造
- 只输出 JSON
"""


# ============================================================
# System prompt template
# ============================================================

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
        # Reuse the robust JSON extractor
        from ..scene import _extract_json
        data = _extract_json(raw)

        if "scenes" not in data:
            raise ValueError("LLM 返回的 JSON 缺少 'scenes' 字段")

        n_scenes = len(data.get("scenes", []))
        total_anims = sum(len(s.get("animations", [])) for s in data["scenes"])
        log.info("Manim 数据: %d 个场景, %d 个动画指令", n_scenes, total_anims)
        return data

    async def render(self, data: dict, output_dir: str) -> str:
        """Convert manim_data → Python script → render → HTML player.

        If Manim is not installed, falls back to a static HTML presentation.
        """
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

        log.info("Manim 渲染完成: %s", html_path)
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

        for i, scene in enumerate(data.get("scenes", [])):
            phase = scene.get("phase", "")
            speech = scene.get("speech", "")
            lines.append(f'')
            lines.append(f'        # === {phase} ===')
            lines.append(f'        # {speech[:60]}...')

            axes_var = None
            last_tex_var = None

            for j, anim in enumerate(scene.get("animations", [])):
                atype = anim.get("type", "")
                var = f"obj_{i}_{j}"

                if atype == "write_tex":
                    tex = anim.get("tex", "")
                    color = anim.get("color", "WHITE")
                    lines.append(f'        {var} = MathTex(r"{tex}", color={color})')
                    pos = anim.get("position", "")
                    if pos:
                        lines.append(f'        {var}.to_edge({pos})')
                    lines.append(f'        self.play(Write({var}))')
                    lines.append(f'        self.wait(0.5)')
                    last_tex_var = var

                elif atype == "transform_tex":
                    from_tex = anim.get("from_tex", "")
                    to_tex = anim.get("to_tex", "")
                    if last_tex_var:
                        lines.append(f'        {var} = MathTex(r"{to_tex}")')
                        lines.append(f'        self.play(TransformMatchingTex({last_tex_var}, {var}))')
                        lines.append(f'        self.wait(0.5)')
                        last_tex_var = var
                    else:
                        lines.append(f'        {var} = MathTex(r"{to_tex}")')
                        lines.append(f'        self.play(Write({var}))')
                        last_tex_var = var

                elif atype == "draw_axes":
                    xr = anim.get("x_range", [-5, 5, 1])
                    yr = anim.get("y_range", [-5, 5, 1])
                    axes_var = var
                    lines.append(f'        {var} = Axes(x_range={xr}, y_range={yr}, axis_config={{"include_numbers": True}})')
                    xl = anim.get("x_label", "x")
                    yl = anim.get("y_label", "y")
                    lines.append(f'        {var}_labels = {var}.get_axis_labels(x_label="{xl}", y_label="{yl}")')
                    lines.append(f'        self.play(Create({var}), Write({var}_labels))')

                elif atype == "plot_function":
                    expr = anim.get("expr", "x")
                    color = anim.get("color", "BLUE")
                    xr = anim.get("x_range", None)
                    if axes_var:
                        if xr:
                            lines.append(f'        {var} = {axes_var}.plot(lambda x: {expr}, x_range={xr}, color={color})')
                        else:
                            lines.append(f'        {var} = {axes_var}.plot(lambda x: {expr}, color={color})')
                        lines.append(f'        self.play(Create({var}))')

                elif atype == "mark_point":
                    x = anim.get("x", 0)
                    y = anim.get("y", 0)
                    label = anim.get("label", "")
                    color = anim.get("color", "RED")
                    if axes_var:
                        lines.append(f'        {var}_dot = Dot({axes_var}.c2p({x}, {y}), color={color})')
                        lines.append(f'        {var}_label = MathTex(r"{label}", color={color}).next_to({var}_dot, UR, buff=0.1)')
                        lines.append(f'        self.play(Create({var}_dot), Write({var}_label))')

                elif atype == "draw_triangle":
                    verts = anim.get("vertices", [[0,0], [3,0], [1.5, 2.6]])
                    labels = anim.get("labels", ["A", "B", "C"])
                    color = anim.get("color", "WHITE")
                    pts = ", ".join([f"[{v[0]}, {v[1]}, 0]" for v in verts])
                    lines.append(f'        {var} = Polygon({pts}, color={color})')
                    lines.append(f'        self.play(Create({var}))')
                    for k, lbl in enumerate(labels):
                        lines.append(f'        {var}_l{k} = Text("{lbl}", font_size=24).next_to({var}.get_vertices()[{k}], direction=normalize({var}.get_vertices()[{k}]), buff=0.2)')
                        lines.append(f'        self.play(Write({var}_l{k}), run_time=0.3)')

                elif atype == "draw_table":
                    headers = anim.get("headers", [])
                    rows = anim.get("rows", [])
                    title_str = anim.get("title", "")
                    h_str = str(headers)
                    r_str = str(rows)
                    lines.append(f'        {var} = Table({r_str}, col_labels=[MathTex(h) for h in {h_str}])')
                    if title_str:
                        lines.append(f'        {var}_title = Text("{title_str}", font_size=28).next_to({var}, UP)')
                        lines.append(f'        self.play(Create({var}), Write({var}_title))')
                    else:
                        lines.append(f'        self.play(Create({var}))')

                elif atype == "write_text":
                    text = anim.get("text", "")
                    color = anim.get("color", "YELLOW")
                    lines.append(f'        {var} = Text("{text}", color={color}, font_size=30)')
                    pos = anim.get("position", "DOWN")
                    if pos:
                        lines.append(f'        {var}.to_edge({pos})')
                    lines.append(f'        self.play(Write({var}))')

                elif atype == "fade_out":
                    lines.append(f'        self.play(*[FadeOut(mob) for mob in self.mobjects])')

                elif atype == "pause":
                    dur = anim.get("duration", 1.0)
                    lines.append(f'        self.wait({dur})')

                elif atype == "highlight_interval":
                    if axes_var:
                        x_from = anim.get("x_from", 0)
                        x_to = anim.get("x_to", 1)
                        color = anim.get("color", "YELLOW")
                        label = anim.get("label", "")
                        lines.append(f'        {var} = {axes_var}.get_area({axes_var}.plot(lambda x: 0), x_range=[{x_from}, {x_to}], color={color}, opacity=0.3)')
                        lines.append(f'        self.play(FadeIn({var}))')
                        if label:
                            lines.append(f'        {var}_l = Text("{label}", font_size=20, color={color}).next_to({var}, DOWN)')
                            lines.append(f'        self.play(Write({var}_l))')

            lines.append(f'        self.wait(1)')

        lines.append('')
        return '\n'.join(lines)

    async def _run_manim(self, script_path: str, output_dir: str) -> Optional[str]:
        """Execute manim render command. Returns video path or None."""
        # Get the scene class name from the script
        with open(script_path, "r") as f:
            content = f.read()
        m = re.search(r'class (\w+)\(Scene\)', content)
        if not m:
            raise RuntimeError("Manim script 中未找到 Scene 类")
        class_name = m.group(1)

        cmd = [
            "manim", "render", "-qm",  # medium quality
            "--media_dir", output_dir,
            script_path, class_name,
        ]

        log.info("执行 Manim: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if proc.returncode != 0:
            log.error("Manim stderr: %s", proc.stderr[:1000])
            raise RuntimeError(f"Manim 渲染失败: {proc.stderr[:500]}")

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

        # Build step cards HTML
        steps_html = ""
        for i, scene in enumerate(scenes):
            # Support both old (animations) and new (instructions) field names
            phase = scene.get("phase") or scene.get("title", "")
            speech = scene.get("speech", "")
            anims = scene.get("instructions") or scene.get("animations", [])

            # Extract formulas from animations/instructions
            formulas = []
            for a in anims:
                if a.get("type") in ("write_tex", "transform_tex"):
                    tex = a.get("tex") or a.get("to_tex", "")
                    if tex:
                        formulas.append(tex)

            formulas_html = "".join(f'<div class="formula">$${f}$$</div>' for f in formulas)

            steps_html += f"""
            <div class="step-card" data-step="{i}">
                <div class="step-header">
                    <span class="step-num">Step {i+1}</span>
                    <span class="step-phase">{phase}</span>
                </div>
                <p class="step-speech">{speech}</p>
                {formulas_html}
            </div>"""

        # Summary
        summary_html = ""
        if summary:
            key_formula = summary.get("key_formula", "")
            method = summary.get("method_name", "")
            tips = summary.get("tips", [])
            tips_html = "".join(f"<li>{t}</li>" for t in tips)
            summary_html = f"""
            <div class="summary-card">
                <h3>总结</h3>
                <p><strong>方法</strong>: {method}</p>
                <div class="formula">$${key_formula}$$</div>
                <ul>{tips_html}</ul>
            </div>"""

        # Video element
        if video_path:
            video_rel = os.path.basename(video_path)
            video_html = f'<video id="lecture-video" controls><source src="{video_rel}" type="video/mp4"></video>'
        else:
            video_html = '<div class="no-video">动画视频暂未生成（需安装 Manim）<br>下方展示解题步骤</div>'

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
