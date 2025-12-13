"""
State definitions for the LangGraph workflow.

Defines the global state structure and related data models.
"""

from typing import TypedDict, Annotated, List, Dict, Optional
import operator
from langchain_core.messages import BaseMessage


class SubTask(TypedDict):
    """子任务结构"""
    id: str                     # 任务 ID
    title: str                  # 任务标题
    description: str            # 详细描述
    files_to_create: List[str]  # 需要创建的文件列表
    dependencies: List[str]     # 依赖的任务 ID 列表
    status: str                 # "pending" | "in_progress" | "completed" | "failed"
    error: Optional[str]        # 错误信息（如果失败）


class FileContent(TypedDict):
    """文件内容结构"""
    path: str          # 相对于 workspace 的路径
    content: str       # 文件内容
    language: str      # 文件类型/语言
    created_at: str    # 创建时间


class EvaluationResult(TypedDict):
    """评估结果结构"""
    task_id: str                # 任务 ID
    passed: bool                # 是否通过
    issues: List[str]           # 发现的问题列表
    suggestions: List[str]      # 修复建议列表
    test_output: Optional[str]  # 测试输出


class AgentState(TypedDict):
    """
    全局状态定义。

    这是整个 LangGraph 工作流的中心状态结构，所有节点都可以访问和更新。
    """
    # ===== 输入 =====
    task_description: str                           # 用户输入的任务描述

    # ===== Planning 阶段产出 =====
    architecture_plan: str                          # 架构设计说明
    technology_stack: Dict[str, str]               # 技术栈选择
    subtasks: List[SubTask]                        # 分解的子任务列表

    # ===== Coding 阶段产出 =====
    generated_files: Dict[str, FileContent]        # 文件路径 -> 文件内容映射
    current_task_index: int                        # 当前执行的任务索引

    # ===== Evaluation 阶段产出 =====
    evaluation_results: List[EvaluationResult]     # 评估结果列表

    # ===== 控制流 =====
    current_phase: str                             # 当前阶段：planning | coding | evaluation | fixing | completed
    iteration_count: int                           # 当前迭代次数
    max_iterations: int                            # 最大迭代次数（默认 3）

    # ===== 消息历史 =====
    # 使用 Annotated 和 operator.add 确保消息追加而非替换
    messages: Annotated[List[BaseMessage], operator.add]

    # ===== 全局状态标记 =====
    is_success: bool                               # 是否成功完成
    final_message: str                             # 最终消息（成功或失败的总结）
