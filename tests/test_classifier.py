# tests/test_classifier.py
"""
Day 1: 测试故障分类器

验证：
1. 能成功调用 LLM
2. 能得到结构化输出
3. 不同类型的故障能正确分类
"""
import pytest
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from classifier import IncidentClassifier
from models import IncidentResult


class TestIncidentClassifier:
    """测试故障分类器"""

    @pytest.fixture
    def classifier(self):
        """创建分类器实例"""
        return IncidentClassifier()

    def test_payment_5xx(self, classifier):
        """测试：支付 5xx 故障"""
        description = "支付接口 5xx 错误率从 0.1% 升到 35%"
        result = classifier.classify(description)

        # 验证返回类型
        assert isinstance(result, IncidentResult)

        # 支付高错误率应该是 P0 或 P1
        assert result.severity in ["P0", "P1"], \
            f"支付 35% 错误率应该是 P0 或 P1，实际: {result.severity}"

        # 应该标记需要人工审核
        assert result.needs_human_review == True, \
            "支付故障必须人工审核"

        # 依据应该包含关键信息
        assert "5xx" in result.rationale or "35%" in result.rationale or "错误" in result.rationale

    def test_recommendation_latency(self, classifier):
        """测试：推荐系统延迟"""
        description = "推荐系统 P99 延迟从 500ms 升至 2 秒"
        result = classifier.classify(description)

        # 推荐系统不是核心功能，应该是 P2 或 P3
        assert result.severity in ["P2", "P3"], \
            f"推荐延迟应该是 P2 或 P3，实际: {result.severity}"

        # 类别应该是 latency 或 availability
        assert result.category in ["latency", "availability"]

    def test_database_deadlock(self, classifier):
        """测试：数据库死锁"""
        description = "MySQL 报 1205 死锁错误，影响订单创建"
        result = classifier.classify(description)

        # 应该识别为数据库问题
        assert result.category == "database", \
            f"应该识别为 database 类别，实际: {result.category}"

        # 影响订单创建，应该是 P1 或 P2
        assert result.severity in ["P1", "P2"]

    def test_result_structure(self, classifier):
        """测试：结果结构完整性"""
        description = "服务响应慢"
        result = classifier.classify(description)

        # 验证所有字段都存在
        assert hasattr(result, 'severity')
        assert hasattr(result, 'category')
        assert hasattr(result, 'needs_human_review')
        assert hasattr(result, 'rationale')

        # 验证 rationale 不为空且有最小长度
        assert len(result.rationale) >= 10

    def test_multiple_classifications(self, classifier):
        """测试：连续多次分类"""
        test_cases = [
            "支付接口报错",
            "推荐系统慢",
            "数据库连接失败"
        ]

        for description in test_cases:
            result = classifier.classify(description)

            # 每次都应该成功返回
            assert isinstance(result, IncidentResult)
            assert result.severity in ["P0", "P1", "P2", "P3"]


class TestClassifierManual:
    """手动测试（需要人工检查结果）"""

    def test_manual_check(self):
        """手动检查分类结果"""
        classifier = IncidentClassifier()

        test_cases = [
            "支付接口 5xx 错误率 35%",
            "推荐系统 P99 延迟 2 秒",
            "数据库死锁"
        ]

        print("\n" + "=" * 80)
        print("手动检查分类结果")
        print("=" * 80)

        for case in test_cases:
            print(f"\n故障: {case}")
            result = classifier.classify(case)
            print(f"  严重程度: {result.severity}")
            print(f"  类别: {result.category}")
            print(f"  需要审核: {result.needs_human_review}")
            print(f"  依据: {result.rationale}")

        print("\n" + "=" * 80)
        print("请检查以上结果是否合理")


if __name__ == "__main__":
    # 运行自动化测试
    pytest.main([__file__, "-v", "-k", "not manual"])

    # 如果要运行手动测试，取消下面的注释
    # pytest.main([__file__, "-v", "-k", "manual", "-s"])
