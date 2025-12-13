"""
Fix Agent implementation.

Resets state and prepares for the next iteration when issues are found.
"""

from src.graph.state import AgentState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def fix_node(state: AgentState) -> dict:
    """
    Fix Agent 节点。

    当评估发现问题时，重置状态以便重新执行任务。

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    iteration = state.get("iteration_count", 0)

    logger.info(f"Fix Agent: Starting fix iteration {iteration + 1}")
    logger.debug(f"Fix Agent: Resetting current_task_index to 0")

    # 重置任务索引，准备重新执行
    # 增加迭代计数
    # 更新 subtasks 状态为 pending（让它们可以重新执行）
    subtasks = list(state.get("subtasks", []))
    for i, task in enumerate(subtasks):
        if task.get("status") != "completed":
            subtasks[i] = {**task, "status": "pending"}

    return {
        "current_task_index": 0,
        "iteration_count": iteration + 1,
        "current_phase": "fixing",
        "subtasks": subtasks
    }
