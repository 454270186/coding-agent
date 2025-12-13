"""
Evaluation Agent implementation.

Reviews generated code for quality, syntax, and functionality.
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.graph.state import AgentState
from src.config.settings import get_settings
from src.utils.logger import get_logger
from src.tools.execution import run_syntax_check

logger = get_logger(__name__)

EVALUATION_PROMPT = """你是一个代码审查员。你的任务是评估生成的代码是否满足需求。

**原始需求：**
{task_description}

**任务列表：**
{subtasks}

**生成的文件：**
{generated_files}

**语法检查结果：**
{syntax_results}

请从以下方面评估：

1. **核心功能**：基本实现了需求中的主要功能
2. **语法正确性**：代码没有明显的语法错误
3. **文件结构**：有必要的HTML/CSS/JS文件
4. **基本可用性**：代码逻辑基本合理
5. **UI质量**：界面是否美观、现代化，布局是否合理，是否有足够的样式

**评估原则（重要）：**
- **文件名不重要**：只要文件引用关系正确，文件名不同没关系
- **关注功能和UI**：核心功能能用，UI要基本美观
- **UI评判标准**：如果CSS过于简单（少于20行）或者没有基本样式（颜色、间距、布局），判定为不合格
- **宽松评判**：语法检查通过、有合理样式的代码，默认为合格
- **只在明显缺陷时才判定失败**：如缺少关键文件、功能完全不对、语法错误、UI过于简陋等

对于每个任务，请返回评估结果：

```json
{{
  "results": [
    {{
      "task_id": "task_1",
      "passed": true/false,
      "issues": ["问题描述1", "问题描述2"],
      "suggestions": ["修复建议1", "修复建议2"]
    }}
  ],
  "overall_passed": true/false,
  "summary": "整体评估总结"
}}
```

请直接返回 JSON，不要添加额外的说明文字。
"""


def evaluation_node(state: AgentState) -> dict:
    """
    Evaluation Agent 节点。

    评估生成的代码质量和功能完整性。

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    logger.info("Evaluation Agent: Starting code evaluation")

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.get_evaluator_model(),
        temperature=0.1,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key
    )

    # 运行语法检查
    syntax_results = {}
    if state.get("generated_files"):
        logger.debug(f"Evaluation Agent: Running syntax checks on {len(state['generated_files'])} files")
        for file_path in state["generated_files"].keys():
            try:
                result = run_syntax_check.invoke({"file_path": file_path})
                syntax_results[file_path] = result
                if not result.get("success"):
                    logger.warning(f"Evaluation Agent: Syntax check failed for {file_path}: {result.get('message')}")
            except Exception as e:
                logger.error(f"Evaluation Agent: Error checking {file_path}: {str(e)}")
                syntax_results[file_path] = {
                    "success": False,
                    "message": f"Check error: {str(e)}"
                }

    # 准备任务信息
    subtasks_info = [
        {
            "id": t["id"],
            "title": t["title"],
            "status": t["status"],
            "files": t["files_to_create"]
        }
        for t in state.get("subtasks", [])
    ]

    # 准备文件列表
    files_list = list(state.get("generated_files", {}).keys())

    # 构建提示
    prompt = EVALUATION_PROMPT.format(
        task_description=state["task_description"],
        subtasks=json.dumps(subtasks_info, indent=2, ensure_ascii=False),
        generated_files=json.dumps(files_list, indent=2, ensure_ascii=False),
        syntax_results=json.dumps(syntax_results, indent=2, ensure_ascii=False)
    )

    messages = [
        SystemMessage(content="You are a thorough code reviewer."),
        HumanMessage(content=prompt)
    ]

    try:
        # 调用 LLM
        logger.debug("Evaluation Agent: Invoking LLM")
        response = llm.invoke(messages)
        logger.debug(f"Evaluation Agent: Received response ({len(response.content)} chars)")

        # 解析响应
        content = response.content

        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        overall_passed = result.get("overall_passed", False)
        logger.info(f"Evaluation Agent: Overall result: {'PASSED' if overall_passed else 'FAILED'}")
        logger.info(f"Evaluation Agent: {result.get('summary', 'No summary')}")

        # 统计问题数量
        total_issues = sum(len(r.get("issues", [])) for r in result.get("results", []))
        if total_issues > 0:
            logger.warning(f"Evaluation Agent: Found {total_issues} issues")

        return {
            "evaluation_results": result.get("results", []),
            "current_phase": "evaluation",
            "is_success": overall_passed,
            "final_message": result.get("summary", "Evaluation completed"),
            "generated_files": state.get("generated_files", {}),  # 保留生成的文件列表
            "messages": [response]
        }

    except json.JSONDecodeError as e:
        logger.error(f"Evaluation Agent: JSON parsing failed: {str(e)}")
        logger.error(f"Evaluation Agent: Raw content: {response.content[:500] if 'response' in locals() else 'N/A'}...")

        return {
            "evaluation_results": [],
            "current_phase": "evaluation",
            "is_success": False,
            "final_message": f"Evaluation failed: Invalid JSON response. {str(e)}",
            "messages": [response] if 'response' in locals() else []
        }

    except Exception as e:
        logger.error(f"Evaluation Agent: Unexpected error: {str(e)}")

        return {
            "evaluation_results": [],
            "current_phase": "evaluation",
            "is_success": False,
            "final_message": f"Evaluation failed: {str(e)}",
            "messages": []
        }
