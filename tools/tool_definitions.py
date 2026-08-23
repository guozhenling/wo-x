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


def get_all_tool_definitions() -> List[Dict[str, Any]]:
    """
    返回所有工具定义

    Day 3: search_logs
    Day 5: search_runbooks（新增）
    Day 8-9: 更多工具
    """
    return [
        get_search_logs_definition(),
        get_search_runbooks_definition()  # Day 5 新增
    ]


if __name__ == "__main__":
    import json

    definition = get_search_logs_definition()
    print("工具定义（JSON）:")
    print(json.dumps(definition, indent=2, ensure_ascii=False))

    print("\n" + "="*80)
    print("这个 JSON 会传给 LLM，告诉它如何调用工具")
