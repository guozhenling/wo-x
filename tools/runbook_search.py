#!/usr/bin/env python3
"""
Day 5: Runbook 检索工具

基于关键词匹配检索相关的处理手册（Runbook），提供标准化的故障处理步骤。

特点：
- 关键词匹配算法
- 返回最相关的 Top-K 结果
- 包含检查步骤和升级条件
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional


def search_runbooks(
    description: str,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    检索相关的 Runbook

    Args:
        description: 故障描述
        severity: 严重程度（P0/P1/P2/P3），可选
        category: 类别，可选
        top_k: 返回最相关的 N 个，默认 3

    Returns:
        Runbook 列表，按相关度排序
    """
    searcher = RunbookSearcher()
    matches = searcher.search(
        query=description,
        severity=severity,
        category=category,
        top_k=top_k
    )

    # 转换为简化格式
    results = []
    for match in matches:
        results.append({
            "title": match['title'],
            "score": match['score'],
            "matched_keywords": match['matched_keywords'],
            "check_steps": match['check_steps'],
            "escalation_conditions": match.get('escalation_conditions', [])
        })

    return results


class RunbookSearcher:
    """
    Runbook 检索器

    功能：
    - 加载 YAML 格式的 Runbook 文件
    - 基于关键词计算相关度
    - 返回最匹配的 Runbook
    """

    def __init__(self, runbooks_dir: Optional[str] = None):
        """
        初始化检索器

        Args:
            runbooks_dir: Runbook 目录，默认使用 runbooks/
        """
        if runbooks_dir:
            self.runbooks_dir = Path(runbooks_dir)
        else:
            # 默认路径
            self.runbooks_dir = Path(__file__).parent.parent / "runbooks"

        self.runbooks: List[Dict[str, Any]] = []
        self._load_runbooks()

    def _load_runbooks(self):
        """加载所有 Runbook"""
        if not self.runbooks_dir.exists():
            # 如果目录不存在，使用模拟数据
            self.runbooks = self._get_mock_runbooks()
            return

        for yaml_file in self.runbooks_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    runbook = yaml.safe_load(f)
                    runbook['_file_path'] = str(yaml_file)
                    self.runbooks.append(runbook)
            except Exception as e:
                print(f"⚠️  加载 {yaml_file} 失败: {e}")

        if not self.runbooks:
            # 没有加载到任何 Runbook，使用模拟数据
            self.runbooks = self._get_mock_runbooks()

    def search(
        self,
        query: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        搜索相关的 Runbook

        Args:
            query: 查询文本（故障描述）
            severity: 严重程度，可选
            category: 类别，可选
            top_k: 返回前 k 个

        Returns:
            匹配结果列表，按分数降序
        """
        query_lower = query.lower()

        matches = []
        for runbook in self.runbooks:
            score, matched_keywords = self._calculate_score(
                query_lower,
                runbook.get('keywords', []),
                severity,
                runbook.get('severity_match', []),
                category,
                runbook.get('category', '')
            )

            if score > 0:
                matches.append({
                    "title": runbook.get('title', 'Untitled'),
                    "score": score,
                    "matched_keywords": matched_keywords,
                    "description": runbook.get('description', ''),
                    "check_steps": runbook.get('check_steps', []),
                    "fix_steps": runbook.get('fix_steps', []),
                    "escalation_conditions": runbook.get('escalation_conditions', []),
                    "related_docs": runbook.get('related_docs', [])
                })

        # 按分数降序排序
        matches.sort(key=lambda x: x['score'], reverse=True)

        return matches[:top_k]

    def _calculate_score(
        self,
        query: str,
        keywords: List[str],
        severity: Optional[str],
        severity_match: List[str],
        category: Optional[str],
        runbook_category: str
    ) -> tuple:
        """
        计算匹配分数

        计分规则：
        - 关键词完全匹配 +10
        - 严重程度匹配 +3
        - 类别匹配 +2
        """
        score = 0.0
        matched_keywords = []

        # 1. 关键词匹配
        for keyword in keywords:
            keyword_str = str(keyword).lower()
            if keyword_str in query:
                matched_keywords.append(str(keyword))
                score += 10

        # 2. 严重程度匹配
        if severity and severity in severity_match:
            score += 3

        # 3. 类别匹配
        if category and category == runbook_category:
            score += 2

        return score, matched_keywords

    def _get_mock_runbooks(self) -> List[Dict[str, Any]]:
        """返回模拟 Runbook（用于演示）"""
        return [
            {
                "title": "支付 5xx 错误处理",
                "description": "处理支付接口返回 5xx 错误",
                "keywords": ["支付", "5xx", "payment", "gateway", "timeout"],
                "severity_match": ["P0", "P1"],
                "category": "availability",
                "check_steps": [
                    "检查支付网关状态",
                    "检查数据库连接",
                    "查看最近部署记录"
                ],
                "fix_steps": [
                    "如果网关问题：切换备用通道",
                    "如果数据库问题：重启连接池",
                    "如果部署问题：回滚版本"
                ],
                "escalation_conditions": [
                    "持续时间 > 10 分钟",
                    "影响用户 > 1000"
                ]
            },
            {
                "title": "数据库死锁处理",
                "description": "处理数据库死锁问题",
                "keywords": ["数据库", "死锁", "deadlock", "1205", "mysql"],
                "severity_match": ["P1", "P2"],
                "category": "database",
                "check_steps": [
                    "查看死锁日志",
                    "分析事务持有的锁",
                    "检查慢查询"
                ],
                "fix_steps": [
                    "优化事务顺序",
                    "减少事务持有时间",
                    "添加索引减少锁范围"
                ],
                "escalation_conditions": [
                    "死锁频率 > 10次/分钟",
                    "影响核心业务"
                ]
            },
            {
                "title": "部署回滚流程",
                "description": "发布后出现问题的回滚步骤",
                "keywords": ["部署", "发布", "回滚", "rollback", "deployment"],
                "severity_match": ["P0", "P1"],
                "category": "deployment",
                "check_steps": [
                    "确认问题出现在发布后",
                    "检查发布版本号",
                    "评估回滚影响"
                ],
                "fix_steps": [
                    "停止灰度流量",
                    "执行回滚命令",
                    "验证功能正常",
                    "通知相关团队"
                ],
                "escalation_conditions": [
                    "回滚失败",
                    "影响全量用户"
                ]
            }
        ]


if __name__ == "__main__":
    # 测试
    print("测试 Runbook 检索\n")

    # 测试 1: 支付问题
    print("1. 查询：支付接口 5xx")
    results = search_runbooks("支付接口 5xx 错误率 35%", severity="P0")
    print(f"   找到 {len(results)} 个 Runbook")
    if results:
        print(f"   最佳匹配: {results[0]['title']}")
        print(f"   匹配度: {results[0]['score']}")
        print(f"   关键词: {results[0]['matched_keywords']}")

    # 测试 2: 数据库问题
    print("\n2. 查询：数据库死锁")
    results = search_runbooks("MySQL 报 1205 死锁错误", category="database")
    print(f"   找到 {len(results)} 个 Runbook")
    if results:
        print(f"   最佳匹配: {results[0]['title']}")

    print("\n✅ 测试完成")
