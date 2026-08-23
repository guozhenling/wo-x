#!/usr/bin/env python3
"""
故障分类 + 运行手册推荐演示

展示如何使用故障分类器，并获取推荐的运行手册
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from incident_triage import IncidentClassifier

# 获取项目根目录的配置文件路径
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")


def demo_classify_with_runbook():
    """演示故障分类 + 运行手册推荐"""

    print("=" * 80)
    print("故障分类 + 运行手册推荐演示")
    print("=" * 80)
    print()

    # 初始化客户端和分类器（使用项目根目录的配置文件）
    client = LLMClient(config_path=CONFIG_PATH)
    classifier = IncidentClassifier(client)

    # 确保使用项目根目录的 runbooks 目录
    from runbook_search import RunbookSearcher
    runbooks_dir = str(PROJECT_ROOT / "runbooks")
    classifier.runbook_searcher = RunbookSearcher(runbooks_dir=runbooks_dir)

    # 测试用例
    test_cases = [
        "支付接口返回 502 错误，错误率 25%",
        "数据库出现死锁，订单表被锁定",
        "刚才发布后错误率从 1% 升到 15%",
        "用户登录接口响应时间从 200ms 上升到 3s"
    ]

    for i, description in enumerate(test_cases, 1):
        print(f"[案例 {i}]")
        print(f"描述: {description}")
        print("-" * 80)

        try:
            # 分类故障
            result = classifier.classify(description)

            # 显示分类结果
            print(f"✓ 严重程度: {result.severity}")
            print(f"✓ 故障类别: {result.category}")
            print(f"✓ 需要人工审核: {'是' if result.needs_human_review else '否'}")
            print(f"✓ 分类理由: {result.rationale}")
            print()

            # 推荐运行手册
            runbooks = classifier.recommend_runbooks(description, top_k=2)

            if runbooks:
                print("📚 推荐的运行手册:")
                for j, rb in enumerate(runbooks, 1):
                    print(f"\n  {j}. {rb.title}")
                    print(f"     文档 ID: {rb.runbook_id}")
                    print(f"     匹配度: {rb.score:.2f}")
                    print(f"     匹配关键词: {', '.join(rb.matched_keywords)}")

                    # 显示运行手册的适用条件（前3条）
                    if rb.applicable_conditions:
                        print(f"     适用条件:")
                        # applicable_conditions 是多行字符串，需要分割
                        conditions = [c.strip() for c in rb.applicable_conditions.split('\n') if c.strip() and not c.strip().startswith('#')]
                        for condition in conditions[:3]:
                            print(f"       {condition}")
                        if len(conditions) > 3:
                            print(f"       ... (还有 {len(conditions) - 3} 条)")
            else:
                print("📚 未找到相关运行手册")

        except Exception as e:
            print(f"✗ 分类失败: {str(e)}")

        print()
        print("=" * 80)
        print()


if __name__ == "__main__":
    demo_classify_with_runbook()
