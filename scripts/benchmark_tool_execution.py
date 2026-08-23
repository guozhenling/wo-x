#!/usr/bin/env python3
"""
工具调用性能测试（聚焦工具执行）

只测试工具调用部分，排除 LLM 调用的影响
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import statistics
from typing import List, Dict, Any
from src.agent_v2 import IncidentAgentV2


# 测试数据：5 个故障场景（精简）
TEST_CASES = [
    "推荐系统 P99 延迟从 500ms 升至 2 秒",
    "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次",
    "搜索接口超时率从 1% 升至 15%",
    "数据库慢查询增多，平均执行时间 5 秒",
    "部署后 payment 服务 CPU 使用率 100%",
]


class ToolExecutionBenchmark:
    """工具执行性能测试"""

    def __init__(self):
        self.results = {}

    def test_scenario(self, name: str, enable_parallel: bool, use_cache: bool):
        """
        测试单个场景

        Args:
            name: 场景名称
            enable_parallel: 是否启用并行
            use_cache: 是否使用缓存
        """
        print(f"\n{'=' * 80}")
        print(f"{name}")
        print(f"{'=' * 80}")

        agent = IncidentAgentV2()

        # 如果不启用并行，替换为串行执行
        if not enable_parallel:
            original_execute = agent.coordinator._execute_batch_parallel
            agent.coordinator._execute_batch_parallel = lambda steps: self._execute_batch_serial(agent.coordinator, steps)

        # 预热（仅在使用缓存时）
        if use_cache:
            print("预热缓存（不计时）...")
            for description in TEST_CASES:
                # 启动 trace
                agent.trace.start_trace(description)

                initial = agent._quick_classify(description)
                plan = agent.coordinator.plan_tool_calls(description, initial)
                agent.coordinator.execute_plan()

                # 结束 trace
                agent.trace.finish_trace(final_answer={}, status="success")

        # 正式测试（只执行 1 遍）
        print(f"开始测试（执行 1 遍）...")
        tool_times = []

        for i, description in enumerate(TEST_CASES, 1):
            print(f"  {i}/{len(TEST_CASES)}: {description[:50]}...")

            # 启动 trace
            agent.trace.start_trace(description)

            # 快速分类
            initial = agent._quick_classify(description)

            # 规划工具
            plan = agent.coordinator.plan_tool_calls(description, initial)
            print(f"    规划了 {len(plan)} 个工具")

            # 执行工具（计时）
            start = time.time()
            results = agent.coordinator.execute_plan()
            elapsed = time.time() - start

            tool_times.append(elapsed)
            print(f"    工具执行耗时: {elapsed:.3f}s")

            # 结束 trace
            agent.trace.finish_trace(final_answer={}, status="success")

        # 恢复原方法
        if not enable_parallel:
            agent.coordinator._execute_batch_parallel = original_execute

        # 统计
        total_time = sum(tool_times)
        avg_time = statistics.mean(tool_times)
        cache_stats = agent.coordinator.cache.get_stats()

        print(f"\n结果:")
        print(f"  总耗时: {total_time:.3f}s")
        print(f"  平均耗时: {avg_time:.3f}s")
        print(f"  缓存命中: {cache_stats['hits']}")
        print(f"  缓存未命中: {cache_stats['misses']}")
        print(f"  缓存命中率: {cache_stats['hit_rate']:.1%}")

        self.results[name] = {
            "total": total_time,
            "avg": avg_time,
            "times": tool_times,
            "cache_stats": cache_stats
        }

    def _execute_batch_serial(self, coordinator, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """串行执行（用于对比）"""
        results = {}

        for step in steps:
            tool_name = step['tool']

            if not coordinator.agent.trace.can_call_tool():
                continue

            result = coordinator._execute_tool_with_cache(
                tool_name,
                step['arguments'],
                step['reason']
            )
            results[tool_name] = result

        return results

    def generate_report(self):
        """生成性能报告"""
        print(f"\n{'=' * 80}")
        print("性能测试报告")
        print(f"{'=' * 80}")

        print(f"\n测试配置:")
        print(f"  测试用例数: {len(TEST_CASES)}")
        print(f"  每用例平均工具数: 3-4 个")

        baseline_key = "1. 串行 + 未命中缓存 (Baseline)"
        baseline = self.results[baseline_key]["total"]

        print(f"\n场景对比:")
        print(f"  {'场景':<35} {'总耗时':<12} {'平均耗时':<12} {'相对基准':<12} {'加速比'}")
        print(f"  {'-' * 85}")

        for name, data in self.results.items():
            total = data["total"]
            avg = data["avg"]
            speedup = baseline / total if total > 0 else 0
            relative = (total / baseline - 1) * 100

            print(f"  {name:<35} {total:>6.3f}s      {avg:>6.3f}s      {relative:>+6.1f}%       {speedup:>4.2f}x")

        # 详细分析
        print(f"\n性能提升分析:")

        s1 = self.results["1. 串行 + 未命中缓存 (Baseline)"]["total"]
        s2 = self.results["2. 串行 + 命中缓存"]["total"]
        s3 = self.results["3. 并行 + 未命中缓存"]["total"]
        s4 = self.results["4. 并行 + 命中缓存 (最优)"]["total"]

        print(f"\n  1. 并行执行提升（无缓存）:")
        print(f"     串行: {s1:.3f}s")
        print(f"     并行: {s3:.3f}s")
        print(f"     提升: {(s1-s3)/s1*100:.1f}% ({s1/s3:.2f}x)")

        print(f"\n  2. 缓存提升（串行）:")
        print(f"     未命中: {s1:.3f}s")
        print(f"     命中: {s2:.3f}s")
        print(f"     提升: {(s1-s2)/s1*100:.1f}% ({s1/s2:.2f}x)")

        print(f"\n  3. 组合效果（并行 + 缓存 vs 基准）:")
        print(f"     基准: {s1:.3f}s")
        print(f"     最优: {s4:.3f}s")
        print(f"     提升: {(s1-s4)/s1*100:.1f}% ({s1/s4:.2f}x)")

        # 缓存详情
        print(f"\n缓存命中率对比:")
        for name, data in self.results.items():
            stats = data["cache_stats"]
            if stats['hits'] + stats['misses'] > 0:
                print(f"  {name:<35} 命中率: {stats['hit_rate']:.1%} (命中:{stats['hits']}, 未命中:{stats['misses']})")

        print(f"\n关键结论:")
        parallel_gain = (s1 - s3) / s1 * 100
        cache_gain = (s1 - s2) / s1 * 100
        combined_gain = (s1 - s4) / s1 * 100

        print(f"  ✓ 并行执行可提升工具调用性能 {parallel_gain:.0f}%")
        print(f"  ✓ 缓存可提升工具调用性能 {cache_gain:.0f}%")
        print(f"  ✓ 组合优化可提升工具调用性能 {combined_gain:.0f}% (达到 {s1/s4:.1f}x 加速)")

        print(f"\n注意:")
        print(f"  ⚠ 本测试只测量工具执行时间，不包括 LLM 调用")
        print(f"  ⚠ 在实际场景中，LLM 调用占总时间的大部分")
        print(f"  ⚠ 因此整体加速比会小于工具调用的加速比")


def main():
    """运行性能测试"""
    print("🚀 工具执行性能测试（精简版）")
    print(f"\n测试数据: {len(TEST_CASES)} 个故障场景")
    print("只测试工具执行部分，排除 LLM 调用影响\n")

    benchmark = ToolExecutionBenchmark()

    # 场景 1: 串行 + 未命中缓存（baseline）
    benchmark.test_scenario(
        "1. 串行 + 未命中缓存 (Baseline)",
        enable_parallel=False,
        use_cache=False
    )

    # 场景 2: 串行 + 命中缓存
    benchmark.test_scenario(
        "2. 串行 + 命中缓存",
        enable_parallel=False,
        use_cache=True
    )

    # 场景 3: 并行 + 未命中缓存
    benchmark.test_scenario(
        "3. 并行 + 未命中缓存",
        enable_parallel=True,
        use_cache=False
    )

    # 场景 4: 并行 + 命中缓存（最优）
    benchmark.test_scenario(
        "4. 并行 + 命中缓存 (最优)",
        enable_parallel=True,
        use_cache=True
    )

    # 生成报告
    benchmark.generate_report()

    print(f"\n{'=' * 80}")
    print("✅ 性能测试完成！")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
