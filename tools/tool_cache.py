"""
工具调用缓存

功能：
- 缓存工具调用结果
- 相同参数的调用直接返回缓存
- 支持 TTL（过期时间）
- 支持缓存统计
"""
import json
import time
import hashlib
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ToolCache:
    """工具调用缓存"""

    def __init__(self, ttl: int = 300):
        """
        初始化缓存

        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def _make_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        生成缓存 key

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            缓存 key
        """
        # 将参数排序后序列化，确保相同参数生成相同 key
        sorted_args = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        content = f"{tool_name}:{sorted_args}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """
        获取缓存

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            缓存的结果，如果不存在或过期返回 None
        """
        key = self._make_key(tool_name, arguments)

        if key in self.cache:
            entry = self.cache[key]
            # 检查是否过期
            if time.time() - entry["timestamp"] < self.ttl:
                self.stats["hits"] += 1
                logger.info(f"缓存命中: {tool_name}({arguments})")
                return entry["result"]
            else:
                # 过期，删除
                del self.cache[key]
                self.stats["evictions"] += 1
                logger.debug(f"缓存过期: {tool_name}({arguments})")

        self.stats["misses"] += 1
        return None

    def set(self, tool_name: str, arguments: Dict[str, Any], result: Any):
        """
        设置缓存

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            result: 工具结果
        """
        key = self._make_key(tool_name, arguments)
        self.cache[key] = {
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "timestamp": time.time()
        }
        logger.debug(f"缓存设置: {tool_name}({arguments})")

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            统计信息
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "hit_rate": hit_rate,
            "cache_size": len(self.cache)
        }

    def __str__(self) -> str:
        """字符串表示"""
        stats = self.get_stats()
        return (
            f"ToolCache(hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']:.2%}, size={stats['cache_size']})"
        )
