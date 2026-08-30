"""
缓存预热

功能：
- 启动时预热常见查询
- 提前执行，填充缓存
- 提升缓存命中率
"""
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class CacheWarmup:
    """缓存预热器"""

    def __init__(self, tool_executor):
        """
        初始化预热器

        Args:
            tool_executor: 工具执行器（RobustToolExecutor 或类似）
        """
        self.executor = tool_executor

    def get_common_queries(self) -> List[Dict[str, Any]]:
        """
        获取常见查询列表

        Returns:
            常见查询配置列表
        """
        return [
            # 日志查询
            {
                "tool": "search_logs",
                "params": {
                    "keywords": ["error", "exception"],
                    "time_range": 60,
                    "max_results": 50
                },
                "description": "最近 1 小时错误日志"
            },
            {
                "tool": "search_logs",
                "params": {
                    "keywords": ["timeout"],
                    "time_range": 60,
                    "max_results": 50
                },
                "description": "最近 1 小时超时日志"
            },

            # OOM 事件
            {
                "tool": "search_oom_events",
                "params": {
                    "time_range": 60
                },
                "description": "最近 1 小时 OOM 事件"
            },

            # 慢查询
            {
                "tool": "search_slow_queries",
                "params": {
                    "time_range": 60
                },
                "description": "最近 1 小时慢查询"
            },

            # 超时事件
            {
                "tool": "search_timeout_events",
                "params": {
                    "time_range": 60
                },
                "description": "最近 1 小时超时事件"
            },

            # 部署历史
            {
                "tool": "get_deployment_history",
                "params": {
                    "hours": 24
                },
                "description": "最近 24 小时部署历史"
            }
        ]

    def warmup(self, parallel: bool = True, max_workers: int = 3) -> Dict[str, Any]:
        """
        执行缓存预热

        Args:
            parallel: 是否并行预热
            max_workers: 并行工作线程数

        Returns:
            预热结果统计
        """
        queries = self.get_common_queries()
        logger.info(f"开始缓存预热，共 {len(queries)} 个查询")

        results = {
            "total": len(queries),
            "success": 0,
            "failed": 0,
            "details": []
        }

        if parallel:
            # 并行预热
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._warmup_one, query): query
                    for query in queries
                }

                for future in as_completed(futures):
                    query = futures[future]
                    try:
                        success = future.result()
                        if success:
                            results["success"] += 1
                            logger.info(f"✓ 预热成功: {query['description']}")
                        else:
                            results["failed"] += 1
                            logger.warning(f"✗ 预热失败: {query['description']}")
                        results["details"].append({
                            "query": query['description'],
                            "success": success
                        })
                    except Exception as e:
                        results["failed"] += 1
                        logger.error(f"✗ 预热异常: {query['description']} - {e}")
                        results["details"].append({
                            "query": query['description'],
                            "success": False,
                            "error": str(e)
                        })
        else:
            # 串行预热
            for query in queries:
                try:
                    success = self._warmup_one(query)
                    if success:
                        results["success"] += 1
                        logger.info(f"✓ 预热成功: {query['description']}")
                    else:
                        results["failed"] += 1
                        logger.warning(f"✗ 预热失败: {query['description']}")
                    results["details"].append({
                        "query": query['description'],
                        "success": success
                    })
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"✗ 预热异常: {query['description']} - {e}")
                    results["details"].append({
                        "query": query['description'],
                        "success": False,
                        "error": str(e)
                    })

        logger.info(
            f"缓存预热完成: 成功 {results['success']}/{results['total']}, "
            f"失败 {results['failed']}"
        )

        return results

    def _warmup_one(self, query: Dict[str, Any]) -> bool:
        """
        预热单个查询

        Args:
            query: 查询配置

        Returns:
            是否成功
        """
        try:
            tool_name = query["tool"]
            params = query["params"]

            # 执行工具调用，结果会自动缓存
            self.executor.execute(tool_name, params)
            return True
        except Exception as e:
            logger.debug(f"预热查询失败: {query['description']} - {e}")
            return False

    def print_warmup_summary(self, results: Dict[str, Any]):
        """打印预热摘要"""
        print("\n" + "=" * 60)
        print("缓存预热摘要")
        print("=" * 60)

        print(f"\n总查询: {results['total']}")
        print(f"成功: {results['success']}")
        print(f"失败: {results['failed']}")

        if results['failed'] > 0:
            print(f"\n失败详情:")
            for detail in results['details']:
                if not detail['success']:
                    print(f"  ✗ {detail['query']}")
                    if 'error' in detail:
                        print(f"    错误: {detail['error']}")
