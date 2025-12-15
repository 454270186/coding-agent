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

EVALUATION_PROMPT = """You are an experienced code reviewer.

**Original Requirements**: {task_description}
**Subtasks**: {subtasks}
**Generated/Modified Files**: {generated_files}
**File Contents**: {file_contents}
**Syntax Check Results**: {syntax_results}

Evaluate focusing on two parts:

**Part 1: Critical Technical Issues (must report if present)**
1. Script loading: External JS must use defer OR be placed before </body> OR wrapped in DOMContentLoaded.
2. DOM element existence: JS references to getElementById/querySelector must correspond to actual HTML elements.
3. Path references: CSS/JS paths in HTML match actual files.
4. CORS handling: If backend proxy is used, CORS must be properly enabled; frontend must call local backend, not external directly.
5. Mock data: Hardcoded sample data used only if explicitly allowed.
6. Selector matching: CSS classes/IDs match HTML.
7. Module usage: If import/export used, script tag must have type="module".

**Part 2: Quality & Functionality**
- Core functionality matches requirements.
- UI is modern, responsive, and aesthetically pleasing (sufficient CSS, not too minimal).
- Code is clean, readable, with reasonable structure.
- Navigation and list/detail pages implemented as planned.

**Principles**:
- Report only real issues with specific file/line references.
- Provide concrete, minimal fix suggestions.
- Be lenient on non-critical styling variations.
- UI fails only if obviously ugly or unusable.

Return ONLY JSON:
{{
  "results": [
    {{
      "task_id": "<use EXACT id from subtasks list above>",
      "passed": true/false,
      "issues": ["Specific issue description with file reference"],
      "suggestions": ["Concrete fix suggestion"]
    }}
  ],
  "overall_passed": true/false,
  "summary": "Brief overall summary"
}}

**CRITICAL**: For task_id, you MUST use the EXACT "id" field from the **Subtasks** list provided above.
For example, if subtasks contains {{"id": "fix_0_0", ...}}, use "fix_0_0" as task_id (NOT "task_1" or any other value).
Evaluate EACH task in the subtasks list and return a result for each one.
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

    # 准备文件内容（用于检查集成问题）
    file_contents = {}
    for file_path, file_info in state.get("generated_files", {}).items():
        content = file_info.get("content", "")
        # 只显示前100行，避免prompt过长
        lines = content.split("\n")
        if len(lines) > 100:
            preview = "\n".join(lines[:100]) + f"\n... (省略 {len(lines) - 100} 行)"
        else:
            preview = content
        file_contents[file_path] = preview

    # 构建提示
    prompt = EVALUATION_PROMPT.format(
        task_description=state["task_description"],
        subtasks=json.dumps(subtasks_info, indent=2, ensure_ascii=False),
        generated_files=json.dumps(files_list, indent=2, ensure_ascii=False),
        file_contents=json.dumps(file_contents, indent=2, ensure_ascii=False),
        syntax_results=json.dumps(syntax_results, indent=2, ensure_ascii=False)
    )

    messages = [
        SystemMessage(content="You are a thorough code reviewer."),
        HumanMessage(content=prompt)
    ]

    try:
        # 调用 LLM
        logger.debug("=" * 80)
        logger.debug("EVALUATION AGENT - INPUT PROMPT:")
        logger.debug("=" * 80)
        logger.debug(prompt)
        logger.debug("=" * 80)

        logger.debug("Evaluation Agent: Invoking LLM")
        response = llm.invoke(messages)

        logger.debug("=" * 80)
        logger.debug("EVALUATION AGENT - RAW RESPONSE:")
        logger.debug("=" * 80)
        logger.debug(response.content)
        logger.debug("=" * 80)

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
