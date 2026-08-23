#!/usr/bin/env python3
"""
工具调用演示

展示如何让 LLM 调用工具获取日志信息
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from tools import get_all_tools, ToolExecutor


def demo_tool_calling():
    """演示工具调用流程"""

    print("=" * 80)
    print("工具调用演示")
    print("=" * 80)
    print()

    # 1. 初始化客户端和工具执行器
    config_path = Path(__file__).parent.parent / "config.yaml"
    client = LLMClient(str(config_path))
    log_path = Path(__file__).parent.parent / "data" / "logs.jsonl"
    executor = ToolExecutor(str(log_path))

    # 2. 获取工具定义
    tools = get_all_tools()
    print(f"✓ 已注册工具: {len(tools)} 个")
    print(f"  - {tools[0]['function']['name']}: {tools[0]['function']['description'][:60]}...")
    print()

    # 3. 用户问题
    user_question = "支付服务最近有什么错误日志？帮我查看最近 5 条 ERROR 级别的日志"
    print(f"用户问题: {user_question}")
    print()

    # 4. 第一次调用：LLM 决定是否使用工具
    print("第一轮：LLM 决定调用工具")
    print("-" * 80)

    messages = [
        {
            "role": "user",
            "content": user_question
        }
    ]

    response = client.chat_with_messages(
        messages=messages,
        tools=tools,
        tool_choice="auto"  # 让模型自动决定是否使用工具
    )

    print(f"模型回复类型: {response.get('finish_reason', 'unknown')}")

    # 5. 检查是否有工具调用
    if response.get('finish_reason') == 'tool_calls':
        tool_calls = response.get('tool_calls', [])
        print(f"✓ 模型决定调用 {len(tool_calls)} 个工具")
        print()

        # 6. 执行工具调用
        for tool_call in tool_calls:
            tool_name = tool_call['function']['name']
            tool_args_str = tool_call['function']['arguments']

            print(f"执行工具: {tool_name}")
            print(f"原始参数: {tool_args_str}")
            print(f"参数类型: {type(tool_args_str)}")

            # 如果已经是字典，直接使用；否则解析 JSON
            if isinstance(tool_args_str, dict):
                tool_args = tool_args_str
            else:
                # 处理可能的格式问题：移除开头的 {}
                tool_args_str_clean = tool_args_str.strip()
                if tool_args_str_clean.startswith('{}'):
                    tool_args_str_clean = tool_args_str_clean[2:]
                tool_args = json.loads(tool_args_str_clean)

            print(f"解析后参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
            print()

            # 执行工具
            if tool_name == 'search_logs':
                result = executor.execute_search_logs(tool_args)

                if result['success']:
                    print(f"✓ 工具执行成功")
                    print(f"  - 匹配日志: {result['result']['total']} 条")
                    print(f"  - 返回日志: {result['result']['returned']} 条")
                    print(f"  - 耗时: {result['result']['search_time_ms']:.2f}ms")
                    print()

                    print("日志详情:")
                    for i, log in enumerate(result['result']['logs'], 1):
                        print(f"  {i}. [{log['level']}] {log['service']} - {log['timestamp']}")
                        print(f"     {log['message']}")
                        print(f"     trace_id: {log['trace_id']}")
                        print()
                else:
                    print(f"✗ 工具执行失败: {result['error']}")
                    print()

                # 7. 第二次调用：将工具结果返回给 LLM
                print("第二轮：将工具结果返回给 LLM")
                print("-" * 80)

                # 添加助手的工具调用消息（使用清理后的参数）
                clean_tool_calls = [{
                    "id": tool_call['id'],
                    "type": tool_call['type'],
                    "function": {
                        "name": tool_call['function']['name'],
                        "arguments": json.dumps(tool_args, ensure_ascii=False)  # 使用解析后的参数
                    }
                }]

                messages.append({
                    "role": "assistant",
                    "content": "",  # 必须是空字符串，不能是 None
                    "tool_calls": clean_tool_calls
                })

                # 添加工具执行结果（简化内容，只保留日志数据）
                if result['success']:
                    tool_result_content = {
                        "total": result['result']['total'],
                        "logs": result['result']['logs']
                    }
                else:
                    tool_result_content = {"error": result['error']}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "content": json.dumps(tool_result_content, ensure_ascii=False)
                })

                # 让 LLM 基于工具结果生成最终回复
                print("准备发送的 messages:")
                print(json.dumps(messages, ensure_ascii=False, indent=2))
                print()

                final_response = client.chat_with_messages(messages=messages)

                print("LLM 最终回复:")
                print(final_response.get('content', ''))
                print()

    else:
        # 模型没有调用工具，直接给出答案
        print("模型直接回复（未调用工具）:")
        print(response.get('content', ''))
        print()

    print("=" * 80)
    print("✅ 工具调用演示完成")
    print("=" * 80)


if __name__ == "__main__":
    demo_tool_calling()
