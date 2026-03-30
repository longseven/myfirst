# Manim 动画 JSON Schema

本文档描述 LLM 需要输出的 JSON 格式，用于自动生成 Manim 教学动画。

## 动画指令类型

| type | 用途 | 必填参数 |
|------|------|----------|
| `write_tex` | 书写公式 | `tex`, `color?`, `position?` |
| `transform_tex` | 公式变换 | `from_tex`, `to_tex` |
| `draw_axes` | 坐标轴 | `x_range`, `y_range` |
| `plot_function` | 函数图像 | `expr`, `color?`, `x_range?` |
| `mark_point` | 标注点 | `x`, `y`, `label`, `color?` |
| `highlight_interval` | 高亮区间 | `x_from`, `x_to`, `label?` |
| `draw_line` | 线段 | `start`, `end`, `label?` |
| `draw_triangle` | 三角形 | `vertices`, `labels` |
| `draw_angle` | 角 | `vertex`, `p1`, `p2`, `label` |
| `draw_table` | 表格 | `headers`, `rows`, `title?` |
| `draw_number_line` | 数轴 | `range`, `marks`, `signs` |
| `draw_tree` | 树形图 | `root`, `branches` |
| `write_text` | 文本 | `text`, `color?` |
| `fade_out` | 淡出 | 无 |
| `pause` | 暂停 | `duration` |

## 学科适用

- 解三角形: `draw_triangle` + `draw_angle` + `write_tex`
- 函数/导数: `draw_axes` + `plot_function` + `highlight_interval` + `draw_table`
- 数列: `write_tex` + `transform_tex` + `draw_table`
- 概率统计: `draw_tree` + `draw_table` + `write_tex`
- 集合不等式: `draw_number_line` + `write_tex`
