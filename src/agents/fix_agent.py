"""
Fix Agent implementation.

Analyzes evaluation results and creates targeted modification tasks for files with issues.
"""

from src.graph.state import AgentState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def fix_node(state: AgentState) -> dict:
    """
    Fix Agent 节点。

    分析评估结果，按文件组织问题，创建修改任务而非重新生成。

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    iteration = state.get("iteration_count", 0)
    logger.info(f"Fix Agent: Starting fix iteration {iteration + 1}")

    # 分析 evaluation_results，按文件组织 issues
    issues_by_file = {}
    evaluation_results = state.get("evaluation_results", [])

    logger.debug(f"Fix Agent: Analyzing {len(evaluation_results)} evaluation results")

    for eval_result in evaluation_results:
        if not eval_result.get("passed"):
            task_id = eval_result.get("task_id")
            issues = eval_result.get("issues", [])
            suggestions = eval_result.get("suggestions", [])

            logger.debug(f"Fix Agent: Task {task_id} failed with {len(issues)} issues")

            # 找到该任务对应的子任务
            task = next((t for t in state.get("subtasks", []) if t["id"] == task_id), None)

            if task:
                # 为该任务创建的每个文件收集问题
                for file_path in task.get("files_to_create", []):
                    if file_path not in issues_by_file:
                        issues_by_file[file_path] = {
                            "issues": [],
                            "suggestions": []
                        }
                    issues_by_file[file_path]["issues"].extend(issues)
                    issues_by_file[file_path]["suggestions"].extend(suggestions)
                    logger.debug(f"Fix Agent: Collected issues for {file_path}")
            else:
                logger.warning(f"Fix Agent: Could not find task with id {task_id}")
                logger.warning(f"Fix Agent: Available task IDs in state: {[t['id'] for t in state.get('subtasks', [])]}")
                logger.warning(f"Fix Agent: This usually means the evaluation agent returned a wrong task_id.")
                logger.warning(f"Fix Agent: Check if evaluation agent is using the ACTUAL task IDs from subtasks.")

    if not issues_by_file:
        logger.warning("Fix Agent: No files with issues found")
        return {
            "current_phase": "completed",
            "is_success": False,
            "final_message": "No files to fix"
        }

    # 创建修改任务
    modification_tasks = []
    generated_files = state.get("generated_files", {})

    for i, (file_path, problems) in enumerate(issues_by_file.items()):
        # Skip data files that don't exist in generated_files
        # These are files that were referenced but never created (e.g., LLM hallucinated the filename)
        if file_path.startswith("data/") and file_path not in generated_files:
            logger.warning(f"Fix Agent: Skipping non-existent data file {file_path} - cannot modify a file that doesn't exist")
            logger.warning(f"Fix Agent: This likely means the LLM referenced a data file that was never created. Issues: {problems['issues'][:2]}")
            continue

        # For non-data files, also check if they exist
        if file_path not in generated_files:
            logger.warning(f"Fix Agent: Skipping non-existent file {file_path} - file was never created")
            continue

        modification_task = {
            "id": f"fix_{iteration}_{i}",
            "title": f"修复 {file_path}",
            "description": f"根据评估反馈修改 {file_path}",
            "files_to_create": [file_path],
            "dependencies": [],
            "status": "pending",
            "is_modification": True,  # 标记为修改模式
            "target_file": file_path,
            "issues": problems["issues"],
            "suggestions": problems["suggestions"]
        }
        modification_tasks.append(modification_task)
        logger.info(f"Fix Agent: Created modification task for {file_path} with {len(problems['issues'])} issues")

    if not modification_tasks:
        logger.warning("Fix Agent: No valid files to fix (all files were non-existent or data files)")
        return {
            "current_phase": "completed",
            "is_success": False,
            "final_message": "No valid files to fix - referenced files don't exist"
        }

    logger.info(f"Fix Agent: Created {len(modification_tasks)} modification tasks")

    return {
        "subtasks": modification_tasks,
        "current_task_index": 0,
        "iteration_count": iteration + 1,
        "current_phase": "fixing"
    }
