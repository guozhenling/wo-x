# classifier.py
"""
Day 1: 故障分类器

实现基本的故障分类功能：
1. 调用 LLM 分析故障描述
2. 输出结构化 JSON
3. 用 Pydantic 校验结果

这是最简单的版本，Day 2 会添加 Policy 规则。
"""
import os
import json
import logging
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

from models import IncidentResult

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncidentClassifier:
    """
    故障分类器

    功能：
    - 接收故障描述
    - 调用 LLM 分析
    - 返回结构化结果

    示例：
        classifier = IncidentClassifier()
        result = classifier.classify("支付接口 5xx 错误率 35%")
        print(f"严重程度: {result.severity}")
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3
    ):
        """
        初始化分类器

        Args:
            model: 使用的 LLM 模型
            temperature: 温度参数（0-1，越低越确定）
        """
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        self.model = model
        self.temperature = temperature

        logger.info(f"初始化分类器: model={model}, temperature={temperature}")

    def classify(self, description: str) -> IncidentResult:
        """
        分类故障

        Args:
            description: 故障描述

        Returns:
            IncidentResult: 结构化的分类结果

        Raises:
            ValueError: 如果 LLM 输出不符合 schema
            Exception: 如果 API 调用失败
        """
        logger.info(f"分类故障: {description[:50]}...")

        # 构造 Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = f"分析以下故障并分类：\n\n{description}"

        try:
            # 调用 LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}  # 强制 JSON 输出
            )

            # 解析响应
            response_text = response.choices[0].message.content
            logger.debug(f"LLM 响应: {response_text}")

            # JSON 解析
            data = json.loads(response_text)

            # Pydantic 校验
            result = IncidentResult(**data)

            logger.info(
                f"分类完成: {result.severity} / {result.category} / "
                f"需要审核: {result.needs_human_review}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            logger.error(f"原始输出: {response_text}")
            raise ValueError(f"LLM 输出不是有效的 JSON: {e}")

        except Exception as e:
            logger.error(f"分类失败: {e}", exc_info=True)
            raise

    def _build_system_prompt(self) -> str:
        """
        构造系统提示词

        定义：
        1. LLM 的角色
        2. 输出格式
        3. 判断标准
        """
        return """你是一个故障分类专家。

你的任务是分析故障描述，输出结构化的 JSON。

## 严重程度判断标准

- P0（紧急）：核心功能完全不可用
  * 支付、登录等关键功能全部失败
  * 错误率 > 20%
  * 影响所有或大部分用户

- P1（高）：核心功能严重受损
  * 核心功能部分失败
  * 错误率 5%-20%
  * 影响大量用户

- P2（中）：非核心功能受损
  * 非关键功能异常
  * 错误率 1%-5%
  * 影响少量用户

- P3（低）：轻微影响
  * 错误率 < 1%
  * 几乎不影响用户

## 类别判断

- availability: 服务不可用、5xx 错误、超时
- latency: 延迟过高、响应慢
- database: 数据库连接、死锁、慢查询
- deployment: 发布后异常、配置错误
- unknown: 无法确定

## 输出格式（JSON）

{
  "severity": "P0/P1/P2/P3",
  "category": "availability/latency/database/deployment/unknown",
  "needs_human_review": true/false,
  "rationale": "判断依据（必须详细说明为什么这么分类）"
}

## 注意事项

1. 只输出 JSON，不要其他文字
2. rationale 必须详细，说明判断依据
3. 如果信息不足，severity 倾向保守（选较高的）
4. needs_human_review: P0/P1 通常为 true
"""


def main():
    """测试分类器"""
    classifier = IncidentClassifier()

    # 测试案例
    test_cases = [
        "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "MySQL 报 1205 死锁错误，影响订单创建"
    ]

    print("=" * 80)
    print("故障分类器测试")
    print("=" * 80)

    for i, case in enumerate(test_cases, 1):
        print(f"\n案例 {i}: {case}")
        print("-" * 80)

        try:
            result = classifier.classify(case)

            print(f"严重程度: {result.severity}")
            print(f"类别: {result.category}")
            print(f"需要审核: {result.needs_human_review}")
            print(f"依据: {result.rationale}")

        except Exception as e:
            print(f"✗ 分类失败: {e}")

    print("\n" + "=" * 80)
    print("测试完成")


if __name__ == "__main__":
    main()
