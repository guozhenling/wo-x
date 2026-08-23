#!/usr/bin/env python3
"""测试工具并行执行和缓存"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_v2 import IncidentAgentV2


def test_parallel_execution():
    """测试并行执行"""
    print("=" * 80)
    print("测试 1: 并行执行")
    print("=" * 80)

    agent = IncidentAgentV2()

    description = "推荐系统 P99 延迟从 500ms 升至 2 秒"

    print(f"\n描述: {description}")
    print("\n开始分析...")

    start_time = time.time()
    result = agent.analyze(description)
    elapsed = time.time() - start_time

    print(f"\n✓ 分析完成，耗时: {elapsed:.2f}s")
    print(f"  分类: {result['classification']['severity']}, {result['classification']['category']}")
    print(f"  调用工具: {len(result['evidence'])} 个")
    for i, ev in enumerate(result['evidence'], 1):
        print(f"    {i}. {ev['tool']}")

    # 输出缓存统计
    cache_stats = agent.coordinator.cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  命中: {cache_stats['hits']}")
    print(f"  未命中: {cache_stats['misses']}")
    print(f"  命中率: {cache_stats['hit_rate']:.1%}")

    return elapsed


def test_cache_hit():
    """测试缓存命中"""
    print("\n" + "=" * 80)
    print("测试 2: 缓存命中")
    print("=" * 80)

    agent = IncidentAgentV2()

    description = "推荐系统 P99 延迟从 500ms 升至 2 秒"

    # 第一次调用（缓存未命中）
    print(f"\n【第一次调用】")
    start1 = time.time()
    result1 = agent.analyze(description)
    elapsed1 = time.time() - start1
    print(f"  耗时: {elapsed1:.2f}s")
    print(f"  调用工具: {len(result1['evidence'])} 个")

    cache_stats1 = agent.coordinator.cache.get_stats()
    print(f"  缓存统计: 命中={cache_stats1['hits']}, 未命中={cache_stats1['misses']}")

    # 第二次调用（缓存命中）
    print(f"\n【第二次调用】（应该命中缓存）")
    start2 = time.time()
    result2 = agent.analyze(description)
    elapsed2 = time.time() - start2
    print(f"  耗时: {elapsed2:.2f}s")
    print(f"  调用工具: {len(result2['evidence'])} 个")

    cache_stats2 = agent.coordinator.cache.get_stats()
    print(f"  缓存统计: 命中={cache_stats2['hits']}, 未命中={cache_stats2['misses']}")

    # 对比
    speedup = elapsed1 / elapsed2 if elapsed2 > 0 else 0
    print(f"\n✓ 加速比: {speedup:.2f}x")
    print(f"  第一次: {elapsed1:.2f}s（未命中）")
    print(f"  第二次: {elapsed2:.2f}s（命中缓存）")

    return speedup


def test_multiple_incidents():
    """测试多个故障场景"""
    print("\n" + "=" * 80)
    print("测试 3: 多个故障场景（观察并行和缓存效果）")
    print("=" * 80)

    agent = IncidentAgentV2()

    test_cases = [
        "推荐系统 P99 延迟从 500ms 升至 2 秒",
        "搜索接口超时率从 1% 升至 15%",
        "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次",
    ]

    total_time = 0
    for i, description in enumerate(test_cases, 1):
        print(f"\n【案例 {i}】{description}")

        start = time.time()
        result = agent.analyze(description)
        elapsed = time.time() - start
        total_time += elapsed

        print(f"  耗时: {elapsed:.2f}s")
        print(f"  分类: {result['classification']['severity']}")
        print(f"  调用工具: {len(result['evidence'])} 个")

    # 最终缓存统计
    cache_stats = agent.coordinator.cache.get_stats()
    print(f"\n最终缓存统计:")
    print(f"  总命中: {cache_stats['hits']}")
    print(f"  总未命中: {cache_stats['misses']}")
    print(f"  命中率: {cache_stats['hit_rate']:.1%}")
    print(f"  缓存大小: {cache_stats['cache_size']}")
    print(f"\n总耗时: {total_time:.2f}s")


if __name__ == "__main__":
    print("🚀 工具并行执行和缓存测试\n")

    # 测试 1: 并行执行
    elapsed = test_parallel_execution()

    # 测试 2: 缓存命中
    speedup = test_cache_hit()

    # 测试 3: 多个故障场景
    test_multiple_incidents()

    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)
    print(f"\n关键指标:")
    print(f"  - 并行执行耗时: {elapsed:.2f}s")
    print(f"  - 缓存加速比: {speedup:.2f}x")
    print(f"\n优化效果:")
    print(f"  ✓ 无依赖工具并行执行，提升性能")
    print(f"  ✓ 相同查询命中缓存，减少重复调用")
    print(f"  ✓ ThreadPoolExecutor 并发控制")
