"""
调用轨迹管理器

功能：
1. 限制工具调用次数（最多 2 次）
2. 记录完整调用轨迹
3. 保存到文件供审计使用
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRecord:
    """单次工具调用记录"""
    timestamp: str
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any
    success: bool
    error_message: Optional[str] = None


@dataclass
class TraceRecord:
    """完整调用轨迹"""
    trace_id: str
    timestamp: str
    user_input: str
    tool_calls: List[ToolCallRecord]
    final_answer: Optional[Dict[str, Any]]
    status: str  # "success", "insufficient_evidence", "error"
    error_message: Optional[str] = None
    total_tool_calls: int = 0
    max_tool_calls_reached: bool = False


class TraceManager:
    """轨迹管理器"""

    MAX_TOOL_CALLS = 2  # 最大工具调用次数

    def __init__(self, trace_dir: str = "traces"):
        """
        初始化轨迹管理器

        Args:
            trace_dir: 轨迹保存目录
        """
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(exist_ok=True)

        # 当前会话状态
        self.current_trace: Optional[TraceRecord] = None
        self.tool_call_count = 0

    def start_trace(self, user_input: str) -> str:
        """
        开始新的调用轨迹

        Args:
            user_input: 用户输入

        Returns:
            trace_id: 轨迹 ID
        """
        trace_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        self.current_trace = TraceRecord(
            trace_id=trace_id,
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            tool_calls=[],
            final_answer=None,
            status="in_progress",
            total_tool_calls=0
        )

        self.tool_call_count = 0

        logger.info(f"开始轨迹记录: {trace_id}")
        return trace_id

    def can_call_tool(self) -> bool:
        """
        检查是否还能调用工具

        Returns:
            bool: True 表示可以调用，False 表示已达上限
        """
        return self.tool_call_count < self.MAX_TOOL_CALLS

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """
        记录工具调用

        Args:
            tool_name: 工具名称
            tool_input: 工具输入
            tool_output: 工具输出
            success: 是否成功
            error_message: 错误信息

        Returns:
            bool: True 表示记录成功，False 表示已达上限
        """
        if not self.current_trace:
            raise RuntimeError("未开始轨迹记录，请先调用 start_trace()")

        if not self.can_call_tool():
            logger.warning(f"已达最大工具调用次数限制: {self.MAX_TOOL_CALLS}")
            self.current_trace.max_tool_calls_reached = True
            return False

        record = ToolCallRecord(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            success=success,
            error_message=error_message
        )

        self.current_trace.tool_calls.append(record)
        self.tool_call_count += 1
        self.current_trace.total_tool_calls = self.tool_call_count

        logger.info(f"记录工具调用 [{self.tool_call_count}/{self.MAX_TOOL_CALLS}]: {tool_name}")

        return True

    def finish_trace(
        self,
        final_answer: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """
        结束轨迹记录并保存

        Args:
            final_answer: 最终答案
            status: 状态 ("success", "insufficient_evidence", "error")
            error_message: 错误信息

        Returns:
            str: 保存的文件路径
        """
        if not self.current_trace:
            raise RuntimeError("未开始轨迹记录，请先调用 start_trace()")

        self.current_trace.final_answer = final_answer
        self.current_trace.status = status
        self.current_trace.error_message = error_message

        # 保存到文件
        filepath = self.trace_dir / f"trace_{self.current_trace.trace_id}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"轨迹保存完成: {filepath}")

        # 重置状态
        trace_id = self.current_trace.trace_id
        self.current_trace = None
        self.tool_call_count = 0

        return str(filepath)

    def _to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        if not self.current_trace:
            return {}

        return {
            "trace_id": self.current_trace.trace_id,
            "timestamp": self.current_trace.timestamp,
            "user_input": self.current_trace.user_input,
            "tool_calls": [
                {
                    "timestamp": tc.timestamp,
                    "tool_name": tc.tool_name,
                    "tool_input": tc.tool_input,
                    "tool_output": tc.tool_output,
                    "success": tc.success,
                    "error_message": tc.error_message
                }
                for tc in self.current_trace.tool_calls
            ],
            "final_answer": self.current_trace.final_answer,
            "status": self.current_trace.status,
            "error_message": self.current_trace.error_message,
            "total_tool_calls": self.current_trace.total_tool_calls,
            "max_tool_calls_reached": self.current_trace.max_tool_calls_reached,
            "max_tool_calls_limit": self.MAX_TOOL_CALLS
        }

    def get_summary(self) -> str:
        """
        获取当前轨迹摘要

        Returns:
            str: 轨迹摘要
        """
        if not self.current_trace:
            return "无活跃轨迹"

        return f"""
轨迹 ID: {self.current_trace.trace_id}
用户输入: {self.current_trace.user_input[:50]}...
工具调用次数: {self.tool_call_count}/{self.MAX_TOOL_CALLS}
状态: {self.current_trace.status}
        """.strip()
