"""
测试 Agent V2 (ToolCoordinator 版本)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.agent_v2 import IncidentAgentV2


class TestAgentV2:
    """测试 Agent V2"""

    @pytest.fixture
    def agent(self):
        """创建 Agent 实例"""
        return IncidentAgentV2()

    def test_analyze_basic(self, agent):
        """基础分析测试"""
        result = agent.analyze("支付接口 5xx 错误率从 0.1% 升到 35%")

        assert "classification" in result
        assert "evidence" in result
        assert "trace_file" in result

        classification = result["classification"]
        assert "severity" in classification
        assert "category" in classification
        assert "needs_human_review" in classification
        assert "rationale" in classification

    def test_analyze_payment_issue(self, agent):
        """测试支付问题分析"""
        result = agent.analyze("支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟")

        classification = result["classification"]
        assert classification["severity"] in ["P0", "P1"]
        assert classification["category"] == "availability"

    def test_analyze_latency_issue(self, agent):
        """测试延迟问题分析"""
        result = agent.analyze("推荐系统 P99 延迟从 500ms 升至 2 秒")

        classification = result["classification"]
        assert classification["severity"] in ["P1", "P2"]
        assert classification["category"] == "latency"

    def test_analyze_database_issue(self, agent):
        """测试数据库问题分析"""
        result = agent.analyze("MySQL 报 1205 死锁错误，影响订单创建")

        classification = result["classification"]
        assert classification["severity"] in ["P0", "P1"]
        assert classification["category"] == "database"

    def test_analyze_oom_issue(self, agent):
        """测试 OOM 问题分析"""
        result = agent.analyze("recommendation 服务 Pod 内存溢出，重启 5 次")

        classification = result["classification"]
        assert classification["severity"] in ["P1", "P2"]

        # 验证调用了 OOM 工具
        evidence_tools = [ev["tool"] for ev in result["evidence"]]
        print(f"调用的工具: {evidence_tools}")
        assert "search_oom_events" in evidence_tools, f"期望调用 OOM 工具，实际调用: {evidence_tools}"

    def test_tool_coordinator_integration(self, agent):
        """测试 ToolCoordinator 集成"""
        result = agent.analyze("推荐系统延迟升高")

        # 验证有证据
        assert len(result["evidence"]) > 0

        # 验证调用了超时工具
        evidence_tools = [ev["tool"] for ev in result["evidence"]]
        assert "search_timeout_events" in evidence_tools

    def test_quick_classify(self, agent):
        """测试快速分类"""
        initial = agent._quick_classify("支付接口 5xx 错误率 35%")

        assert "severity" in initial
        assert "category" in initial
        assert initial["severity"] in ["P0", "P1", "P2", "P3"]
        assert initial["category"] in ["availability", "latency", "database", "deployment", "unknown"]

    def test_parse_json(self, agent):
        """测试 JSON 解析"""
        # 测试纯 JSON
        result = agent._parse_json('{"severity": "P0", "category": "availability"}')
        assert result["severity"] == "P0"
        assert result["category"] == "availability"

        # 测试带 markdown 包裹
        result = agent._parse_json('```json\n{"severity": "P1", "category": "latency"}\n```')
        assert result["severity"] == "P1"
        assert result["category"] == "latency"

        # 测试解析失败
        result = agent._parse_json('invalid json')
        assert result["severity"] == "P3"
        assert result["category"] == "unknown"


if __name__ == "__main__":
    print("=" * 80)
    print("Agent V2 单元测试")
    print("=" * 80)

    agent = IncidentAgentV2()

    print("\n【测试 1】基础分析:")
    result = agent.analyze("支付接口 5xx 错误率 35%")
    print(f"✓ 分类: {result['classification']['severity']}, {result['classification']['category']}")
    print(f"✓ 证据: {len(result['evidence'])} 个工具")

    print("\n【测试 2】延迟问题 + 超时工具:")
    result = agent.analyze("推荐系统延迟升高")
    evidence_tools = [ev["tool"] for ev in result["evidence"]]
    print(f"✓ 调用工具: {', '.join(evidence_tools)}")
    assert "search_timeout_events" in evidence_tools
    print("✓ 正确调用了超时工具")

    print("\n【测试 3】OOM 问题 + OOM 工具:")
    result = agent.analyze("Pod 频繁 OOMKilled")
    evidence_tools = [ev["tool"] for ev in result["evidence"]]
    print(f"✓ 调用工具: {', '.join(evidence_tools)}")
    assert "search_oom_events" in evidence_tools
    print("✓ 正确调用了 OOM 工具")

    print("\n【测试 4】数据库问题 + 慢查询工具:")
    result = agent.analyze("MySQL 死锁")
    evidence_tools = [ev["tool"] for ev in result["evidence"]]
    print(f"✓ 调用工具: {', '.join(evidence_tools)}")
    assert "search_slow_queries" in evidence_tools
    print("✓ 正确调用了慢查询工具")

    print("\n✅ 所有测试通过！")
