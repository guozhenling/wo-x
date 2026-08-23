# models.py
"""
Day 1: Pydantic 数据模型定义

定义故障分类的结构化输出模型，用于：
1. 强制 LLM 输出符合预期格式
2. 自动校验字段类型和值域
3. 提供清晰的数据结构
"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Severity(str):
    """严重程度枚举"""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Category(str):
    """故障类别枚举"""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    DATABASE = "database"
    DEPLOYMENT = "deployment"
    UNKNOWN = "unknown"


class IncidentResult(BaseModel):
    """
    故障分类结果模型

    使用 Pydantic 强制校验 LLM 输出，确保：
    1. 严重程度只能是 P0/P1/P2/P3
    2. 类别在预定义范围内
    3. 必填字段不为空
    4. rationale 有最小长度要求

    示例：
        result = IncidentResult(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="支付接口完全不可用，影响所有用户"
        )
    """

    severity: Literal["P0", "P1", "P2", "P3"] = Field(
        description="故障严重程度: P0=紧急, P1=高, P2=中, P3=低"
    )

    category: Literal["availability", "latency", "database", "deployment", "unknown"] = Field(
        description="故障类别"
    )

    needs_human_review: bool = Field(
        description="是否需要人工审核"
    )

    rationale: str = Field(
        min_length=10,
        max_length=500,
        description="分类依据，必须提供充分理由"
    )

    @field_validator('rationale')
    @classmethod
    def validate_rationale(cls, v: str) -> str:
        """
        验证 rationale 字段

        要求：
        - 不能为空
        - 去除首尾空格后至少 10 个字符
        """
        if not v or v.strip() == "":
            raise ValueError("rationale 不能为空")

        if len(v.strip()) < 10:
            raise ValueError("rationale 必须提供充分的分类理由（至少10个字符）")

        return v.strip()

    class Config:
        """Pydantic 配置"""
        use_enum_values = True  # 序列化时使用枚举值


# 向后兼容：保留旧名称
IncidentTriage = IncidentResult


if __name__ == "__main__":
    # 测试：合法输入
    print("测试 1: 合法输入")
    try:
        result = IncidentResult(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="支付接口完全不可用，所有用户无法支付"
        )
        print("✓ 校验通过:", result.model_dump_json(indent=2))
    except Exception as e:
        print("✗ 校验失败:", e)

    # 测试：非法的 severity
    print("\n测试 2: 非法的 severity")
    try:
        result = IncidentResult(
            severity="critical",  # 错误：不是 P0/P1/P2/P3
            category="availability",
            needs_human_review=True,
            rationale="测试非法值"
        )
        print("✗ 应该失败但通过了")
    except Exception as e:
        print("✓ 正确拒绝:", str(e)[:100])

    # 测试：rationale 太短
    print("\n测试 3: rationale 太短")
    try:
        result = IncidentResult(
            severity="P0",
            category="availability",
            needs_human_review=True,
            rationale="短"  # 错误：太短
        )
        print("✗ 应该失败但通过了")
    except Exception as e:
        print("✓ 正确拒绝:", str(e)[:100])

    print("\n✅ 所有测试完成")
