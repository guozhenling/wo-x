#!/usr/bin/env python3
"""
工具调用性能测试套件

测试场景：
1. 串行 + 未命中缓存（baseline）
2. 串行 + 命中缓存
3. 并行 + 未命中缓存
4. 并行 + 命中缓存（最优）

测试数据：
- 使用固定的故障描述确保可重复性
- 每个场景运行多次取平均值
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import statistics
from typing import List, Dict, Any
from src.agent_v2 import IncidentAgentV2
from tools.tool_coordinator import ToolCoordinator


# 测试数据：10 个不同的故障场景
TEST_CASES = [
    "支付接口 5xx 错误率从 0.1% 升到 35%，持续 10 分钟",
    "推荐系统 P99 延迟从 500ms 升至 2 秒",
    "MySQL 报 1205 死锁错误，影响订单创建",
    "recommendation 服务 Pod 频繁 OOMKilled，重启 5 次",
    "搜索接口超时率从 1% 升至 15%",
    "部署后 payment 服务 CPU 使用率 100%",
    "广告服务返回空结果，影响 10% 流量",
    "数据库慢查询增多，平均执行时间 5 秒",
    "订单服务日志出现大量 Connection timeout",
    "Kafka 消息堆积 100 万条，消费延迟 2 小时",
]


class PerformanceTestSuite:
    """性能测试套件"""

    def __init__(self):
        self.results = {
            "serial_no_cache": [],
            "serial_with_cache": [],
            "parallel_no_cache": [],
            "parallel_with_cache": []
        }

    def run_scenario_1_serial_no_cache(self, rounds: int = 3):
        """
        场景 1: 串行 + 未命中缓存（baseline）

        每轮测试：
        - 创建新 Agent（清空缓存）
        - 禁用并行执行
        - 运行所有测试用例
        """
        print("\n" + "=" * 80)
        print("场景 1: 串行 + 未命中缓存（Baseline）")
        print("=" * 80)

        elapsed_times = []

        for round_num in range(1, rounds + 1):
            print(f"\n--- 第 {round_num}/{rounds} 轮 ---")

            # 创建新 Agent（清空缓存）
            agent = IncidentAgentV2()

            # 禁用并行执行（临时修改）
            original_execute = agent.coordinator.execute_plan
            agent.coordinator.execute_plan = lambda: self._execute_serial(agent.coordinator)

            start_time = time.time()

            for i, description in enumerate(TEST_CASES, 1):
                print(f"  {i}/{len(TEST_CASES)}: {description[:50]}...")
                agent.analyze(description)

            elapsed = time.time() - start_time
            elapsed_times.append(elapsed)

            # 恢复原方法
            agent.coordinator.execute_plan = original_execute

            print(f"  耗时: {elapsed:.2f}s")

        avg_time = statistics.mean(elapsed_times)
        std_time = statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0

        self.results["serial_no_cache"] = {
            "times": elapsed_times,
            "avg": avg_time,
            "std": std_time
        }

        print(f"\n平均耗时: {avg_time:.2f}s ± {std_time:.2f}s")

    def run_scenario_2_serial_with_cache(self, rounds: int = 3):
        """
        场景 2: 串行 + 命中缓存

        每轮测试：
        - 使用同一个 Agent（缓存保留）
        - 禁用并行执行
        - 运行所有测试用例 2 次（第 2 次命中缓存）
        """
        print("\n" + "=" * 80)
        print("场景 2: 串行 + 命中缓存")
        print("=" * 80)

        elapsed_times = []

        for round_num in range(1, rounds + 1):
            print(f"\n--- 第 {round_num}/{rounds} 轮 ---")

            # 创建新 Agent
            agent = IncidentAgentV2()

            # 禁用并行执行
            original_execute = agent.coordinator.execute_plan
            agent.coordinator.execute_plan = lambda: self._execute_serial(agent.coordinator)

            # 第 1 次：预热缓存
            print("  预热缓存...")
            for description in TEST_CASES:
                agent.analyze(description)

            # 第 2 次：命中缓存（计时）
            print("  开始计时（命中缓存）...")
            start_time = time.time()

            for i, description in enumerate(TEST_CASES, 1):
                print(f"  {i}/{len(TEST_CASES)}: {description[:50]}...")
                agent.analyze(description)

            elapsed = time.time() - start_time
            elapsed_times.append(elapsed)

            # 恢复原方法
            agent.coordinator.execute_plan = original_execute

            # 输出缓存统计
            cache_stats = agent.coordinator.cache.get_stats()
            print(f"  耗时: {elapsed:.2f}s")
            print(f"  缓存命中率: {cache_stats['hit_rate']:.1%}")

        avg_time = statistics.mean(elapsed_times)
        std_time = statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0

        self.results["serial_with_cache"] = {
            "times": elapsed_times,
            "avg": avg_time,
            "std": std_time
        }

        print(f"\n平均耗时: {avg_time:.2f}s ± {std_time:.2f}s")

    def run_scenario_3_parallel_no_cache(self, rounds: int = 3):
        """
        场景 3: 并行 + 未命中缓存

        每轮测试：
        - 创建新 Agent（清空缓存）
        - 启用并行执行（默认）
        - 运行所有测试用例
        """
        print("\n" + "=" * 80)
        print("场景 3: 并行 + 未命中缓存")
        print("=" * 80)

        elapsed_times = []

        for round_num in range(1, rounds + 1):
            print(f"\n--- 第 {round_num}/{rounds} 轮 ---")

            # 创建新 Agent（清空缓存）
            agent = IncidentAgentV2()

            start_time = time.time()

            for i, description in enumerate(TEST_CASES, 1):
                print(f"  {i}/{len(TEST_CASES)}: {description[:50]}...")
                agent.analyze(description)

            elapsed = time.time() - start_time
            elapsed_times.append(elapsed)

            print(f"  耗时: {elapsed:.2f}s")

        avg_time = statistics.mean(elapsed_times)
        std_time = statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0

        self.results["parallel_no_cache"] = {
            "times": elapsed_times,
            "avg": avg_time,
            "std": std_time
        }

        print(f"\n平均耗时: {avg_time:.2f}s ± {std_time:.2f}s")

    def run_scenario_4_parallel_with_cache(self, rounds: int = 3):
        """
        场景 4: 并行 + 命中缓存（最优）

        每轮测试：
        - 使用同一个 Agent（缓存保留）
        - 启用并行执行（默认）
        - 运行所有测试用例 2 次（第 2 次命中缓存）
        """
        print("\n" + "=" * 80)
        print("场景 4: 并行 + 命中缓存（最优）")
        print("=" * 80)

        elapsed_times = []

        for round_num in range(1, rounds + 1):
            print(f"\n--- 第 {round_num}/{rounds} 轮 ---")

            # 创建新 Agent
            agent = IncidentAgentV2()

            # 第 1 次：预热缓存
            print("  预热缓存...")
            for description in TEST_CASES:
                agent.analyze(description)

            # 第 2 次：命中缓存（计时）
            print("  开始计时（并行 + 缓存）...")
            start_time = time.time()

            for i, description in enumerate(TEST_CASES, 1):
                print(f"  {i}/{len(TEST_CASES)}: {description[:50]}...")
                agent.analyze(description)

            elapsed = time.time() - start_time
            elapsed_times.append(elapsed)

            # 输出缓存统计
            cache_stats = agent.coordinator.cache.get_stats()
            print(f"  耗时: {elapsed:.2f}s")
            print(f"  缓存命中率: {cache_stats['hit_rate']:.1%}")

        avg_time = statistics.mean(elapsed_times)
        std_time = statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0

        self.results["parallel_with_cache"] = {
            "times": elapsed_times,
            "avg": avg_time,
            "std": std_time
        }

        print(f"\n平均耗时: {avg_time:.2f}s ± {std_time:.2f}s")

    def _execute_serial(self, coordinator: ToolCoordinator) -> Dict[str, Any]:
        """串行执行工具（用于场景 1 和 2）"""
        results = {}

        for step in coordinator.execution_plan:
            tool_name = step['tool']

            # 检查依赖
            if 'depends_on' in step and step['depends_on']:
                missing_deps = [
                    dep for dep in step['depends_on']
                    if dep not in results
                ]
                if missing_deps:
                    continue

            # 检查是否可以调用
            if not coordinator.agent.trace.can_call_tool():
                continue

            # 执行工具（带缓存）
            result = coordinator._execute_tool_with_cache(
                tool_name,
                step['arguments'],
                step['reason']
            )
            results[tool_name] = result

        return results

    def generate_report(self):
        """生成性能测试报告"""
        print("\n" + "=" * 80)
        print("性能测试报告")
        print("=" * 80)

        # 基准时间（场景 1）
        baseline = self.results["serial_no_cache"]["avg"]

        print(f"\n测试配置:")
        print(f"  测试用例数: {len(TEST_CASES)}")
        print(f"  每场景轮数: {len(self.results['serial_no_cache']['times'])}")

        print(f"\n场景对比:")
        print(f"  {'场景':<30} {'平均耗时':<15} {'相对基准':<15} {'加速比'}")
        print(f"  {'-' * 70}")

        scenarios = [
            ("1. 串行 + 未命中缓存 (Baseline)", "serial_no_cache"),
            ("2. 串行 + 命中缓存", "serial_with_cache"),
            ("3. 并行 + 未命中缓存", "parallel_no_cache"),
            ("4. 并行 + 命中缓存 (最优)", "parallel_with_cache"),
        ]

        for name, key in scenarios:
            avg = self.results[key]["avg"]
            std = self.results[key]["std"]
            speedup = baseline / avg if avg > 0 else 0
            relative = (avg / baseline - 1) * 100

            print(f"  {name:<30} {avg:>6.2f}s ± {std:>4.2f}s   {relative:>+6.1f}%        {speedup:>4.2f}x")

        # 详细分析
        print(f"\n性能提升分析:")

        # 并行 vs 串行（无缓存）
        serial_no_cache = self.results["serial_no_cache"]["avg"]
        parallel_no_cache = self.results["parallel_no_cache"]["avg"]
        parallel_gain = (serial_no_cache - parallel_no_cache) / serial_no_cache * 100

        print(f"  1. 并行执行提升（无缓存）:")
        print(f"     串行: {serial_no_cache:.2f}s")
        print(f"     并行: {parallel_no_cache:.2f}s")
        print(f"     提升: {parallel_gain:.1f}% ({serial_no_cache/parallel_no_cache:.2f}x)")

        # 缓存提升（串行）
        serial_with_cache = self.results["serial_with_cache"]["avg"]
        cache_gain_serial = (serial_no_cache - serial_with_cache) / serial_no_cache * 100

        print(f"\n  2. 缓存提升（串行）:")
        print(f"     未命中: {serial_no_cache:.2f}s")
        print(f"     命中: {serial_with_cache:.2f}s")
        print(f"     提升: {cache_gain_serial:.1f}% ({serial_no_cache/serial_with_cache:.2f}x)")

        # 组合效果（并行 + 缓存）
        parallel_with_cache = self.results["parallel_with_cache"]["avg"]
        combined_gain = (baseline - parallel_with_cache) / baseline * 100

        print(f"\n  3. 组合效果（并行 + 缓存 vs 基准）:")
        print(f"     基准: {baseline:.2f}s")
        print(f"     最优: {parallel_with_cache:.2f}s")
        print(f"     提升: {combined_gain:.1f}% ({baseline/parallel_with_cache:.2f}x)")

        # 结论
        print(f"\n关键结论:")
        print(f"  ✓ 并行执行可提升性能 {parallel_gain:.0f}%")
        print(f"  ✓ 缓存可提升性能 {cache_gain_serial:.0f}%")
        print(f"  ✓ 组合优化可提升性能 {combined_gain:.0f}% (达到 {baseline/parallel_with_cache:.1f}x 加速)")

        print(f"\n推荐配置:")
        print(f"  ✓ 启用并行执行（ThreadPoolExecutor）")
        print(f"  ✓ 启用工具缓存（TTL = 5 分钟）")
        print(f"  ✓ 适用场景：重复分析相似故障、批量处理")


def main():
    """运行完整性能测试"""
    print("🚀 工具调用性能测试套件")
    print(f"\n测试数据: {len(TEST_CASES)} 个故障场景")
    print("每场景运行 3 轮取平均值\n")

    suite = PerformanceTestSuite()

    # 场景 1: 串行 + 未命中缓存（baseline）
    suite.run_scenario_1_serial_no_cache(rounds=3)

    # 场景 2: 串行 + 命中缓存
    suite.run_scenario_2_serial_with_cache(rounds=3)

    # 场景 3: 并行 + 未命中缓存
    suite.run_scenario_3_parallel_no_cache(rounds=3)

    # 场景 4: 并行 + 命中缓存（最优）
    suite.run_scenario_4_parallel_with_cache(rounds=3)

    # 生成报告
    suite.generate_report()

    print("\n" + "=" * 80)
    print("✅ 性能测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
