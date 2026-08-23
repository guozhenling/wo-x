"""测试 OOM 事件查询工具"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.oom_search import search_oom_events
from tools.executor import execute_tool


def test_oom_events_basic():
    """基础查询测试"""
    result = search_oom_events(time_range=60)

    assert result['total'] >= 0
    assert 'events' in result
    assert 'summary' in result
    assert 'affected_services' in result['summary']
    assert 'total_kills' in result['summary']
    assert 'max_restart_count' in result['summary']


def test_oom_events_time_range():
    """时间范围过滤测试"""
    # 查询最近 60 分钟
    result_60 = search_oom_events(time_range=60)
    # 查询最近 120 分钟
    result_120 = search_oom_events(time_range=120)

    # 120 分钟应该 >= 60 分钟的数据
    assert result_120['total'] >= result_60['total']


def test_oom_events_filter_service():
    """服务过滤测试"""
    result = search_oom_events(time_range=180, service="recommendation")

    # 验证所有事件都是 recommendation 服务
    for event in result['events']:
        assert event['service'] == 'recommendation'


def test_oom_events_filter_restart_count():
    """重启次数过滤测试"""
    result = search_oom_events(time_range=180, min_restart_count=3)

    # 验证所有事件重启次数 >= 3
    for event in result['events']:
        assert event['restart_count'] >= 3


def test_oom_events_limit():
    """数量限制测试"""
    result = search_oom_events(time_range=180, limit=5)

    # 验证返回数量不超过限制
    assert len(result['events']) <= 5
    assert result['total'] <= 5


def test_oom_events_summary():
    """统计信息测试"""
    result = search_oom_events(time_range=180)

    if result['total'] > 0:
        # 验证统计信息
        assert result['summary']['total_kills'] == result['total']
        assert result['summary']['max_restart_count'] >= 0
        assert len(result['summary']['affected_services']) > 0
        assert result['summary']['most_affected_service'] in result['summary']['affected_services']


def test_oom_events_no_results():
    """无结果测试"""
    # 查询不存在的服务
    result = search_oom_events(time_range=1, service="nonexistent")

    # 应该没有结果
    assert result['total'] == 0
    assert len(result['events']) == 0


def test_oom_events_via_executor():
    """通过 executor 调用"""
    result = execute_tool("search_oom_events", {
        "time_range": 30,
        "limit": 3
    })

    assert 'events' in result
    assert len(result['events']) <= 3


if __name__ == "__main__":
    print("=" * 80)
    print("测试 search_oom_events")
    print("=" * 80)

    print("\n【测试 1】查询所有 OOM 事件:")
    result = search_oom_events(time_range=60)
    print(f"找到 {result['total']} 个 OOM 事件")
    print(f"受影响服务: {', '.join(result['summary']['affected_services'])}")
    print(f"总 Kill 次数: {result['summary']['total_kills']}")
    print(f"最大重启次数: {result['summary']['max_restart_count']}")
    print(f"最受影响服务: {result['summary']['most_affected_service']}")

    for i, event in enumerate(result['events'][:3], 1):
        print(f"\n{i}. {event['timestamp']}")
        print(f"   服务: {event['service']}")
        print(f"   Pod: {event['pod']}")
        print(f"   容器: {event['container']}")
        print(f"   内存限制: {event['memory_limit']}")
        print(f"   实际使用: {event['memory_used']}")
        print(f"   重启次数: {event['restart_count']}")
        print(f"   消息: {event['message'][:60]}...")

    print("\n【测试 2】时间范围过滤:")
    result_60 = search_oom_events(time_range=60)
    result_120 = search_oom_events(time_range=120)
    print(f"最近 60 分钟: {result_60['total']} 个")
    print(f"最近 120 分钟: {result_120['total']} 个")

    print("\n【测试 3】查询特定服务:")
    result = search_oom_events(time_range=180, service="recommendation")
    print(f"找到 {result['total']} 个 recommendation 服务 OOM 事件")
    for event in result['events'][:3]:
        print(f"  - {event['pod']}: 重启 {event['restart_count']} 次")

    print("\n【测试 4】查询频繁重启 (>= 3 次):")
    result = search_oom_events(time_range=180, min_restart_count=3)
    print(f"找到 {result['total']} 个频繁重启的容器")
    for event in result['events']:
        print(f"  - {event['service']}/{event['pod']}: {event['restart_count']} 次")

    print("\n【测试 5】数量限制:")
    result = search_oom_events(time_range=180, limit=2)
    print(f"限制 2 条，实际返回: {len(result['events'])} 条")

    print("\n【测试 6】统计信息验证:")
    result = search_oom_events(time_range=180)
    if result['total'] > 0:
        print(f"总 Kill 数: {result['summary']['total_kills']}")
        print(f"事件总数: {result['total']}")
        assert result['summary']['total_kills'] == result['total']
        print("✓ 统计信息一致")

    print("\n✅ 所有测试通过！")
