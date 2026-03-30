"""Auto-generated Manim script."""
from manim import *

class Lecture(Scene):
    def construct(self):

        # ===  ===
        # 我们先对函数 f(x) = x³ - 3x + 1 求导数，得到 f'(x) = 3x² - 3 = 3(x² - 1)...
        self.wait(1)

        # ===  ===
        # 接下来分析导数在各区间的符号。当 x < -1 时，(x+1)(x-1) > 0，导数大于零，函数单调递增。当 -1 <...
        self.wait(1)

        # ===  ===
        # 现在计算极值点处的函数值。在 x = -1 处，f(-1) = 3，这是极大值。在 x = 1 处，f(1) = -1，...
        self.wait(1)

        # ===  ===
        # 最后我们总结一下结果：单调递增区间是 (-∞, -1) 和 (1, +∞)，单调递减区间是 (-1, 1)；极大值为 3...
        self.wait(1)
