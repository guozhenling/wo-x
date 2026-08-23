# AI Agent 工程师：最小资源清单

只跟随这几类官方资料，避免在第一个月被框架教程淹没。先理解基础能力，再用第 4 周的项目验证它们。

## 核心知识

- [OpenAI API：开发者快速开始](https://platform.openai.com/docs/quickstart/make-your-first-api-request)
  用于：通过 OpenAI 兼容 API 学习模型调用、结构化输出和工具调用。
- [Python 文档：虚拟环境](https://docs.python.org/3/library/venv.html)
  用于：建立隔离环境；只需掌握创建、激活和安装依赖。
- [Pydantic 文档](https://docs.pydantic.dev/)
  用于：让模型输出、工具输入和最终报告都具备可校验的数据契约。
- [Model Context Protocol 规范](https://modelcontextprotocol.io/specification/draft/index)
  用于：理解 prompts、resources、tools 的边界，以及用户同意与安全要求。
- [LangGraph：工作流与 Agent](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
  用于：区分确定性工作流和由模型决策的 Agent 循环。
- [LangGraph：Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)
  用于：把业务过程分为 state、node、edge，并为失败和人工介入建模。

## 使用顺序

第 1 周只看 Python、OpenAI API 与 Pydantic；第 2 周再看 MCP 与 LangGraph 的工作流思路。每读一个概念，完成一个小练习；第 4 周才把它映射到“故障诊断 Agent”。
