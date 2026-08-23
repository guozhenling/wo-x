"""测试慢查询工具"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.slow_query_search import search_slow_queries
from tools.executor import execute_tool


def test_search_slow_queries_basic():
    """基础查询测试"""
    result = search_slow_queries(time_range=60, min_duration=1.0, limit=5)

    assert result['total'] >= 0
    assert 'queries' in result
    assert 'summary' in result
    assert 'avg_duration' in result['summary']
    assert 'max_duration' in result['summary']
    assert 'total_lock_time' in result['summary']


def test_search_slow_queries_time_range():
    """时间范围过滤测试"""
    # 查询最近 30 分钟
    result_30 = search_slow_queries(time_range=30)
    # 查询最近 60 分钟
    result_60 = search_slow_queries(time_range=60)

    # 60 分钟应该 >= 30 分钟的数据
    assert result_60['total'] >= result_30['total']


def test_search_slow_queries_filter_duration():
    """执行时间过滤测试"""
    result = search_slow_queries(time_range=180, min_duration=2.0, limit=20)

    # 验证所有查询都满足最小执行时间
    for query in result['queries']:
        assert query['duration'] >= 2.0


def test_search_slow_queries_limit():
    """数量限制测试"""
    result = search_slow_queries(time_range=180, limit=3)

    # 验证返回数量不超过限制
    assert len(result['queries']) <= 3
    assert result['total'] <= 3


def test_search_slow_queries_summary():
    """统计信息测试"""
    result = search_slow_queries(time_range=60, min_duration=1.0)

    if result['total'] > 0:
        # 验证统计信息合理性
        assert result['summary']['avg_duration'] > 0
        assert result['summary']['max_duration'] >= result['summary']['avg_duration']
        assert result['summary']['total_lock_time'] >= 0


def test_search_slow_queries_no_results():
    """无结果测试"""
    # 设置一个很高的阈值
    result = search_slow_queries(time_range=1, min_duration=100.0)

    # 可能没有结果
    assert result['total'] >= 0
    assert 'queries' in result


def test_search_slow_queries_via_executor():
    """通过 executor 调用"""
    result = execute_tool("search_slow_queries", {
        "time_range": 30,
        "limit": 3
    })

    assert 'queries' in result
    assert len(result['queries']) <= 3


if __name__ == "__main__":
    print("=" * 80)
    print("测试 search_slow_queries")
    print("=" * 80)

    print("\n【测试 1】基础查询:")
    result = search_slow_queries(time_range=60, min_duration=1.0, limit=5)
    print(f"找到 {result['total']} 条慢查询")
    print(f"平均执行时间: {result['summary']['avg_duration']} 秒")
    print(f"最大执行时间: {result['summary']['max_duration']} 秒")
    print(f"总锁等待时间: {result['summary']['total_lock_time']} 秒")

    for i, query in enumerate(result['queries'][:3], 1):
        print(f"\n{i}. {query['timestamp']}")
        print(f"   数据库: {query['database']}")
        print(f"   执行时间: {query['duration']} 秒")
        print(f"   锁等待: {query['lock_time']} 秒")
        print(f"   扫描行数: {query['rows_examined']}")
        print(f"   SQL: {query['query'][:80]}...")

    print("\n【测试 2】时间范围过滤:")
    result_30 = search_slow_queries(time_range=30)
    result_60 = search_slow_queries(time_range=60)
    print(f"最近 30 分钟: {result_30['total']} 条")
    print(f"最近 60 分钟: {result_60['total']} 条")

    print("\n【测试 3】执行时间过滤 (>= 3 秒):")
    result = search_slow_queries(time_range=180, min_duration=3.0)
    print(f"找到 {result['total']} 条执行时间 >= 3 秒的慢查询")
    for query in result['queries'][:3]:
        print(f"  - {query['query'][:50]}... ({query['duration']} 秒)")

    print("\n【测试 4】数量限制:")
    result = search_slow_queries(time_range=180, limit=2)
    print(f"限制 2 条，实际返回: {len(result['queries'])} 条")

    print("\n【测试 5】统计信息验证:")
    result = search_slow_queries(time_range=60)
    if result['total'] > 0:
        print(f"平均执行时间: {result['summary']['avg_duration']} 秒")
        print(f"最大执行时间: {result['summary']['max_duration']} 秒")
        assert result['summary']['max_duration'] >= result['summary']['avg_duration']
        print("✓ 统计信息合理")

    print("\n✅ 所有测试通过！")
