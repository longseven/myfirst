"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment."""
    # Set test mode environment variable
    os.environ["TESTING"] = "true"
    yield
    # Cleanup if needed


@pytest.fixture
def sample_problem_derivative():
    """Sample derivative problem."""
    return "已知函数 f(x) = x³ - 3x + 1，求：(1) 单调区间；(2) 极值"


@pytest.fixture
def sample_problem_geometry():
    """Sample solid geometry problem."""
    return "四棱锥 P-ABCD 中，PA⊥底面 ABCD，底面 ABCD 是正方形，PA=AB=2"


@pytest.fixture
def sample_problem_trig():
    """Sample trigonometry problem."""
    return "已知 sinα = 3/5，α∈(0, π/2)，求 cosα 和 tanα"


@pytest.fixture
def sample_manim_data():
    """Sample Manim output structure."""
    return {
        "title": "函数讲解",
        "scenes": [
            {
                "scene_id": 1,
                "title": "引入",
                "speech": "我们来学习这个函数",
                "instructions": [
                    {"type": "write_tex", "tex": "f(x) = x²"}
                ]
            }
        ],
        "summary": {
            "key_formula": "f(x) = x²",
            "method_name": "配方法",
            "tips": ["注意开口方向"]
        }
    }


@pytest.fixture
def sample_scene_data():
    """Sample Three.js scene data structure."""
    return {
        "title": "立体几何题",
        "problem_html": "四棱锥 P-ABCD",
        "questions": [{"label": "(1)", "html": "证明 PC⊥BD"}],
        "vertices": {
            "A": [0, 0, 0],
            "B": [2, 0, 0],
            "C": [2, 2, 0],
            "D": [0, 2, 0],
            "P": [1, 1, 2]
        },
        "vertex_styles": {},
        "base_edges_solid": [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]],
        "base_edges_dashed": [],
        "base_edges_special": [],
        "base_face_vertices": ["A", "B", "C", "D"],
        "right_angles": [],
        "lines": [],
        "planes": [],
        "coord_system": {"origin": "A", "axes": []},
        "vectors": [],
        "normals": [],
        "shapes": [],
        "face_defs": [],
        "all_edges": [],
        "all_planes": [],
        "detail_rules": [],
        "sticky_elements": [],
        "initial_camera": {"position": [5, 4, 5], "target": [0, 0, 0]},
        "solution_script": [
            {"phase": "审题", "speech": "分析题目条件", "els": [], "cam": []}
        ]
    }
