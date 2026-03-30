"""Inject scene_data JSON into the Three.js template."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from ..config import settings

log = logging.getLogger("pipeline.assembler")

PLACEHOLDER = "/*__SCENE_DATA__*/"


def assemble_html(scene_data: dict, template_path: Optional[str] = None) -> str:
    """Return a complete HTML string with scene_data injected."""
    if template_path is None:
        template_path = settings.template_path

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"模板文件不存在: {template_path}")

    with open(template_path, "r", encoding="utf-8") as fh:
        template = fh.read()

    json_str = json.dumps(scene_data, ensure_ascii=False, indent=2)

    if PLACEHOLDER in template:
        html = template.replace(PLACEHOLDER, f"window.sceneData = {json_str};")
    else:
        inject = f"<script>window.sceneData = {json_str};</script>\n</head>"
        html = template.replace("</head>", inject, 1)

    log.info("HTML 组装完成 (%d 字符)", len(html))
    return html
