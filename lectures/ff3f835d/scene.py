"""Auto-generated Manim script."""
from manim import *

class MathLecture(Scene):
    def construct(self):

        # ===  ===
        # 今天我们来求二次函数 f(x) = 2x² - 8x + 5 的顶点。顶点是二次函数图像的最高点或最低点。...
        obj_0_0 = MathTex(r"f(x) = 2x^2 - 8x + 5", color=white)
        obj_0_0.to_edge([0, 2])
        self.play(Write(obj_0_0))
        self.wait(0.5)
        obj_0_1 = Text("求顶点坐标", color=yellow, font_size=30)
        obj_0_1.to_edge([0, 0.5])
        self.play(Write(obj_0_1))
        self.wait(1)

        # ===  ===
        # 我们先画出这个二次函数的图像，观察顶点的位置。...
        obj_1_0 = Axes(x_range=[-1, 5], y_range=[-5, 5], axis_config={"include_numbers": True})
        obj_1_0_labels = obj_1_0.get_axis_labels(x_label="x", y_label="y")
        self.play(Create(obj_1_0), Write(obj_1_0_labels))
        obj_1_1 = obj_1_0.plot(lambda x: 2*x**2 - 8*x + 5, x_range=[-0.5, 4.5], color=blue)
        self.play(Create(obj_1_1))
        self.wait(1)

        # ===  ===
        # 使用配方法求顶点。先提取二次项系数：f(x) = 2(x² - 4x) + 5...
        obj_2_0 = MathTex(r"f(x) = 2(x^2 - 4x) + 5")
        self.play(Write(obj_2_0))
        obj_2_1 = Text("提取二次项系数 2", color=green, font_size=30)
        obj_2_1.to_edge([0, -2.5])
        self.play(Write(obj_2_1))
        self.wait(1)

        # ===  ===
        # 对括号内配方：(x² - 4x + 4) - 4 = (x - 2)² - 4...
        obj_3_0 = MathTex(r"f(x) = 2[(x-2)^2 - 4] + 5")
        self.play(Write(obj_3_0))
        obj_3_1 = Text("加4减4，配成完全平方式", color=green, font_size=30)
        obj_3_1.to_edge([0, -2.5])
        self.play(Write(obj_3_1))
        self.wait(1)

        # ===  ===
        # 展开化简：2(x-2)² - 8 + 5 = 2(x-2)² - 3...
        obj_4_0 = MathTex(r"f(x) = 2(x-2)^2 - 3")
        self.play(Write(obj_4_0))
        self.wait(1)

        # ===  ===
        # 也可以直接用顶点公式：x = -b/(2a) = -(-8)/(2×2) = 2，代入求 y 值。...
        obj_5_0 = MathTex(r"x_{vertex} = -\frac{b}{2a} = -\frac{-8}{2\times2} = 2", color=white)
        obj_5_0.to_edge([0, 1.5])
        self.play(Write(obj_5_0))
        self.wait(0.5)
        obj_5_1 = MathTex(r"y_{vertex} = 2(2)^2 - 8(2) + 5 = -3", color=white)
        obj_5_1.to_edge([0, 0])
        self.play(Write(obj_5_1))
        self.wait(0.5)
        self.wait(1)

        # ===  ===
        # 在图像上标注顶点 (2, -3)。...
        obj_6_0 = Axes(x_range=[-1, 5], y_range=[-5, 5], axis_config={"include_numbers": True})
        obj_6_0_labels = obj_6_0.get_axis_labels(x_label="x", y_label="y")
        self.play(Create(obj_6_0), Write(obj_6_0_labels))
        obj_6_1 = obj_6_0.plot(lambda x: 2*x**2 - 8*x + 5, x_range=[-0.5, 4.5], color=blue)
        self.play(Create(obj_6_1))
        obj_6_2_dot = Dot(obj_6_0.c2p(2, -3), color=red)
        obj_6_2_label = MathTex(r"顶点 (2, -3)", color=red).next_to(obj_6_2_dot, UR, buff=0.1)
        self.play(Create(obj_6_2_dot), Write(obj_6_2_label))
        self.wait(1)

        # ===  ===
        # 二次函数 f(x) = 2x² - 8x + 5 的顶点是 (2, -3)。由于 a = 2 > 0，所以这是开口向上的...
        obj_7_0 = MathTex(r"Vertex = (2, -3)", color=yellow)
        obj_7_0.to_edge([0, 2])
        self.play(Write(obj_7_0))
        self.wait(0.5)
        obj_7_1 = Text("最小值 f(2) = -3", color=green, font_size=30)
        obj_7_1.to_edge([0, 0])
        self.play(Write(obj_7_1))
        self.wait(1)
