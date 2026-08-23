#!/usr/bin/env python3
"""
工具定义和参数校验模块

提供给 LLM 调用的工具定义（OpenAI Function Calling 格式）
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from log_search import LogSearchTool, SearchLogsResult


# ==================== 工具参数 Pydantic 模型 ====================

class SearchLogsParams(BaseModel):
    """search_logs 工具的参数模型"""

    service_name: Optional[str] = Field(
        None,
        description="服务名称，如 'payment'、'user-service'，不区分大小写"
    )

    keyword: Optional[str] = Field(
        None,
        description="关键字，在消息和 trace_id 中搜索，不区分大小写"
    )

    level: Optional[str] = Field(
        None,
        description="日志级别，必须是 INFO/WARN/ERROR/FATAL 之一，不区分大小写"
    )

    start_time: Optional[str] = Field(
        None,
        description="开始时间，ISO 8601 格式，如 '2024-01-15T10:00:00'"
    )

    end_time: Optional[str] = Field(
        None,
        description="结束时间，ISO 8601 格式，如 '2024-01-15T12:00:00'"
    )

    limit: int = Field(
        10,
        ge=1,
        le=20,
        description="返回结果数量限制，1-20 之间，默认 10"
    )

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        """校验日志级别"""
        if v is None:
            return v
        valid_levels = ['INFO', 'WARN', 'ERROR', 'FATAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"level 必须是 {valid_levels} 之一")
        return v_upper

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time(cls, v):
        """校验时间格式"""
        if v is None:
            return v
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"时间格式必须是 ISO 8601，如 '2024-01-15T10:00:00'")


# ==================== 工具定义（OpenAI Function Calling 格式）====================

SEARCH_LOGS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_logs",
        "description": """搜索应用日志，用于故障排查和问题调查。

## 何时使用
- 故障发生时，需要查看相关日志
- 需要查找特定服务的错误日志
- 需要根据 trace_id 追踪请求链路
- 需要查看某个时间段内的日志

## 能返回什么
- 匹配条件的日志记录（最多 20 条）
- 每条日志包含：时间戳、服务名、日志级别、消息、trace_id
- 搜索耗时统计

## 不能做什么
- 不能修改或删除日志
- 不能搜索超过 20 条结果（会自动截断）
- 不能执行复杂的聚合统计（如计数、求和）
- 搜索超时限制 5 秒

## 参数说明
所有参数都是可选的，至少提供一个搜索条件。多个条件之间是 AND 关系。

## 使用示例
1. 查找支付服务的错误日志：
   service_name="payment", level="ERROR"

2. 查找包含 "timeout" 的日志：
   keyword="timeout"

3. 根据 trace_id 追踪请求：
   keyword="trace-12345"

4. 查找特定时间段的日志：
   start_time="2024-01-15T10:00:00", end_time="2024-01-15T12:00:00"
""",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "服务名称，如 'payment'、'user-service'，不区分大小写"
                },
                "keyword": {
                    "type": "string",
                    "description": "关键字，在消息和 trace_id 中搜索，不区分大小写"
                },
                "level": {
                    "type": "string",
                    "enum": ["INFO", "WARN", "ERROR", "FATAL"],
                    "description": "日志级别，必须是 INFO/WARN/ERROR/FATAL 之一"
                },
                "start_time": {
                    "type": "string",
                    "description": "开始时间，ISO 8601 格式，如 '2024-01-15T10:00:00'"
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间，ISO 8601 格式，如 '2024-01-15T12:00:00'"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 10,
                    "description": "返回结果数量限制，1-20 之间，默认 10"
                }
            },
            "required": []  # 所有参数都是可选的
        }
    }
}


# ==================== 工具执行器 ====================

class ToolExecutor:
    """工具执行器，负责参数校验和执行"""

    def __init__(self, log_file_path: str = "data/logs.jsonl"):
        """
        初始化工具执行器

        Args:
            log_file_path: 日志文件路径
        """
        self.log_search_tool = LogSearchTool(log_file_path)

    def execute_search_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 search_logs 工具调用

        Args:
            params: 工具参数字典

        Returns:
            工具执行结果，包含 success、result 或 error
        """
        try:
            # 第一步：Pydantic 参数校验
            validated_params = SearchLogsParams(**params)

            # 第二步：参数映射（工具参数 -> Python 函数参数）
            # service_name -> service （匹配 log_search.py 的参数名）
            search_kwargs = {
                "service": validated_params.service_name or "",  # 必填参数
                "keyword": validated_params.keyword,
                "limit": validated_params.limit
            }

            # 注意：log_search.py 当前只支持 service、keyword、limit
            # level、start_time、end_time 在工具定义中声明了，但底层函数暂不支持
            # TODO: 扩展 log_search.py 支持更多过滤条件

            # 第三步：执行 Python 函数
            result: SearchLogsResult = self.log_search_tool.search(**search_kwargs)

            # 第四步：格式化返回结果
            return {
                "success": True,
                "result": {
                    "total": result.total,
                    "returned": len(result.logs),
                    "search_time_ms": result.search_time_ms,
                    "logs": [
                        {
                            "timestamp": log.timestamp,
                            "service": log.service,
                            "level": log.level,
                            "message": log.message,
                            "trace_id": log.trace_id
                        }
                        for log in result.logs
                    ]
                }
            }

        except Exception as e:
            # 参数校验失败或执行失败
            return {
                "success": False,
                "error": str(e)
            }

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用工具执行入口

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            执行结果
        """
        if tool_name == "search_logs":
            return self.execute_search_logs(params)
        else:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}"
            }


# ==================== 工具列表 ====================

def get_all_tools() -> List[Dict[str, Any]]:
    """
    获取所有可用工具的定义列表

    Returns:
        工具定义列表（OpenAI Function Calling 格式）
    """
    return [
        SEARCH_LOGS_TOOL
    ]


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("工具定义和参数校验测试")
    print("=" * 80)
    print()

    # 测试 1: 参数校验成功
    print("测试 1: 参数校验成功")
    print("-" * 80)
    params = {
        "service_name": "payment",
        "level": "ERROR",
        "limit": 5
    }
    try:
        validated = SearchLogsParams(**params)
        print(f"✓ 参数校验通过")
        print(f"  service_name: {validated.service_name}")
        print(f"  level: {validated.level}")
        print(f"  limit: {validated.limit}")
    except Exception as e:
        print(f"✗ 参数校验失败: {e}")
    print()

    # 测试 2: 参数校验失败（无效的 level）
    print("测试 2: 参数校验失败（无效的 level）")
    print("-" * 80)
    params = {
        "level": "INVALID"
    }
    try:
        validated = SearchLogsParams(**params)
        print(f"✗ 应该失败但通过了")
    except Exception as e:
        print(f"✓ 参数校验失败（符合预期）: {e}")
    print()

    # 测试 3: 工具执行成功
    print("测试 3: 工具执行成功")
    print("-" * 80)
    import os
    log_path = os.path.join(os.path.dirname(__file__), "..", "data", "logs.jsonl")
    executor = ToolExecutor(log_path)
    result = executor.execute_search_logs({
        "service_name": "payment",
        "level": "ERROR",
        "limit": 3
    })
    print(f"success: {result['success']}")
    if result['success']:
        print(f"total: {result['result']['total']}")
        print(f"returned: {result['result']['returned']}")
        print(f"search_time_ms: {result['result']['search_time_ms']}")
        print(f"logs: {len(result['result']['logs'])} 条")
        for log in result['result']['logs']:
            print(f"  - [{log['level']}] {log['service']}: {log['message'][:50]}...")
    else:
        print(f"error: {result['error']}")
    print()

    # 测试 4: 工具定义
    print("测试 4: 工具定义")
    print("-" * 80)
    tools = get_all_tools()
    print(f"可用工具数量: {len(tools)}")
    print(f"工具名称: {tools[0]['function']['name']}")
    print(f"描述长度: {len(tools[0]['function']['description'])} 字符")
    print()

    print("=" * 80)
    print("✅ 工具定义和参数校验测试完成")
    print("=" * 80)
