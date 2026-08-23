# tests/test_models.py
"""
Day 1: 测试 Pydantic 模型

验证：
1. 合法输入能通过校验
2. 非法输入被正确拒绝
3. 字段验证器工作正常
"""
import pytest
from pydantic import ValidationError
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import IncidentResult


class TestIncidentResult:
    """测试 IncidentResult 模型"""

    def test_valid_input(self):
        """测试：合法输入"""
        result = IncidentResult(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="支付接口完全不可用"
        )

        assert result.severity == "P0"
        assert result.category == "availability"
        assert result.needs_human_review == True
        assert "支付接口" in result.rationale

    def test_invalid_severity(self):
        """测试：非法的 severity 值"""
        with pytest.raises(ValidationError) as exc_info:
            IncidentResult(
                severity="critical",  # 错误：不是 P0/P1/P2/P3
                category="availability",
                needs_human_review=True,
                rationale="测试非法值"
            )

        assert "severity" in str(exc_info.value).lower()

    def test_invalid_category(self):
        """测试：非法的 category 值"""
        with pytest.raises(ValidationError) as exc_info:
            IncidentResult(
                severity="P0",
                category="network_error",  # 错误：不在预定义类别中
                needs_human_review=True,
                rationale="测试非法类别"
            )

        assert "category" in str(exc_info.value).lower()

    def test_rationale_too_short(self):
        """测试：rationale 太短"""
        with pytest.raises(ValidationError) as exc_info:
            IncidentResult(
                severity="P0",
                category="availability",
                needs_human_review=True,
                rationale="短"  # 错误：只有 1 个字符，少于 5
            )

        error_msg = str(exc_info.value).lower()
        assert "rationale" in error_msg

    def test_rationale_empty(self):
        """测试：rationale 为空"""
        with pytest.raises(ValidationError) as exc_info:
            IncidentResult(
                severity="P0",
                category="availability",
                needs_human_review=True,
                rationale=""  # 错误：空字符串
            )

        error_msg = str(exc_info.value).lower()
        assert "rationale" in error_msg

    def test_missing_required_field(self):
        """测试：缺少必需字段"""
        with pytest.raises(ValidationError) as exc_info:
            IncidentResult(
                severity="P0",
                category="availability",
                # 缺少 needs_human_review 和 rationale
            )

        error_msg = str(exc_info.value).lower()
        assert "required" in error_msg or "missing" in error_msg

    def test_all_severity_levels(self):
        """测试：所有严重程度都有效"""
        for severity in ["P0", "P1", "P2", "P3"]:
            result = IncidentResult(
                severity=severity,
                category="availability",
                needs_human_review=True,
                rationale="测试所有严重程度级别"
            )
            assert result.severity == severity

    def test_all_categories(self):
        """测试：所有类别都有效"""
        categories = ["availability", "latency", "database", "deployment", "unknown"]

        for category in categories:
            result = IncidentResult(
                severity="P1",
                category=category,
                needs_human_review=False,
                rationale="测试所有故障类别"
            )
            assert result.category == category

    def test_rationale_whitespace_trimmed(self):
        """测试：rationale 的空格被正确处理"""
        result = IncidentResult(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="  有前后空格的依据  "
        )

        # 应该去除首尾空格
        assert result.rationale == "有前后空格的依据"

    def test_model_serialization(self):
        """测试：模型序列化"""
        result = IncidentResult(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="支付接口完全不可用"
        )

        # 转换为字典
        data = result.model_dump()
        assert data["severity"] == "P0"
        assert data["category"] == "availability"

        # 转换为 JSON
        json_str = result.model_dump_json()
        assert "P0" in json_str
        assert "availability" in json_str


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
