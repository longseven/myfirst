"""Auto-generated Manim script."""
from manim import *

class fxx3x(Scene):
    def construct(self):

        # ===  ===
        # 今天我们来研究三次函数 f(x) = x³ - 3x 的单调性和极值问题。首先我们画出这个函数的图像，通过数形结合来直观...
        obj_0_0 = MathTex(r"f(x) = x^3 - 3x", color=WHITE)
        obj_0_0.to_edge([0, 2])
        self.play(Write(obj_0_0))
        self.wait(0.5)
        self.wait(1)

        # ===  ===
        # 对于多项式函数，我们用求导法判断单调性。先求导数：f'(x) = 3x² - 3。...
        obj_1_0 = MathTex(r"f'(x) = 3x^2 - 3")
        self.play(Write(obj_1_0))
        self.wait(1)

        # ===  ===
        # 把导数因式分解：f'(x) = 3(x² - 1) = 3(x+1)(x-1)。令导数为零，得到两个零点 x = -1 ...
        obj_2_0 = MathTex(r"f'(x) = 3(x+1)(x-1) = 0")
        self.play(Write(obj_2_0))
        obj_2_1 = MathTex(r"x_1 = -1, \quad x_2 = 1", color=WHITE)
        obj_2_1.to_edge([0, -0.5])
        self.play(Write(obj_2_1))
        self.wait(0.5)
        self.wait(1)

        # ===  ===
        # 现在我们在坐标系中画出 f(x) = x³ - 3x 的图像。这是一个奇函数，图像关于原点对称，有两个极值点。...
        obj_3_0 = Axes(x_range=[-3, 3, 1], y_range=[-4, 4, 1], axis_config={"include_numbers": True})
        obj_3_0_labels = obj_3_0.get_axis_labels(x_label="x", y_label="y")
        self.play(Create(obj_3_0), Write(obj_3_0_labels))
        obj_3_1 = obj_3_0.plot(lambda x: x**3 - 3*x, x_range=[-2.5, 2.5], color=BLUE)
        self.play(Create(obj_3_1))
        self.wait(1)

        # ===  ===
        # 在图像上标注两个极值点。当 x = -1 时，f(-1) = (-1)³ - 3(-1) = 2，这是极大值点。当 x ...
        self.wait(1)

        # ===  ===
        # 根据导数符号，我们用三个区间来分析单调性。在数轴上标出两个零点 -1 和 1。...
        self.wait(1)

        # ===  ===
        # 当 x < -1 时，导数 f'(x) > 0，函数在 (-∞, -1) 上单调递增。我们把这段区间高亮显示。...
        self.wait(1)

        # ===  ===
        # 当 -1 < x < 1 时，导数 f'(x) < 0，函数在 (-1, 1) 上单调递减。...
        self.wait(1)

        # ===  ===
        # 当 x > 1 时，导数 f'(x) > 0，函数在 (1, +∞) 上单调递增。...
        self.wait(1)

        # ===  ===
        # 让我们用表格完整总结这个函数的单调区间和极值：单调递增区间是 (-∞, -1) 和 (1, +∞)，单调递减区间是 (-...
        obj_9_0 = Table([['单调递增区间', '(-∞, -1)', '—'], ['极大值点', 'x = -1', 'f(-1) = 2'], ['单调递减区间', '(-1, 1)', '—'], ['极小值点', 'x = 1', 'f(1) = -2'], ['单调递增区间', '(1, +∞)', '—']], col_labels=[MathTex(h) for h in ['类型', '区间/点', '函数值']])
        obj_9_0_title = Text("f(x) = x³ - 3x 的单调性与极值", font_size=28).next_to(obj_9_0, UP)
        self.play(Create(obj_9_0), Write(obj_9_0_title))
        self.wait(1)
