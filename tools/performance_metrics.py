"""
性能指标收集器

功能：
- 收集各步骤耗时
- 记录 API 调用次数
- 统计缓存命中率
- 生成性能报告
"""
import time
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 延迟
    total_duration: float = 0.0
    step_durations: Dict[str, float] = field(default_factory=dict)

    # API 调用
    llm_calls: int = 0
    tool_calls: int = 0

    # 缓存
    cache_hits: int = 0
    cache_misses: int = 0

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_duration": self.total_duration,
            "step_durations": self.step_durations,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "timestamp": self.timestamp.isoformat()
        }

    def get_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class PerformanceCollector:
    """性能指标收集器"""

    def __init__(self):
        self.current_metrics = PerformanceMetrics()
        self.step_start_times: Dict[str, float] = {}
        self.history: List[PerformanceMetrics] = []

    def start_step(self, step_name: str):
        """开始一个步骤"""
        self.step_start_times[step_name] = time.time()

    def end_step(self, step_name: str):
        """结束一个步骤"""
        if step_name in self.step_start_times:
            duration = time.time() - self.step_start_times[step_name]
            self.current_metrics.step_durations[step_name] = duration
            del self.step_start_times[step_name]

    def record_llm_call(self):
        """记录 LLM 调用"""
        self.current_metrics.llm_calls += 1

    def record_tool_call(self):
        """记录工具调用"""
        self.current_metrics.tool_calls += 1

    def record_cache_hit(self):
        """记录缓存命中"""
        self.current_metrics.cache_hits += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.current_metrics.cache_misses += 1

    def get_metrics(self) -> PerformanceMetrics:
        """获取当前指标"""
        self.current_metrics.total_duration = sum(
            self.current_metrics.step_durations.values()
        )
        return self.current_metrics

    def reset(self):
        """重置当前指标"""
        # 保存到历史
        if self.current_metrics.total_duration > 0:
            self.history.append(self.current_metrics)

        # 重置
        self.current_metrics = PerformanceMetrics()
        self.step_start_times.clear()

    def print_summary(self):
        """打印性能摘要"""
        metrics = self.get_metrics()

        print("\n" + "=" * 60)
        print("性能摘要")
        print("=" * 60)

        print(f"\n总耗时: {metrics.total_duration:.2f}s")

        if metrics.step_durations:
            print(f"\n各步骤耗时:")
            for step, duration in metrics.step_durations.items():
                pct = duration / metrics.total_duration * 100 if metrics.total_duration > 0 else 0
                print(f"  {step}: {duration:.2f}s ({pct:.1f}%)")

        print(f"\nAPI 调用:")
        print(f"  LLM 调用: {metrics.llm_calls} 次")
        print(f"  工具调用: {metrics.tool_calls} 次")

        if metrics.cache_hits + metrics.cache_misses > 0:
            hit_rate = metrics.get_cache_hit_rate()
            print(f"\n缓存:")
            print(f"  命中: {metrics.cache_hits}")
            print(f"  未命中: {metrics.cache_misses}")
            print(f"  命中率: {hit_rate:.1%}")

    def save_to_file(self, filepath: str):
        """保存到文件"""
        metrics = self.get_metrics()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)

    def get_history_summary(self) -> Dict:
        """获取历史统计摘要"""
        if not self.history:
            return {}

        durations = [m.total_duration for m in self.history]
        llm_calls = [m.llm_calls for m in self.history]
        tool_calls = [m.tool_calls for m in self.history]
        hit_rates = [m.get_cache_hit_rate() for m in self.history]

        return {
            "total_runs": len(self.history),
            "duration": {
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations)
            },
            "llm_calls": {
                "avg": sum(llm_calls) / len(llm_calls),
                "total": sum(llm_calls)
            },
            "tool_calls": {
                "avg": sum(tool_calls) / len(tool_calls),
                "total": sum(tool_calls)
            },
            "cache_hit_rate": {
                "avg": sum(hit_rates) / len(hit_rates)
            }
        }


# 全局收集器实例
_global_collector = PerformanceCollector()


def get_collector() -> PerformanceCollector:
    """获取全局收集器"""
    return _global_collector
