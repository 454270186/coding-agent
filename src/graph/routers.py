"""
Router functions for conditional edges in the workflow.

Determines the next node to execute based on the current state.
"""

from src.graph.state import AgentState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def should_continue_coding(state: AgentState) -> str:
    """
    判断是否继续执行下一个编码任务。

    如果还有待处理的任务，继续编码；否则进入评估阶段。

    Args:
        state: 当前状态

    Returns:
        路由目标：'code_next' 或 'evaluate'
    """
    current_index = state.get("current_task_index", 0)
    total_tasks = len(state.get("subtasks", []))

    logger.debug(f"Router: Coding progress {current_index}/{total_tasks}")

    if current_index >= total_tasks:
        logger.info("Router: All coding tasks completed, moving to evaluation")
        return "evaluate"

    logger.info(f"Router: Continuing with next coding task ({current_index + 1}/{total_tasks})")
    return "code_next"


def should_fix_code(state: AgentState) -> str:
    """
    判断是否需要修复代码。

    根据评估结果和迭代次数决定：
    - 有问题且未超过最大迭代次数：修复
    - 没有问题或已通过：成功结束
    - 超过最大迭代次数：失败结束

    Args:
        state: 当前状态

    Returns:
        路由目标：'fix', 'end_success', 或 'end_failed'
    """
    results = state.get("evaluation_results", [])
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)

    logger.debug(f"Router: Evaluation check - iteration {iteration}/{max_iter}")

    # 检查是否有失败的评估
    has_issues = any(not r.get("passed", True) for r in results)
    total_issues = sum(len(r.get("issues", [])) for r in results)

    logger.debug(f"Router: Has issues: {has_issues}, Total issues: {total_issues}")

    # 超过最大迭代次数
    if iteration >= max_iter:
        if has_issues:
            logger.warning(f"Router: Max iterations ({max_iter}) reached with issues, ending as failed")
            return "end_failed"
        else:
            logger.info(f"Router: Max iterations ({max_iter}) reached but no issues, ending as success")
            return "end_success"

    # 有问题需要修复
    if has_issues:
        logger.info(f"Router: Issues found, starting fix iteration {iteration + 1}/{max_iter}")
        return "fix"

    # 通过所有检查
    logger.info("Router: All checks passed, ending as success")
    return "end_success"
