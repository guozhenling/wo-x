#!/usr/bin/env python3
"""
故障分类器演示
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from incident_triage import IncidentClassifier


def demo_incident_classification():
    """故障分类演示"""
    print("=== 故障分类器演示 ===\n")

    # 初始化客户端和分类器
    llm_client = LLMClient()
    classifier = IncidentClassifier(llm_client)

    # 测试案例
    test_incidents = [
        "生产环境API服务完全无法访问，所有请求返回502错误，影响全部用户",
        "用户报告登录页面加载时间从1秒增加到5秒，但功能正常",
        "数据库主从同步延迟达到30秒，可能导致数据不一致",
        "昨晚的自动部署失败，新版本未能上线，目前使用旧版本",
        "有用户反馈搜索功能偶尔返回空结果，无法复现"
    ]

    print(f"共 {len(test_incidents)} 个故障需要分类\n")
    print("-" * 80)

    for i, incident in enumerate(test_incidents, 1):
        print(f"\n故障 #{i}:")
        print(f"描述: {incident}")
        print("\n正在分类...")

        try:
            result = classifier.classify(incident)

            print(f"✓ 分类完成")
            print(f"  严重程度: {result.severity}")
            print(f"  故障类别: {result.category}")
            print(f"  需要人工审核: {'是' if result.needs_human_review else '否'}")
            print(f"  分类依据: {result.rationale}")

        except Exception as e:
            print(f"✗ 分类失败: {e}")

        print("-" * 80)


def demo_single_incident():
    """单个故障分类演示"""
    print("\n=== 单个故障分类演示 ===\n")

    llm_client = LLMClient()
    classifier = IncidentClassifier(llm_client)

    # 自定义故障描述
    incident = """
    监控告警显示：
    - 应用服务器CPU使用率突然升至95%
    - 响应时间从平均200ms飙升到3000ms
    - 错误率从0.1%上升到2%
    - 影响范围：约30%的用户请求变慢
    - 时间：最近15分钟开始
    """

    print("故障描述:")
    print(incident)
    print("\n正在分类...\n")

    try:
        result = classifier.classify(incident)

        print("分类结果:")
        print(f"  严重程度: {result.severity}")
        print(f"  故障类别: {result.category}")
        print(f"  需要人工审核: {'是' if result.needs_human_review else '否'}")
        print(f"  分类依据:\n    {result.rationale}")

    except Exception as e:
        print(f"分类失败: {e}")


def main():
    """主函数"""
    try:
        demo_incident_classification()
        demo_single_incident()

    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保config.yaml文件存在并配置正确。")
    except Exception as e:
        print(f"发生错误: {e}")
        print("请检查API配置和网络连接。")


if __name__ == "__main__":
    main()
