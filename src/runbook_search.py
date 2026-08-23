#!/usr/bin/env python3
"""
运行手册检索工具

基于关键词匹配检索相关的运行手册
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RunbookMatch:
    """运行手册匹配结果"""
    runbook_id: str
    title: str
    score: float  # 匹配分数 0-1
    matched_keywords: List[str]  # 匹配到的关键词
    file_path: str
    applicable_conditions: List[str]  # 适用条件
    check_steps: List[Dict[str, Any]]  # 检查步骤
    escalation_conditions: List[str]  # 人工升级条件


class RunbookSearcher:
    """运行手册检索器"""

    def __init__(self, runbooks_dir: str = "runbooks"):
        """
        初始化检索器

        Args:
            runbooks_dir: 运行手册目录
        """
        self.runbooks_dir = Path(runbooks_dir)
        self.runbooks: List[Dict[str, Any]] = []
        self._load_runbooks()

    def _load_runbooks(self):
        """加载所有运行手册"""
        if not self.runbooks_dir.exists():
            raise FileNotFoundError(f"运行手册目录不存在: {self.runbooks_dir}")

        for yaml_file in self.runbooks_dir.glob("*.yaml"):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                runbook = yaml.safe_load(f)
                runbook['_file_path'] = str(yaml_file)
                self.runbooks.append(runbook)

        if not self.runbooks:
            raise ValueError(f"未找到任何运行手册: {self.runbooks_dir}")

    def search(self, query: str, top_k: int = 3) -> List[RunbookMatch]:
        """
        搜索相关的运行手册

        Args:
            query: 查询文本（故障描述）
            top_k: 返回前 k 个最相关的结果

        Returns:
            匹配结果列表，按分数降序排列
        """
        # 将查询文本转为小写，便于匹配
        query_lower = query.lower()

        matches = []
        for runbook in self.runbooks:
            score, matched_keywords = self._calculate_match_score(
                query_lower,
                runbook.get('keywords', [])
            )

            if score > 0:
                matches.append(RunbookMatch(
                    runbook_id=runbook['id'],
                    title=runbook['title'],
                    score=score,
                    matched_keywords=matched_keywords,
                    file_path=runbook['_file_path'],
                    applicable_conditions=runbook.get('applicable_conditions', []),
                    check_steps=runbook.get('check_steps', []),
                    escalation_conditions=runbook.get('escalation_conditions', [])
                ))

        # 按分数降序排序
        matches.sort(key=lambda x: x.score, reverse=True)

        return matches[:top_k]

    def _calculate_match_score(
        self,
        query: str,
        keywords: List[str]
    ) -> tuple[float, List[str]]:
        """
        计算匹配分数

        Args:
            query: 查询文本（已转小写）
            keywords: 关键词列表

        Returns:
            (分数, 匹配的关键词列表)
        """
        matched_keywords = []
        total_weight = 0.0

        for keyword in keywords:
            # 转换为字符串（YAML 可能解析数字为 int）
            keyword_str = str(keyword)
            keyword_lower = keyword_str.lower()
            if keyword_lower in query:
                matched_keywords.append(keyword_str)
                # 关键词越长，权重越高（更精确）
                weight = len(keyword_lower) / 10.0
                total_weight += weight

        # 归一化分数到 0-1
        # 假设匹配 3 个长度为 5 的关键词得满分
        score = min(1.0, total_weight / 1.5)

        return score, matched_keywords

    def get_runbook(self, runbook_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取完整的运行手册

        Args:
            runbook_id: 运行手册 ID

        Returns:
            运行手册内容，如果不存在返回 None
        """
        for runbook in self.runbooks:
            if runbook['id'] == runbook_id:
                return runbook
        return None

    def format_runbook(self, runbook: Dict[str, Any]) -> str:
        """
        格式化运行手册为易读的文本

        Args:
            runbook: 运行手册数据

        Returns:
            格式化后的文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"运行手册: {runbook['title']}")
        lines.append(f"文档 ID: {runbook['id']}")
        lines.append("=" * 80)
        lines.append("")

        lines.append("📋 适用条件:")
        lines.append(runbook.get('applicable_conditions', '').strip())
        lines.append("")

        lines.append("🔍 检查步骤:")
        for step_data in runbook.get('check_steps', []):
            step_num = step_data['step']
            title = step_data['title']
            lines.append(f"\n步骤 {step_num}: {title}")
            lines.append("-" * 60)

            if 'actions' in step_data:
                lines.append("  操作:")
                for action in step_data['actions']:
                    lines.append(f"    • {action}")

            if 'commands' in step_data:
                lines.append("  命令:")
                for cmd in step_data['commands']:
                    lines.append(f"    $ {cmd}")

            # 特殊字段处理
            if 'decision_tree' in step_data:
                lines.append("  决策树:")
                lines.append("    " + step_data['decision_tree'].strip())

            if 'caution' in step_data:
                lines.append("  ⚠️  注意:")
                lines.append("    " + step_data['caution'].strip())

            if 'time_limit' in step_data:
                lines.append("  ⏰ 时间限制:")
                lines.append("    " + step_data['time_limit'].strip())

        lines.append("")
        lines.append("🚨 人工升级条件:")
        lines.append(runbook.get('escalate_conditions', '').strip())
        lines.append("")

        if 'decision_matrix' in runbook:
            lines.append("📊 决策矩阵:")
            lines.append(runbook['decision_matrix'].strip())
            lines.append("")

        if 'contact_info' in runbook:
            lines.append("📞 联系方式:")
            for role, contact in runbook['contact_info'].items():
                lines.append(f"  • {role}: {contact}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    # 测试运行手册检索
    searcher = RunbookSearcher()

    test_queries = [
        "支付接口返回 502 错误",
        "数据库出现死锁了",
        "刚才发布后错误率上升了",
        "订单服务 timeout",
    ]

    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"查询: {query}")
        print('=' * 80)

        matches = searcher.search(query, top_k=2)

        if matches:
            print(f"\n找到 {len(matches)} 个相关运行手册:\n")
            for i, match in enumerate(matches, 1):
                print(f"{i}. {match.title}")
                print(f"   ID: {match.runbook_id}")
                print(f"   匹配度: {match.score:.2f}")
                print(f"   匹配关键词: {', '.join(match.matched_keywords)}")
                print()

            # 显示第一个运行手册的内容
            best_match = matches[0]
            runbook = searcher.get_runbook(best_match.runbook_id)
            if runbook:
                print(f"\n最佳匹配运行手册:")
                print(searcher.format_runbook(runbook))
        else:
            print("\n未找到相关运行手册")
