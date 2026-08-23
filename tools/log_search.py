#!/usr/bin/env python3
"""
Day 3: 日志搜索工具

提供基于服务名和关键字的日志搜索功能，带有参数校验和脱敏保护。

这是一个只读工具：
- 不修改任何数据
- 幂等（多次调用结果一致）
- 有安全边界（限制、脱敏）
"""

import json
import time
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SearchLogsInput(BaseModel):
    """日志搜索输入参数"""

    service: Optional[str] = Field(None, description="服务名，可选")
    keyword: Optional[str] = Field(None, description="关键字，最长100字符")
    limit: int = Field(10, description="返回结果数量，最大20")

    @field_validator('service')
    @classmethod
    def validate_service(cls, v: Optional[str]) -> Optional[str]:
        """校验服务名格式"""
        if v is not None and v.strip():
            return v.strip()
        return None

    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v: Optional[str]) -> Optional[str]:
        """校验关键字长度"""
        if v is not None:
            if len(v) > 100:
                raise ValueError("关键字长度不能超过100字符")
            return v.strip()
        return None

    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """校验结果数量范围"""
        if v < 1:
            return 1
        if v > 20:
            return 20
        return v


class SearchLogsResult(BaseModel):
    """日志搜索结果"""

    logs: List[Dict[str, Any]] = Field(default_factory=list, description="日志列表")
    total: int = Field(0, description="匹配的日志总数")
    search_time_ms: float = Field(0.0, description="搜索耗时（毫秒）")


class LogSearchTool:
    """
    日志搜索工具

    功能：
    - 根据服务名和关键字搜索日志
    - 参数校验
    - 结果限制
    - 敏感信息脱敏

    安全特性：
    - 只读操作
    - 限制返回条数（最多20条）
    - 脱敏处理（密码、token等）
    - 超时保护
    """

    def __init__(self, log_file_path: Optional[str] = None):
        """
        初始化日志搜索工具

        Args:
            log_file_path: 日志文件路径，默认使用 data/sample_logs.jsonl
        """
        if log_file_path:
            self.log_file_path = Path(log_file_path)
        else:
            # 默认路径
            self.log_file_path = Path(__file__).parent.parent / "data" / "sample_logs.jsonl"

    def search(
        self,
        service: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 10
    ) -> SearchLogsResult:
        """
        搜索日志

        Args:
            service: 服务名（可选）
            keyword: 关键字（可选）
            limit: 返回结果数量，最大20

        Returns:
            SearchLogsResult: 搜索结果

        Raises:
            TimeoutError: 搜索超时
            RuntimeError: 搜索失败
        """
        start_time = time.time()

        # 参数校验
        params = SearchLogsInput(service=service, keyword=keyword, limit=limit)

        try:
            matched_logs = []

            # 如果日志文件不存在，返回模拟数据
            if not self.log_file_path.exists():
                return self._generate_mock_logs(params)

            # 读取并搜索日志
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # 超时检查（5秒）
                    if time.time() - start_time > 5:
                        raise TimeoutError("日志搜索超时")

                    # 达到限制数量
                    if len(matched_logs) >= params.limit:
                        break

                    try:
                        log = json.loads(line)

                        # 服务名过滤
                        if params.service and log.get('service') != params.service:
                            continue

                        # 关键字过滤
                        if params.keyword:
                            message = log.get('message', '')
                            if params.keyword.lower() not in message.lower():
                                continue

                        # 脱敏处理
                        log['message'] = self._redact_sensitive(log.get('message', ''))

                        matched_logs.append(log)

                    except json.JSONDecodeError:
                        # 忽略无法解析的日志行
                        continue

            search_time_ms = (time.time() - start_time) * 1000

            return SearchLogsResult(
                logs=matched_logs,
                total=len(matched_logs),
                search_time_ms=round(search_time_ms, 2)
            )

        except TimeoutError:
            raise
        except Exception as e:
            raise RuntimeError(f"日志搜索失败: {str(e)}")

    def _redact_sensitive(self, message: str) -> str:
        """
        脱敏敏感信息

        隐藏：
        - 密码
        - Token
        - API Key
        - 信用卡号
        """
        # 隐藏密码
        message = re.sub(
            r'(password|pwd|passwd)[=:]\s*\S+',
            r'\1=***REDACTED***',
            message,
            flags=re.IGNORECASE
        )

        # 隐藏 token
        message = re.sub(
            r'(token|auth|key|secret)[=:]\s*\S+',
            r'\1=***REDACTED***',
            message,
            flags=re.IGNORECASE
        )

        # 隐藏信用卡号
        message = re.sub(
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            '****-****-****-****',
            message
        )

        return message

    def _generate_mock_logs(self, params: SearchLogsInput) -> SearchLogsResult:
        """生成模拟日志（用于演示）"""
        import random

        mock_logs = [
            {
                "timestamp": "2024-01-20T10:30:00Z",
                "service": "payment",
                "level": "ERROR",
                "message": "Database connection timeout after 30s",
                "trace_id": "trace_12345"
            },
            {
                "timestamp": "2024-01-20T10:31:00Z",
                "service": "payment",
                "level": "ERROR",
                "message": "Payment gateway returned 503",
                "trace_id": "trace_12346"
            },
            {
                "timestamp": "2024-01-20T10:32:00Z",
                "service": "order",
                "level": "WARN",
                "message": "Order creation slow: 3.2s",
                "trace_id": "trace_12347"
            },
        ]

        # 简单过滤
        filtered = []
        for log in mock_logs:
            if params.service and log['service'] != params.service:
                continue
            if params.keyword and params.keyword.lower() not in log['message'].lower():
                continue
            filtered.append(log)

        return SearchLogsResult(
            logs=filtered[:params.limit],
            total=len(filtered),
            search_time_ms=10.0
        )


# 便捷函数
def search_logs(
    service: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    搜索日志的便捷函数

    Args:
        service: 服务名
        keyword: 关键字（可选）
        limit: 返回结果数量

    Returns:
        日志列表
    """
    tool = LogSearchTool()
    result = tool.search(service=service, keyword=keyword, limit=limit)
    return result.logs


if __name__ == "__main__":
    # 测试
    print("测试日志搜索工具\n")

    tool = LogSearchTool()

    # 测试 1: 查询支付服务日志
    print("1. 查询支付服务日志:")
    result = tool.search(service="payment", limit=5)
    print(f"   找到 {result.total} 条日志，耗时 {result.search_time_ms}ms")
    for log in result.logs:
        print(f"   [{log['timestamp']}] {log['message']}")

    # 测试 2: 关键字搜索
    print("\n2. 搜索包含 'timeout' 的日志:")
    result = tool.search(keyword="timeout", limit=3)
    print(f"   找到 {result.total} 条日志")
    for log in result.logs:
        print(f"   [{log['service']}] {log['message']}")

    # 测试 3: 脱敏测试
    print("\n3. 测试脱敏功能:")
    sensitive_msg = "Login failed: password=secret123, token=abc-xyz-123"
    redacted = tool._redact_sensitive(sensitive_msg)
    print(f"   原始: {sensitive_msg}")
    print(f"   脱敏: {redacted}")

    print("\n✅ 测试完成")
