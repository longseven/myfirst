"""Tests for JSON extraction from LLM output."""

import pytest
from app.pipeline.scene import _extract_json


class TestExtractJson:
    """Test cases for _extract_json function."""

    def test_clean_json(self):
        """Test extracting clean JSON."""
        text = '{"title": "test", "value": 123}'
        result = _extract_json(text)
        assert result == {"title": "test", "value": 123}

    def test_json_in_code_block(self):
        """Test extracting JSON from markdown code block."""
        text = '''```json
{"title": "test", "value": 456}
```'''
        result = _extract_json(text)
        assert result == {"title": "test", "value": 456}

    def test_json_without_language_hint(self):
        """Test extracting JSON from code block without language."""
        text = '''```
{"name": "example"}
```'''
        result = _extract_json(text)
        assert result == {"name": "example"}

    def test_json_with_extra_text(self):
        """Test extracting JSON with surrounding text."""
        text = '''好的，这是生成的 JSON：
{"title": "示例", "items": [1, 2, 3]}
希望对你有帮助。'''
        result = _extract_json(text)
        assert result == {"title": "示例", "items": [1, 2, 3]}

    def test_json_with_trailing_comma(self):
        """Test fixing trailing comma."""
        text = '{"items": [1, 2, 3,], "name": "test"}'
        result = _extract_json(text)
        assert result == {"items": [1, 2, 3], "name": "test"}

    def test_json_with_class_syntax(self):
        """Test fixing class='t' syntax."""
        text = '{"html": "<span class=\'t\'>text</span>"}'
        result = _extract_json(text)
        assert "html" in result

    def test_nested_json(self):
        """Test extracting nested JSON."""
        text = '''```
{
  "scene": {
    "vertices": {"A": [0, 0, 0], "B": [1, 0, 0]},
    "edges": [["A", "B"]]
  }
}
```'''
        result = _extract_json(text)
        assert "scene" in result
        assert "vertices" in result["scene"]
        assert "edges" in result["scene"]

    def test_json_with_escape(self):
        """Test handling escaped characters."""
        text = r'{"formula": "x^2 - 3x + 1", "note": "使用公式 $a^2+b^2$"}'
        result = _extract_json(text)
        assert "formula" in result

    def test_complex_scene_data(self):
        """Test extracting complex scene_data structure."""
        text = '''```json
{
  "title": "立体几何题",
  "vertices": {
    "A": [0, 0, 0],
    "B": [3, 0, 0],
    "C": [0, 4, 0],
    "P": [0, 0, 5]
  },
  "base_edges_solid": [["A", "B"], ["B", "C"], ["C", "A"]],
  "solution_script": [
    {"phase": "审题", "speech": "我们来分析这道题"},
    {"phase": "求解", "speech": "首先建立坐标系"}
  ]
}
```'''
        result = _extract_json(text)
        assert "title" in result
        assert "vertices" in result
        assert "base_edges_solid" in result
        assert "solution_script" in result
        assert len(result["solution_script"]) == 2

    def test_multiple_json_objects_first_extracted(self):
        """Test extracting first JSON when multiple objects exist."""
        # This simulates LLM outputting multiple JSON objects
        text = '{"a": 1} {"b": 2}'
        # Should extract the first complete object
        result = _extract_json(text)
        assert result == {"a": 1} or "a" in result


class TestExtractJsonEdgeCases:
    """Edge case tests for JSON extraction."""

    def test_empty_object(self):
        """Test extracting empty object."""
        text = '{}'
        result = _extract_json(text)
        assert result == {}

    def test_empty_array_value(self):
        """Test JSON with empty arrays."""
        text = '{"items": [], "data": {}}'
        result = _extract_json(text)
        assert result == {"items": [], "data": {}}

    def test_unicode_characters(self):
        """Test JSON with Unicode characters."""
        text = '{"title": "数学题", "content": "求函数 f(x) 的极值"}'
        result = _extract_json(text)
        assert result["title"] == "数学题"
        assert "函数" in result["content"]
