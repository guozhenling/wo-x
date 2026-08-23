"""
Policy 模块 - 确定性规则引擎

用于定义和执行确定性规则，避免模型幻觉。
规则优先级高于模型输出，确保关键决策的可靠性。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import re
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class PolicyLevel(Enum):
    """规则优先级"""
    CRITICAL = "critical"  # 关键规则，必须执行
    HIGH = "high"          # 高优先级规则
    MEDIUM = "medium"      # 中优先级规则
    LOW = "low"            # 低优先级规则


class PolicyAction(Enum):
    """规则动作"""
    ENFORCE = "enforce"    # 强制执行（直接修改结果）
    WARN = "warn"         # 警告（记录日志但不修改）
    REJECT = "reject"     # 拒绝（抛出异常）
    REVIEW = "review"     # 需要人工审核


@dataclass
class PolicyViolation:
    """规则违反记录"""
    policy_name: str
    level: PolicyLevel
    action: PolicyAction
    message: str
    original_value: Any
    corrected_value: Optional[Any] = None


class PolicyEngine:
    """规则引擎"""

    def __init__(self):
        self.violations: List[PolicyViolation] = []
        self._init_policies()

    def _init_policies(self):
        """初始化所有规则"""
        logger.info("初始化 Policy 引擎")

    def check_and_enforce(
        self,
        description: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查并执行所有规则

        Args:
            description: 故障描述
            result: 模型输出结果

        Returns:
            修正后的结果
        """
        start_time = time.time()
        self.violations.clear()

        # 记录原始输入（用于监控）
        original_severity = result.get('severity')
        original_needs_review = result.get('needs_human_review')

        # 规则 1：高优先级事故必须人工复核
        result = self._enforce_high_priority_review(result)

        # 规则 2：分类未知时，不能假装已经找到根因
        result = self._enforce_unknown_category_humility(result, description)

        # 规则 3：影响收入的故障必须高优先级
        result = self._enforce_revenue_impact(result, description)

        # 规则 4：内部工具故障不应该是 P0/P1
        result = self._enforce_internal_tool_priority(result, description)

        # 规则 5：完全不可用的核心服务必须 P0
        result = self._enforce_critical_outage(result, description)

        # 规则 6：数据安全相关必须人工审核
        result = self._enforce_data_security_review(result, description)

        # 规则 7：错误率阈值强制规则
        result = self._enforce_error_rate_threshold(result, description)

        # 计算执行耗时
        duration_ms = (time.time() - start_time) * 1000

        # 结构化日志监控埋点
        if self.violations:
            self._log_violations_structured(
                description=description,
                original_severity=original_severity,
                final_severity=result.get('severity'),
                original_needs_review=original_needs_review,
                final_needs_review=result.get('needs_human_review'),
                duration_ms=duration_ms
            )
        else:
            # 即使没有违反，也记录执行情况（用于性能监控）
            logger.info(json.dumps({
                "event": "policy_check_no_violation",
                "timestamp": datetime.now().isoformat(),
                "duration_ms": round(duration_ms, 2),
                "severity": result.get('severity')
            }, ensure_ascii=False))

        return result

    def _enforce_high_priority_review(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        规则 1：高优先级事故必须人工复核

        P0 和 P1 级别的故障必须标记为需要人工审核。
        这是硬性要求，不容商量。
        """
        severity = result.get('severity')
        needs_review = result.get('needs_human_review')

        if severity in ['P0', 'P1'] and not needs_review:
            self.violations.append(PolicyViolation(
                policy_name="高优先级必须人工复核",
                level=PolicyLevel.CRITICAL,
                action=PolicyAction.ENFORCE,
                message=f"{severity} 级别故障必须人工审核",
                original_value=needs_review,
                corrected_value=True
            ))
            result['needs_human_review'] = True
            logger.critical(f"强制修正: {severity} 必须人工审核")

        return result

    def _enforce_unknown_category_humility(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 2：分类未知时，不能假装已经找到根因

        如果描述中明确说"原因不明"、"不确定"等，category 必须是 unknown。
        避免模型强行给出一个看似合理但可能错误的分类。
        """
        uncertainty_keywords = [
            "原因不明", "不确定", "不清楚", "未知", "unknown",
            "怀疑", "可能", "初步", "疑似"
        ]

        category = result.get('category')

        if any(kw in description for kw in uncertainty_keywords):
            if category != 'unknown':
                self.violations.append(PolicyViolation(
                    policy_name="未知原因谦逊原则",
                    level=PolicyLevel.HIGH,
                    action=PolicyAction.ENFORCE,
                    message=f"描述中存在不确定性关键词，但分类为 {category}",
                    original_value=category,
                    corrected_value='unknown'
                ))
                result['category'] = 'unknown'
                logger.warning(f"强制修正: 存在不确定性关键词，分类改为 unknown")

                # 同时修正 rationale
                result['needs_human_review'] = True
                rationale = result.get('rationale', '')
                if '原因不明' not in rationale:
                    result['rationale'] = f"[Policy修正] 原因不明确，需进一步调查。{rationale}"

        return result

    def _enforce_revenue_impact(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 3：影响收入的故障必须高优先级

        支付、交易、订单等直接影响收入的故障，根据错误率判断：
        - 错误率 >= 20%: 必须 P0
        - 错误率 >= 5%: 至少 P1
        - 错误率 < 5%: 可以是 P2（有降级处理的情况）
        """
        revenue_keywords = ["支付", "交易", "订单", "结算", "payment", "transaction"]
        severity = result.get('severity')

        if any(kw in description for kw in revenue_keywords):
            # 检查错误率
            error_rate = self._extract_error_rate(description)

            # 高错误率：>= 20%，必须 P0
            if error_rate >= 20:
                if severity != 'P0':
                    self.violations.append(PolicyViolation(
                        policy_name="收入影响高优先级",
                        level=PolicyLevel.CRITICAL,
                        action=PolicyAction.ENFORCE,
                        message=f"收入相关故障且错误率 {error_rate}% >= 20%，必须 P0",
                        original_value=severity,
                        corrected_value='P0'
                    ))
                    result['severity'] = 'P0'
                    result['needs_human_review'] = True
                    logger.critical(f"强制修正: 收入相关高错误率故障提升为 P0")

            # 中等错误率：>= 5%，至少 P1
            elif error_rate >= 5:
                if severity in ['P2', 'P3']:
                    self.violations.append(PolicyViolation(
                        policy_name="收入影响高优先级",
                        level=PolicyLevel.HIGH,
                        action=PolicyAction.ENFORCE,
                        message=f"收入相关故障且错误率 {error_rate}% >= 5%，至少 P1",
                        original_value=severity,
                        corrected_value='P1'
                    ))
                    result['severity'] = 'P1'
                    result['needs_human_review'] = True
                    logger.warning(f"强制修正: 收入相关中等错误率故障提升为 P1")

            # 低错误率：< 5%，可以是 P2
            # 这种情况通常有降级处理，整体成功率高，不强制提升
            else:
                logger.info(f"收入相关故障但错误率 {error_rate}% < 5%，保持 {severity}")

        return result

    def _enforce_internal_tool_priority(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 4：内部工具故障不应该是 P0/P1

        内部工具、管理后台等不直接影响用户的功能，
        最高只能是 P2。
        """
        internal_keywords = ["内部", "管理后台", "内部工具", "后台管理"]
        severity = result.get('severity')

        if any(kw in description for kw in internal_keywords):
            if severity in ['P0', 'P1']:
                self.violations.append(PolicyViolation(
                    policy_name="内部工具优先级限制",
                    level=PolicyLevel.HIGH,
                    action=PolicyAction.ENFORCE,
                    message=f"内部工具故障不应高于 P2",
                    original_value=severity,
                    corrected_value='P2'
                ))
                result['severity'] = 'P2'
                result['needs_human_review'] = False
                logger.warning(f"强制修正: 内部工具故障降级为 P2")

        return result

    def _enforce_critical_outage(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 5：完全不可用的核心服务必须 P0

        如果核心服务（支付、登录、主站等）完全不可用，
        必须是 P0。
        """
        critical_services = ["支付", "登录", "注册", "主站", "数据库主库"]
        outage_keywords = ["完全不可用", "宕机", "崩溃", "down", "crash"]

        severity = result.get('severity')

        has_critical = any(svc in description for svc in critical_services)
        has_outage = any(kw in description for kw in outage_keywords)

        if has_critical and has_outage:
            if severity != 'P0':
                self.violations.append(PolicyViolation(
                    policy_name="核心服务宕机必须P0",
                    level=PolicyLevel.CRITICAL,
                    action=PolicyAction.ENFORCE,
                    message=f"核心服务完全不可用必须 P0",
                    original_value=severity,
                    corrected_value='P0'
                ))
                result['severity'] = 'P0'
                result['needs_human_review'] = True
                logger.critical(f"强制修正: 核心服务宕机提升为 P0")

        return result

    def _enforce_data_security_review(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 6：数据安全相关必须人工审核

        涉及数据泄露、数据丢失、安全漏洞等，
        无论严重程度如何，都必须人工审核。
        """
        security_keywords = [
            "数据泄露", "数据丢失", "安全", "漏洞", "攻击",
            "权限", "越权", "注入", "XSS", "CSRF"
        ]

        needs_review = result.get('needs_human_review')

        if any(kw in description for kw in security_keywords):
            if not needs_review:
                self.violations.append(PolicyViolation(
                    policy_name="数据安全必须审核",
                    level=PolicyLevel.CRITICAL,
                    action=PolicyAction.ENFORCE,
                    message=f"安全相关故障必须人工审核",
                    original_value=needs_review,
                    corrected_value=True
                ))
                result['needs_human_review'] = True
                logger.critical(f"强制修正: 安全相关故障必须人工审核")

        return result

    def _enforce_error_rate_threshold(
        self,
        result: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        规则 7：错误率阈值强制规则

        根据错误率自动判断严重程度：
        - >= 50%: 至少 P1
        - >= 30%: 至少 P1（如果是核心服务）
        - >= 20%: 至少 P1（如果是收入相关）
        """
        error_rate = self._extract_error_rate(description)
        severity = result.get('severity')

        if error_rate >= 50:
            if severity in ['P2', 'P3']:
                self.violations.append(PolicyViolation(
                    policy_name="高错误率阈值",
                    level=PolicyLevel.HIGH,
                    action=PolicyAction.ENFORCE,
                    message=f"错误率 {error_rate}% >= 50%，至少 P1",
                    original_value=severity,
                    corrected_value='P1'
                ))
                result['severity'] = 'P1'
                result['needs_human_review'] = True
                logger.warning(f"强制修正: 高错误率 {error_rate}% 提升为 P1")

        return result

    def _extract_error_rate(self, description: str) -> float:
        """
        提取错误率百分比

        注意：
        - "错误率 30%" -> 30
        - "成功率 97%" -> 3 (反向计算)
        - "5xx 升到 35%" -> 35
        """
        # 先检查是否明确提到错误率
        error_match = re.search(r'错误率\s*[：:]\s*(\d+(?:\.\d+)?)%', description)
        if error_match:
            return float(error_match.group(1))

        # 检查是否提到成功率（需要反向计算）
        success_match = re.search(r'成功率\s*[：:]\s*(\d+(?:\.\d+)?)%', description)
        if success_match:
            success_rate = float(success_match.group(1))
            return 100.0 - success_rate

        # 检查整体成功率的表述
        success_match2 = re.search(r'整体成功率\s*(\d+(?:\.\d+)?)%', description)
        if success_match2:
            success_rate = float(success_match2.group(1))
            return 100.0 - success_rate

        # 检查 5xx 升到 xx%、从 xx% 升到 yy% 等模式
        increase_match = re.search(r'(?:升到|升至|达到)\s*(\d+(?:\.\d+)?)%', description)
        if increase_match:
            return float(increase_match.group(1))

        # 检查 "影响 xx% 用户"、"xx% 用户" 等模式
        impact_match = re.search(r'(?:影响|超时|失败).*?(\d+(?:\.\d+)?)%', description)
        if impact_match:
            return float(impact_match.group(1))

        # 最后才用通用匹配（第一个百分比）
        general_match = re.search(r'(\d+(?:\.\d+)?)%', description)
        if general_match:
            return float(general_match.group(1))

        return 0.0

    def get_violations(self) -> List[PolicyViolation]:
        """获取所有规则违反记录"""
        return self.violations

    def has_critical_violations(self) -> bool:
        """是否存在关键规则违反"""
        return any(v.level == PolicyLevel.CRITICAL for v in self.violations)

    def _log_violations_structured(
        self,
        description: str,
        original_severity: str,
        final_severity: str,
        original_needs_review: bool,
        final_needs_review: bool,
        duration_ms: float
    ):
        """
        结构化日志记录规则违反（监控埋点）

        输出 JSON 格式日志，便于日志收集工具（Filebeat/Fluentd）解析和聚合。

        日志分析：
            # 统计规则触发次数
            cat policy.log | jq -r '.violations[].policy_name' | sort | uniq -c

            # 查看 CRITICAL 级别触发
            cat policy.log | jq 'select(.violations[].level=="critical")'

            # 统计严重度修正
            cat policy.log | jq 'select(.changes.severity.changed==true)'

            # 使用分析工具
            python tests/analyze_policy_logs.py logs/policy.log

        生产环境：
            1. 配置日志输出到文件（RotatingFileHandler）
            2. 使用 Filebeat/Fluentd 收集日志
            3. 发送到 Elasticsearch/Splunk
            4. 在 Kibana/Grafana 中可视化

        告警建议：
            - 违反率 > 50%: 模型质量下降
            - CRITICAL 触发: 关键规则触发，立即检查
            - 执行耗时 > 100ms: 性能问题
        """
        # 汇总日志（一次性输出所有违反）
        log_data = {
            "event": "policy_violations",
            "timestamp": datetime.now().isoformat(),
            "total_violations": len(self.violations),
            "duration_ms": round(duration_ms, 2),
            "description_preview": description[:100],  # 截取前100字符
            "changes": {
                "severity": {
                    "original": original_severity,
                    "final": final_severity,
                    "changed": original_severity != final_severity
                },
                "needs_human_review": {
                    "original": original_needs_review,
                    "final": final_needs_review,
                    "changed": original_needs_review != final_needs_review
                }
            },
            "violations": []
        }

        # 记录每个违反详情
        for v in self.violations:
            violation_detail = {
                "policy_name": v.policy_name,
                "level": v.level.value,
                "action": v.action.value,
                "message": v.message,
                "original_value": str(v.original_value),
                "corrected_value": str(v.corrected_value) if v.corrected_value else None
            }
            log_data["violations"].append(violation_detail)

        # 输出结构化 JSON 日志
        logger.warning(json.dumps(log_data, ensure_ascii=False))

        # 按规则级别统计（用于快速告警）
        by_level = {}
        for v in self.violations:
            level = v.level.value
            by_level[level] = by_level.get(level, 0) + 1

        # 如果有 CRITICAL 级别违反，额外输出告警日志
        if self.has_critical_violations():
            critical_policies = [v.policy_name for v in self.violations if v.level == PolicyLevel.CRITICAL]
            logger.critical(json.dumps({
                "event": "critical_policy_violation",
                "timestamp": datetime.now().isoformat(),
                "policies": critical_policies,
                "severity_change": f"{original_severity} -> {final_severity}",
                "alert": "CRITICAL规则触发，需要关注模型输出质量"
            }, ensure_ascii=False))
