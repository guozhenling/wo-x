"""
性能基准测试

功能：
- 运行多个测试案例
- 统计延迟分布
- 生成基准报告
"""
import time
from typing import List, Dict, Any
import statistics


class PerformanceBenchmark:
    """性能基准测试"""

    def run_benchmark(
        self,
        agent,
        test_cases: List[str],
        iterations: int = 3
    ) -> Dict[str, Any]:
        """
        运行基准测试

        Args:
            agent: Agent 实例
            test_cases: 测试案例列表
            iterations: 每个案例运行次数

        Returns:
            基准测试结果
        """
        results = []

        print(f"\n运行基准测试: {len(test_cases)} 个案例 × {iterations} 次")
        print("=" * 60)

        for idx, case in enumerate(test_cases, 1):
            case_results = []

            print(f"\n[{idx}/{len(test_cases)}] 测试: {case[:50]}...")

            for i in range(iterations):
                start = time.time()
                try:
                    agent.analyze(case)
                    duration = time.time() - start
                    case_results.append(duration)
                    print(f"  第 {i+1} 次: {duration:.2f}s")
                except Exception as e:
                    print(f"  第 {i+1} 次: 失败 - {e}")
                    # 失败的用 0 占位，后续计算时会过滤
                    case_results.append(0)

            # 过滤掉失败的（0 值）
            valid_results = [r for r in case_results if r > 0]

            if valid_results:
                results.append({
                    "case": case[:50],
                    "full_case": case,
                    "avg": statistics.mean(valid_results),
                    "min": min(valid_results),
                    "max": max(valid_results),
                    "median": statistics.median(valid_results),
                    "runs": len(valid_results),
                    "failed": len(case_results) - len(valid_results)
                })
            else:
                results.append({
                    "case": case[:50],
                    "full_case": case,
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "median": 0,
                    "runs": 0,
                    "failed": len(case_results)
                })

        # 计算整体统计
        valid_avgs = [r["avg"] for r in results if r["avg"] > 0]

        if valid_avgs:
            sorted_avgs = sorted(valid_avgs)
            p50_idx = int(len(sorted_avgs) * 0.50)
            p95_idx = int(len(sorted_avgs) * 0.95)
            p99_idx = int(len(sorted_avgs) * 0.99)

            summary = {
                "total_cases": len(test_cases),
                "successful_cases": len(valid_avgs),
                "failed_cases": len(test_cases) - len(valid_avgs),
                "avg": statistics.mean(valid_avgs),
                "median": statistics.median(valid_avgs),
                "min": min(valid_avgs),
                "max": max(valid_avgs),
                "p50": sorted_avgs[p50_idx] if p50_idx < len(sorted_avgs) else 0,
                "p95": sorted_avgs[p95_idx] if p95_idx < len(sorted_avgs) else 0,
                "p99": sorted_avgs[p99_idx] if p99_idx < len(sorted_avgs) else 0,
            }
        else:
            summary = {
                "total_cases": len(test_cases),
                "successful_cases": 0,
                "failed_cases": len(test_cases),
                "avg": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
            }

        return {
            "results": results,
            "summary": summary
        }

    def print_results(self, benchmark: Dict[str, Any]):
        """打印基准测试结果"""
        print("\n" + "=" * 60)
        print("性能基准测试结果")
        print("=" * 60)

        summary = benchmark["summary"]

        print(f"\n整体统计:")
        print(f"  测试案例: {summary['total_cases']} 个")
        print(f"  成功: {summary['successful_cases']} 个")
        print(f"  失败: {summary['failed_cases']} 个")

        if summary['successful_cases'] > 0:
            print(f"\n延迟统计:")
            print(f"  平均: {summary['avg']:.2f}s")
            print(f"  中位数: {summary['median']:.2f}s")
            print(f"  最快: {summary['min']:.2f}s")
            print(f"  最慢: {summary['max']:.2f}s")
            print(f"  P50:  {summary['p50']:.2f}s")
            print(f"  P95:  {summary['p95']:.2f}s")
            print(f"  P99:  {summary['p99']:.2f}s")

            print(f"\n各案例详情:")
            for r in benchmark["results"]:
                if r['avg'] > 0:
                    print(f"\n  {r['case']}...")
                    print(f"    平均: {r['avg']:.2f}s")
                    print(f"    范围: {r['min']:.2f}s - {r['max']:.2f}s")
                    print(f"    中位数: {r['median']:.2f}s")
                    if r['failed'] > 0:
                        print(f"    失败: {r['failed']} 次")

    def save_results(self, benchmark: Dict[str, Any], filepath: str):
        """保存结果到文件"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(benchmark, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {filepath}")
