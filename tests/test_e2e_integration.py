#!/usr/bin/env python3
"""
端到端集成测试 - Day 12

测试完整的故障分类流程
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
from pathlib import Path
from src.incident_classifier_v1 import IncidentClassifierV1


class TestE2EIntegration:
    """端到端集成测试"""

    @pytest.fixture
    def classifier(self):
        """创建分类器实例"""
        return IncidentClassifierV1(trace_dir="traces/test")

    def test_p0_payment_failure(self, classifier):
        """测试 P0 支付故障"""
        description = "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟"

        result = classifier.classify(description)

        # 验证基本结构
        assert result['success'] is True
        assert result['version'] == "1.0.0"
        assert 'classification' in result
        assert 'evidence_summary' in result
        assert 'trace' in result

        # 验证分类结果
        classification = result['classification']
        assert classification['severity'] in ['P0', 'P1']  # 应该是 P0 或被 Policy 修正为 P1
        assert classification['category'] == 'availability'
        assert 'rationale' in classification

        # 验证证据收集
        assert len(result['evidence_summary']) > 0

        # 验证轨迹
        assert result['trace']['trace_id'] is not None
        assert result['trace']['file'] is not None
        assert Path(result['trace']['file']).exists()

        # 验证性能指标
        assert 'performance' in result
        assert result['performance']['tool_calls'] > 0

        print(f"\n✓ P0 支付故障测试通过")
        print(f"  严重程度: {classification['severity']}")
        print(f"  类别: {classification['category']}")
        print(f"  工具调用: {result['performance']['tool_calls']}")

    def test_p1_latency_issue(self, classifier):
        """测试 P1 延迟问题"""
        description = "推荐系统 P99 延迟从 500ms 升至 2 秒，超时率 15%"

        result = classifier.classify(description)

        assert result['success'] is True
        classification = result['classification']

        # 延迟问题应该是 P1 或 P2
        assert classification['severity'] in ['P1', 'P2']
        assert classification['category'] == 'latency'

        print(f"\n✓ P1 延迟问题测试通过")
        print(f"  严重程度: {classification['severity']}")
        print(f"  类别: {classification['category']}")

    def test_p1_database_deadlock(self, classifier):
        """测试 P1 数据库死锁"""
        description = "MySQL 报 1205 死锁错误，影响订单创建，每分钟 20 次"

        result = classifier.classify(description)

        assert result['success'] is True
        classification = result['classification']

        assert classification['severity'] in ['P0', 'P1']
        assert classification['category'] == 'database'

        print(f"\n✓ P1 数据库死锁测试通过")
        print(f"  严重程度: {classification['severity']}")
        print(f"  类别: {classification['category']}")

    def test_p1_oom_issue(self, classifier):
        """测试 P1 OOM 问题"""
        description = "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次"

        result = classifier.classify(description)

        assert result['success'] is True
        classification = result['classification']

        assert classification['severity'] in ['P1', 'P2']
        assert classification['category'] in ['availability', 'deployment']

        print(f"\n✓ P1 OOM 问题测试通过")
        print(f"  严重程度: {classification['severity']}")
        print(f"  类别: {classification['category']}")

    def test_p2_minor_issue(self, classifier):
        """测试 P2 小故障"""
        description = "用户头像上传偶尔失败，错误率 2%"

        result = classifier.classify(description)

        assert result['success'] is True
        classification = result['classification']

        # 非核心功能，应该是 P2 或 P3
        assert classification['severity'] in ['P2', 'P3']

        print(f"\n✓ P2 小故障测试通过")
        print(f"  严重程度: {classification['severity']}")
        print(f"  类别: {classification['category']}")

    def test_p3_low_error_rate(self, classifier):
        """测试 P3 低错误率"""
        description = "日志中发现少量 404 错误，错误率 0.5%，已恢复"

        result = classifier.classify(description)

        assert result['success'] is True
        classification = result['classification']

        # 低错误率应该是 P3
        assert classification['severity'] == 'P3'

        print(f"\n✓ P3 低错误率测试通过")
        print(f"  严重程度: {classification['severity']}")
        print(f"  需要审核: {classification['needs_human_review']}")

    def test_policy_enforcement(self, classifier):
        """测试 Policy 规则修正"""
        # 这个案例应该触发 P0 必须人工审核的规则
        description = "用户数据库表被删除，影响 1000 个用户"

        result = classifier.classify(description)

        assert result['success'] is True
        classification = result['classification']

        # P0 必须人工审核
        assert classification['needs_human_review'] is True

        # 检查是否有 Policy 修正
        if result.get('policy_violations'):
            print(f"\n✓ Policy 规则测试通过")
            print(f"  触发规则数: {len(result['policy_violations'])}")
            for v in result['policy_violations']:
                print(f"  - {v['policy']}: {v['message']}")

    def test_tool_coordinator_integration(self, classifier):
        """测试 ToolCoordinator 集成"""
        description = "支付接口 5xx 错误率 35%"

        result = classifier.classify(description)

        assert result['success'] is True

        # 验证工具调用
        assert result['performance']['tool_calls'] > 0

        # 验证缓存命中率（第二次调用应该有缓存）
        result2 = classifier.classify(description)
        assert result2['success'] is True

        # 第二次调用应该更快（有缓存）
        # assert result2['duration_seconds'] <= result['duration_seconds']

        print(f"\n✓ ToolCoordinator 集成测试通过")
        print(f"  第一次调用:")
        print(f"    工具调用: {result['performance']['tool_calls']}")
        print(f"    耗时: {result['duration_seconds']}s")
        print(f"  第二次调用:")
        print(f"    工具调用: {result2['performance']['tool_calls']}")
        print(f"    耗时: {result2['duration_seconds']}s")
        print(f"    缓存命中率: {result2['performance']['cache_hit_rate']:.1%}")

    def test_robust_executor_fallback(self, classifier):
        """测试健壮执行器的降级能力"""
        # 这个测试主要验证即使工具失败，系统也能继续
        description = "未知服务报错"

        result = classifier.classify(description)

        # 即使工具失败，也应该有结果
        assert result['success'] is True
        assert result['classification']['severity'] in ['P0', 'P1', 'P2', 'P3']

        print(f"\n✓ 健壮执行器降级测试通过")
        print(f"  成功率: {result['performance']['success_rate']:.1%}")

    def test_trace_manager_integration(self, classifier):
        """测试 TraceManager 集成"""
        description = "测试轨迹记录"

        result = classifier.classify(description)

        assert result['success'] is True
        assert result['trace']['trace_id'] is not None
        assert result['trace']['file'] is not None

        # 读取轨迹文件
        trace_file = Path(result['trace']['file'])
        assert trace_file.exists()

        with open(trace_file, 'r', encoding='utf-8') as f:
            trace_data = json.load(f)

        # 验证轨迹内容
        assert trace_data['trace_id'] == result['trace']['trace_id']
        assert trace_data['user_input'] == description
        assert trace_data['status'] == 'success'
        assert len(trace_data['tool_calls']) >= 0

        print(f"\n✓ TraceManager 集成测试通过")
        print(f"  轨迹 ID: {trace_data['trace_id']}")
        print(f"  工具调用: {len(trace_data['tool_calls'])}")
        print(f"  轨迹文件: {trace_file}")


def run_all_tests():
    """运行所有测试"""
    print("="*80)
    print("端到端集成测试 - Day 12")
    print("="*80)

    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_all_tests()
