"""Tests for Manim instruction handlers."""

import pytest
from app.pipeline.renderers.manim_instructions import (
    init_handlers,
    get_handler,
    WriteTexHandler,
    DrawAxesHandler,
    PlotFunctionHandler,
)


class TestInstructionHandlers:
    """Test cases for individual instruction handlers."""

    def setup_method(self):
        """Initialize handlers before each test."""
        init_handlers()

    def test_write_tex_handler(self):
        """Test write_tex instruction generation."""
        handler = get_handler("write_tex")
        assert handler is not None

        anim = {"tex": "f(x) = x^2", "color": "BLUE", "position": "UP"}
        lines = handler.generate(anim, "obj_1", None)

        assert 'MathTex(r"f(x) = x^2"' in lines[0]
        assert "color=BLUE" in lines[0]
        assert "to_edge(UP)" in lines[1]
        assert "Write(obj_1)" in lines[2]

    def test_draw_axes_handler(self):
        """Test draw_axes instruction generation."""
        handler = get_handler("draw_axes")
        assert handler is not None

        anim = {
            "x_range": [-3, 3, 1],
            "y_range": [-5, 5, 1],
            "x_label": "x",
            "y_label": "y"
        }
        lines = handler.generate(anim, "axes", None)

        assert 'Axes(x_range=' in lines[0]
        assert 'get_axis_labels' in lines[1]
        assert "Create(axes)" in lines[2]

    def test_plot_function_handler(self):
        """Test plot_function instruction generation."""
        handler = get_handler("plot_function")
        assert handler is not None

        anim = {"expr": "x**2 - 1", "color": "BLUE", "x_range": [-2, 2]}
        lines = handler.generate(anim, "graph", "axes")

        assert 'axes.plot(lambda x:' in lines[0]
        assert "Create(graph)" in lines[1]

    def test_mark_point_handler(self):
        """Test mark_point instruction generation."""
        handler = get_handler("mark_point")
        assert handler is not None

        anim = {"x": 1, "y": -1, "label": "极小值", "color": "RED"}
        lines = handler.generate(anim, "point", "axes")

        assert 'Dot(axes.c2p(1, -1)' in lines[0]
        assert 'MathTex(r"极小值"' in lines[1]

    def test_fade_out_handler(self):
        """Test fade_out instruction generation."""
        handler = get_handler("fade_out")
        assert handler is not None

        lines = handler.generate({}, "obj", None)
        assert 'FadeOut(mob)' in lines[0]

    def test_pause_handler(self):
        """Test pause instruction generation."""
        handler = get_handler("pause")
        assert handler is not None

        lines = handler.generate({"duration": 2.0}, "obj", None)
        assert 'self.wait(2.0)' in lines[0]

    def test_draw_triangle_handler(self):
        """Test draw_triangle instruction generation."""
        handler = get_handler("draw_triangle")
        assert handler is not None

        anim = {
            "vertices": [[0, 0], [3, 0], [1.5, 2.6]],
            "labels": ["A", "B", "C"],
            "color": "WHITE"
        }
        lines = handler.generate(anim, "tri", None)

        assert 'Polygon(' in lines[0]
        assert 'Text("A"' in lines[2]

    def test_handler_not_found(self):
        """Test unknown instruction type returns None."""
        handler = get_handler("unknown_type_xyz")
        assert handler is None


class TestManimRendererRefactored:
    """Test cases for refactored ManimRenderer."""

    def test_generate_script_with_handlers(self):
        """Test script generation uses instruction handlers."""
        from app.pipeline.renderers.manim_ import ManimRenderer

        renderer = ManimRenderer()
        data = {
            "title": "Test Function",
            "scenes": [
                {
                    "phase": "引入",
                    "speech": "我们来学习函数",
                    "instructions": [
                        {"type": "write_tex", "tex": "f(x) = x^2", "color": "BLUE"}
                    ]
                }
            ]
        }

        script = renderer._generate_manim_script(data)

        assert 'class TestFunction(Scene):' in script
        assert 'MathTex(r"f(x) = x^2"' in script
        assert "color=BLUE" in script

    def test_generate_script_multiple_scenes(self):
        """Test script generation with multiple scenes."""
        from app.pipeline.renderers.manim_ import ManimRenderer

        renderer = ManimRenderer()
        data = {
            "title": "多步骤题目",
            "scenes": [
                {
                    "phase": "审题",
                    "speech": "第一步",
                    "instructions": [
                        {"type": "write_tex", "tex": "已知 f(x)"}
                    ]
                },
                {
                    "phase": "求解",
                    "speech": "第二步",
                    "instructions": [
                        {"type": "draw_axes"},
                        {"type": "plot_function", "expr": "x**2"}
                    ]
                }
            ]
        }

        script = renderer._generate_manim_script(data)

        assert "# === 审题 ===" in script
        assert "# === 求解 ===" in script
        assert "draw_axes" not in script  # Should be converted to actual code
        assert "Axes(" in script  # Actual generated code
