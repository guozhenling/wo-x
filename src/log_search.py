#!/usr/bin/env python3
"""
日志搜索工具

提供基于服务名和关键字的日志搜索功能，带有参数校验和超时保护。
"""

import json
import time
from pathlib import Path
from typing import List, Optional
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
        if v is not None and len(v) > 100:
            raise ValueError("关键字长度不能超过100字符")
        return v

    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """校验 limit 不超过20"""
        if v > 20:
            raise ValueError("limit 不能超过20")
        if v < 1:
            raise ValueError("limit 必须大于0")
        return v


class LogEntry(BaseModel):
    """单条日志记录"""

    timestamp: str
    service: str
    level: str
    message: str
    trace_id: str


class SearchLogsResult(BaseModel):
    """日志搜索结果"""

    logs: List[LogEntry] = Field(default_factory=list, description="日志列表")
    total: int = Field(0, description="匹配的日志总数")
    search_time_ms: float = Field(0.0, description="搜索耗时（毫秒）")


class LogSearchTool:
    """日志搜索工具"""

    def __init__(self, log_file_path: str = "data/logs.jsonl", timeout_seconds: float = 1.0):
        """
        初始化日志搜索工具

        Args:
            log_file_path: 日志文件路径
            timeout_seconds: 搜索超时时间（秒）
        """
        # 如果是相对路径，从项目根目录解析
        if not Path(log_file_path).is_absolute():
            # 获取项目根目录（src 的父目录）
            project_root = Path(__file__).parent.parent
            self.log_file_path = project_root / log_file_path
        else:
            self.log_file_path = Path(log_file_path)

        self.timeout_seconds = timeout_seconds

        if not self.log_file_path.exists():
            raise FileNotFoundError(f"日志文件不存在: {self.log_file_path}")

    def search(self, service: Optional[str] = None, keyword: Optional[str] = None, limit: int = 10) -> SearchLogsResult:
        """
        搜索日志

        Args:
            service: 服务名（可选）
            keyword: 关键字（可选）
            limit: 返回结果数量

        Returns:
            SearchLogsResult: 搜索结果

        Raises:
            ValueError: 参数校验失败
            TimeoutError: 搜索超时
        """
        # 参数校验
        search_input = SearchLogsInput(service=service, keyword=keyword, limit=limit)

        start_time = time.time()
        matched_logs = []

        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # 超时检查
                    if time.time() - start_time > self.timeout_seconds:
                        raise TimeoutError(f"搜索超时（超过 {self.timeout_seconds} 秒）")

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        log_data = json.loads(line)

                        # 服务名过滤（如果指定了服务名）
                        if search_input.service and log_data.get('service') != search_input.service:
                            continue

                        # 关键字过滤
                        if search_input.keyword:
                            if search_input.keyword.lower() not in log_data.get('message', '').lower():
                                continue

                        # 匹配成功
                        matched_logs.append(LogEntry(**log_data))

                        # 达到 limit 提前退出
                        if len(matched_logs) >= search_input.limit:
                            break

                    except json.JSONDecodeError:
                        # 忽略无效的 JSON 行
                        continue
                    except Exception:
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


# 便捷函数
def search_logs(service: str, keyword: Optional[str] = None, limit: int = 10) -> SearchLogsResult:
    """
    搜索日志的便捷函数

    Args:
        service: 服务名
        keyword: 关键字（可选）
        limit: 返回结果数量

    Returns:
        SearchLogsResult: 搜索结果
    """
    tool = LogSearchTool()
    return tool.search(service=service, keyword=keyword, limit=limit)
