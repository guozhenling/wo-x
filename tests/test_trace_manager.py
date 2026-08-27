#!/usr/bin/env python3
"""
测试 TraceManager - 轨迹管理器

验证：
1. 工具调用次数限制（最多 2 次）
2. 轨迹记录完整性
3. 文件保存功能
"""

import sys
import json
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from trace_manager import TraceManager, ToolCallRecord


class TestTraceManager:
    """TraceManager 测试类"""

    def setup_method(self):
        """每个测试前初始化"""
        self.test_trace_dir = "test_traces"
        self.manager = TraceManager(trace_dir=self.test_trace_dir)

    def teardown_method(self):
        """每个测试后清理"""
        # 清理测试目录
        if Path(self.test_trace_dir).exists():
            shutil.rmtree(self.test_trace_dir)

    # ==================== 基础功能测试 ====================

    def test_start_trace(self):
        """测试开始轨迹记录"""
        trace_id = self.manager.start_trace("测试输入")

        assert trace_id is not None
        assert self.manager.current_trace is not None
        assert self.manager.current_trace.user_input == "测试输入"
        assert self.manager.tool_call_count == 0

    def test_can_call_tool_initial(self):
        """测试初始状态可以调用工具"""
        self.manager.start_trace("测试")
        assert self.manager.can_call_tool() is True

    def test_record_tool_call(self):
        """测试记录工具调用"""
        self.manager.start_trace("测试")

        result = self.manager.record_tool_call(
            tool_name="test_tool",
            tool_input={"param": "value"},
            tool_output="result",
            success=True
        )

        assert result is True
        assert self.manager.tool_call_count == 1
        assert len(self.manager.current_trace.tool_calls) == 1
        assert self.manager.current_trace.tool_calls[0].tool_name == "test_tool"

    # ==================== 调用次数限制测试 ====================

    def test_max_tool_calls_limit(self):
        """测试最大调用次数限制（10次）"""
        self.manager.start_trace("测试")

        # 调用 10 次 - 全部成功
        for i in range(10):
            result = self.manager.record_tool_call(
                tool_name=f"tool{i+1}",
                tool_input={},
                tool_output=f"result{i+1}"
            )
            assert result is True

        # 第 10 次后应该不能再调用
        assert self.manager.can_call_tool() is False

        # 第 11 次调用 - 失败
        result11 = self.manager.record_tool_call(
            tool_name="tool11",
            tool_input={},
            tool_output="result11"
        )
        assert result11 is False
        assert self.manager.tool_call_count == 10  # 仍然是 10
        assert self.manager.current_trace.max_tool_calls_reached is True

    def test_tool_call_count_increment(self):
        """测试工具调用计数器递增"""
        self.manager.start_trace("测试")

        assert self.manager.tool_call_count == 0

        self.manager.record_tool_call("tool1", {}, "result1")
        assert self.manager.tool_call_count == 1

        self.manager.record_tool_call("tool2", {}, "result2")
        assert self.manager.tool_call_count == 2

    # ==================== 轨迹保存测试 ====================

    def test_finish_trace_success(self):
        """测试成功完成轨迹"""
        self.manager.start_trace("测试输入")
        self.manager.record_tool_call("tool1", {"param": "value"}, "result")

        final_answer = {"severity": "P0", "category": "availability"}
        filepath = self.manager.finish_trace(
            final_answer=final_answer,
            status="success"
        )

        # 验证文件存在
        assert Path(filepath).exists()

        # 验证文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["user_input"] == "测试输入"
        assert data["status"] == "success"
        assert data["final_answer"] == final_answer
        assert data["total_tool_calls"] == 1
        assert len(data["tool_calls"]) == 1

    def test_finish_trace_insufficient_evidence(self):
        """测试证据不足状态"""
        self.manager.start_trace("测试")
        self.manager.record_tool_call("tool1", {}, "result1")
        self.manager.record_tool_call("tool2", {}, "result2")

        filepath = self.manager.finish_trace(
            status="insufficient_evidence",
            error_message="已达最大工具调用次数"
        )

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["status"] == "insufficient_evidence"
        assert data["error_message"] == "已达最大工具调用次数"
        assert data["total_tool_calls"] == 2

    def test_finish_trace_error(self):
        """测试错误状态"""
        self.manager.start_trace("测试")

        filepath = self.manager.finish_trace(
            status="error",
            error_message="分类失败"
        )

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["status"] == "error"
        assert data["error_message"] == "分类失败"

    def test_trace_reset_after_finish(self):
        """测试完成后状态重置"""
        self.manager.start_trace("测试")
        self.manager.record_tool_call("tool1", {}, "result")
        self.manager.finish_trace(status="success")

        # 验证状态已重置
        assert self.manager.current_trace is None
        assert self.manager.tool_call_count == 0

    # ==================== 错误处理测试 ====================

    def test_record_without_start_raises_error(self):
        """测试未开始轨迹就记录会报错"""
        with pytest.raises(RuntimeError, match="未开始轨迹记录"):
            self.manager.record_tool_call("tool", {}, "result")

    def test_finish_without_start_raises_error(self):
        """测试未开始轨迹就完成会报错"""
        with pytest.raises(RuntimeError, match="未开始轨迹记录"):
            self.manager.finish_trace()

    # ==================== 完整流程测试 ====================

    def test_complete_workflow(self):
        """测试完整工作流"""
        # 1. 开始
        trace_id = self.manager.start_trace("支付接口错误率 35%")

        # 2. 第一次工具调用 - LLM
        self.manager.record_tool_call(
            tool_name="llm_chat",
            tool_input={"prompt": "分类故障"},
            tool_output='{"severity":"P0","category":"availability","needs_human_review":false}',
            success=True
        )

        # 3. 第二次工具调用 - Policy 修正
        self.manager.record_tool_call(
            tool_name="policy_engine",
            tool_input={"original": {"needs_human_review": False}},
            tool_output={"corrected": {"needs_human_review": True}},
            success=True
        )

        # 4. 完成
        final_answer = {
            "severity": "P0",
            "category": "availability",
            "needs_human_review": True
        }
        filepath = self.manager.finish_trace(
            final_answer=final_answer,
            status="success"
        )

        # 验证保存的数据
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["user_input"] == "支付接口错误率 35%"
        assert data["total_tool_calls"] == 2
        assert data["tool_calls"][0]["tool_name"] == "llm_chat"
        assert data["tool_calls"][1]["tool_name"] == "policy_engine"
        assert data["final_answer"] == final_answer
        assert data["status"] == "success"
        assert data["max_tool_calls_limit"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
