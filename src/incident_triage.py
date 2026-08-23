from typing import Literal, Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationError
import logging
from policy import PolicyEngine
from trace_manager import TraceManager
from runbook_search import RunbookSearcher, RunbookMatch

# 配置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class IncidentTriage(BaseModel):
    """故障分类结果模型

    使用 Pydantic 强制校验模型输出，确保：
    1. 所有枚举值严格匹配
    2. 字段类型正确
    3. 必填字段不为空
    4. 数据完整性
    """

    severity: Literal["P0", "P1", "P2", "P3"] = Field(
        description="故障严重程度: P0=紧急(全面中断), P1=高(核心功能受影响), P2=中(部分功能受影响), P3=低(轻微影响)"
    )
    category: Literal["availability", "latency", "database", "deployment", "unknown"] = Field(
        description="故障类别: availability=可用性, latency=延迟, database=数据库, deployment=部署, unknown=未知"
    )
    needs_human_review: bool = Field(
        description="是否需要人工审核"
    )
    rationale: str = Field(
        min_length=10,
        max_length=500,
        description="分类依据和推理过程，必须提供充分理由"
    )

    @field_validator('rationale')
    @classmethod
    def validate_rationale(cls, v: str) -> str:
        """验证 rationale 字段不为空且有实际内容"""
        if not v or v.strip() == "":
            raise ValueError("rationale 不能为空")
        if len(v.strip()) < 10:
            raise ValueError("rationale 必须提供充分的分类理由（至少10个字符）")
        return v.strip()


class IncidentClassifier:
    """故障分类器"""

    def __init__(self, llm_client, trace_dir: str = "traces"):
        """
        初始化分类器

        Args:
            llm_client: LLM客户端实例
            trace_dir: 轨迹保存目录
        """
        self.llm_client = llm_client
        self.policy_engine = PolicyEngine()  # 初始化规则引擎
        self.trace_manager = TraceManager(trace_dir=trace_dir)  # 初始化轨迹管理器

        # 初始化运行手册检索器（如果目录存在）
        try:
            self.runbook_searcher = RunbookSearcher()
        except (FileNotFoundError, ValueError):
            logger.warning("运行手册目录不存在或为空，运行手册推荐功能将不可用")
            self.runbook_searcher = None

        self.system_prompt = """你是一个专业的故障分类助手。根据故障描述，你需要分析并返回以下信息：

1. severity (严重程度):
   - P0: 紧急 - 必须立即处理的严重故障，包括：
     * 涉及支付、交易、订单等直接影响收入的核心功能
     * 关键业务流程错误率超过 20% 或完全不可用
     * 全面服务中断，影响所有或绝大多数用户
     * 数据丢失、安全漏洞等重大风险

   - P1: 高 - 核心功能受到严重影响，但不直接影响收入或用户可以使用替代方案
     * 重要功能部分不可用，影响大量用户
     * 错误率在 5%-20% 之间

   - P2: 中 - 部分功能受影响，影响有限
     * 非核心功能异常
     * 错误率在 1%-5% 之间
     * 影响少量用户
     * 偶发且能自动恢复的问题（如：任务失败后重试成功）

   - P3: 低 - 轻微影响，可以稍后处理
     * 错误率低于 1%
     * 不影响用户体验

2. category (故障类别):
   分类优先级：database > deployment > latency > availability > unknown

   - database: 数据库相关故障（数据库宕机、主从同步、连接失败、查询慢、数据不一致、Redis/缓存问题）
     * 关键词：数据库、主库、从库、同步、Redis、缓存、OOM、连接池

   - deployment: 部署相关故障（发布失败、配置错误、静态资源加载失败、CSS/JS加载问题）
     * 关键词：部署、发布、配置、静态资源、CSS、JS、CDN配置

   - latency: 延迟/性能问题（响应慢、性能下降、消息队列积压）
     * 关键词：响应时间、延迟、慢、性能、队列积压

   - availability: 纯可用性问题（服务崩溃、超时、5xx错误、服务不可访问）
     * 仅当不属于上述任何类别时使用

   - unknown: 无法明确分类到以上任何类别的问题
     * 如：日志异常、推荐不准确、监控告警但无明确故障点

3. needs_human_review: 是否需要人工介入处理
   - P0、P1 级别故障：必须设为 true，需要人工立即介入处理
   - P2 级别故障：通常设为 false，除非满足以下条件之一才设为 true：
     * 影响范围可能扩大
     * 涉及数据安全或用户隐私
     * 原因不明确且可能影响核心业务
   - P3 级别故障：必须设为 false，可以自动化处理或稍后处理
   - 特殊规则：涉及金钱交易（支付、订单、退款）必须设为 true

4. rationale: 分类的理由，简要说明判断依据

重要提示：
- 支付、交易、订单等涉及收入的功能，只要错误率超过 20%，必须判定为 P0
- 关注业务影响，而不仅仅是技术指标
- 优先考虑对用户和业务的实际影响
- 分类 category 时严格遵循优先级：database > deployment > latency > availability > unknown
- Redis/缓存问题归类为 database，而非 availability
- CSS/JS 加载失败归类为 deployment，而非 availability
- 404 错误增多、日志异常等无明确故障点的归类为 unknown
- P2 和 P3 级别的常规故障，needs_human_review 应为 false

请仅返回JSON格式的分类结果。"""

    def classify(self, incident_description: str) -> IncidentTriage:
        """
        对故障进行分类

        Args:
            incident_description: 故障描述

        Returns:
            IncidentTriage: 分类结果

        Raises:
            ValueError: 当输入为空或模型输出无效时
            ValidationError: 当模型输出不符合 schema 约束时
        """
        import json

        # 开始轨迹记录
        trace_id = self.trace_manager.start_trace(incident_description)
        logger.info(f"开始分类，轨迹 ID: {trace_id}")

        if not incident_description or incident_description.strip() == "":
            error_msg = "故障描述不能为空"
            self.trace_manager.finish_trace(status="error", error_message=error_msg)
            raise ValueError(error_msg)

        prompt = f"""请对以下故障进行分类：

故障描述：
{incident_description}

请返回JSON格式的分类结果，包含以下字段：
- severity: "P0" | "P1" | "P2" | "P3"
- category: "availability" | "latency" | "database" | "deployment" | "unknown"
- needs_human_review: true | false
- rationale: string (分类理由)"""

        try:
            # 检查工具调用次数限制
            if not self.trace_manager.can_call_tool():
                error_msg = "证据不足：已达最大工具调用次数限制"
                logger.warning(error_msg)
                self.trace_manager.finish_trace(
                    status="insufficient_evidence",
                    error_message=error_msg
                )
                raise ValueError(error_msg)

            # 记录 LLM 调用
            tool_input = {
                "message": prompt,
                "system_prompt": self.system_prompt,
                "temperature": 0.3
            }

            response = self.llm_client.chat(
                message=prompt,
                system_prompt=self.system_prompt,
                temperature=0.3  # 使用较低温度以获得更稳定的分类结果
            )

            # 记录 LLM 调用结果
            self.trace_manager.record_tool_call(
                tool_name="llm_chat",
                tool_input=tool_input,
                tool_output=response,
                success=True
            )

            # 提取JSON（处理可能的markdown代码块包裹）
            response_text = response.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()

            # 第一层防护：JSON 解析校验
            try:
                result_dict = json.loads(response_text)
            except json.JSONDecodeError as e:
                error_msg = f"模型返回了无效的 JSON 格式: {str(e)}"
                logger.error(f"模型输出无法解析为 JSON: {response_text}")
                self.trace_manager.finish_trace(status="error", error_message=error_msg)
                raise ValueError(error_msg)

            # 第二层防护：Pydantic 强制校验
            try:
                validated_result = IncidentTriage(**result_dict)
            except ValidationError as e:
                error_msg = f"模型输出不符合分类规范: {str(e)}"
                logger.error(f"模型输出未通过 Pydantic 校验: {result_dict}")
                logger.error(f"校验错误详情: {e}")
                self.trace_manager.finish_trace(status="error", error_message=error_msg)
                raise ValueError(error_msg)

            # 第三层防护：Policy 规则引擎
            logger.info("执行 Policy 规则检查...")
            result_dict_after_policy = self.policy_engine.check_and_enforce(
                description=incident_description,
                result=validated_result.model_dump()
            )

            # 如果有规则修正，记录并重新创建对象
            if self.policy_engine.violations:
                logger.warning(f"Policy 引擎执行了 {len(self.policy_engine.violations)} 项修正")

                # 记录 Policy 修正
                self.trace_manager.record_tool_call(
                    tool_name="policy_engine",
                    tool_input={"original": validated_result.model_dump()},
                    tool_output={
                        "corrected": result_dict_after_policy,
                        "violations": [
                            {
                                "policy_name": v.policy_name,
                                "level": v.level.name,
                                "message": v.message,
                                "original_value": v.original_value,
                                "corrected_value": v.corrected_value
                            }
                            for v in self.policy_engine.violations
                        ]
                    },
                    success=True
                )

                validated_result = IncidentTriage(**result_dict_after_policy)

            # 第四层防护：业务逻辑一致性校验（兜底）
            self._validate_business_logic(validated_result)

            # 推荐相关运行手册
            recommended_runbooks = self.recommend_runbooks(incident_description)

            # 保存成功轨迹
            final_answer = validated_result.model_dump()
            final_answer['recommended_runbooks'] = [
                {
                    'runbook_id': rb.runbook_id,
                    'title': rb.title,
                    'score': rb.score,
                    'matched_keywords': rb.matched_keywords
                }
                for rb in recommended_runbooks
            ]
            self.trace_manager.finish_trace(
                final_answer=final_answer,
                status="success"
            )

            return validated_result

        except Exception as e:
            logger.error(f"分类失败: {str(e)}")
            # 如果还没保存轨迹，保存错误轨迹
            if self.trace_manager.current_trace:
                self.trace_manager.finish_trace(
                    status="error",
                    error_message=str(e)
                )
            raise

    def _validate_business_logic(self, result: IncidentTriage) -> None:
        """
        业务逻辑一致性校验

        Args:
            result: Pydantic 验证后的结果

        Raises:
            ValueError: 当业务逻辑不一致时
        """
        # 规则1: P0 和 P1 必须需要人工审核
        if result.severity in ["P0", "P1"] and not result.needs_human_review:
            logger.warning(f"业务逻辑警告: {result.severity} 级别故障应该需要人工审核")
            # 自动修正
            result.needs_human_review = True

        # 规则2: P3 级别不应该需要人工审核
        if result.severity == "P3" and result.needs_human_review:
            logger.warning(f"业务逻辑警告: P3 级别故障通常不需要人工审核")
            # 自动修正
            result.needs_human_review = False

    def recommend_runbooks(self, incident_description: str, top_k: int = 3) -> List[RunbookMatch]:
        """
        根据故障描述推荐相关运行手册

        Args:
            incident_description: 故障描述
            top_k: 返回最相关的 top_k 个运行手册

        Returns:
            List[RunbookMatch]: 推荐的运行手册列表，按匹配度降序排列
        """
        if not self.runbook_searcher:
            logger.warning("运行手册检索器未初始化，无法推荐运行手册")
            return []

        try:
            matches = self.runbook_searcher.search(incident_description, top_k=top_k)

            if matches:
                logger.info(f"为故障描述找到 {len(matches)} 个相关运行手册")
                for match in matches:
                    logger.info(f"  - {match.title} (匹配度: {match.score:.2f})")
            else:
                logger.info("未找到相关运行手册")

            return matches
        except Exception as e:
            logger.error(f"推荐运行手册失败: {str(e)}")
            return []

    def classify_batch(self, incidents: list[str]) -> list[IncidentTriage]:
        """
        批量分类故障

        Args:
            incidents: 故障描述列表

        Returns:
            list[IncidentTriage]: 分类结果列表

        Note:
            每个故障独立分类，单个故障失败不会影响其他故障的处理
            失败的分类会记录日志但不会抛出异常
        """
        results = []
        for i, incident in enumerate(incidents):
            try:
                result = self.classify(incident)
                results.append(result)
            except Exception as e:
                logger.error(f"批量分类第 {i+1} 项失败: {incident[:50]}... 错误: {str(e)}")
                # 跳过失败项，继续处理其他故障
                continue
        return results
