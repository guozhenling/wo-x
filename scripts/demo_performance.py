#!/usr/bin/env python3
"""
Day 19-20 性能优化演示

展示：
1. 缓存预热
2. 性能指标收集
3. 基准测试
4. 异步执行（可选）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cache_warmup import CacheWarmup
from tools.performance_metrics import get_collector
from tools.benchmark import PerformanceBenchmark
from tools.robust_executor import RobustToolExecutor
from src.agent_v2 import IncidentAgentV2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_cache_warmup():
    """演示缓存预热"""
    print("\n" + "=" * 60)
    print("1. 缓存预热演示")
    print("=" * 60)

    # 创建执行器和预热器
    executor = RobustToolExecutor()
    warmup = CacheWarmup(executor)

    # 执行预热
    print("\n开始预热缓存...")
    results = warmup.warmup(parallel=True, max_workers=3)

    # 打印结果
    warmup.print_warmup_summary(results)

    return executor


def demo_performance_metrics():
    """演示性能指标收集"""
    print("\n" + "=" * 60)
    print("2. 性能指标收集演示")
    print("=" * 60)

    # 获取全局收集器
    collector = get_collector()
    collector.reset()

    # 创建 Agent
    agent = IncidentAgentV2()

    # 测试案例
    test_case = "API 响应超时，大量 502 错误"

    print(f"\n测试案例: {test_case}")
    print("\n开始分析...")

    # 记录性能
    collector.start_step("total")

    try:
        result = agent.analyze(test_case)

        collector.end_step("total")

        # 打印性能摘要
        collector.print_summary()

        # 保存到文件
        os.makedirs("outputs/performance", exist_ok=True)
        collector.save_to_file("outputs/performance/metrics_demo.json")
        print(f"\n性能数据已保存到: outputs/performance/metrics_demo.json")

    except Exception as e:
        logger.error(f"分析失败: {e}")

    return collector


def demo_benchmark():
    """演示基准测试"""
    print("\n" + "=" * 60)
    print("3. 基准测试演示")
    print("=" * 60)

    # 创建 Agent
    agent = IncidentAgentV2()

    # 测试案例（小规模）
    test_cases = [
        "数据库连接池耗尽",
        "Redis 缓存失效",
        "API 网关超时",
    ]

    print(f"\n准备测试 {len(test_cases)} 个案例，每个运行 2 次")

    # 创建基准测试器
    benchmark = PerformanceBenchmark()

    # 运行基准测试
    results = benchmark.run_benchmark(
        agent=agent,
        test_cases=test_cases,
        iterations=2
    )

    # 打印结果
    benchmark.print_results(results)

    # 保存结果
    os.makedirs("outputs/performance", exist_ok=True)
    benchmark.save_results(results, "outputs/performance/benchmark_demo.json")

    return results


def demo_comparison():
    """演示优化前后对比"""
    print("\n" + "=" * 60)
    print("4. 性能优化效果对比")
    print("=" * 60)

    collector = get_collector()

    # 获取历史统计
    history = collector.get_history_summary()

    if history:
        print(f"\n历史运行统计 (共 {history['total_runs']} 次):")
        print(f"\n延迟:")
        print(f"  平均: {history['duration']['avg']:.2f}s")
        print(f"  最快: {history['duration']['min']:.2f}s")
        print(f"  最慢: {history['duration']['max']:.2f}s")

        print(f"\nLLM 调用:")
        print(f"  平均: {history['llm_calls']['avg']:.1f} 次/分析")
        print(f"  总计: {history['llm_calls']['total']} 次")

        print(f"\n工具调用:")
        print(f"  平均: {history['tool_calls']['avg']:.1f} 次/分析")
        print(f"  总计: {history['tool_calls']['total']} 次")

        print(f"\n缓存命中率:")
        print(f"  平均: {history['cache_hit_rate']['avg']:.1%}")
    else:
        print("\n暂无历史数据")

    print("\n" + "=" * 60)
    print("优化建议:")
    print("=" * 60)
    print("\n✅ 已实现的优化:")
    print("  - 超时保护 (5s)")
    print("  - 并发执行 (5 workers)")
    print("  - 缓存机制 (300s TTL)")
    print("  - 降级方案 (3 级)")
    print("  - 缓存预热")

    print("\n🔄 可进一步优化:")
    print("  - 减少 LLM 调用次数（合并步骤）")
    print("  - 智能工具选择（基于关键词）")
    print("  - 异步执行（流式返回）")
    print("  - 结果缓存（相同描述复用）")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Day 19-20: 性能分析与优化")
    print("=" * 60)

    mode = "all"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    try:
        if mode in ["all", "warmup"]:
            demo_cache_warmup()

        if mode in ["all", "metrics"]:
            demo_performance_metrics()

        if mode in ["all", "benchmark"]:
            demo_benchmark()

        if mode in ["all", "comparison"]:
            demo_comparison()

        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)

        print("\n生成的文件:")
        print("  - outputs/performance/metrics_demo.json")
        print("  - outputs/performance/benchmark_demo.json")

        print("\n运行特定模式:")
        print("  python scripts/demo_performance.py warmup     # 仅缓存预热")
        print("  python scripts/demo_performance.py metrics    # 仅性能指标")
        print("  python scripts/demo_performance.py benchmark  # 仅基准测试")
        print("  python scripts/demo_performance.py comparison # 仅对比分析")

    except KeyboardInterrupt:
        print("\n\n中断执行")
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
