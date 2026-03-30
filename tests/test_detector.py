"""Tests for problem type detection."""

import pytest
from app.pipeline.detector import detect_subject_and_types, detect_problem_type


class TestDetectSubjectAndTypes:
    """Test cases for detect_subject_and_types."""

    def test_solid_geometry(self):
        """Test 立体几何 detection."""
        text = "四棱锥 P-ABCD 中，PA⊥底面 ABCD，证明：PC⊥BD"
        result = detect_subject_and_types(text)
        assert any(subj == "立体几何" for subj, _ in result)

    def test_derivative_monotonic(self):
        """Test 导数单调性 detection."""
        text = "已知函数 f(x) = x³ - 3x + 1，求 f(x) 的单调区间和极值"
        result = detect_subject_and_types(text)
        assert any(subj == "导数" for subj, _ in result)

    def test_trig_function(self):
        """Test 三角函数 detection."""
        text = "求函数 f(x) = sin(2x + π/4) 的最小正周期"
        result = detect_subject_and_types(text)
        assert any(subj == "三角函数" for subj, _ in result)

    def test_sequence_arithmetic(self):
        """Test 等差数列 detection."""
        text = "已知等差数列 {a_n} 中，a₁=1, a₅=9，求通项公式"
        result = detect_subject_and_types(text)
        assert any(subj == "数列" for subj, _ in result)

    def test_probability(self):
        """Test 概率检测."""
        text = "随机变量 X 服从正态分布 N(0,1)，求 P(X>1)"
        result = detect_subject_and_types(text)
        assert any(subj == "排列组合概率统计" for subj, _ in result)

    def test_function_with_derivative_fallback(self):
        """Test feature-based fallback for derivative."""
        text = "设 f'(x) = 3x² - 6x，求 f(x) 的极值点"
        result = detect_subject_and_types(text)
        assert any(subj == "导数" for subj, _ in result)

    def test_mixed_subject(self):
        """Test mixed subject detection."""
        text = "已知 sinα = 3/5，求 cosα 和 tanα"
        result = detect_subject_and_types(text)
        assert any(subj == "三角函数" for subj, _ in result)

    def test_unknown_fallback_mixed(self):
        """Test fallback to 混合 when no match."""
        text = "这是一道没有任何数学特征的纯文字题目"
        result = detect_subject_and_types(text)
        assert result == [("混合", [])]


class TestDetectProblemType:
    """Test cases for legacy detect_problem_type API."""

    def test_returns_flat_list(self):
        """Test that legacy API returns flat list."""
        text = "已知函数 f(x) = x² - 2x，求单调区间"
        result = detect_problem_type(text)
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_derivative_types(self):
        """Test derivative problem types."""
        text = "求函数 f(x) 的极大值和极小值"
        result = detect_problem_type(text)
        assert "导数" in result[0] or "极值" in result[0] or "函数" in result[0]
