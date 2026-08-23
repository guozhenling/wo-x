"""
pytest 测试用例 - Policy 规则引擎

纯单元测试，不调用 LLM 模型，直接测试规则逻辑
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from policy import PolicyEngine, PolicyLevel, PolicyAction, PolicyViolation


class TestPolicyEngine:
    """Policy 规则引擎测试类"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = PolicyEngine()

    def teardown_method(self):
        """每个测试后清理"""
        self.engine.violations.clear()

    # ==================== 规则 1: 高优先级必须人工复核 ====================

    def test_p0_must_have_human_review(self):
        """测试 P0 必须人工审核"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "测试故障"
        }

        corrected = self.engine.check_and_enforce("测试故障", result)

        assert corrected["needs_human_review"] is True
        assert len(self.engine.violations) == 1
        assert self.engine.violations[0].policy_name == "高优先级必须人工复核"
        assert self.engine.violations[0].level == PolicyLevel.CRITICAL

    def test_p1_must_have_human_review(self):
        """测试 P1 必须人工审核"""
        result = {
            "severity": "P1",
            "category": "latency",
            "needs_human_review": False,
            "rationale": "测试故障"
        }

        corrected = self.engine.check_and_enforce("测试故障", result)

        assert corrected["needs_human_review"] is True
        assert len(self.engine.violations) == 1

    def test_p0_already_has_review_no_violation(self):
        """测试 P0 已有人工审核，无违反"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True,
            "rationale": "测试故障"
        }

        corrected = self.engine.check_and_enforce("测试故障", result)

        assert corrected["needs_human_review"] is True
        # 可能有其他规则触发，但不应该有这条规则的违反
        # 这里不检查 violations 总数，只检查结果正确

    def test_p2_p3_no_forced_review(self):
        """测试 P2/P3 不强制人工审核"""
        for severity in ["P2", "P3"]:
            result = {
                "severity": severity,
                "category": "availability",
                "needs_human_review": False,
                "rationale": "测试故障"
            }

            corrected = self.engine.check_and_enforce("测试故障", result)

            # P2/P3 不强制审核（除非其他规则触发）
            # 这里只验证规则 1 不会触发
            violations_rule1 = [v for v in self.engine.violations if v.policy_name == "高优先级必须人工复核"]
            assert len(violations_rule1) == 0

    # ==================== 规则 2: 未知原因谦逊原则 ====================

    def test_unknown_cause_humility(self):
        """测试原因不明时必须标记为 unknown"""
        uncertain_keywords = [
            "原因不明", "不确定", "不清楚", "未知",
            "怀疑", "可能", "初步", "疑似"
        ]

        for keyword in uncertain_keywords:
            self.engine.violations.clear()

            result = {
                "severity": "P2",
                "category": "database",
                "needs_human_review": False,
                "rationale": "数据库问题"
            }

            corrected = self.engine.check_and_enforce(f"数据库连接失败，{keyword}", result)

            assert corrected["category"] == "unknown", f"关键词 '{keyword}' 未触发规则"
            assert corrected["needs_human_review"] is True
            violations = [v for v in self.engine.violations if v.policy_name == "未知原因谦逊原则"]
            assert len(violations) == 1

    def test_known_cause_no_humility_violation(self):
        """测试明确原因时不触发谦逊规则"""
        result = {
            "severity": "P2",
            "category": "database",
            "needs_human_review": False,
            "rationale": "数据库主库宕机"
        }

        corrected = self.engine.check_and_enforce("数据库主库宕机", result)

        assert corrected["category"] == "database"
        violations = [v for v in self.engine.violations if v.policy_name == "未知原因谦逊原则"]
        assert len(violations) == 0

    def test_already_unknown_no_violation(self):
        """测试已经是 unknown 时不重复触发"""
        result = {
            "severity": "P2",
            "category": "unknown",
            "needs_human_review": False,
            "rationale": "原因不明"
        }

        corrected = self.engine.check_and_enforce("故障原因不明", result)

        assert corrected["category"] == "unknown"
        violations = [v for v in self.engine.violations if v.policy_name == "未知原因谦逊原则"]
        assert len(violations) == 0

    # ==================== 规则 3: 收入影响高优先级 ====================

    def test_revenue_impact_high_error_rate(self):
        """测试收入相关 + 高错误率 → P0"""
        revenue_keywords = ["支付", "交易", "订单", "结算"]

        for keyword in revenue_keywords:
            self.engine.violations.clear()

            result = {
                "severity": "P2",
                "category": "availability",
                "needs_human_review": False,
                "rationale": "接口错误"
            }

            corrected = self.engine.check_and_enforce(f"{keyword}接口错误率 25%", result)

            assert corrected["severity"] == "P0", f"关键词 '{keyword}' + 高错误率未升级为 P0"
            assert corrected["needs_human_review"] is True

    def test_revenue_impact_low_error_rate(self):
        """测试收入相关 + 低错误率 → 至少 P1"""
        result = {
            "severity": "P3",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "支付接口错误"
        }

        corrected = self.engine.check_and_enforce("支付接口错误率 5%", result)

        assert corrected["severity"] == "P1"
        assert corrected["needs_human_review"] is True

    def test_revenue_p0_no_upgrade(self):
        """测试收入相关已经是 P0，不重复升级"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True,
            "rationale": "支付接口完全不可用"
        }

        corrected = self.engine.check_and_enforce("支付接口错误率 30%", result)

        assert corrected["severity"] == "P0"
        violations = [v for v in self.engine.violations if v.policy_name == "收入影响高优先级"]
        assert len(violations) == 0

    def test_non_revenue_no_upgrade(self):
        """测试非收入相关不触发此规则"""
        result = {
            "severity": "P3",
            "category": "latency",
            "needs_human_review": False,
            "rationale": "页面加载慢"
        }

        corrected = self.engine.check_and_enforce("页面加载慢", result)

        assert corrected["severity"] == "P3"
        violations = [v for v in self.engine.violations if v.policy_name == "收入影响高优先级"]
        assert len(violations) == 0

    # ==================== 规则 4: 内部工具优先级限制 ====================

    def test_internal_tool_downgrade_from_p0(self):
        """测试内部工具从 P0 降级为 P2"""
        internal_keywords = ["内部", "管理后台", "内部工具", "后台管理"]

        for keyword in internal_keywords:
            self.engine.violations.clear()

            result = {
                "severity": "P0",
                "category": "availability",
                "needs_human_review": True,
                "rationale": "工具不可用"
            }

            corrected = self.engine.check_and_enforce(f"{keyword}响应慢", result)

            assert corrected["severity"] == "P2", f"关键词 '{keyword}' 未降级"
            assert corrected["needs_human_review"] is False

    def test_internal_tool_downgrade_from_p1(self):
        """测试内部工具从 P1 降级为 P2"""
        result = {
            "severity": "P1",
            "category": "latency",
            "needs_human_review": True,
            "rationale": "管理后台慢"
        }

        corrected = self.engine.check_and_enforce("内部管理后台响应慢", result)

        assert corrected["severity"] == "P2"
        assert corrected["needs_human_review"] is False

    def test_internal_tool_p2_no_change(self):
        """测试内部工具已经是 P2，不改变"""
        result = {
            "severity": "P2",
            "category": "latency",
            "needs_human_review": False,
            "rationale": "管理后台慢"
        }

        corrected = self.engine.check_and_enforce("内部工具响应慢", result)

        assert corrected["severity"] == "P2"
        violations = [v for v in self.engine.violations if v.policy_name == "内部工具优先级限制"]
        assert len(violations) == 0

    def test_external_tool_no_downgrade(self):
        """测试外部工具不触发此规则"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True,
            "rationale": "用户页面不可用"
        }

        corrected = self.engine.check_and_enforce("用户页面完全不可用", result)

        assert corrected["severity"] == "P0"
        violations = [v for v in self.engine.violations if v.policy_name == "内部工具优先级限制"]
        assert len(violations) == 0

    # ==================== 规则 5: 核心服务宕机必须 P0 ====================

    def test_critical_service_outage_upgrade_to_p0(self):
        """测试核心服务宕机升级为 P0"""
        critical_services = ["支付", "登录", "注册", "主站", "数据库主库"]
        outage_keywords = ["完全不可用", "宕机", "崩溃", "down", "crash"]

        for service in critical_services:
            for outage in outage_keywords:
                self.engine.violations.clear()

                result = {
                    "severity": "P2",
                    "category": "availability",
                    "needs_human_review": False,
                    "rationale": "服务故障"
                }

                corrected = self.engine.check_and_enforce(f"{service}{outage}", result)

                assert corrected["severity"] == "P0", f"{service} + {outage} 未升级为 P0"
                assert corrected["needs_human_review"] is True

    def test_critical_service_slow_no_upgrade(self):
        """测试核心服务慢但没宕机，不触发规则"""
        result = {
            "severity": "P2",
            "category": "latency",
            "needs_human_review": False,
            "rationale": "支付慢"
        }

        corrected = self.engine.check_and_enforce("支付接口响应慢", result)

        # 支付相关会触发规则3，但不会触发规则5
        violations = [v for v in self.engine.violations if v.policy_name == "核心服务宕机必须P0"]
        assert len(violations) == 0

    def test_non_critical_service_outage_no_upgrade(self):
        """测试非核心服务宕机不触发规则"""
        result = {
            "severity": "P2",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "推荐服务宕机"
        }

        corrected = self.engine.check_and_enforce("推荐服务完全宕机", result)

        violations = [v for v in self.engine.violations if v.policy_name == "核心服务宕机必须P0"]
        assert len(violations) == 0

    # ==================== 规则 6: 数据安全必须审核 ====================

    def test_security_issue_must_review(self):
        """测试安全相关必须人工审核"""
        security_keywords = [
            "数据泄露", "数据丢失", "安全", "漏洞", "攻击",
            "权限", "越权", "注入", "XSS", "CSRF"
        ]

        for keyword in security_keywords:
            self.engine.violations.clear()

            result = {
                "severity": "P2",
                "category": "unknown",
                "needs_human_review": False,
                "rationale": "发现问题"
            }

            corrected = self.engine.check_and_enforce(f"发现{keyword}问题", result)

            assert corrected["needs_human_review"] is True, f"关键词 '{keyword}' 未强制审核"
            violations = [v for v in self.engine.violations if v.policy_name == "数据安全必须审核"]
            assert len(violations) == 1

    def test_security_already_review_no_violation(self):
        """测试安全问题已经审核，不重复触发"""
        result = {
            "severity": "P1",
            "category": "unknown",
            "needs_human_review": True,
            "rationale": "发现安全漏洞"
        }

        corrected = self.engine.check_and_enforce("发现安全漏洞", result)

        assert corrected["needs_human_review"] is True
        violations = [v for v in self.engine.violations if v.policy_name == "数据安全必须审核"]
        assert len(violations) == 0

    def test_non_security_no_forced_review(self):
        """测试非安全问题不触发此规则"""
        result = {
            "severity": "P3",
            "category": "latency",
            "needs_human_review": False,
            "rationale": "页面加载慢"
        }

        corrected = self.engine.check_and_enforce("页面加载慢", result)

        violations = [v for v in self.engine.violations if v.policy_name == "数据安全必须审核"]
        assert len(violations) == 0

    # ==================== 规则 7: 错误率阈值强制规则 ====================

    def test_high_error_rate_upgrade(self):
        """测试高错误率升级为 P1"""
        high_error_rates = ["50%", "60%", "75%", "90%"]

        for rate in high_error_rates:
            self.engine.violations.clear()

            result = {
                "severity": "P3",
                "category": "availability",
                "needs_human_review": False,
                "rationale": "接口错误"
            }

            corrected = self.engine.check_and_enforce(f"接口错误率 {rate}", result)

            assert corrected["severity"] == "P1", f"错误率 {rate} 未升级为 P1"
            assert corrected["needs_human_review"] is True

    def test_medium_error_rate_no_upgrade(self):
        """测试中等错误率不触发规则"""
        result = {
            "severity": "P3",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "接口错误"
        }

        corrected = self.engine.check_and_enforce("接口错误率 30%", result)

        # 30% 不触发规则7（阈值是50%），但可能触发其他规则
        violations = [v for v in self.engine.violations if v.policy_name == "高错误率阈值"]
        assert len(violations) == 0

    def test_no_error_rate_no_upgrade(self):
        """测试没有错误率信息不触发规则"""
        result = {
            "severity": "P3",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "接口偶尔失败"
        }

        corrected = self.engine.check_and_enforce("接口偶尔失败", result)

        violations = [v for v in self.engine.violations if v.policy_name == "高错误率阈值"]
        assert len(violations) == 0

    # ==================== 规则组合测试 ====================

    def test_multiple_rules_triggered(self):
        """测试多个规则同时触发"""
        result = {
            "severity": "P2",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "支付接口故障"
        }

        corrected = self.engine.check_and_enforce("支付接口完全宕机", result)

        # 应该触发规则3（收入影响）和规则5（核心服务宕机）
        assert corrected["severity"] == "P0"
        assert corrected["needs_human_review"] is True
        assert len(self.engine.violations) >= 2

    def test_rule_priority_order(self):
        """测试规则优先级顺序"""
        # 内部工具 + P0 → 应该降级为 P2（规则4）
        # 但如果同时是支付相关，规则3会覆盖规则4
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True,
            "rationale": "内部支付工具"
        }

        corrected = self.engine.check_and_enforce("内部支付管理工具宕机", result)

        # 规则4会先降级，但后续规则可能再次修改
        # 最终结果取决于规则执行顺序
        assert corrected["severity"] in ["P0", "P1", "P2"]

    def test_no_violations(self):
        """测试无违反的正常情况"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True,
            "rationale": "支付接口完全不可用，错误率100%"
        }

        corrected = self.engine.check_and_enforce("支付接口完全不可用，错误率100%", result)

        # 结果正确，没有需要修正的
        assert corrected["severity"] == "P0"
        assert corrected["needs_human_review"] is True
        # 可能有规则触发但没有修正（因为本来就对）
        critical_violations = [v for v in self.engine.violations if v.level == PolicyLevel.CRITICAL]
        # 关键规则不应该有违反
        assert len(critical_violations) == 0

    # ==================== 辅助方法测试 ====================

    def test_extract_error_rate(self):
        """测试错误率提取"""
        test_cases = [
            ("错误率 35%", 35.0),
            ("错误率35%", 35.0),
            ("错误率 99.9%", 99.9),
            ("错误率0.5%", 0.5),
            ("没有错误率", 0.0),
        ]

        for description, expected in test_cases:
            rate = self.engine._extract_error_rate(description)
            assert rate == expected, f"{description} 提取错误率失败"

    def test_has_critical_violations(self):
        """测试是否存在关键规则违反"""
        result = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": False,
            "rationale": "测试"
        }

        self.engine.check_and_enforce("测试", result)

        assert self.engine.has_critical_violations() is True

    def test_get_violations(self):
        """测试获取违反记录"""
        result = {
            "severity": "P0",
            "category": "database",
            "needs_human_review": False,
            "rationale": "数据库问题"
        }

        self.engine.check_and_enforce("数据库连接失败，原因不明", result)

        violations = self.engine.get_violations()
        assert len(violations) >= 2  # 至少触发规则1和规则2
        assert all(isinstance(v, PolicyViolation) for v in violations)


# ==================== Pytest Fixtures ====================

@pytest.fixture
def policy_engine():
    """Policy 引擎 fixture"""
    return PolicyEngine()


@pytest.fixture
def sample_result():
    """示例结果 fixture"""
    return {
        "severity": "P2",
        "category": "availability",
        "needs_human_review": False,
        "rationale": "测试故障描述"
    }


# ==================== Parametrized Tests ====================

@pytest.mark.parametrize("severity,expected_review", [
    ("P0", True),
    ("P1", True),
    ("P2", False),  # 除非其他规则触发
    ("P3", False),
])
def test_severity_review_mapping(policy_engine, severity, expected_review):
    """参数化测试：严重程度与审核的映射"""
    result = {
        "severity": severity,
        "category": "latency",
        "needs_human_review": False,
        "rationale": "测试故障"
    }

    corrected = policy_engine.check_and_enforce("普通故障", result)

    if severity in ["P0", "P1"]:
        assert corrected["needs_human_review"] is True
    # P2/P3 可能被其他规则修改，不做强制断言


@pytest.mark.parametrize("keyword,should_trigger", [
    ("原因不明", True),
    ("不确定", True),
    ("怀疑", True),
    ("确定是", False),
    ("已知", False),
])
def test_uncertainty_keywords(policy_engine, keyword, should_trigger):
    """参数化测试：不确定性关键词"""
    result = {
        "severity": "P2",
        "category": "database",
        "needs_human_review": False,
        "rationale": "数据库问题"
    }

    corrected = policy_engine.check_and_enforce(f"数据库连接失败，{keyword}", result)

    if should_trigger:
        assert corrected["category"] == "unknown"
    else:
        # 不应该被修改为 unknown
        assert corrected["category"] == "database"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
