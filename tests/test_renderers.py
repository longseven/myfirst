"""Tests for renderers."""

import pytest
from app.pipeline.renderers.manim_ import ManimRenderer
from app.pipeline.renderers.threejs import ThreeJSRenderer
from app.pipeline.renderers.video import VideoRenderer


class TestManimRenderer:
    """Test cases for Manim renderer."""

    def test_parse_valid_manim_data(self):
        """Test parsing valid Manim JSON output."""
        renderer = ManimRenderer()
        raw_output = '''```json
{
  "title": "函数讲解",
  "scenes": [
    {
      "scene_id": 1,
      "title": "引入",
      "speech": "我们来学习这个函数",
      "instructions": [
        {"type": "write_tex", "tex": "f(x) = x^2"}
      ]
    }
  ]
}
```'''
        import asyncio
        result = asyncio.run(renderer.parse_llm_output(raw_output))
        assert "scenes" in result
        assert len(result["scenes"]) == 1

    def test_parse_manim_data_without_code_block(self):
        """Test parsing JSON without markdown wrapper."""
        renderer = ManimRenderer()
        raw_output = '{"title": "test", "scenes": [{"scene_id": 1, "speech": "hello"}]}'
        import asyncio
        result = asyncio.run(renderer.parse_llm_output(raw_output))
        assert "scenes" in result

    def test_get_system_prompt(self):
        """Test system prompt generation."""
        renderer = ManimRenderer()
        teaching_data = "# 教学方法论\n\n使用配方法求解..."
        prompt = renderer.get_system_prompt(teaching_data)
        assert "任务" in prompt
        assert " JSON" in prompt


class TestThreeJSRenderer:
    """Test cases for ThreeJS renderer."""

    def test_parse_valid_scene_data(self):
        """Test parsing valid Three.js scene data."""
        renderer = ThreeJSRenderer()
        raw_output = '''```json
{
  "title": "立体几何",
  "vertices": {"A": [0, 0, 0], "B": [1, 0, 0]},
  "solution_script": [
    {"phase": "审题", "speech": "分析题目"}
  ]
}
```'''
        import asyncio
        result = asyncio.run(renderer.parse_llm_output(raw_output))
        assert "vertices" in result
        assert "solution_script" in result

    def test_parse_missing_vertices_raises(self):
        """Test that missing vertices raises error."""
        renderer = ThreeJSRenderer()
        raw_output = '{"title": "test", "solution_script": []}'
        import asyncio
        with pytest.raises(ValueError, match="vertices"):
            asyncio.run(renderer.parse_llm_output(raw_output))

    def test_parse_missing_solution_script_raises(self):
        """Test that missing solution_script raises error."""
        renderer = ThreeJSRenderer()
        raw_output = '{"title": "test", "vertices": {}}'
        import asyncio
        with pytest.raises(ValueError, match="solution_script"):
            asyncio.run(renderer.parse_llm_output(raw_output))


class TestVideoRenderer:
    """Test cases for Video renderer."""

    def test_parse_valid_analysis_data(self):
        """Test parsing valid video analysis data."""
        renderer = VideoRenderer()
        raw_output = '''```json
{
  "title": "题目讲解",
  "analysis": {
    "subject": "函数",
    "type": "单调性",
    "keywords": ["函数", "单调"]
  },
  "solution_steps": [
    {"phase": "分析", "speech": "第一步"}
  ]
}
```'''
        import asyncio
        result = asyncio.run(renderer.parse_llm_output(raw_output))
        assert "solution_steps" in result
        assert len(result["solution_steps"]) == 1
