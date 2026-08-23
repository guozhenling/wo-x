"""
Day 3: 工具定义（Tool Definitions）

定义工具的 schema，告诉 LLM：
- 工具叫什么名字
- 什么时候该用这个工具
- 有哪些参数
- 参数的类型和限制

这个文件是给 LLM 看的，不是给 Python 看的。
"""
from typing import Dict, Any, List


def get_search_logs_definition() -> Dict[str, Any]:
    """
    返回 search_logs 的工具定义

    这个定义会传给 LLM，告诉它：
    - 这个工具叫什么
    - 什么时候该用
    - 有哪些参数
    - 参数的类型和限制
    """
    return {
        "type": "function",
        "function": {
            "name": "search_logs",
            "description": """搜索指定服务的日志，用于分析故障原因。

使用场景：
- 当需要查看具体错误信息时
- 当需要统计错误频率时
- 当需要查找特定时间段的异常时

返回：
- 日志列表，包含时间、级别、消息等信息
- 最多返回 20 条（性能考虑）

注意：
- 不能查询敏感信息（密码、token 已脱敏）
- 只读操作，不会修改任何数据""",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "服务名，例如：payment, order, user, recommendation",
                        "enum": ["payment", "order", "user", "recommendation"]
                    },
                    "keyword": {
                        "type": "string",
                        "description": "关键字过滤，可选。例如：timeout, 5xx, error"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最大返回条数，默认 10，最大 20",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 10
                    }
                },
                "required": ["service"]
            }
        }
    }


def get_search_runbooks_definition() -> Dict[str, Any]:
    """
    返回 search_runbooks 的工具定义

    告诉 LLM 如何使用 Runbook 检索工具
    """
    return {
        "type": "function",
        "function": {
            "name": "search_runbooks",
            "description": """检索相关的故障处理手册（Runbook），获取标准化的处理步骤。

使用场景：
- 当需要了解如何处理某类故障时
- 当需要标准化的检查步骤时
- 当需要升级条件判断时

返回：
- 相关 Runbook 列表
- 包含检查步骤和修复建议
- 最多返回 3 个最相关的

注意：
- 基于关键词匹配，需要提供准确的故障描述
- 优先返回与严重程度和类别匹配的 Runbook""",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "故障描述，用于匹配 Runbook"
                    },
                    "severity": {
                        "type": "string",
                        "description": "严重程度，可选",
                        "enum": ["P0", "P1", "P2", "P3"]
                    },
                    "category": {
                        "type": "string",
                        "description": "故障类别，可选",
                        "enum": ["availability", "latency", "database", "deployment"]
                    }
                },
                "required": ["description"]
            }
        }
    }


def get_search_slow_queries_definition() -> Dict[str, Any]:
    """
    返回 search_slow_queries 的工具定义

    用于查询数据库慢查询日志
    """
    return {
        "type": "function",
        "function": {
            "name": "search_slow_queries",
            "description": """搜索数据库慢查询日志，用于分析数据库性能问题。

使用场景：
- 数据库死锁问题
- 查询超时问题
- 数据库响应慢

返回：
- 慢查询列表，包含 SQL、执行时间、锁等待时间等
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_range": {
                        "type": "integer",
                        "description": "查询最近多少分钟的慢查询，默认 60 分钟"
                    },
                    "min_duration": {
                        "type": "number",
                        "description": "最小执行时间（秒），默认 1.0 秒"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回记录数量，默认 10"
                    }
                },
                "required": []
            }
        }
    }


def get_deployment_history_definition() -> Dict[str, Any]:
    """
    返回 get_deployment_history 的工具定义

    用于查询部署历史记录
    """
    return {
        "type": "function",
        "function": {
            "name": "get_deployment_history",
            "description": """查询最近的部署历史，用于排查部署相关问题。

使用场景：
- 故障发生时间与部署时间接近
- 新功能上线后出现问题
- 需要回滚判断

返回：
- 部署记录列表，包含时间、服务、版本、操作人等
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "查询最近多少小时的部署，默认 24 小时"
                    },
                    "service": {
                        "type": "string",
                        "description": "服务名称，不指定则查所有服务"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回记录数量，默认 20"
                    }
                },
                "required": []
            }
        }
    }


def get_all_tool_definitions() -> List[Dict[str, Any]]:
    """
    返回所有工具定义

    Day 3: search_logs
    Day 5: search_runbooks
    Day 6: search_slow_queries, get_deployment_history
    """
    return [
        get_search_logs_definition(),
        get_search_runbooks_definition(),
        get_search_slow_queries_definition(),
        get_deployment_history_definition()
    ]


if __name__ == "__main__":
    import json

    definition = get_search_logs_definition()
    print("工具定义（JSON）:")
    print(json.dumps(definition, indent=2, ensure_ascii=False))

    print("\n" + "="*80)
    print("这个 JSON 会传给 LLM，告诉它如何调用工具")
