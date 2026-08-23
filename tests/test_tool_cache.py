"""
测试工具缓存
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import pytest
from tools.tool_cache import ToolCache


class TestToolCache:
    """测试工具缓存"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return ToolCache(ttl=2)  # 2 秒过期，方便测试

    def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get("search_logs", {"service": "payment"})
        assert result is None
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0

    def test_cache_hit(self, cache):
        """测试缓存命中"""
        # 设置缓存
        cache.set("search_logs", {"service": "payment"}, {"logs": []})

        # 获取缓存
        result = cache.get("search_logs", {"service": "payment"})
        assert result is not None
        assert result == {"logs": []}
        assert cache.stats["hits"] == 1

    def test_cache_key_same_args(self, cache):
        """测试相同参数生成相同 key"""
        cache.set("search_logs", {"service": "payment", "limit": 10}, "result1")

        # 参数顺序不同，但内容相同
        result = cache.get("search_logs", {"limit": 10, "service": "payment"})
        assert result == "result1"

    def test_cache_key_different_args(self, cache):
        """测试不同参数生成不同 key"""
        cache.set("search_logs", {"service": "payment"}, "result1")
        cache.set("search_logs", {"service": "order"}, "result2")

        result1 = cache.get("search_logs", {"service": "payment"})
        result2 = cache.get("search_logs", {"service": "order"})

        assert result1 == "result1"
        assert result2 == "result2"

    def test_cache_expiration(self, cache):
        """测试缓存过期"""
        # 设置缓存
        cache.set("search_logs", {"service": "payment"}, {"logs": []})

        # 立即获取，应该命中
        result1 = cache.get("search_logs", {"service": "payment"})
        assert result1 is not None

        # 等待过期（TTL = 2s）
        time.sleep(2.1)

        # 再次获取，应该未命中（已过期）
        result2 = cache.get("search_logs", {"service": "payment"})
        assert result2 is None
        assert cache.stats["evictions"] == 1

    def test_cache_clear(self, cache):
        """测试清空缓存"""
        cache.set("search_logs", {"service": "payment"}, {"logs": []})
        cache.set("search_runbooks", {"severity": "P0"}, {"runbooks": []})

        cache.clear()

        assert len(cache.cache) == 0
        result = cache.get("search_logs", {"service": "payment"})
        assert result is None

    def test_cache_stats(self, cache):
        """测试缓存统计"""
        # 设置缓存
        cache.set("tool1", {"arg": "val1"}, "result1")

        # 命中
        cache.get("tool1", {"arg": "val1"})

        # 未命中
        cache.get("tool2", {"arg": "val2"})

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["cache_size"] == 1


if __name__ == "__main__":
    print("=" * 80)
    print("工具缓存单元测试")
    print("=" * 80)

    cache = ToolCache(ttl=2)

    print("\n【测试 1】缓存未命中:")
    result = cache.get("search_logs", {"service": "payment"})
    print(f"  结果: {result}")
    print(f"  统计: {cache}")
    assert result is None

    print("\n【测试 2】设置缓存:")
    cache.set("search_logs", {"service": "payment"}, {"logs": ["log1", "log2"]})
    print(f"  统计: {cache}")

    print("\n【测试 3】缓存命中:")
    result = cache.get("search_logs", {"service": "payment"})
    print(f"  结果: {result}")
    print(f"  统计: {cache}")
    assert result == {"logs": ["log1", "log2"]}

    print("\n【测试 4】相同参数（顺序不同）:")
    cache.set("test_tool", {"a": 1, "b": 2}, "result_ab")
    result1 = cache.get("test_tool", {"a": 1, "b": 2})
    result2 = cache.get("test_tool", {"b": 2, "a": 1})
    print(f"  参数1: {result1}")
    print(f"  参数2: {result2}")
    assert result1 == result2 == "result_ab"

    print("\n【测试 5】缓存过期:")
    cache.clear()
    cache.set("expire_test", {"key": "val"}, "result")
    print(f"  立即获取: {cache.get('expire_test', {'key': 'val'})}")
    print("  等待 2.1 秒...")
    time.sleep(2.1)
    print(f"  过期后获取: {cache.get('expire_test', {'key': 'val'})}")
    print(f"  统计: {cache}")

    print("\n【测试 6】最终统计:")
    stats = cache.get_stats()
    print(f"  命中: {stats['hits']}")
    print(f"  未命中: {stats['misses']}")
    print(f"  过期: {stats['evictions']}")
    print(f"  命中率: {stats['hit_rate']:.1%}")
    print(f"  缓存大小: {stats['cache_size']}")

    print("\n✅ 所有测试通过！")
