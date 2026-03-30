"""Video library matcher — matches problems to pre-recorded lecture videos.

For subjects/topics that are best served by curated human-recorded videos
rather than auto-generated content (e.g., 高考冲刺综合).
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from typing import Optional

from . import RendererBase
from ..llm import call_llm

log = logging.getLogger("renderers.video")

# ============================================================
# Schema for video matching
# ============================================================

VIDEO_SCHEMA_DOC = r"""
你必须输出**严格合法的 JSON**，用于匹配预录制的教学视频。

```json
{
  "title": "题目简短标题",
  "problem_tex": "题目 LaTeX",
  "analysis": {
    "subject": "学科",
    "type": "题型",
    "methods": ["涉及的方法"],
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "difficulty": "易/中档/拔高"
  },
  "solution_steps": [
    {
      "phase": "审题/分析/求解/总结",
      "speech": "讲解文本（口语化，30-80字）",
      "math": [
        {"type": "tex", "v": "LaTeX公式"},
        {"type": "desc", "v": "文字说明"}
      ]
    }
  ],
  "summary": {
    "key_formula": "$核心公式$",
    "method_name": "方法名称",
    "tips": ["注意点1"]
  }
}
```

### 约束：
- solution_steps 必须完整展示解题过程（8-15步）
- speech 要口语化
- 只输出 JSON
"""

VIDEO_SYSTEM_PROMPT = textwrap.dedent("""\
你是一位高中数学名师。

任务：根据给定题目，生成结构化的解题过程 JSON，用于匹配教学视频和生成文字讲解。

=== 教学方法论 ===
{teaching_data}

=== 输出 JSON 格式 ===
{schema_doc}

=== 重要约束 ===
1. 解题过程必须完整，不能跳步。
2. speech 要像老师自然讲课。
3. keywords 用于匹配视频库中的标签。
4. 只输出 JSON。
""")


class VideoRenderer(RendererBase):
    """Renderer that matches to pre-recorded videos or generates text-based lectures."""

    name = "video"

    def __init__(self):
        self._library = None
        self._library_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "video_library", "index.json"
        )

    def _load_library(self) -> list[dict]:
        """Load video library index."""
        if self._library is not None:
            return self._library

        path = os.path.normpath(self._library_path)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                self._library = json.load(f).get("videos", [])
        else:
            self._library = []
            log.warning("视频库索引不存在: %s", path)

        return self._library

    def get_prompt_schema(self) -> str:
        return VIDEO_SCHEMA_DOC

    def get_system_prompt(self, teaching_data: str) -> str:
        return VIDEO_SYSTEM_PROMPT.format(
            teaching_data=teaching_data or "（暂无教学数据）",
            schema_doc=self.get_prompt_schema(),
        )

    async def parse_llm_output(self, raw: str) -> dict:
        """Extract analysis JSON from LLM output."""
        from ..scene import _extract_json
        data = _extract_json(raw)

        if "solution_steps" not in data:
            raise ValueError("LLM 返回的 JSON 缺少 'solution_steps' 字段")

        log.info("视频匹配数据: %d 个解题步骤", len(data.get("solution_steps", [])))
        return data

    def _match_video(self, data: dict) -> Optional[dict]:
        """Match analysis keywords against video library. Returns best match or None."""
        library = self._load_library()
        if not library:
            return None

        analysis = data.get("analysis", {})
        keywords = set(analysis.get("keywords", []))
        subject = analysis.get("subject", "")
        type_name = analysis.get("type", "")
        methods = set(analysis.get("methods", []))

        best_match = None
        best_score = 0

        for video in library:
            score = 0
            vtags = set(video.get("tags", []))
            vsubject = video.get("subject", "")
            vtype = video.get("type", "")

            # Subject match: +5
            if vsubject == subject:
                score += 5
            # Type match: +3
            if vtype == type_name:
                score += 3
            # Keyword overlap
            score += len(keywords & vtags) * 2
            # Method overlap
            vmethods = set(video.get("methods", []))
            score += len(methods & vmethods) * 3

            if score > best_score:
                best_score = score
                best_match = video

        if best_match and best_score >= 5:
            log.info("视频匹配成功: %s (score=%d)", best_match.get("title", ""), best_score)
            return best_match

        log.info("未找到匹配视频 (best_score=%d)", best_score)
        return None

    async def render(self, data: dict, output_dir: str) -> str:
        """Match video or generate text-based lecture HTML."""
        os.makedirs(output_dir, exist_ok=True)

        # Save analysis data
        json_path = os.path.join(output_dir, "analysis.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Try to match a video
        matched = self._match_video(data)

        # Generate HTML
        html_path = os.path.join(output_dir, "index.html")
        html = self._generate_html(data, matched)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        log.info("视频渲染完成: %s (matched=%s)", html_path, matched is not None)
        return html_path

    def _generate_html(self, data: dict, matched_video: Optional[dict]) -> str:
        """Generate HTML page with matched video or text-based solution."""
        title = data.get("title", "数学讲解")
        steps = data.get("solution_steps", [])
        summary = data.get("summary", {})

        # Video section
        if matched_video:
            video_url = matched_video.get("url", "")
            timestamps = matched_video.get("timestamps", [])
            ts_html = ""
            for ts in timestamps:
                t = ts.get("time", "0:00")
                label = ts.get("label", "")
                ts_html += f'<a class="ts-link" href="#" data-time="{t}">{t} - {label}</a>'

            video_section = f"""
            <div class="video-section">
                <video id="lecture-video" controls>
                    <source src="{video_url}" type="video/mp4">
                </video>
                <div class="timestamps">{ts_html}</div>
            </div>"""
        else:
            video_section = '<div class="no-video-banner">暂无匹配的录制视频，以下为 AI 生成的文字讲解</div>'

        # Steps
        steps_html = ""
        for i, step in enumerate(steps):
            phase = step.get("phase", "")
            speech = step.get("speech", "")
            math_items = step.get("math", [])

            math_html = ""
            for item in math_items:
                if item.get("type") == "tex":
                    math_html += f'<div class="formula">$${item["v"]}$$</div>'
                else:
                    math_html += f'<p class="math-desc">{item.get("v", "")}</p>'

            steps_html += f"""
            <div class="step-card">
                <div class="step-header">
                    <span class="step-num">Step {i+1}</span>
                    <span class="step-phase">{phase}</span>
                </div>
                <p class="step-speech">{speech}</p>
                {math_html}
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
.container {{ max-width:1000px; margin:0 auto; padding:20px; }}
h1 {{ font-size:1.5rem; color:#64ffda; margin-bottom:20px; text-align:center; }}
.video-section {{ background:#111; border-radius:12px; overflow:hidden; margin-bottom:24px; }}
video {{ width:100%; display:block; }}
.timestamps {{ padding:12px 16px; display:flex; flex-wrap:wrap; gap:8px; }}
.ts-link {{ color:#64ffda; text-decoration:none; font-size:0.85rem; padding:4px 8px; background:#1a2a2a; border-radius:4px; }}
.ts-link:hover {{ background:#2a3a3a; }}
.no-video-banner {{ padding:40px; text-align:center; color:#888; background:#111; border-radius:12px; margin-bottom:24px; }}
.steps-section {{ display:grid; gap:16px; }}
.step-card {{ background:#1a1a2e; border-radius:10px; padding:16px 20px; border-left:3px solid #333; }}
.step-card:hover {{ border-left-color:#64ffda; }}
.step-header {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; }}
.step-num {{ background:#64ffda; color:#0a0a0f; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; }}
.step-phase {{ color:#888; font-size:0.85rem; }}
.step-speech {{ font-size:0.95rem; line-height:1.6; color:#ccc; }}
.formula {{ margin:8px 0; padding:8px 12px; background:#111; border-radius:6px; overflow-x:auto; }}
.math-desc {{ color:#aaa; font-size:0.9rem; margin:4px 0; }}
.summary-card {{ background:#1a2a1a; border:1px solid #2a4a2a; border-radius:10px; padding:20px; margin-top:24px; }}
.summary-card h3 {{ color:#64ffda; margin-bottom:12px; }}
.summary-card ul {{ padding-left:20px; }}
.summary-card li {{ margin:4px 0; color:#aaa; }}
</style>
</head>
<body>
<div class="container">
    <h1>{title}</h1>
    {video_section}
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
    // Timestamp click handler
    document.querySelectorAll(".ts-link").forEach(function(el) {{
        el.addEventListener("click", function(e) {{
            e.preventDefault();
            var video = document.getElementById("lecture-video");
            if (!video) return;
            var parts = this.dataset.time.split(":");
            var seconds = parseInt(parts[0]) * 60 + parseInt(parts[1] || 0);
            video.currentTime = seconds;
            video.play();
        }});
    }});
}});
</script>
</body>
</html>"""
