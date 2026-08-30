"""
性能监控集成的 Agent

包装 IncidentAgentV2，自动收集性能指标
"""
import logging
from typing import Dict, Any
from src.agent_v2 import IncidentAgentV2
from tools.performance_metrics import get_collector

logger = logging.getLogger(__name__)


class PerformanceMonitoredAgent(IncidentAgentV2):
    """带性能监控的 Agent"""

    def __init__(self, model: str = None, temperature: float = 0.3):
        super().__init__(model, temperature)
        self.collector = get_collector()
        logger.info("启用性能监控")

    def analyze(self, incident_description: str) -> Dict[str, Any]:
        """
        分析故障（带性能监控）

        自动收集：
        - 各步骤耗时
        - LLM 调用次数
        - 工具调用次数
        - 缓存命中率
        """
        # 重置收集器
        self.collector.reset()

        # 开始总计时
        self.collector.start_step("total")
        self.collector.start_step("initial_classification")

        try:
            # 调用父类的 analyze
            result = super().analyze(incident_description)

            # 记录成功
            self.collector.end_step("total")

            # 打印性能摘要
            logger.info("\n" + "=" * 60)
            self.collector.print_summary()

            return result

        except Exception as e:
            self.collector.end_step("total")
            logger.error(f"分析失败: {e}")
            raise

    def _quick_classify(self, incident_description: str) -> Dict[str, Any]:
        """快速分类（带监控）"""
        self.collector.record_llm_call()
        result = super()._quick_classify(incident_description)
        self.collector.end_step("initial_classification")
        return result

    def _final_classify_with_evidence(
        self,
        incident_description: str,
        initial_classification: Dict[str, Any],
        evidence: list
    ) -> Dict[str, Any]:
        """最终分类（带监控）"""
        self.collector.start_step("final_classification")
        self.collector.record_llm_call()
        result = super()._final_classify_with_evidence(
            incident_description,
            initial_classification,
            evidence
        )
        self.collector.end_step("final_classification")
        return result

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return self.collector.get_metrics().to_dict()


def create_monitored_agent() -> PerformanceMonitoredAgent:
    """创建带性能监控的 Agent"""
    return PerformanceMonitoredAgent()
