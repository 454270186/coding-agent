"""
LangGraph workflow assembly.

Creates and compiles the multi-agent workflow graph.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph.state import AgentState
from src.graph.routers import should_continue_coding, should_fix_code
from src.agents.planning_agent import planning_node
from src.agents.coding_agent import coding_node
from src.agents.evaluation_agent import evaluation_node
from src.agents.fix_agent import fix_node
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_workflow():
    """
    创建并编译 LangGraph 工作流。

    工作流结构：
    START → Planning → Coding (循环) → Evaluation → [Fix/End]
                           ↑                           ↓
                           └────── Fix (reset) ←───────┘

    Returns:
        编译后的工作流图
    """
    logger.info("Creating LangGraph workflow")

    # 初始化状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    logger.debug("Adding nodes: planning, coding, evaluation, fix")
    workflow.add_node("planning", planning_node)
    workflow.add_node("coding", coding_node)
    workflow.add_node("evaluation", evaluation_node)
    workflow.add_node("fix", fix_node)

    # 添加边
    logger.debug("Adding edges and conditional edges")

    # START → Planning
    workflow.add_edge(START, "planning")

    # Planning → Coding
    workflow.add_edge("planning", "coding")

    # Coding → ? (条件边：继续编码 或 评估)
    workflow.add_conditional_edges(
        "coding",
        should_continue_coding,
        {
            "code_next": "coding",      # 继续下一个任务
            "evaluate": "evaluation"     # 所有任务完成，评估
        }
    )

    # Evaluation → ? (条件边：修复、成功结束 或 失败结束)
    workflow.add_conditional_edges(
        "evaluation",
        should_fix_code,
        {
            "fix": "fix",             # 进入修复节点
            "end_success": END,       # 成功完成
            "end_failed": END         # 失败（超过最大迭代）
        }
    )

    # Fix → Coding（重置状态后重新编码）
    workflow.add_edge("fix", "coding")

    # 配置检查点（用于持久化和调试）
    # TODO: Fix checkpointer initialization
    logger.debug("Compiling workflow without checkpointer (temporary)")

    # 编译图（暂时不使用 checkpointer）
    logger.info("Compiling workflow graph")
    app = workflow.compile()

    logger.info("Workflow created successfully")
    return app
