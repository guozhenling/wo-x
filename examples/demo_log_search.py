#!/usr/bin/env python3
"""
日志搜索工具演示

展示如何使用日志搜索工具查询日志
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from log_search import search_logs, LogSearchTool
from pydantic import ValidationError


def demo_basic_search():
    """基础搜索演示"""
    print("=" * 80)
    print("示例 1: 基础搜索 - 查询 payment 服务的日志")
    print("=" * 80)

    result = search_logs(service="payment", limit=5)
    print(f"找到 {result.total} 条日志，耗时 {result.search_time_ms}ms\n")

    for i, log in enumerate(result.logs, 1):
        print(f"{i}. [{log.level}] {log.timestamp}")
        print(f"   {log.message}")
        print(f"   trace_id: {log.trace_id}\n")


def demo_keyword_search():
    """关键字搜索演示"""
    print("=" * 80)
    print("示例 2: 关键字搜索 - 查询 payment 服务包含 'timeout' 的日志")
    print("=" * 80)

    result = search_logs(service="payment", keyword="timeout", limit=10)
    print(f"找到 {result.total} 条日志，耗时 {result.search_time_ms}ms\n")

    for i, log in enumerate(result.logs, 1):
        print(f"{i}. [{log.level}] {log.message}")
        print(f"   trace_id: {log.trace_id}\n")


def demo_no_results():
    """无结果演示"""
    print("=" * 80)
    print("示例 3: 无结果 - 查询不存在的服务")
    print("=" * 80)

    result = search_logs(service="nonexistent_service", limit=10)
    print(f"找到 {result.total} 条日志，耗时 {result.search_time_ms}ms")
    print("(没有匹配的日志)\n")


def demo_validation_error():
    """参数校验演示"""
    print("=" * 80)
    print("示例 4: 参数校验 - 空服务名")
    print("=" * 80)

    try:
        result = search_logs(service="", limit=10)
    except ValidationError as e:
        print(f"❌ 参数校验失败:")
        for error in e.errors():
            print(f"   字段: {error['loc'][0]}")
            print(f"   错误: {error['msg']}\n")


def demo_limit_exceeded():
    """超出限制演示"""
    print("=" * 80)
    print("示例 5: 参数校验 - limit 超过20")
    print("=" * 80)

    try:
        result = search_logs(service="payment", limit=25)
    except ValidationError as e:
        print(f"❌ 参数校验失败:")
        for error in e.errors():
            print(f"   字段: {error['loc'][0]}")
            print(f"   错误: {error['msg']}\n")


def demo_multiple_services():
    """多服务查询演示"""
    print("=" * 80)
    print("示例 6: 查询多个服务的日志统计")
    print("=" * 80)

    services = ["payment", "order", "user", "recommendation"]

    for service in services:
        result = search_logs(service=service, limit=20)
        print(f"{service:20s} {result.total:3d} 条日志")

    print()


def demo_error_analysis():
    """错误分析演示"""
    print("=" * 80)
    print("示例 7: 错误分析 - 统计各服务的 ERROR 日志")
    print("=" * 80)

    tool = LogSearchTool()
    services = ["payment", "order", "user", "recommendation"]

    for service in services:
        # 搜索包含 ERROR 的日志
        result = tool.search(service=service, keyword="", limit=20)
        error_logs = [log for log in result.logs if log.level == "ERROR"]

        print(f"{service:20s} ERROR: {len(error_logs):2d} 条")

        if error_logs:
            # 显示前2条
            for log in error_logs[:2]:
                print(f"  - {log.message[:60]}...")

    print()


def demo_trace_search():
    """Trace ID 搜索演示"""
    print("=" * 80)
    print("示例 8: 通过关键字查找特定 trace")
    print("=" * 80)

    # 查找所有 payment 相关的 trace
    result = search_logs(service="payment", keyword="gateway", limit=3)

    print(f"找到 {result.total} 条相关日志:\n")

    for log in result.logs:
        print(f"[{log.level}] {log.timestamp}")
        print(f"Message: {log.message}")
        print(f"Trace: {log.trace_id}")
        print("-" * 60)

    print()


def main():
    """运行所有演示"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 24 + "日志搜索工具演示" + " " * 38 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    demo_basic_search()
    demo_keyword_search()
    demo_no_results()
    demo_validation_error()
    demo_limit_exceeded()
    demo_multiple_services()
    demo_error_analysis()
    demo_trace_search()

    print("=" * 80)
    print("✅ 演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
