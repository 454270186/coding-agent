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

EVALUATION_PROMPT = """You are a code reviewer. Your task is to evaluate whether the generated code meets requirements and detect technical integration errors.

**Original Requirements:**
{task_description}

**Task List:**
{subtasks}

**Generated Files:**
{generated_files}

**File Contents (for checking integration issues):**
{file_contents}

**Syntax Check Results:**
{syntax_results}

Please evaluate from the following aspects:

## Part 1: Technical Integration Checks (Critical - Must Pass)

Carefully check the following common technical integration errors. **These are fatal issues that prevent code from running**:

1. **ES6 Module Errors**:
   - ✓ Check: If JS files use `import`/`export`, HTML `<script>` tags must have `type="module"` attribute

2. **HTML and CSS Selector Matching**:
   - ✓ Check: If HTML uses `class="xxx"`, CSS should use `.xxx`; if HTML uses `id="xxx"`, CSS should use `#xxx`

3. **File Reference Paths**:
   - ✓ Check: Whether CSS/JS file paths referenced in HTML match the actual generated file paths

4. **JavaScript Function Calls**:
   - ✓ Check: Whether function call parameter types and counts match the function definition

5. **DOM Element References**:
   - ✓ Check: Whether elements retrieved by ID/class in JS exist in HTML

6. **Necessary Rendering Functions**:
   - ✓ Check: If there is game logic or dynamic content, there must be rendering functions to display data on the page

7. **No Runtime API Calls (Critical)**:
   - ✓ Check: JavaScript code should NOT contain runtime fetch(), XMLHttpRequest, or axios API calls
   - ✓ Check: Data should be embedded as static JavaScript constants (e.g., const STATIC_DATA = <data>)
   - ✓ Check: Static data should contain sufficient items (at least 10+ items, not just 1-2 samples)
   - ✓ Check: No placeholder comments like "// More entries..." - all data should be present
   - ❌ Wrong example: fetch('http://api.example.com/data').then(...) or const DATA = <two items>, // More entries...
   - ✓ Correct example: const STATIC_DATA = <20+ complete items>; // Use STATIC_DATA directly
   - ✓ Reason: Runtime API calls cause CORS errors; static data approach eliminates this issue

8. **JavaScript Loading Timing (Critical)**:
   - ✓ Check: When HTML `<script>` tags reference external JS files, they must satisfy one of the following:
     a) Use `defer` attribute: `<script src="..." defer></script>` (Recommended)
     b) Place `<script>` tag before the closing `</body>` tag
     c) Wrap all DOM operations in JS code with DOMContentLoaded event
   - ✓ Check: Ensure DOM operations in JS code (getElementById, addEventListener, etc.) execute after elements exist
   - ❌ Wrong example: Using `<script src="app.js"></script>` in `<head>` without defer
   - ✓ Correct example: `<script src="app.js" defer></script>` or placing at body bottom
   - ✓ Reason: Otherwise getElementById/querySelector returns null, causing "Cannot read properties of null" runtime error

9. **Page Navigation Completeness (Important)**:
   - ✓ Check: If project has multiple HTML pages, verify bidirectional navigation exists
   - ✓ Check: List pages should link to detail pages (e.g., click on item to view details)
   - ✓ Check: Detail pages should link back to list/home pages (e.g., back button or navigation bar)
   - ✓ Check: Navigation bar (if exists) should include links to all major pages
   - ❌ Wrong example: paperDetail.html links to index.html, but index.html has no way to reach paperDetail.html
   - ✓ Correct example: index.html displays paper list with clickable links to paperDetail.html, and paperDetail.html has back button to index.html

## Part 2: Functionality and Quality Evaluation

10. **Core Functionality**: Basically implements the main features in the requirements
11. **Syntax Correctness**: Code has no obvious syntax errors
12. **File Completeness**: Has necessary HTML/CSS/JS files
13. **Basic Usability**: Code logic is generally reasonable
14. **UI Quality**: Whether the interface is beautiful and modern, whether the layout is reasonable, whether there are sufficient styles

**Evaluation Principles (Important):**
- **Technical errors in Part 1 must be reported**: Any integration error will cause code to fail, and must be clearly stated in issues
- **Provide specific fix suggestions**: Don't just say "there's a problem", point out which file and which line needs how to be modified
- **Filenames don't matter**: As long as file reference relationships are correct, different filenames are okay
- **UI Criteria**: If CSS is too simple (less than 20 lines) or lacks basic styles (color, spacing, layout), mark as fail
- **Lenient on functionality**: Only mark as fail on obvious defects

For each task, please return evaluation results:

```json
{{
  "results": [
    {{
      "task_id": "task_1",
      "passed": true/false,
      "issues": ["Issue description 1", "Issue description 2"],
      "suggestions": ["Fix suggestion 1", "Fix suggestion 2"]
    }}
  ],
  "overall_passed": true/false,
  "summary": "Overall evaluation summary"
}}
```

Please return JSON directly without additional explanatory text.
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
