"""Manim animation instruction handlers.

Each handler generates Python code for a specific animation type.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

log = logging.getLogger("renderers.manim.instructions")


class InstructionHandler(ABC):
    """Base class for animation instruction handlers."""

    @property
    @abstractmethod
    def instruction_type(self) -> str:
        """Return the instruction type this handler handles."""
        ...

    @abstractmethod
    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        """Generate Manim Python code for this instruction.

        Args:
            anim: Animation instruction dict
            var: Variable name for the generated object
            axes_var: Optional axes variable name

        Returns:
            List of Python code lines
        """
        ...


class WriteTexHandler(InstructionHandler):
    """Handler for write_tex instructions."""

    @property
    def instruction_type(self) -> str:
        return "write_tex"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        tex = anim.get("tex", "")
        color = anim.get("color", "WHITE")
        position = anim.get("position", "")

        lines = [
            f'        {var} = MathTex(r"{tex}", color={color})',
        ]
        if position:
            lines.append(f'        {var}.to_edge({position})')
        lines.extend([
            f'        self.play(Write({var}))',
            f'        self.wait(0.5)',
        ])
        return lines


class TransformTexHandler(InstructionHandler):
    """Handler for transform_tex instructions."""

    @property
    def instruction_type(self) -> str:
        return "transform_tex"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        from_tex = anim.get("from_tex", "")
        to_tex = anim.get("to_tex", "")
        color = anim.get("color", "WHITE")

        lines = [
            f'        {var} = MathTex(r"{to_tex}", color={color})',
            f'        self.play(TransformMatchingTex({var}_prev, {var}))',
            f'        self.wait(0.5)',
        ]
        return lines


class DrawAxesHandler(InstructionHandler):
    """Handler for draw_axes instructions."""

    @property
    def instruction_type(self) -> str:
        return "draw_axes"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        xr = anim.get("x_range", [-5, 5, 1])
        yr = anim.get("y_range", [-5, 5, 1])
        x_label = anim.get("x_label", "x")
        y_label = anim.get("y_label", "y")

        return [
            f'        {var} = Axes(x_range={xr}, y_range={yr}, axis_config={{"include_numbers": True}})',
            f'        {var}_labels = {var}.get_axis_labels(x_label="{x_label}", y_label="{y_label}")',
            f'        self.play(Create({var}), Write({var}_labels))',
        ]


class PlotFunctionHandler(InstructionHandler):
    """Handler for plot_function instructions."""

    @property
    def instruction_type(self) -> str:
        return "plot_function"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        expr = anim.get("expr", "x")
        color = anim.get("color", "BLUE")
        xr = anim.get("x_range", None)

        if not axes_var:
            log.warning("plot_function requires axes to be created first")
            return []

        if xr:
            return [
                f'        {var} = {axes_var}.plot(lambda x: {expr}, x_range={xr}, color={color})',
                f'        self.play(Create({var}))',
            ]
        return [
            f'        {var} = {axes_var}.plot(lambda x: {expr}, color={color})',
            f'        self.play(Create({var}))',
        ]


class MarkPointHandler(InstructionHandler):
    """Handler for mark_point instructions."""

    @property
    def instruction_type(self) -> str:
        return "mark_point"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        x = anim.get("x", 0)
        y = anim.get("y", 0)
        label = anim.get("label", "")
        color = anim.get("color", "RED")

        if not axes_var:
            return []

        return [
            f'        {var}_dot = Dot({axes_var}.c2p({x}, {y}), color={color})',
            f'        {var}_label = MathTex(r"{label}", color={color}).next_to({var}_dot, UR, buff=0.1)',
            f'        self.play(Create({var}_dot), Write({var}_label))',
        ]


class DrawTriangleHandler(InstructionHandler):
    """Handler for draw_triangle instructions."""

    @property
    def instruction_type(self) -> str:
        return "draw_triangle"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        verts = anim.get("vertices", [[0, 0], [3, 0], [1.5, 2.6]])
        labels = anim.get("labels", ["A", "B", "C"])
        color = anim.get("color", "WHITE")

        pts = ", ".join([f"[{v[0]}, {v[1]}, 0]" for v in verts])
        lines = [
            f'        {var} = Polygon({pts}, color={color})',
            f'        self.play(Create({var}))',
        ]

        for k, lbl in enumerate(labels):
            lines.extend([
                f'        {var}_l{k} = Text("{lbl}", font_size=24).next_to({var}.get_vertices()[{k}], buff=0.2)',
                f'        self.play(Write({var}_l{k}), run_time=0.3)',
            ])
        return lines


class DrawTableHandler(InstructionHandler):
    """Handler for draw_table instructions."""

    @property
    def instruction_type(self) -> str:
        return "draw_table"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        headers = anim.get("headers", [])
        rows = anim.get("rows", [])
        title_str = anim.get("title", "")

        lines = [
            f'        {var} = Table({rows}, col_labels=[MathTex(h) for h in {headers}])',
        ]
        if title_str:
            lines.append(f'        {var}_title = Text("{title_str}", font_size=28).next_to({var}, UP)')
            lines.append(f'        self.play(Create({var}), Write({var}_title))')
        else:
            lines.append(f'        self.play(Create({var}))')
        return lines


class FadeOutHandler(InstructionHandler):
    """Handler for fade_out instructions."""

    @property
    def instruction_type(self) -> str:
        return "fade_out"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        return ['        self.play(*[FadeOut(mob) for mob in self.mobjects])']


class PauseHandler(InstructionHandler):
    """Handler for pause instructions."""

    @property
    def instruction_type(self) -> str:
        return "pause"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        duration = anim.get("duration", 1.0)
        return [f'        self.wait({duration})']


class WriteTextHandler(InstructionHandler):
    """Handler for write_text instructions."""

    @property
    def instruction_type(self) -> str:
        return "write_text"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        text = anim.get("text", "")
        color = anim.get("color", "YELLOW")
        position = anim.get("position", "DOWN")

        lines = [
            f'        {var} = Text("{text}", color={color}, font_size=30)',
        ]
        if position:
            lines.append(f'        {var}.to_edge({position})')
        lines.append(f'        self.play(Write({var}))')
        return lines


class HighlightIntervalHandler(InstructionHandler):
    """Handler for highlight_interval instructions."""

    @property
    def instruction_type(self) -> str:
        return "highlight_interval"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        if not axes_var:
            return []

        x_from = anim.get("x_from", 0)
        x_to = anim.get("x_to", 1)
        color = anim.get("color", "YELLOW")
        label = anim.get("label", "")

        lines = [
            f'        {var} = {axes_var}.get_area({axes_var}.plot(lambda x: 0), x_range=[{x_from}, {x_to}], color={color}, opacity=0.3)',
            f'        self.play(FadeIn({var}))',
        ]
        if label:
            lines.append(f'        {var}_l = Text("{label}", font_size=20, color={color}).next_to({var}, DOWN)')
            lines.append(f'        self.play(Write({var}_l))')
        return lines


class DrawNumberLineHandler(InstructionHandler):
    """Handler for draw_number_line instructions."""

    @property
    def instruction_type(self) -> str:
        return "draw_number_line"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        range_vals = anim.get("range", [-5, 5])
        marks = anim.get("marks", [])
        signs = anim.get("signs", [])

        lines = [
            f'        {var} = NumberLine(x_range={range_vals}, include_numbers=True)',
            f'        self.play(Create({var}))',
        ]

        for i, mark in enumerate(marks):
            x = mark if isinstance(mark, (int, float)) else mark.get("x", 0)
            label = mark.get("label", str(x)) if isinstance(mark, dict) else str(x)
            lines.extend([
                f'        {var}_m{i} = Dot({var}.n2p({x}), color=WHITE)',
                f'        {var}_ml{i} = MathTex(r"{label}").next_to({var}_m{i}, DOWN)',
                f'        self.play(Create({var}_m{i}), Write({var}_ml{i}))',
            ])
        return lines


class DrawLineHandler(InstructionHandler):
    """Handler for draw_line instructions."""

    @property
    def instruction_type(self) -> str:
        return "draw_line"

    def generate(self, anim: dict, var: str, axes_var: Optional[str]) -> list[str]:
        start = anim.get("start", [0, 0])
        end = anim.get("end", [3, 4])
        color = anim.get("color", "GREEN")
        label = anim.get("label", "")

        lines = [
            f'        {var} = Line([{start[0]}, {start[1]}, 0], [{end[0]}, {end[1]}, 0], color={color})',
            f'        self.play(Create({var}))',
        ]
        if label:
            lines.append(f'        {var}_l = Text("{label}", font_size=20).next_to({var}, RIGHT)')
            lines.append(f'        self.play(Write({var}_l))')
        return lines


# Registry of all handlers
INSTRUCTION_HANDLERS: dict[str, InstructionHandler] = {}


def register_handler(handler: InstructionHandler):
    """Register an instruction handler."""
    INSTRUCTION_HANDLERS[handler.instruction_type] = handler


def init_handlers():
    """Initialize all instruction handlers."""
    handlers = [
        WriteTexHandler(),
        TransformTexHandler(),
        DrawAxesHandler(),
        PlotFunctionHandler(),
        MarkPointHandler(),
        DrawTriangleHandler(),
        DrawTableHandler(),
        FadeOutHandler(),
        PauseHandler(),
        WriteTextHandler(),
        HighlightIntervalHandler(),
        DrawNumberLineHandler(),
        DrawLineHandler(),
    ]
    for handler in handlers:
        register_handler(handler)


def get_handler(instruction_type: str) -> Optional[InstructionHandler]:
    """Get handler for instruction type."""
    return INSTRUCTION_HANDLERS.get(instruction_type)
