#!/usr/bin/env python3
"""
Day 19-20 性能工具简单演示

不依赖实际 Agent，只演示工具本身的功能
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.performance_metrics import PerformanceCollector, get_collector
from tools.cache_warmup import CacheWarmup
from tools.robust_executor import RobustToolExecutor


def demo_performance_collector():
    """演示性能指标收集器"""
    print("\n" + "=" * 60)
    print("1. 性能指标收集器演示")
    print("=" * 60)

    collector = PerformanceCollector()
    collector.reset()

    print("\n模拟一次故障分析...")

    # 步骤 1: 初步分类
    collector.start_step("initial_classification")
    collector.record_llm_call()
    time.sleep(0.1)  # 模拟耗时
    collector.end_step("initial_classification")
    print("  ✓ 初步分类完成")

    # 步骤 2: 工具执行
    collector.start_step("tool_execution")
    for i in range(3):
        collector.record_tool_call()
        if i == 0:
            collector.record_cache_hit()  # 第一个工具命中缓存
        else:
            collector.record_cache_miss()
    time.sleep(0.2)  # 模拟耗时
    collector.end_step("tool_execution")
    print("  ✓ 工具执行完成")

    # 步骤 3: 最终分析
    collector.start_step("final_analysis")
    collector.record_llm_call()
    time.sleep(0.15)  # 模拟耗时
    collector.end_step("final_analysis")
    print("  ✓ 最终分析完成")

    # 打印性能摘要
    collector.print_summary()

    # 保存到文件
    os.makedirs("outputs/performance", exist_ok=True)
    collector.save_to_file("outputs/performance/demo_metrics.json")
    print(f"\n性能数据已保存到: outputs/performance/demo_metrics.json")


def demo_cache_warmup():
    """演示缓存预热"""
    print("\n" + "=" * 60)
    print("2. 缓存预热演示")
    print("=" * 60)

    executor = RobustToolExecutor()
    warmup = CacheWarmup(executor)

    print("\n常见查询列表:")
    queries = warmup.get_common_queries()
    for i, query in enumerate(queries, 1):
        print(f"  {i}. {query['description']} ({query['tool']})")

    print(f"\n共 {len(queries)} 个常见查询")
    print("\n说明: 在实际环境中，这些查询会被预先执行，")
    print("      将结果缓存起来，提升后续查询的命中率。")


def demo_history_tracking():
    """演示历史统计"""
    print("\n" + "=" * 60)
    print("3. 历史统计演示")
    print("=" * 60)

    collector = get_collector()

    # 模拟多次运行
    print("\n模拟 3 次故障分析...")
    for run in range(3):
        collector.reset()
        collector.start_step("total")

        # 模拟不同的耗时
        collector.record_llm_call()
        collector.record_llm_call()
        collector.record_tool_call()
        collector.record_tool_call()
        collector.record_tool_call()

        if run == 0:
            # 第一次，缓存全未命中
            collector.record_cache_miss()
            collector.record_cache_miss()
            collector.record_cache_miss()
        elif run == 1:
            # 第二次，部分命中
            collector.record_cache_hit()
            collector.record_cache_miss()
            collector.record_cache_miss()
        else:
            # 第三次，命中率更高
            collector.record_cache_hit()
            collector.record_cache_hit()
            collector.record_cache_miss()

        time.sleep(0.05 * (run + 1))
        collector.end_step("total")

        print(f"  运行 {run + 1}: {collector.get_metrics().total_duration:.3f}s")

    # 获取历史统计
    history = collector.get_history_summary()

    print("\n历史统计摘要:")
    print(f"  总运行次数: {history['total_runs']}")
    print(f"  平均耗时: {history['duration']['avg']:.3f}s")
    print(f"  耗时范围: {history['duration']['min']:.3f}s - {history['duration']['max']:.3f}s")
    print(f"  平均 LLM 调用: {history['llm_calls']['avg']:.1f} 次")
    print(f"  平均工具调用: {history['tool_calls']['avg']:.1f} 次")
    print(f"  平均缓存命中率: {history['cache_hit_rate']['avg']:.1%}")


def demo_optimization_comparison():
    """演示优化效果对比"""
    print("\n" + "=" * 60)
    print("4. 优化效果对比")
    print("=" * 60)

    print("\n无优化情况:")
    print("  - 工具串行执行")
    print("  - 无缓存机制")
    print("  - 无超时保护")
    print("  - 无降级方案")
    print("\n  Tool 1: 5s")
    print("  Tool 2: 4s")
    print("  Tool 3: 3s")
    print("  ────────────")
    print("  总计: 12s")

    print("\n有优化情况:")
    print("  - 工具并发执行 ✓")
    print("  - 缓存机制 ✓")
    print("  - 超时保护 (5s) ✓")
    print("  - 降级方案 ✓")
    print("\n  Tool 1: 5s  ┐")
    print("  Tool 2: 4s  ├─ 并发")
    print("  Tool 3: 3s  ┘")
    print("  ────────────")
    print("  总计: 5s (提升 2.4x)")

    print("\n加上缓存预热:")
    print("  - 第一次查询: 5s")
    print("  - 第二次查询: 0s (缓存命中)")
    print("  - 命中率提升: 30% → 50%")
    print("  - 平均延迟降低: 15%")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Day 19-20: 性能分析与优化 - 工具演示")
    print("=" * 60)

    demo_performance_collector()
    demo_cache_warmup()
    demo_history_tracking()
    demo_optimization_comparison()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    print("\n生成的文件:")
    print("  - outputs/performance/demo_metrics.json")

    print("\n工具说明:")
    print("  1. PerformanceCollector - 收集各步骤耗时、API 调用、缓存统计")
    print("  2. CacheWarmup - 预热常见查询，提升缓存命中率")
    print("  3. PerformanceBenchmark - 运行基准测试，生成性能报告")
    print("  4. AsyncExecutor - 异步执行，流式返回结果")

    print("\n详细使用文档:")
    print("  docs/day-19-20-usage.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断执行")
    except Exception as e:
        import traceback
        print(f"\n错误: {e}")
        traceback.print_exc()
        sys.exit(1)
