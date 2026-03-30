"""Scene data generation: LLM prompt + JSON extraction."""

from __future__ import annotations

import json
import logging
import re
import textwrap
from typing import Optional

from .llm import call_llm

log = logging.getLogger("pipeline.scene")

# --- Schema doc and system prompt ---
SCENE_DATA_SCHEMA_DOC = ""
SYSTEM_PROMPT_TEMPLATE = ""


def _init_prompts():
    """Initialise the prompt constants. Called once at import time."""
    global SCENE_DATA_SCHEMA_DOC, SYSTEM_PROMPT_TEMPLATE
    pass


def _extract_json(text: str) -> dict:
    """Extract and repair JSON from LLM output."""
    # Step 1: Extract from markdown code blocks
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    candidate = m.group(1).strip() if m else text.strip()

    # Step 2: Find outermost braces
    first = candidate.find("{")
    last = candidate.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = candidate[first : last + 1]

    # Try direct parse
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as parse_error:
        log.warning("JSON 直接解析失败：%s — 尝试修复", parse_error)

        # Fix 1: Handle "Extra data" error - multiple JSON objects
        if "Extra data" in str(parse_error):
            depth = 0
            end_pos = 0
            for i, ch in enumerate(candidate):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                candidate = candidate[:end_pos]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

        # Fix 2: Handle trailing comma
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    # Fix 3: Fix class='t' syntax (common in HTML-containing JSON)
    fixed = re.sub(r"class='t'", r'class=\\"t\\"', candidate)
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    fixed = re.sub(r"}\s*{", r"},{", fixed)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Fix 4: Remove control characters and fix invalid escapes
    fixed = re.sub(r"[\x00-\x1f]", " ", candidate)
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    # Fix invalid escape sequences
    fixed = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4}|[0-9])', r'\\\\', fixed)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Fix 5: Aggressive cleaning
    try:
        fixed = re.sub(r'\\(["\\])', r'\\\\\1', candidate)
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        return json.loads(fixed)
    except Exception as e2:
        log.error("JSON 修复失败，前 2000 字:\n%s", candidate[:2000])
        log.error("原始错误：%s", e2)
        raise


async def generate_scene_data(problem: str, teaching_data: str, answer: Optional[str] = None) -> dict:
    """Call LLM to produce structured scene_data JSON."""
    log.info("调用 LLM 生成场景数据 (model=%s) ...", "")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        teaching_data=teaching_data if teaching_data else "（暂无教学数据）",
        schema_doc=SCENE_DATA_SCHEMA_DOC,
    )

    user_content = f"题目：\n{problem}"
    if answer:
        user_content += f"\n\n参考答案：\n{answer}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    raw = await call_llm(messages, temperature=0.1, max_tokens=16000)
    scene = _extract_json(raw)

    for required in ("vertices", "solution_script"):
        if required not in scene:
            raise ValueError(f"LLM 返回的 JSON 缺少必要字段：{required}")

    n_verts = len(scene.get("vertices", {}))
    n_steps = len(scene.get("solution_script", []))
    log.info("场景数据：%d 个顶点，%d 个教学步骤", n_verts, n_steps)
    return scene


# ============================================================
# Prompt constants
# ============================================================

SCENE_DATA_SCHEMA_DOC = r"""
你必须输出 **严格合法的 JSON**，顶层 key 说明如下（不可省略任何 key，值为空时使用空数组/对象）：

```
{
  "title": "string",
  "problem_html": "string",
  "questions": [{"label":"(1)","html":"..."}],
  "vertices": {"A":[x,y,z], ...},
  "vertex_styles": {"A":{...}},
  "base_edges_solid": [["A","B"],...],
  "base_edges_dashed": [["A","C"],...],
  "base_edges_special": [{"from":"P","to":"A","color":"0xff4444","width":2}],
  "base_face_vertices": ["A","B","C","D"],
  "right_angles": [{"vertex":"A","dir1_toward":"B","dir2_toward":"P"}],
  "lines": [{"id":"ln_PA","from":"P","to":"A"}],
  "planes": [{"id":"pl_PBC","vertices":["P","B","C"]}],
  "coord_system": {"origin":"A","axes":[...]},
  "vectors": [{"id":"vec_AD","from":"A","to":"D"}],
  "normals": [{"id":"nrm_ACP","center_vertices":["A","C","P"]}],
  "shapes": [{"type":"frustum",...}],
  "face_defs": [{"name":"ABCD","pts":["A","B","C","D"]}],
  "all_edges": [["A","B"],...],
  "all_planes": [{"name":"ABCD","pts":["A","B","C","D"]}],
  "detail_rules": [{"condition":{"all":["ln_AD"]},"content":[]}],
  "sticky_elements": ["coord_axes"],
  "initial_camera": {"position":[5,4,5],"target":[0,0,0]},
  "solution_script": [{"phase":"审题","speech":"...","els":[],"cam":[]}]
}
```
"""

SYSTEM_PROMPT_TEMPLATE = textwrap.dedent("""\
你是一位高中数学名师 + 3D 可视化工程师。

任务：根据给定的立体几何题目，生成一份完整的 JSON 场景数据。

=== 教学方法论 ===
{teaching_data}

=== 输出 JSON 格式说明 ===
{schema_doc}

=== 重要约束 ===
1. 坐标精确：√3=1.7320508，√2=1.4142136
2. 使用 Three.js 坐标系（x 向右，y 向上，z 向前）
3. solution_script 必须 18-26 步
4. speech 口语化，30-80 字
5. id 前缀：ln_/pl_/vec_/nrm_
6. problem_html 中几何元素用 <span class='t' data-el='id'>$公式$</span> 包裹
7. 只输出 JSON，无解释
""")
