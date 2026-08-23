#!/usr/bin/env python3
"""
故障分析 Agent 评测脚本

使用评测数据集测试 Agent 的分类准确性
"""
import sys
import os
import json
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import IncidentAgent


def load_evaluation_dataset(file_path: str) -> List[Dict[str, Any]]:
    """加载评测数据集"""
    dataset = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                dataset.append(json.loads(line))
    return dataset


def evaluate_classification(predicted: Dict, expected: Dict) -> Dict[str, bool]:
    """评估分类结果"""
    return {
        "severity_match": predicted.get("severity") == expected.get("severity"),
        "category_match": predicted.get("category") == expected.get("category"),
        "review_match": predicted.get("needs_human_review") == expected.get("needs_human_review")
    }


def run_evaluation(dataset_path: str, limit: int = None):
    """运行评测"""
    print("=" * 80)
    print("故障分析 Agent 评测")
    print("=" * 80)

    # 加载数据集
    dataset = load_evaluation_dataset(dataset_path)
    if limit:
        dataset = dataset[:limit]

    print(f"\n加载评测数据: {len(dataset)} 条")

    # 初始化 Agent
    agent = IncidentAgent()

    # 评测结果
    results = []
    severity_correct = 0
    category_correct = 0
    review_correct = 0

    for i, case in enumerate(dataset, 1):
        case_id = case.get("id", f"case_{i}")
        description = case["description"]
        expected = case["expected"]

        print(f"\n{'=' * 80}")
        print(f"案例 {i}/{len(dataset)}: {case_id}")
        print(f"描述: {description}")
        print(f"预期: severity={expected['severity']}, category={expected['category']}, review={expected['needs_human_review']}")

        # 执行分析
        try:
            result = agent.analyze(description)
            predicted = result["classification"]

            # 评估
            eval_result = evaluate_classification(predicted, expected)

            print(f"实际: severity={predicted['severity']}, category={predicted['category']}, review={predicted['needs_human_review']}")
            print(f"匹配: severity={eval_result['severity_match']}, category={eval_result['category_match']}, review={eval_result['review_match']}")

            # 统计
            if eval_result["severity_match"]:
                severity_correct += 1
            if eval_result["category_match"]:
                category_correct += 1
            if eval_result["review_match"]:
                review_correct += 1

            results.append({
                "case_id": case_id,
                "description": description,
                "expected": expected,
                "predicted": predicted,
                "evaluation": eval_result,
                "tools_called": len(result.get("evidence", []))
            })

        except Exception as e:
            print(f"❌ 分析失败: {e}")
            results.append({
                "case_id": case_id,
                "description": description,
                "expected": expected,
                "error": str(e)
            })

    # 汇总结果
    print("\n" + "=" * 80)
    print("评测结果汇总")
    print("=" * 80)

    total = len(dataset)
    print(f"\n总案例数: {total}")
    print(f"\n严重程度准确率: {severity_correct}/{total} ({severity_correct/total*100:.1f}%)")
    print(f"类别准确率: {category_correct}/{total} ({category_correct/total*100:.1f}%)")
    print(f"审核标记准确率: {review_correct}/{total} ({review_correct/total*100:.1f}%)")

    # 全部匹配的案例
    all_correct = sum(1 for r in results if
                     r.get("evaluation", {}).get("severity_match") and
                     r.get("evaluation", {}).get("category_match") and
                     r.get("evaluation", {}).get("review_match"))
    print(f"\n完全匹配: {all_correct}/{total} ({all_correct/total*100:.1f}%)")

    # 保存详细结果
    output_file = "evaluation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total": total,
                "severity_correct": severity_correct,
                "category_correct": category_correct,
                "review_correct": review_correct,
                "all_correct": all_correct,
                "severity_accuracy": severity_correct / total,
                "category_accuracy": category_correct / total,
                "review_accuracy": review_correct / total,
                "overall_accuracy": all_correct / total
            },
            "details": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n详细结果已保存: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="故障分析 Agent 评测")
    parser.add_argument("--dataset",
                       default=os.path.join(os.path.dirname(__file__), "..", "data", "evaluation_dataset.jsonl"),
                       help="评测数据集路径")
    parser.add_argument("--limit", type=int, default=None,
                       help="限制评测案例数量（用于快速测试）")

    args = parser.parse_args()

    run_evaluation(args.dataset, args.limit)
