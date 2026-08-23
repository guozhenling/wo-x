#!/usr/bin/env python3
"""测试新增的工具"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.slow_query_search import search_slow_queries
from tools.deployment_history import get_deployment_history
import json


def test_slow_queries():
    print("=" * 80)
    print("测试 search_slow_queries")
    print("=" * 80)

    result = search_slow_queries(time_range=60, min_duration=1.0, limit=5)

    print(f"\n找到 {result['total']} 条慢查询")
    print(f"平均执行时间: {result['summary']['avg_duration']} 秒")
    print(f"最大执行时间: {result['summary']['max_duration']} 秒")
    print(f"总锁等待时间: {result['summary']['total_lock_time']} 秒")

    print("\n慢查询列表:")
    for i, query in enumerate(result['queries'], 1):
        print(f"\n{i}. {query['timestamp']}")
        print(f"   数据库: {query['database']}")
        print(f"   执行时间: {query['duration']} 秒")
        print(f"   锁等待: {query['lock_time']} 秒")
        print(f"   扫描行数: {query['rows_examined']}")
        print(f"   SQL: {query['query'][:80]}...")


def test_deployment_history():
    print("\n" + "=" * 80)
    print("测试 get_deployment_history")
    print("=" * 80)

    # 测试 1: 查询所有服务
    print("\n【测试 1】查询最近 24 小时所有部署:")
    result = get_deployment_history(hours=24)

    print(f"\n找到 {result['total']} 条部署记录")
    print(f"涉及服务: {', '.join(result['summary']['services_deployed'])}")
    print(f"成功部署: {result['summary']['successful_deployments']}")
    print(f"回滚次数: {result['summary']['rollback_count']}")

    print("\n部署列表:")
    for i, deploy in enumerate(result['deployments'][:3], 1):
        print(f"\n{i}. {deploy['timestamp']}")
        print(f"   服务: {deploy['service']}")
        print(f"   版本: {deploy['previous_version']} → {deploy['version']}")
        print(f"   操作人: {deploy['deployed_by']}")
        print(f"   状态: {deploy['status']}")
        print(f"   变更:")
        for change in deploy['changes']:
            print(f"     - {change}")
        if deploy['status'] == 'rollback':
            print(f"   回滚原因: {deploy['rollback_reason']}")

    # 测试 2: 查询特定服务
    print("\n【测试 2】查询 payment 服务部署:")
    result = get_deployment_history(hours=24, service="payment")

    print(f"\n找到 {result['total']} 条 payment 服务部署记录")
    for deploy in result['deployments']:
        print(f"  - {deploy['timestamp']}: {deploy['version']} by {deploy['deployed_by']}")


def test_executor():
    print("\n" + "=" * 80)
    print("测试通过 executor 调用")
    print("=" * 80)

    from tools.executor import execute_tool

    # 测试慢查询
    print("\n【通过 executor 调用 search_slow_queries】")
    result = execute_tool("search_slow_queries", {"time_range": 30, "limit": 3})
    print(f"找到 {result['total']} 条慢查询")

    # 测试部署历史
    print("\n【通过 executor 调用 get_deployment_history】")
    result = execute_tool("get_deployment_history", {"hours": 12, "service": "order"})
    print(f"找到 {result['total']} 条部署记录")


if __name__ == "__main__":
    test_slow_queries()
    test_deployment_history()
    test_executor()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)
