#!/usr/bin/env python3
"""
演示 TraceManager 功能

展示：
1. 工具调用次数限制（最多 2 次）
2. 完整调用轨迹记录
3. 保存到文件供审计
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client import LLMClient
from incident_triage import IncidentClassifier
import json


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)
    print()


def demo_basic_classification():
    """演示基础分类 + 轨迹记录"""
    print_separator("演示 1: 基础分类 + 轨迹记录")

    config_path = Path(__file__).parent.parent / "config.yaml"
    client = LLMClient(str(config_path))
    classifier = IncidentClassifier(client, trace_dir="demo_traces")

    description = "支付接口错误率 35%，影响所有用户"

    print(f"故障描述: {description}")
    print()

    try:
        result = classifier.classify(description)

        print("✓ 分类结果:")
        print(f"  - severity: {result.severity}")
        print(f"  - category: {result.category}")
        print(f"  - needs_human_review: {result.needs_human_review}")
        print(f"  - rationale: {result.rationale}")

        print("\n✓ 轨迹已保存到 demo_traces/ 目录")

    except Exception as e:
        print(f"✗ 分类失败: {e}")


def demo_trace_content():
    """演示查看轨迹内容"""
    print_separator("演示 2: 查看轨迹内容")

    # 找到最新的轨迹文件
    trace_dir = Path("demo_traces")
    if not trace_dir.exists():
        print("未找到轨迹文件，请先运行演示 1")
        return

    trace_files = sorted(trace_dir.glob("trace_*.json"), key=lambda x: x.stat().st_mtime)
    if not trace_files:
        print("未找到轨迹文件")
        return

    latest_trace = trace_files[-1]
    print(f"读取轨迹文件: {latest_trace.name}")
    print()

    with open(latest_trace, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"轨迹 ID: {data['trace_id']}")
    print(f"时间戳: {data['timestamp']}")
    print(f"用户输入: {data['user_input']}")
    print(f"状态: {data['status']}")
    print(f"工具调用次数: {data['total_tool_calls']}/{data['max_tool_calls_limit']}")
    print()

    print("工具调用记录:")
    for i, call in enumerate(data['tool_calls'], 1):
        print(f"\n  [{i}] {call['tool_name']}")
        print(f"      时间: {call['timestamp']}")
        print(f"      成功: {call['success']}")
        if call['tool_name'] == 'llm_chat':
            print(f"      输入: message={call['tool_input']['message'][:50]}...")
            print(f"      输出: {call['tool_output'][:100]}...")
        elif call['tool_name'] == 'policy_engine':
            if 'violations' in call['tool_output']:
                print(f"      修正: {len(call['tool_output']['violations'])} 项")
                for v in call['tool_output']['violations']:
                    print(f"        - {v['policy_name']}: {v['original_value']} → {v['corrected_value']}")

    if data['final_answer']:
        print("\n最终答案:")
        print(f"  {json.dumps(data['final_answer'], ensure_ascii=False, indent=2)}")


def demo_max_calls_limit():
    """演示最大调用次数限制（需要修改代码触发）"""
    print_separator("演示 3: 最大调用次数限制")

    print("在实际使用中，如果模型需要多次工具调用（例如需要查询外部数据库）")
    print("而超过 2 次限制时，系统会返回\"证据不足\"错误。")
    print()
    print("这个限制确保：")
    print("  1. 防止无限循环调用")
    print("  2. 控制 API 成本")
    print("  3. 快速失败，避免长时间等待")
    print()
    print("当前实现中，分类任务通常只需要 1-2 次调用：")
    print("  - 第 1 次: LLM 分类")
    print("  - 第 2 次: Policy 引擎修正（如果需要）")


def main():
    """主函数"""
    print_separator("TraceManager 功能演示")

    print("本演示展示两个新增功能：")
    print("  1. 限制最多 2 次工具调用，超过时返回\"证据不足\"")
    print("  2. 保存完整调用轨迹到文件")
    print()

    import time

    # 演示 1
    demo_basic_classification()
    time.sleep(1)

    # 演示 2
    demo_trace_content()
    time.sleep(1)

    # 演示 3
    demo_max_calls_limit()

    print_separator("演示完成")
    print("轨迹文件保存在 demo_traces/ 目录，可以用于：")
    print("  - 调试和故障排查")
    print("  - 审计和合规检查")
    print("  - 分析模型行为")
    print("  - 优化 Prompt 和规则")


if __name__ == "__main__":
    main()
