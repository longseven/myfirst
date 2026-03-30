"""Problem type detection via keyword matching + feature fallback."""

from __future__ import annotations

import re
import logging

log = logging.getLogger("pipeline.detector")

# ── Subject → Problem-type keyword registry ─────────────────────────────

SUBJECT_TYPES: dict[str, dict] = {
    "立体几何": {
        "subject_keywords": [
            "棱锥", "棱柱", "正方体", "长方体", "四面体", "三棱",
            "底面", "侧面", "PA⊥", "空间几何", "立体几何",
            "圆台", "圆锥", "圆柱", "母线",
            "翻折", "二面角", "面.*面.*角",
        ],
        "types": {
            "空间平行与垂直证明": {
                "keywords": [
                    "线面平行", "面面平行", "平行.*证明", "证明.*平行",
                    "垂直", "⊥", "证明.*垂直", "垂直.*证明",
                    "面面垂直", "线面垂直", "∥",
                ],
            },
            "空间向量求角度距离": {
                "keywords": [
                    "异面直线.*角", "线面角", "二面角", "所成.*角",
                    "余弦值", "正弦值", "二面角.*余弦", "二面角.*正弦",
                    "距离", "点.*面.*距", "线.*面.*距", "点到.*距离",
                ],
            },
            "外接球问题": {
                "keywords": ["外接球", "球.*半径", "球.*表面积", "球.*体积", "内切球"],
            },
        },
    },
    "三角函数": {
        "subject_keywords": [
            r"sin\b", r"cos\b", r"tan\b", "三角函数", "周期", "振幅",
            r"Asin", "sinx", "cosx", "tanx", "诱导公式",
        ],
        "types": {
            "三角函数基础概念": {
                "keywords": ["定义域", "值域", "周期", "单调", "图象", "奇偶"],
            },
            "三角恒等变换": {
                "keywords": [
                    "和差", "二倍角", "辅助角", "化简", "降幂",
                    "恒等变换", "和角", "差角", "积化和差", "和差化积",
                ],
            },
            "Asin 模型": {
                "keywords": [
                    r"Asin\(", r"ωx\+φ", "平移", "伸缩", "振幅",
                    "相位", "频率", "角频率",
                ],
            },
        },
    },
    "函数": {
        "subject_keywords": [
            "函数", "定义域", "值域", "单调性", "奇偶性", "对称性",
            "零点", "指数函数", "对数函数", "幂函数", r"f\(x\)",
        ],
        "types": {
            "函数单调性与奇偶性": {
                "keywords": ["单调", "奇偶", "对称", "周期"],
            },
            "初等函数": {
                "keywords": ["指数", "对数", "幂函数", "比大小", "底数"],
            },
            "函数零点问题": {
                "keywords": ["零点", "方程的根", "交点个数"],
            },
        },
    },
    "导数": {
        "subject_keywords": [
            "导数", "导函数", r"f'\(", "切线", "极值", "极大", "极小",
            "恒成立", "隐零点", "放缩",
        ],
        "types": {
            "导数与单调性极值": {
                "keywords": ["单调", "极值", "极大", "极小", "最值", "递增", "递减"],
            },
            "导数恒成立问题": {
                "keywords": ["恒成立", "恒大于", "恒小于", "任意.*成立", "分离参数"],
            },
            "导数放缩与不等式证明": {
                "keywords": ["放缩", "不等式.*证明", "证明.*不等式", "隐零点", "极值点偏移"],
            },
        },
    },
    "解析几何": {
        "subject_keywords": [
            "椭圆", "双曲线", "抛物线", "圆锥曲线", "焦点", "准线",
            "离心率", "直线.*圆", "弦长",
        ],
        "types": {
            "直线与圆": {
                "keywords": ["直线.*圆", "圆.*直线", "弦长", "切线.*圆", "圆.*方程"],
            },
            "圆锥曲线基础": {
                "keywords": ["椭圆", "双曲线", "抛物线", "离心率", "焦点", "标准方程"],
            },
            "圆锥曲线大题": {
                "keywords": [
                    "联立", "韦达", "定点", "定值", "弦长.*面积",
                    "直线.*椭圆", "直线.*双曲线", "直线.*抛物线",
                ],
            },
        },
    },
    "数列": {
        "subject_keywords": [
            "数列", "等差", "等比", "通项", r"a_n", r"S_n", "前 n 项和",
            "公差", "公比", "递推",
        ],
        "types": {
            "等差等比数列": {
                "keywords": ["等差", "等比", "公差", "公比"],
            },
            "数列求通项与求和": {
                "keywords": ["通项", "求和", "错位相减", "裂项", "累加", "累乘"],
            },
            "数列综合": {
                "keywords": ["放缩", "不等式", "数列.*最值"],
            },
        },
    },
    "平面向量": {
        "subject_keywords": [
            "向量", "数量积", "模", "夹角", "基底", "共线",
        ],
        "types": {
            "向量基础运算与数量积": {
                "keywords": ["数量积", "模", "夹角", "坐标运算"],
            },
            "向量解题技巧": {
                "keywords": ["等和线", "极化恒等式", "三点共线"],
            },
        },
    },
    "解三角形": {
        "subject_keywords": [
            "正弦定理", "余弦定理", "△ABC", "三角形.*边",
            "三角形.*角", "解三角形",
        ],
        "types": {
            "正余弦定理基础": {
                "keywords": ["正弦定理", "余弦定理", "解的个数"],
            },
            "最值与范围": {
                "keywords": ["最值", "最大", "最小", "范围", "取值"],
            },
        },
    },
    "排列组合概率统计": {
        "subject_keywords": [
            "排列", "组合", "概率", "频率", "二项式", "方差",
            "期望", "随机变量", "分布列", "统计",
        ],
        "types": {
            "排列组合": {
                "keywords": ["排列", "组合", "二项式", "分配"],
            },
            "概率与统计": {
                "keywords": ["概率", "频率", "方差", "期望", "分布列", "抽样"],
            },
        },
    },
    "集合与不等式": {
        "subject_keywords": [
            "集合", "子集", "交集", "并集", "补集",
            "不等式", "均值不等式", "充分", "必要",
        ],
        "types": {
            "集合与逻辑": {
                "keywords": ["集合", "子集", "充分", "必要", "命题"],
            },
            "不等式": {
                "keywords": ["不等式", "均值不等式", "基本不等式"],
            },
        },
    },
    "复数": {
        "subject_keywords": ["复数", "虚数", "共轭", r"i\^"],
        "types": {
            "复数基础与运算": {
                "keywords": ["复数", "虚数", "共轭", "模"],
            },
        },
    },
}


# ── Detection API ────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """Normalize text for better matching."""
    text = text.replace("⊥", "垂直")
    text = text.replace("∥", "平行")
    text = text.replace("△", "三角形")
    text = text.replace("°", "度")
    text = re.sub(r"_\{?(\d+)\}?", r"\1", text)  # a_1 → a1
    return text


def _extract_math_features(text: str) -> dict:
    """Extract mathematical features from problem text."""
    return {
        "has_function_notation": bool(re.search(r"f\s*\(\s*x\s*\)", text)),
        "has_derivative": bool(re.search(r"f\s*'\s*\(", text)) or "导数" in text,
        "has_integral": bool(re.search(r"∫|积分", text)),
        "has_vector": bool(re.search(r"向量 |→|⃗|boldsymbol", text)),
        "has_geometry_3d": bool(re.search(r"棱 | 锥 | 柱 | 面 | 空间", text)),
        "has_trig": bool(re.search(r"sin|cos|tan|三角", text)),
        "has_sequence": bool(re.search(r"a_\d|S_\d|数列 | 等差 | 等比", text)),
        "has_probability": bool(re.search(r"概率 | 分布 | 期望 | 方差", text)),
    }


def detect_subject_and_types(text: str) -> list[tuple[str, list[str]]]:
    """Return [(subject, [type1, ...]), ...] with two-stage detection."""
    normalized = _normalize_text(text)
    features = _extract_math_features(text)
    results: list[tuple[str, list[str]]] = []

    for subject, cfg in SUBJECT_TYPES.items():
        subject_hit = any(re.search(kw, normalized) for kw in cfg["subject_keywords"])
        if not subject_hit:
            continue

        matched_types = [
            type_name for type_name, type_cfg in cfg["types"].items()
            if any(re.search(kw, normalized) for kw in type_cfg["keywords"])
        ]
        results.append((subject, matched_types))

    # Fallback: feature-based detection
    if not results:
        log.info("关键字匹配未命中，尝试特征匹配")
        if features["has_geometry_3d"]:
            results.append(("立体几何", []))
        elif features["has_derivative"]:
            results.append(("导数", ["导数与单调性极值"]))
        elif features["has_function_notation"]:
            results.append(("函数", ["函数单调性与奇偶性"]))
        elif features["has_trig"]:
            results.append(("三角函数", ["三角函数基础概念"]))
        elif features["has_sequence"]:
            results.append(("数列", ["等差等比数列"]))
        elif features["has_probability"]:
            results.append(("排列组合概率统计", ["概率与统计"]))
        elif features["has_vector"]:
            results.append(("平面向量", ["向量基础运算与数量积"]))

    if not results:
        log.warning("关键字和特征匹配均未命中，标记为 混合")
        return [("混合", [])]

    # Merge duplicates
    subject_map: dict[str, set[str]] = {}
    for subj, types in results:
        subject_map.setdefault(subj, set()).update(types)
    merged = [(s, list(t)) for s, t in subject_map.items()]

    log.info("检测结果：%s", "; ".join(
        f"{s}: [{', '.join(t)}]" if t else s for s, t in merged
    ))
    return merged


def detect_problem_type(text: str) -> list[str]:
    """Legacy API: return flat list of type names."""
    results = detect_subject_and_types(text)
    flat: list[str] = []
    for subject, types in results:
        if types:
            flat.extend(types)
        else:
            flat.append(subject)
    return flat if flat else ["混合"]
