"""测试搜推广超时查询工具"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.timeout_search import search_timeout_events
from tools.executor import execute_tool


def test_timeout_events_basic():
    """基础查询测试 - 查询所有事件"""
    result = search_timeout_events(time_range=60)

    assert result['total'] >= 0
    assert 'events' in result
    assert 'summary' in result
    assert 'affected_services' in result['summary']
    assert 'total_timeouts' in result['summary']
    assert 'total_success' in result['summary']


def test_timeout_events_filter_service():
    """服务过滤测试 - 只查询推荐服务"""
    result = search_timeout_events(time_range=120, service="recommendation")

    # 验证所有事件都是 recommendation 服务
    for event in result['events']:
        assert event['service'] == 'recommendation'


def test_timeout_events_filter_status_timeout():
    """状态过滤测试 - 只查询超时事件"""
    result = search_timeout_events(time_range=180, status="timeout")

    # 验证所有事件都是超时状态
    for event in result['events']:
        assert event.get('status') == 'timeout'

    # 验证统计正确
    assert result['summary']['total_success'] == 0
    assert result['summary']['total_timeouts'] == len(result['events'])


def test_timeout_events_filter_status_success():
    """状态过滤测试 - 只查询成功事件"""
    result = search_timeout_events(time_range=180, status="success")

    # 验证所有事件都是成功状态
    for event in result['events']:
        assert event.get('status') == 'success'

    # 验证统计正确
    assert result['summary']['total_timeouts'] == 0
    assert result['summary']['total_success'] == len(result['events'])


def test_timeout_events_filter_timeout_threshold():
    """超时时间过滤测试 - 查询严重超时"""
    result = search_timeout_events(time_range=180, min_timeout_ms=5000)

    # 验证所有事件超时 >= 5000ms
    for event in result['events']:
        assert event['actual_ms'] >= 5000


def test_timeout_events_multiple_filters():
    """组合过滤测试 - 服务 + 状态"""
    result = search_timeout_events(
        time_range=180,
        service="search",
        status="timeout"
    )

    # 验证所有事件都满足条件
    for event in result['events']:
        assert event['service'] == 'search'
        assert event.get('status') == 'timeout'


def test_timeout_events_via_executor():
    """通过 executor 调用"""
    result = execute_tool("search_timeout_events", {
        "time_range": 45,
        "service": "search"
    })

    assert 'events' in result


if __name__ == "__main__":
    print("=" * 80)
    print("测试 search_timeout_events")
    print("=" * 80)

    print("\n【测试 1】查询所有事件（包含正常和超时）:")
    result = search_timeout_events(time_range=60)
    print(f"找到 {result['total']} 个事件")
    print(f"受影响服务: {', '.join(result['summary']['affected_services'])}")
    print(f"成功请求: {result['summary']['total_success']}")
    print(f"超时请求: {result['summary']['total_timeouts']}")
    print(f"平均耗时: {result['summary']['avg_timeout_ms']} ms")
    print(f"最大耗时: {result['summary']['max_timeout_ms']} ms")

    for i, event in enumerate(result['events'][:3], 1):
        print(f"\n{i}. {event['timestamp']}")
        print(f"   服务: {event['service']}")
        print(f"   接口: {event['endpoint']}")
        print(f"   实际耗时: {event['actual_ms']} ms")
        print(f"   状态: {event.get('status', 'unknown')}")

    print("\n【测试 2】只查询超时事件:")
    result = search_timeout_events(time_range=120, status="timeout")
    print(f"找到 {result['total']} 个超时事件")
    print(f"超时率: {result['summary']['total_timeouts']} / {result['summary']['total_events']}")

    print("\n【测试 3】只查询成功事件:")
    result = search_timeout_events(time_range=120, status="success")
    print(f"找到 {result['total']} 个成功事件")
    print(f"成功率: {result['summary']['total_success']} / {result['summary']['total_events']}")

    print("\n【测试 4】查询推荐服务:")
    result = search_timeout_events(time_range=120, service="recommendation")
    print(f"找到 {result['total']} 个 recommendation 服务事件")
    print(f"  成功: {result['summary']['total_success']}")
    print(f"  超时: {result['summary']['total_timeouts']}")

    print("\n【测试 5】查询搜索服务:")
    result = search_timeout_events(time_range=120, service="search")
    print(f"找到 {result['total']} 个 search 服务事件")
    print(f"  成功: {result['summary']['total_success']}")
    print(f"  超时: {result['summary']['total_timeouts']}")

    print("\n【测试 6】查询广告服务:")
    result = search_timeout_events(time_range=120, service="ad")
    print(f"找到 {result['total']} 个 ad 服务事件")
    print(f"  成功: {result['summary']['total_success']}")
    print(f"  超时: {result['summary']['total_timeouts']}")

    print("\n【测试 7】查询严重超时 (> 5000ms):")
    result = search_timeout_events(time_range=180, min_timeout_ms=5000)
    print(f"找到 {result['total']} 个严重超时事件")

    print("\n【测试 8】组合过滤 - 搜索服务的超时:")
    result = search_timeout_events(time_range=180, service="search", status="timeout")
    print(f"找到 {result['total']} 个搜索服务超时事件")

    print("\n✅ 所有测试通过！")
