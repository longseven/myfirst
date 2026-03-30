"""Load teaching methodology markdown files — three-level hierarchy.

Directory structure:
    teaching_data/
    ├── _通用/解题通用建议.md          (always loaded)
    ├── {学科}/_通用.md                (when subject detected)
    ├── {学科}/{题型}/_概述.md          (when type detected)
    └── {学科}/{题型}/{方法}.md          (when type detected, load all methods)
"""

from __future__ import annotations

import os
import logging
from typing import Optional

log = logging.getLogger("pipeline.teaching")


def _read(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_dir_methods(dir_path: str) -> str:
    """Load _概述.md + all method .md files in a type directory."""
    parts: list[str] = []

    overview = _read(os.path.join(dir_path, "_概述.md"))
    if overview:
        parts.append(overview)

    if os.path.isdir(dir_path):
        for fname in sorted(os.listdir(dir_path)):
            if fname.startswith("_") or not fname.endswith(".md"):
                continue
            content = _read(os.path.join(dir_path, fname))
            if content:
                method_name = fname.replace(".md", "")
                parts.append(f"### 方法: {method_name}\n\n{content}")

    return "\n\n".join(parts)


def load_teaching_data(
    detected: list[tuple[str, list[str]]],
    data_dir: str,
) -> str:
    """
    Load teaching markdown based on detection results.

    Args:
        detected: Output from detect_subject_and_types(), e.g.
                  [("立体几何", ["空间平行与垂直证明", "空间向量求角度距离"])]
        data_dir: Path to teaching_data/ root directory.

    Returns:
        Aggregated teaching text for prompt injection.
    """
    parts: list[str] = []

    # 1. Always load general advice
    general = _read(os.path.join(data_dir, "_通用", "解题通用建议.md"))
    if general:
        parts.append(f"# 通用解题建议\n\n{general}")

    # 2. Per-subject loading
    for subject, types in detected:
        if subject == "混合":
            continue

        subject_dir = os.path.join(data_dir, subject)
        if not os.path.isdir(subject_dir):
            log.warning("学科目录不存在: %s", subject_dir)
            continue

        # 2a. Subject overview
        subj_overview = _read(os.path.join(subject_dir, "_通用.md"))
        if subj_overview:
            parts.append(f"# {subject} 学科概览\n\n{subj_overview}")

        # 2b. Per problem-type content
        if types:
            for type_name in types:
                type_dir = os.path.join(subject_dir, type_name)
                if not os.path.isdir(type_dir):
                    log.warning("题型目录不存在: %s/%s", subject, type_name)
                    continue
                type_content = _load_dir_methods(type_dir)
                if type_content:
                    parts.append(f"## {subject} → {type_name}\n\n{type_content}")
        else:
            # Subject matched but no specific type — load all type overviews
            for entry in sorted(os.listdir(subject_dir)):
                entry_path = os.path.join(subject_dir, entry)
                if os.path.isdir(entry_path) and not entry.startswith("_"):
                    overview = _read(os.path.join(entry_path, "_概述.md"))
                    if overview:
                        parts.append(f"## {subject} → {entry} (概述)\n\n{overview}")

    result = "\n\n---\n\n".join(parts)
    log.info("加载教学数据: %d 字符, 来自 %d 个模块", len(result), len(parts))
    return result


def load_teaching_data_legacy(types: list[str], data_dir: str) -> str:
    """Backward-compatible wrapper for old-style flat type list."""
    from .detector import SUBJECT_TYPES

    # Attempt to map flat type names back to (subject, types) pairs
    subject_map: dict[str, list[str]] = {}
    for flat_type in types:
        found = False
        for subject, cfg in SUBJECT_TYPES.items():
            if flat_type in cfg["types"]:
                subject_map.setdefault(subject, []).append(flat_type)
                found = True
                break
            if flat_type == subject:
                subject_map.setdefault(subject, [])
                found = True
                break
        if not found:
            subject_map.setdefault(flat_type, [])

    detected = [(s, ts) for s, ts in subject_map.items()]
    return load_teaching_data(detected, data_dir)
