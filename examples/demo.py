#!/usr/bin/env python3
"""
OpenAI协议LLM客户端演示
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient


def demo_basic_chat():
    """基础对话演示"""
    print("=== 基础对话演示 ===\n")

    client = LLMClient()

    response = client.chat(
        message="你好，请用一句话介绍Python语言。",
        system_prompt="你是一个专业的编程助手。"
    )

    print(f"用户: 你好，请用一句话介绍Python语言。")
    print(f"助手: {response}\n")


def demo_stream_chat():
    """流式对话演示"""
    print("=== 流式对话演示 ===\n")

    client = LLMClient()

    print("用户: 请用三句话介绍机器学习的基本概念。")
    print("助手: ", end="", flush=True)

    for chunk in client.stream_chat(
        message="请用三句话介绍机器学习的基本概念。",
        system_prompt="你是一个专业的AI助手。"
    ):
        print(chunk, end="", flush=True)

    print("\n")


def demo_custom_parameters():
    """自定义参数演示"""
    print("=== 自定义参数演示 ===\n")

    client = LLMClient()

    response = client.chat(
        message="写一首关于代码的打油诗",
        temperature=0.9,
        max_tokens=200
    )

    print(f"用户: 写一首关于代码的打油诗")
    print(f"助手: {response}\n")


def main():
    """主函数"""
    try:
        demo_basic_chat()
        demo_stream_chat()
        demo_custom_parameters()

    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保config.yaml文件存在并配置正确。")
    except Exception as e:
        print(f"发生错误: {e}")
        print("请检查API配置和网络连接。")


if __name__ == "__main__":
    main()
