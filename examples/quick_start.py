#!/usr/bin/env python3
"""
故障分类器 - 交互式命令行工具
输入故障描述，返回JSON格式的分类结果
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from incident_triage import IncidentClassifier


def main():
    """主函数 - 程序从这里开始执行"""

    print("=" * 60)
    print("故障分类器 - 交互式模式")
    print("=" * 60)

    # 初始化客户端和分类器
    try:
        print("\n正在初始化...")
        llm_client = LLMClient()
        classifier = IncidentClassifier(llm_client)
        print("✓ 初始化成功\n")
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        print("\n请检查：")
        print("1. config.yaml 是否存在且配置正确")
        print("2. API Key 是否有效")
        return

    print("使用说明：")
    print("- 输入故障描述，按回车获取分类结果")
    print("- 输入 'quit' 或 'exit' 退出程序")
    print("- 输入 'clear' 清屏\n")
    print("=" * 60)

    # 持续循环，等待用户输入
    while True:
        try:
            # 获取用户输入
            print("\n请输入故障描述：")
            user_input = input("> ").strip()

            # 检查退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n再见！")
                break

            # 检查清屏命令
            if user_input.lower() == 'clear':
                import os
                os.system('clear' if os.name == 'posix' else 'cls')
                continue

            # 检查空输入
            if not user_input:
                print("⚠️  请输入故障描述")
                continue

            # 进行分类
            print("\n正在分类...")
            result = classifier.classify(user_input)

            # 将结果转换为JSON格式
            result_json = {
                "severity": result.severity,
                "category": result.category,
                "needs_human_review": result.needs_human_review,
                "rationale": result.rationale
            }

            # 输出格式化的JSON
            print("\n分类结果：")
            print(json.dumps(result_json, ensure_ascii=False, indent=2))

        except KeyboardInterrupt:
            print("\n\n程序被中断，再见！")
            break
        except Exception as e:
            print(f"\n✗ 分类失败: {e}")
            print("请重试或检查网络连接")


if __name__ == "__main__":
    main()
