#!/usr/bin/env python3
"""
工具调用演示 - 让 LLM 调用 search_logs 工具
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from tools import get_all_tools, ToolExecutor


def demo_tool_calling():
    """演示完整的工具调用流程"""

    print("=" * 80)
    print("LLM 工具调用演示 - search_logs")
    print("=" * 80)
    print()

    # 初始化
    config_path = Path(__file__).parent.parent / "config.yaml"
    client = LLMClient(str(config_path))
    tool_executor = ToolExecutor()
    tools = get_all_tools()

    # 测试场景
    scenarios = [
        {
            "name": "场景 1: 查找支付服务的错误日志",
            "query": "帮我查找支付服务最近的错误日志，限制 5 条"
        },
        {
            "name": "场景 2: 根据关键字搜索",
            "query": "查找包含 'timeout' 的日志，我想看看有哪些超时问题"
        },
        {
            "name": "场景 3: 查找特定 trace_id",
            "query": "帮我查找 trace-67890 相关的所有日志"
        },
        {
            "name": "场景 4: 不需要工具的问题",
            "query": "什么是日志搜索工具？"
        }
    ]

    for scenario in scenarios:
        print("=" * 80)
        print(scenario["name"])
        print("=" * 80)
        print(f"用户问题: {scenario['query']}")
        print()

        # 第一步：发送请求给 LLM（携带工具定义）
        print("📤 发送请求给 LLM（携带工具定义）...")
        response = client.chat(
            message=scenario["query"],
            system_prompt="""你是一个运维助手，可以帮用户查询日志。
当用户需要查看日志时，调用 search_logs 工具。
如果用户只是询问信息而不需要查日志，直接回答。""",
            tools=tools
        )

        # 第二步：判断响应类型
        if isinstance(response, str):
            # 旧代码兼容：直接返回文本
            print(f"💬 LLM 响应: {response}")
        elif response["type"] == "text":
            # 普通文本响应
            print(f"💬 LLM 响应: {response['content']}")
        elif response["type"] == "tool_call":
            # 工具调用
            print(f"🔧 LLM 决定调用工具: {response['tool_name']}")
            print(f"📝 工具参数:")
            for key, value in response['tool_params'].items():
                print(f"   {key}: {value}")
            print()

            # 第三步：执行工具（Pydantic 参数校验 + Python 函数执行）
            print("⚙️  执行工具（Pydantic 校验 + 函数调用）...")
            tool_result = tool_executor.execute_tool(
                response['tool_name'],
                response['tool_params']
            )

            # 第四步：返回结果
            if tool_result['success']:
                print(f"✅ 工具执行成功")
                print(f"   找到日志: {tool_result['result']['total']} 条")
                print(f"   返回日志: {tool_result['result']['returned']} 条")
                print(f"   搜索耗时: {tool_result['result']['search_time_ms']:.2f} ms")
                print()
                print("📋 日志内容:")
                for i, log in enumerate(tool_result['result']['logs'], 1):
                    print(f"   [{i}] {log['timestamp']} [{log['level']}] {log['service']}")
                    print(f"       {log['message']}")
                    print(f"       trace_id: {log['trace_id']}")
                    print()
            else:
                print(f"❌ 工具执行失败: {tool_result['error']}")

        print()

    print("=" * 80)
    print("✅ 工具调用演示完成")
    print("=" * 80)


def demo_multi_turn():
    """演示多轮对话 + 工具调用"""

    print("\n\n")
    print("=" * 80)
    print("多轮对话演示 - 工具调用 + 结果分析")
    print("=" * 80)
    print()

    # 使用项目根目录的配置文件
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config.yaml"

    client = LLMClient(config_path=str(config_path))
    tool_executor = ToolExecutor()
    tools = get_all_tools()

    user_query = "支付服务有什么错误吗？帮我分析一下"

    # 第一轮：LLM 决定调用工具
    print("👤 用户: " + user_query)
    print()
    print("🤖 LLM 思考中...")
    response1 = client.chat(
        message=user_query,
        system_prompt="""你是一个运维助手。
当用户询问服务状态、错误等问题时，使用 search_logs 工具查询日志。
查询后，分析日志内容并给出专业的总结。""",
        tools=tools
    )

    if response1["type"] == "tool_call":
        print(f"🔧 LLM 决定调用工具: {response1['tool_name']}")
        print(f"   参数: {response1['tool_params']}")
        print()

        # 执行工具
        tool_result = tool_executor.execute_tool(
            response1['tool_name'],
            response1['tool_params']
        )

        if tool_result['success']:
            print(f"✅ 找到 {tool_result['result']['total']} 条日志")
            print()

            # 第二轮：将工具结果返回给 LLM，让它分析
            print("🤖 LLM 分析日志中...")

            # 构建工具结果摘要
            log_summary = f"搜索到 {tool_result['result']['total']} 条支付服务的错误日志：\n"
            for log in tool_result['result']['logs'][:5]:  # 只显示前5条
                log_summary += f"- [{log['timestamp']}] {log['message']}\n"

            # 注意：这里简化处理，实际完整的多轮对话应该用 messages 数组
            # 当前 client.chat() 只支持单条消息，所以用文本描述工具结果
            analysis = client.chat(
                message=f"用户问题：支付服务有什么错误吗？帮我分析一下\n\n我已经调用了 search_logs 工具，结果如下：\n\n{log_summary}\n\n请基于这些日志给出专业的分析和建议。",
                system_prompt="你是一个运维专家，擅长分析日志并给出建议。",
                tools=None  # 第二轮不需要工具
            )

            print(f"💬 LLM 分析结果:")
            if isinstance(analysis, str):
                print(f"   {analysis}")
            else:
                print(f"   {analysis.get('content', analysis)}")
            print()
        else:
            print(f"⚠️  工具执行失败: {tool_result['error']}")
            print()

    print("=" * 80)
    print("✅ 多轮对话演示完成")
    print("=" * 80)


if __name__ == "__main__":
    # 基础工具调用演示
    demo_tool_calling()

    # 多轮对话演示
    demo_multi_turn()
