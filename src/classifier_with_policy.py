# classifier_with_policy.py
"""
Day 2: 集成 Classifier 和 Policy

展示完整流程：
1. LLM 初步分类
2. Policy 规则修正
3. 返回最终结果
"""
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from classifier import IncidentClassifier
from policy import PolicyEngine
from models import IncidentResult


class ClassifierWithPolicy:
    """
    带 Policy 的故障分类器

    工作流程：
    1. Classifier 进行初步分类（基于 LLM）
    2. PolicyEngine 检查并修正（基于规则）
    3. 返回修正后的结果
    """

    def __init__(self):
        self.classifier = IncidentClassifier()
        self.policy = PolicyEngine()

    def classify(self, description: str) -> IncidentResult:
        """
        完整的分类流程（LLM + Policy）

        Args:
            description: 故障描述

        Returns:
            修正后的分类结果
        """
        print(f"\n{'='*80}")
        print(f"分析故障: {description}")
        print(f"{'='*80}")

        # Step 1: LLM 初步分类
        print("\n[Step 1] LLM 初步分类...")
        llm_result = self.classifier.classify(description)

        print(f"  LLM 输出:")
        print(f"    severity: {llm_result.severity}")
        print(f"    category: {llm_result.category}")
        print(f"    needs_human_review: {llm_result.needs_human_review}")
        print(f"    rationale: {llm_result.rationale[:80]}...")

        # Step 2: Policy 规则检查
        print("\n[Step 2] Policy 规则检查...")

        # 转换为字典（Policy 接受字典输入）
        result_dict = llm_result.model_dump()

        # 应用规则
        final_dict = self.policy.check_and_enforce(description, result_dict)

        # 检查是否有修正
        violations = self.policy.get_violations()
        if violations:
            print(f"  ⚠️  检测到 {len(violations)} 个规则违反:")
            for v in violations:
                print(f"    - [{v.level.value}] {v.policy_name}")
                print(f"      {v.message}")
                print(f"      修正: {v.original_value} → {v.corrected_value}")
        else:
            print("  ✓ 无需修正")

        # Step 3: 转换回 Pydantic 模型
        final_result = IncidentResult(**final_dict)

        print(f"\n[最终结果]")
        print(f"  severity: {final_result.severity}")
        print(f"  category: {final_result.category}")
        print(f"  needs_human_review: {final_result.needs_human_review}")

        return final_result


def main():
    """测试 Classifier + Policy 集成"""
    analyzer = ClassifierWithPolicy()

    # 测试案例：展示 Policy 修正
    test_cases = [
        # 案例 1: 应该触发"高优先级必须审核"规则
        {
            "description": "支付接口 5xx 错误率 35%",
            "expected_correction": "P0/P1 必须人工审核"
        },

        # 案例 2: 应该触发"内部工具优先级限制"规则
        {
            "description": "内部管理后台响应慢",
            "expected_correction": "内部工具不应高于 P2"
        },

        # 案例 3: 应该触发"收入影响高优先级"规则
        {
            "description": "支付接口报错，错误率 25%",
            "expected_correction": "收入相关高错误率必须 P0"
        },

        # 案例 4: 不应该触发规则（推荐系统）
        {
            "description": "推荐系统 P99 延迟 2 秒",
            "expected_correction": "无"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        result = analyzer.classify(case["description"])

        print(f"\n预期修正: {case['expected_correction']}")
        print(f"{'='*80}\n")

        # 暂停一下，避免 API 限流
        if i < len(test_cases):
            import time
            time.sleep(1)


if __name__ == "__main__":
    main()
