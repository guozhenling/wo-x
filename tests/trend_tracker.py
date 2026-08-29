"""
趋势追踪工具

追踪多次评测结果，分析趋势变化
"""
import json
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# matplotlib 是可选依赖
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


@dataclass
class TrendPoint:
    """趋势数据点"""
    timestamp: str
    report_id: str
    version: str
    accuracy: float
    p0_accuracy: float
    p1_accuracy: float
    avg_duration: float
    p95_duration: float


class TrendTracker:
    """
    趋势追踪器

    记录和分析多次评测结果的趋势变化
    """

    def __init__(self, history_file: str = "outputs/trends/history.json"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_history(self):
        """保存历史记录"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def add_report(self, report_file: str):
        """
        添加一次评测报告到历史记录

        Args:
            report_file: 报告文件路径
        """
        # 加载报告
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)

        # 提取关键指标
        point = {
            "timestamp": report["metadata"]["end_time"],
            "report_id": report["metadata"]["report_id"],
            "version": report["metadata"]["agent_version"],
            "accuracy": report["summary"]["accuracy"],
            "acceptable_rate": report["summary"]["acceptable_rate"],
            "p0_accuracy": report["key_metrics"]["p0_accuracy"],
            "p1_accuracy": report["key_metrics"]["p1_accuracy"],
            "avg_duration": report["performance"]["avg_duration"],
            "p95_duration": report["performance"]["p95_duration"],
            "total_cases": report["summary"]["total_cases"],
            "failed": report["summary"]["failed"],
        }

        # 添加到历史
        self.history.append(point)
        self._save_history()

        print(f"✅ 已添加报告到趋势追踪: {report['metadata']['report_id']}")

    def analyze_trends(self) -> Dict[str, Any]:
        """
        分析趋势

        Returns:
            趋势分析结果
        """
        if len(self.history) < 2:
            return {
                "status": "insufficient_data",
                "message": "需要至少 2 次评测才能分析趋势",
                "count": len(self.history)
            }

        # 提取时间序列数据
        timestamps = [p["timestamp"] for p in self.history]
        accuracies = [p["accuracy"] for p in self.history]
        p0_accuracies = [p["p0_accuracy"] for p in self.history]
        p1_accuracies = [p["p1_accuracy"] for p in self.history]
        avg_durations = [p["avg_duration"] for p in self.history]

        # 计算趋势
        latest = self.history[-1]
        baseline = self.history[0]

        accuracy_trend = latest["accuracy"] - baseline["accuracy"]
        p0_trend = latest["p0_accuracy"] - baseline["p0_accuracy"]
        p1_trend = latest["p1_accuracy"] - baseline["p1_accuracy"]
        duration_trend = latest["avg_duration"] - baseline["avg_duration"]

        # 识别趋势方向
        trends = {
            "accuracy": self._classify_trend(accuracy_trend, "higher_better"),
            "p0_accuracy": self._classify_trend(p0_trend, "higher_better"),
            "p1_accuracy": self._classify_trend(p1_trend, "higher_better"),
            "avg_duration": self._classify_trend(duration_trend, "lower_better"),
        }

        # 计算改进速度（最近 3 次）
        recent_improvements = {}
        if len(self.history) >= 3:
            recent = self.history[-3:]
            recent_improvements = {
                "accuracy": recent[-1]["accuracy"] - recent[0]["accuracy"],
                "avg_duration": recent[-1]["avg_duration"] - recent[0]["avg_duration"],
            }

        return {
            "status": "success",
            "data_points": len(self.history),
            "baseline": {
                "timestamp": baseline["timestamp"],
                "version": baseline["version"],
                "accuracy": baseline["accuracy"],
                "p0_accuracy": baseline["p0_accuracy"],
                "p1_accuracy": baseline["p1_accuracy"],
                "avg_duration": baseline["avg_duration"],
            },
            "latest": {
                "timestamp": latest["timestamp"],
                "version": latest["version"],
                "accuracy": latest["accuracy"],
                "p0_accuracy": latest["p0_accuracy"],
                "p1_accuracy": latest["p1_accuracy"],
                "avg_duration": latest["avg_duration"],
            },
            "changes": {
                "accuracy": accuracy_trend,
                "p0_accuracy": p0_trend,
                "p1_accuracy": p1_trend,
                "avg_duration": duration_trend,
            },
            "trends": trends,
            "recent_improvements": recent_improvements,
            "summary": self._generate_trend_summary(trends, accuracy_trend, duration_trend)
        }

    def _classify_trend(
        self,
        change: float,
        direction: str
    ) -> Dict[str, Any]:
        """分类趋势方向"""
        threshold = 0.05  # 5% 变化算显著

        if direction == "higher_better":
            if change > threshold:
                return {"direction": "improving", "label": "改善", "color": "green"}
            elif change < -threshold:
                return {"direction": "declining", "label": "下降", "color": "red"}
            else:
                return {"direction": "stable", "label": "稳定", "color": "blue"}
        else:  # lower_better
            if change < -threshold:
                return {"direction": "improving", "label": "改善", "color": "green"}
            elif change > threshold:
                return {"direction": "declining", "label": "恶化", "color": "red"}
            else:
                return {"direction": "stable", "label": "稳定", "color": "blue"}

    def _generate_trend_summary(
        self,
        trends: Dict[str, Dict],
        accuracy_change: float,
        duration_change: float
    ) -> str:
        """生成趋势摘要"""
        lines = []

        # 准确率趋势
        acc_trend = trends["accuracy"]
        if acc_trend["direction"] == "improving":
            lines.append(f"✅ 准确率持续改善 (+{accuracy_change:.1%})")
        elif acc_trend["direction"] == "declining":
            lines.append(f"⚠️ 准确率下降 ({accuracy_change:.1%})")
        else:
            lines.append(f"→ 准确率保持稳定")

        # 性能趋势
        dur_trend = trends["avg_duration"]
        if dur_trend["direction"] == "improving":
            lines.append(f"⚡ 性能提升 ({duration_change:.1f}s)")
        elif dur_trend["direction"] == "declining":
            lines.append(f"⚠️ 性能下降 (+{duration_change:.1f}s)")
        else:
            lines.append(f"→ 性能保持稳定")

        return "\n".join(lines)

    def generate_chart(self, output_file: str = "outputs/trends/trend_chart.png"):
        """
        生成趋势图

        Args:
            output_file: 输出文件路径
        """
        if not HAS_MATPLOTLIB:
            print("⚠️ 需要安装 matplotlib 才能生成趋势图")
            print("   安装命令: pip install matplotlib")
            return

        if len(self.history) < 2:
            print("⚠️ 需要至少 2 次评测才能生成趋势图")
            return

        # 提取数据
        timestamps = [datetime.fromisoformat(p["timestamp"]) for p in self.history]
        accuracies = [p["accuracy"] * 100 for p in self.history]
        p0_accuracies = [p["p0_accuracy"] * 100 for p in self.history]
        p1_accuracies = [p["p1_accuracy"] * 100 for p in self.history]
        avg_durations = [p["avg_duration"] for p in self.history]

        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # 准确率趋势
        ax1.plot(timestamps, accuracies, 'o-', label='整体准确率', linewidth=2)
        ax1.plot(timestamps, p0_accuracies, 's-', label='P0 准确率', linewidth=2)
        ax1.plot(timestamps, p1_accuracies, '^-', label='P1 准确率', linewidth=2)
        ax1.set_ylabel('准确率 (%)')
        ax1.set_title('准确率趋势')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 性能趋势
        ax2.plot(timestamps, avg_durations, 'o-', color='orange', linewidth=2)
        ax2.set_xlabel('时间')
        ax2.set_ylabel('平均延迟 (秒)')
        ax2.set_title('性能趋势')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        # 保存
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 趋势图已保存到: {output_file}")

    def print_trends(self, analysis: Dict[str, Any]):
        """打印趋势分析报告"""
        print("\n" + "=" * 60)
        print("趋势分析报告")
        print("=" * 60)

        if analysis["status"] != "success":
            print(f"\n⚠️ {analysis['message']}")
            print(f"当前数据点: {analysis['count']}")
            return

        print(f"\n数据点数量: {analysis['data_points']}")

        # 基线
        baseline = analysis["baseline"]
        print(f"\n基线（第一次评测）:")
        print(f"  时间: {baseline['timestamp']}")
        print(f"  版本: {baseline['version']}")
        print(f"  准确率: {baseline['accuracy']:.1%}")
        print(f"  P0 准确率: {baseline['p0_accuracy']:.1%}")
        print(f"  平均延迟: {baseline['avg_duration']:.1f}s")

        # 最新
        latest = analysis["latest"]
        print(f"\n最新（最近一次评测）:")
        print(f"  时间: {latest['timestamp']}")
        print(f"  版本: {latest['version']}")
        print(f"  准确率: {latest['accuracy']:.1%}")
        print(f"  P0 准确率: {latest['p0_accuracy']:.1%}")
        print(f"  平均延迟: {latest['avg_duration']:.1f}s")

        # 变化
        changes = analysis["changes"]
        print(f"\n总体变化:")
        print(f"  准确率: {changes['accuracy']:+.1%}")
        print(f"  P0 准确率: {changes['p0_accuracy']:+.1%}")
        print(f"  P1 准确率: {changes['p1_accuracy']:+.1%}")
        print(f"  平均延迟: {changes['avg_duration']:+.1f}s")

        # 趋势
        trends = analysis["trends"]
        print(f"\n趋势:")
        print(f"  准确率: {trends['accuracy']['label']}")
        print(f"  P0 准确率: {trends['p0_accuracy']['label']}")
        print(f"  P1 准确率: {trends['p1_accuracy']['label']}")
        print(f"  性能: {trends['avg_duration']['label']}")

        # 摘要
        print(f"\n{analysis['summary']}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    """
    使用示例
    """
    print("趋势追踪使用示例:")
    print("\nfrom tests.trend_tracker import TrendTracker")
    print("")
    print("# 1. 创建追踪器")
    print("tracker = TrendTracker()")
    print("")
    print("# 2. 添加评测报告")
    print("tracker.add_report('outputs/evaluations/baseline.json')")
    print("tracker.add_report('outputs/evaluations/optimized.json')")
    print("")
    print("# 3. 分析趋势")
    print("analysis = tracker.analyze_trends()")
    print("tracker.print_trends(analysis)")
    print("")
    print("# 4. 生成趋势图")
    print("tracker.generate_chart('outputs/trends/trend_chart.png')")
