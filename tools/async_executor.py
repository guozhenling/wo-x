"""
异步执行器

功能：
- 流式返回结果
- 后台任务执行
- 提升用户体验
"""
import asyncio
import uuid
from typing import Dict, Any, AsyncIterator, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    step: str
    result: Any
    timestamp: datetime
    error: Optional[str] = None


class AsyncExecutor:
    """异步执行器"""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    async def classify_stream(
        self,
        agent,
        incident_description: str
    ) -> AsyncIterator[TaskResult]:
        """
        流式返回分类结果

        Args:
            agent: Agent 实例
            incident_description: 故障描述

        Yields:
            TaskResult: 每个步骤的结果
        """
        task_id = str(uuid.uuid4())

        try:
            # 步骤 1: 初步分类
            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="initial_classification",
                result=None,
                timestamp=datetime.now()
            )

            initial_result = agent._initial_classify(incident_description)

            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="initial_classification",
                result=initial_result,
                timestamp=datetime.now()
            )

            # 步骤 2: 工具规划
            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="tool_planning",
                result=None,
                timestamp=datetime.now()
            )

            tool_plan = agent.coordinator.plan_tool_calls(
                incident_description,
                initial_result
            )

            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="tool_planning",
                result={"tools": [t["tool"] for t in tool_plan]},
                timestamp=datetime.now()
            )

            # 步骤 3: 工具执行
            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="tool_execution",
                result=None,
                timestamp=datetime.now()
            )

            tool_results = agent.coordinator.execute_tools(tool_plan)

            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="tool_execution",
                result={"count": len(tool_results)},
                timestamp=datetime.now()
            )

            # 步骤 4: 综合分析
            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                step="final_analysis",
                result=None,
                timestamp=datetime.now()
            )

            final_result = agent._comprehensive_analysis(
                incident_description,
                initial_result,
                tool_results
            )

            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                step="final_analysis",
                result=final_result,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"流式执行失败: {e}")
            yield TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                step="error",
                result=None,
                timestamp=datetime.now(),
                error=str(e)
            )

    def classify_async(
        self,
        agent,
        incident_description: str
    ) -> str:
        """
        异步分类，返回任务 ID

        Args:
            agent: Agent 实例
            incident_description: 故障描述

        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())

        self.tasks[task_id] = {
            "status": TaskStatus.PENDING,
            "description": incident_description,
            "result": None,
            "error": None,
            "created_at": datetime.now()
        }

        # 启动后台任务
        asyncio.create_task(self._execute_background(agent, task_id, incident_description))

        return task_id

    async def _execute_background(
        self,
        agent,
        task_id: str,
        incident_description: str
    ):
        """后台执行任务"""
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING
            self.tasks[task_id]["started_at"] = datetime.now()

            # 执行分析
            result = agent.analyze(incident_description)

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED
            self.tasks[task_id]["result"] = result
            self.tasks[task_id]["completed_at"] = datetime.now()

        except Exception as e:
            logger.error(f"后台任务失败 [{task_id}]: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED
            self.tasks[task_id]["error"] = str(e)
            self.tasks[task_id]["completed_at"] = datetime.now()

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务状态，如果任务不存在返回 None
        """
        return self.tasks.get(task_id)

    def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        获取任务结果

        Args:
            task_id: 任务 ID

        Returns:
            任务结果，如果任务未完成或不存在返回 None
        """
        task = self.tasks.get(task_id)
        if task and task["status"] == TaskStatus.COMPLETED:
            return task["result"]
        return None

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task["status"] in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task["status"] = TaskStatus.FAILED
                task["error"] = "Task cancelled by user"
                return True
        return False

    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """
        清理旧任务

        Args:
            max_age_seconds: 最大保留时间（秒）
        """
        now = datetime.now()
        to_remove = []

        for task_id, task in self.tasks.items():
            created_at = task["created_at"]
            age = (now - created_at).total_seconds()

            if age > max_age_seconds:
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]

        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个旧任务")
