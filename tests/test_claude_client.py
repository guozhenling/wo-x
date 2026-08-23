#!/usr/bin/env python3
"""
测试 LLM 客户端连接（支持 OpenAI 和 Anthropic 协议）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient


def test_llm_connection():
    """测试 LLM 客户端连接"""
    print("=" * 80)
    print("测试 LLM 客户端连接")
    print("=" * 80)
    print()

    try:
        # 初始化客户端
        print("1. 正在初始化客户端...")
        client = LLMClient()

        protocol = client.config['api'].get('protocol', 'openai')
        model = client.config['api']['model']
        print(f"   ✓ 客户端初始化成功")
        print(f"   协议: {protocol}")
        print(f"   模型: {model}")
        if protocol == 'openai' and 'base_url' in client.config['api']:
            print(f"   地址: {client.config['api']['base_url']}")
        print()

        # 测试基础对话
        print("2. 测试基础对话...")
        response = client.chat(
            message="请用一句话回答：1+1等于几？",
            temperature=0.3
        )
        print(f"   ✓ 对话成功")
        print(f"   响应: {response}")
        print()

        # 测试带系统提示词
        print("3. 测试带系统提示词...")
        response = client.chat(
            message="支付接口 5xx 从 0.1% 升到 35%，持续 8 分钟",
            system_prompt="你是一个故障分类专家，请简要分析这个故障的严重程度。",
            temperature=0.3
        )
        print(f"   ✓ 分析成功")
        print(f"   响应: {response[:100]}...")
        print()

        # 测试流式对话
        print("4. 测试流式对话...")
        print("   响应: ", end="", flush=True)
        for chunk in client.stream_chat(
            message="用一句话说明什么是 P0 级故障",
            temperature=0.3
        ):
            print(chunk, end="", flush=True)
        print()
        print("   ✓ 流式对话成功")
        print()

        print("=" * 80)
        print(f"✅ 所有测试通过！{protocol.upper()} 协议工作正常")
        print("=" * 80)

    except FileNotFoundError as e:
        print(f"✗ 配置文件错误: {e}")
        print()
        print("请检查:")
        print("1. config.yaml 文件是否存在")
        print("2. 参考 config.yaml.example 配置正确的 API 信息")

    except ImportError as e:
        print(f"✗ 依赖包错误: {e}")
        print()
        print("请运行:")
        print("  pip install anthropic  # 如果使用 Anthropic 协议")
        print("  pip install openai     # 如果使用 OpenAI 协议")

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        print()
        print("请检查:")
        print("1. API Key 是否正确")
        print("2. 网络连接是否正常")
        print("3. base_url 是否正确（如果使用 OpenAI 协议）")
        print("4. 模型名称是否正确")


if __name__ == "__main__":
    test_llm_connection()
