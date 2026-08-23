import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
import json
import os

if TYPE_CHECKING:
    from openai import OpenAI
    from anthropic import Anthropic


def find_project_root() -> Path:
    """
    查找项目根目录（包含 config.yaml 的目录）
    从当前文件向上查找，直到找到 config.yaml
    """
    current = Path(__file__).resolve().parent

    # 最多向上查找 5 层
    for _ in range(5):
        config_file = current / "config.yaml"
        if config_file.exists():
            return current

        parent = current.parent
        if parent == current:  # 已到根目录
            break
        current = parent

    # 如果没找到，返回项目根目录（src 的父目录）
    return Path(__file__).resolve().parent.parent


class LLMClient:
    """支持多种协议的LLM客户端（OpenAI 和 Anthropic）"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化客户端

        Args:
            config_path: 配置文件路径（可选）
                        如果不提供，会自动查找项目根目录的 config.yaml
        """
        if config_path is None:
            # 自动查找配置文件
            project_root = find_project_root()
            config_path = str(project_root / "config.yaml")

        self.config = self._load_config(config_path)
        self.protocol = self.config['api'].get('protocol', 'openai')  # 默认 openai
        self.client: Any  # 运行时是 OpenAI 或 Anthropic，使用 Any 避免类型检查问题

        if self.protocol == 'anthropic':
            self._init_anthropic_client()
        else:
            self._init_openai_client()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                f"请确保项目根目录存在 config.yaml 文件。\n"
                f"可以从 config.yaml.example 复制一份并修改配置。"
            )

        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _init_openai_client(self):
        """初始化 OpenAI 客户端"""
        from openai import OpenAI
        self.client = OpenAI(
            api_key=self.config['api']['api_key'],
            base_url=self.config['api'].get('base_url')
        )

    def _init_anthropic_client(self):
        """初始化 Anthropic 客户端"""
        from anthropic import Anthropic
        self.client = Anthropic(
            api_key=self.config['api']['api_key']
        )

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求

        Args:
            message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            tools: 工具定义列表（OpenAI Function Calling 格式）

        Returns:
            如果没有工具调用：返回字符串（兼容旧代码）
            如果有工具调用：返回字典 {
                "type": "tool_call",
                "tool_name": str,
                "tool_params": dict,
                "call_id": str
            }
            如果是普通响应：返回字典 {
                "type": "text",
                "content": str
            }
        """
        if self.protocol == 'anthropic':
            return self._chat_anthropic(message, system_prompt, temperature, max_tokens, model, tools)
        else:
            return self._chat_openai(message, system_prompt, temperature, max_tokens, model, tools)

    def chat_with_messages(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """
        多轮对话（支持工具调用）

        Args:
            messages: 消息列表，格式为 OpenAI messages 格式
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            tools: 工具定义列表
            tool_choice: 工具选择策略 ("auto", "none", 或具体工具名)

        Returns:
            返回字典包含：
            - finish_reason: 结束原因 ("stop", "tool_calls", "length")
            - content: 文本内容（如果有）
            - tool_calls: 工具调用列表（如果有）
        """
        # 规范化消息格式，确保 tool 角色的消息格式正确
        normalized_messages = []
        for msg in messages:
            normalized_msg = {"role": msg["role"]}

            # 确保 content 字段存在
            if "content" in msg:
                normalized_msg["content"] = msg["content"] if msg["content"] is not None else ""
            elif msg["role"] == "tool":
                # tool 角色必须有 content 字段
                normalized_msg["content"] = msg.get("content", "")

            # 保留其他字段（如 tool_calls, tool_call_id, name）
            for key in msg:
                if key not in ["role", "content"]:
                    normalized_msg[key] = msg[key]

            normalized_messages.append(normalized_msg)

        request_params = {
            "model": model or self.config['api']['model'],
            "messages": normalized_messages,
            "temperature": temperature or self.config['api']['temperature'],
            "max_tokens": max_tokens or self.config['api']['max_tokens']
        }

        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**request_params)
        choice = response.choices[0]

        result: Dict[str, Any] = {
            "finish_reason": choice.finish_reason,
            "content": choice.message.content
        }

        # 如果有工具调用
        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in choice.message.tool_calls
            ]

        return result

    def _chat_openai(
        self,
        message: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Union[str, Dict[str, Any]]:
        """OpenAI 协议的聊天请求（支持工具调用）"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        # 构建请求参数
        request_params = {
            "model": model or self.config['api']['model'],
            "messages": messages,
            "temperature": temperature or self.config['api']['temperature'],
            "max_tokens": max_tokens or self.config['api']['max_tokens']
        }

        # 如果提供了工具定义，添加到请求中
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"  # 让模型自动决定是否调用工具

        response = self.client.chat.completions.create(**request_params)

        choice = response.choices[0]

        # 检查是否有工具调用
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]

            # 解析工具参数，处理可能的格式问题
            try:
                tool_params = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                # 如果解析失败，尝试清理格式（去除多余的 {} 等）
                args_str = tool_call.function.arguments.strip()
                # 如果以 }{} 开头，说明有重复的括号
                if args_str.startswith('}{'):
                    args_str = args_str[1:]  # 去掉第一个 }
                elif args_str.startswith('{}'):
                    args_str = args_str[2:]  # 去掉前面的 {}
                tool_params = json.loads(args_str)

            return {
                "type": "tool_call",
                "tool_name": tool_call.function.name,
                "tool_params": tool_params,
                "call_id": tool_call.id
            }
        else:
            # 普通文本响应（兼容旧代码）
            content = choice.message.content or ""
            # 如果调用时没有传 tools，返回字符串（完全兼容旧代码）
            if tools is None:
                return content
            # 如果传了 tools，返回结构化响应
            return {
                "type": "text",
                "content": content
            }

    def _chat_anthropic(
        self,
        message: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Anthropic 协议的聊天请求（支持工具调用）"""
        kwargs = {
            "model": model or self.config['api']['model'],
            "max_tokens": max_tokens or self.config['api']['max_tokens'],
            "messages": [{"role": "user", "content": message}]
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if temperature is not None:
            kwargs["temperature"] = temperature
        elif self.config['api'].get('temperature') is not None:
            kwargs["temperature"] = self.config['api']['temperature']

        # 如果提供了工具定义，添加到请求中
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)  # type: ignore[attr-defined]

        # 如果没有传 tools，返回纯文本（兼容旧代码）
        if tools is None:
            return response.content[0].text

        # 检查是否有工具调用
        if hasattr(response, 'stop_reason') and response.stop_reason == 'tool_use':
            # 找到工具调用的 content block
            tool_use = None
            for block in response.content:
                if block.type == 'tool_use':
                    tool_use = block
                    break

            if tool_use:
                return {
                    "type": "tool_call",
                    "tool_name": tool_use.name,
                    "tool_params": tool_use.input,
                    "call_id": tool_use.id
                }

        # 普通文本响应
        return {
            "type": "text",
            "content": response.content[0].text
        }

    def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ):
        """
        流式发送聊天请求

        Args:
            message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称

        Yields:
            模型响应的文本片段
        """
        if self.protocol == 'anthropic':
            yield from self._stream_anthropic(message, system_prompt, temperature, max_tokens, model)
        else:
            yield from self._stream_openai(message, system_prompt, temperature, max_tokens, model)

    def _stream_openai(
        self,
        message: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        model: Optional[str]
    ):
        """OpenAI 协议的流式聊天"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        stream = self.client.chat.completions.create(
            model=model or self.config['api']['model'],
            messages=messages,
            temperature=temperature or self.config['api']['temperature'],
            max_tokens=max_tokens or self.config['api']['max_tokens'],
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_anthropic(
        self,
        message: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        model: Optional[str]
    ):
        """Anthropic 协议的流式聊天"""
        kwargs = {
            "model": model or self.config['api']['model'],
            "max_tokens": max_tokens or self.config['api']['max_tokens'],
            "messages": [{"role": "user", "content": message}]
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if temperature is not None:
            kwargs["temperature"] = temperature
        elif self.config['api'].get('temperature') is not None:
            kwargs["temperature"] = self.config['api']['temperature']

        with self.client.messages.stream(**kwargs) as stream:  # type: ignore[attr-defined]
            for text in stream.text_stream:
                yield text
