"""
Coding Agent implementation.

Generates code based on task specifications and creates files.
"""

import json
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.graph.state import AgentState
from src.config.settings import get_settings
from src.utils.logger import get_logger
from src.tools.filesystem import create_file
from src.tools.api_fetch import fetch_api_data

logger = get_logger(__name__)


def extract_file_summary(file_path: str, content: str, language: str) -> str:
    """
    智能提取文件摘要。

    Args:
        file_path: 文件路径
        content: 文件内容
        language: 文件类型

    Returns:
        文件摘要字符串
    """
    lines = content.split("\n")

    if language == "html":
        # 提取关键 HTML 标签
        imports = []
        for line in lines:
            line_lower = line.lower().strip()
            if '<link' in line_lower and 'href=' in line_lower:
                imports.append(line.strip())
            elif '<script' in line_lower and 'src=' in line_lower:
                imports.append(line.strip())

        summary = f"HTML 文件 (共 {len(lines)} 行)\n"
        if imports:
            summary += "引用:\n  " + "\n  ".join(imports[:5])
        return summary

    elif language == "css":
        # 提取 CSS 选择器
        selectors = []
        for line in lines:
            line = line.strip()
            if line and ('{' in line or line.endswith(',')):
                selector = line.split('{')[0].strip().rstrip(',')
                if selector and not selector.startswith('/*'):
                    selectors.append(selector)

        summary = f"CSS 文件 (共 {len(lines)} 行)\n"
        if selectors:
            summary += "主要选择器:\n  " + "\n  ".join(selectors[:10])
        return summary

    elif language in ["js", "javascript"]:
        # 提取函数定义和导入导出
        functions = []
        imports = []
        exports = []

        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('function ') or ' function ' in line_stripped:
                func_name = line_stripped.split('function')[1].split('(')[0].strip()
                functions.append(f"function {func_name}()")
            elif line_stripped.startswith('const ') and '=>' in line_stripped:
                func_name = line_stripped.split('const')[1].split('=')[0].strip()
                functions.append(f"const {func_name}")
            elif 'import ' in line_stripped:
                imports.append(line_stripped)
            elif 'export ' in line_stripped:
                exports.append(line_stripped)

        summary = f"JavaScript 文件 (共 {len(lines)} 行)\n"
        if imports:
            summary += "Imports:\n  " + "\n  ".join(imports[:3]) + "\n"
        if functions:
            summary += "函数:\n  " + "\n  ".join(functions[:5]) + "\n"
        if exports:
            summary += "Exports:\n  " + "\n  ".join(exports[:3])
        return summary

    else:
        # 默认：显示前 10 行
        preview = "\n".join(lines[:10])
        if len(lines) > 10:
            preview += f"\n... (共 {len(lines)} 行)"
        return preview


def format_existing_files(generated_files: dict) -> str:
    """
    格式化已有文件信息，使用智能摘要。

    Args:
        generated_files: 已生成的文件字典

    Returns:
        格式化后的文件信息字符串
    """
    if not generated_files:
        return "无"

    sections = []
    for path, info in generated_files.items():
        content = info.get("content", "")
        language = info.get("language", "")

        summary = extract_file_summary(path, content, language)

        section = f"📄 {path}\n{summary}"
        sections.append(section)

    return "\n\n".join(sections)


def format_subtasks_status(subtasks: list, current_index: int) -> str:
    """
    格式化子任务状态列表。

    Args:
        subtasks: 所有子任务列表
        current_index: 当前任务索引

    Returns:
        格式化的任务状态字符串
    """
    lines = []

    for i, task in enumerate(subtasks):
        # 状态标记
        if i < current_index:
            status = "[✓]"
            status_text = "已完成"
        elif i == current_index:
            status = "[→]"
            status_text = "正在进行 ← 你现在的任务"
        else:
            status = "[ ]"
            status_text = "待处理"

        # 任务信息
        line = f"{i+1}. {status} {task['title']} ({status_text})"
        lines.append(line)

        # 文件列表
        files = task.get("files_to_create", [])
        if files:
            lines.append(f"   文件: {', '.join(files)}")

    return "\n".join(lines)


CODING_PROMPT = """You are a professional software engineer. Your task is to implement specific code based on requirements and architectural design.

**Complete User Requirements:**
{user_requirement}

**Overall Architecture Design:**
{architecture_plan}

**Technology Stack:**
{technology_stack}

**All Subtasks Progress (understand overall situation):**
{all_subtasks_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Current Task:**
Task {current_task_index}/{total_tasks}: {task_title}

**Task Description:**
{task_description}

**Files to Create:**
{files_to_create}

**Completed Files (for reference and reuse):**
{existing_files}

**Requirements:**
1. Carefully review the "Complete User Requirements" and "All Subtasks Progress" above to understand your task's position in the overall context
2. Review "Completed Files" to understand existing code and functionality, ensuring new code integrates correctly
3. Reuse existing styles, functions, and components - don't duplicate implementations
4. Ensure generated code coordinates consistently with existing files
5. Generate complete, runnable code for each file
6. Use modern, aesthetically pleasing design styles
7. Follow best practices (code standards, appropriate comments, clear structure)
8. **UI Design Requirements**:
   - Use modern, aesthetically pleasing design styles
   - Proper color schemes (can use gradients, shadows, etc.)
   - Adequate spacing and whitespace
   - Responsive layout (flexbox/grid)
   - Interactive feedback (hover effects, transition animations, etc.)
9. **Static Data Approach for External APIs (Important)**:
   - **Never use runtime fetch() or XMLHttpRequest in generated code** - this causes CORS errors
   - **Use the fetch_api_data tool** to retrieve API data during code generation
   - **Request sufficient data quantity**: When calling APIs, request 20-50 items minimum (e.g., max_results=50 for arXiv API)
   - **Embed ALL retrieved data** as JavaScript constants in your generated code - don't truncate or use placeholders like "// More entries..."
   - **Process and use static data** in your JavaScript logic
   - Example workflow:
     a) First, use fetch_api_data tool with sufficient quantity: fetch_api_data(url="http://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=50")
     b) Then embed the COMPLETE result as: const STATIC_DATA = <all fetched items>;
     c) Use STATIC_DATA in your code instead of runtime API calls
   - This eliminates CORS issues since data is fetched server-side during code generation
   - **Do NOT use placeholder comments** like "// More entries..." - embed all actual data
10. Consider basic error handling
11. Keep code concise and practical, avoid over-engineering
12. **No Mock Data**: Unless explicitly specified by user, do NOT use mock/fake data. Use fetch_api_data tool to get real data
13. **Navigation Bar Required**: If the project has multiple pages, MUST include a navigation bar for page switching in all HTML files
14. **Page Navigation Completeness**: Ensure bidirectional navigation between pages
   - List pages must have clickable links to detail pages (e.g., clicking paper title opens paperDetail.html?id=123)
   - Detail pages must have back links to list/home pages (e.g., back button or navigation bar link)
   - Navigation bar should include links to all major pages
15. **JavaScript and HTML Integration Best Practices (Important)**:
   - **Script Tag Loading**: When referencing JavaScript in HTML `<head>` or `<body>`, **must use `defer` attribute**
     - Correct example: `<script src="js/app.js" defer></script>`
     - Wrong example: `<script src="js/app.js"></script>` (missing defer)
   - **Reason**: defer ensures scripts execute after DOM is fully parsed, preventing getElementById/querySelector from returning null
   - **Alternative**: If defer cannot be used, place `<script>` tag before the closing `</body>` tag
   - **DOM Operation Safety**: Ensure all getElementById, querySelector, and other DOM operations execute after elements are loaded
   - **Null Checks**: Add null checks for DOM query results to avoid "Cannot read properties of null" errors
     - Example: `const btn = document.getElementById('btn'); if (btn) {{ btn.addEventListener(...) }}`

**Output Format:**
For each file, use the following JSON format:

```json
{{
  "files": [
    {{
      "path": "index.html",
      "content": "Complete file content..."
    }}
  ]
}}
```

Please return JSON directly without additional explanatory text. Ensure all file contents are complete and directly usable.
"""


MODIFICATION_PROMPT = """You are a code modification expert. Your task is to modify existing code based on evaluation feedback.

**Complete User Requirements:**
{user_requirement}

**Overall Architecture Design:**
{architecture_plan}

**Current File to Modify:**
File path: {file_path}

**Current Complete File Content:**
```
{current_content}
```

**Issues Found in Evaluation:**
{issues}

**Fix Suggestions:**
{suggestions}

**Other Related Files (for reference):**
{other_files_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Your Tasks:**
1. **Carefully read** the file content above to understand the existing implementation
2. **Locate issues**: Based on "Issues Found in Evaluation", find specific locations that need modification
3. **Minimize changes**: Only modify problematic parts, keep other parts unchanged
4. **Verify integration**: Ensure modified code remains compatible with other files (refer to "Other Related Files")

**Important Principles:**
- ⚠️ Don't rewrite the entire file, only modify problematic parts
- ⚠️ Keep code style consistent with the original file
- ⚠️ Preserve all correct code and functionality
- ⚠️ If the issue is "missing a feature", add it in appropriate location without deleting existing code
- ⚠️ Check if HTML `<script>` tags have `defer` attribute or are placed before `</body>`
- ⚠️ Ensure all DOM operation code doesn't execute before elements are loaded
- ⚠️ Add null checks for DOM query results (e.g., `if (element) {{ ... }}`)
- ⚠️ **Never use runtime fetch() or XMLHttpRequest** - replace with fetch_api_data tool and embed static data
- ⚠️ If CORS errors are mentioned in issues, convert runtime API calls to static data approach

**Output Format:**
Return modified complete file content (JSON format):
{{
  "files": [
    {{
      "path": "{file_path}",
      "content": "Modified complete file content..."
    }}
  ]
}}

Please return JSON directly without additional explanatory text.
"""


def coding_node(state: AgentState) -> dict:
    """
    Coding Agent 节点。

    根据任务描述生成代码并创建文件。

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    current_index = state["current_task_index"]

    # 检查是否还有任务要执行
    if current_index >= len(state["subtasks"]):
        logger.warning(f"Coding Agent: No more tasks (index {current_index} >= {len(state['subtasks'])})")
        return {}

    current_task = state["subtasks"][current_index]
    logger.info(f"Coding Agent: Processing task {current_index + 1}/{len(state['subtasks'])}: {current_task['title']}")

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.get_coder_model(),
        temperature=0.2,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key
    )

    # Bind the API fetch tool to allow fetching data during code generation
    llm_with_tools = llm.bind_tools([fetch_api_data])

    # 判断是否为修改模式
    is_modification = current_task.get("is_modification", False)

    # 构建提示
    if is_modification:
        # 修改模式：使用 MODIFICATION_PROMPT
        file_path = current_task.get("target_file")
        file_info = state["generated_files"].get(file_path, {})
        current_content = file_info.get("content", "")

        # 准备其他文件的摘要（排除当前文件）
        other_files = {k: v for k, v in state.get("generated_files", {}).items() if k != file_path}
        other_files_summary = format_existing_files(other_files)

        prompt = MODIFICATION_PROMPT.format(
            user_requirement=state.get("task_description", ""),
            architecture_plan=state.get("architecture_plan", "N/A"),
            file_path=file_path,
            current_content=current_content,
            issues="\n".join(current_task.get("issues", [])),
            suggestions="\n".join(current_task.get("suggestions", [])),
            other_files_summary=other_files_summary
        )
        logger.info(f"Coding Agent: Using MODIFICATION mode for {file_path}")
    else:
        # 生成模式：使用 CODING_PROMPT
        # 准备已有文件信息（使用智能摘要）
        existing_files_str = format_existing_files(state.get("generated_files", {}))

        # 准备子任务进度信息
        all_subtasks_status = format_subtasks_status(state.get("subtasks", []), current_index)

        prompt = CODING_PROMPT.format(
            user_requirement=state.get("task_description", ""),
            architecture_plan=state.get("architecture_plan", "N/A"),
            technology_stack=json.dumps(state.get("technology_stack", {}), indent=2, ensure_ascii=False),
            all_subtasks_status=all_subtasks_status,
            current_task_index=current_index + 1,
            total_tasks=len(state.get("subtasks", [])),
            task_title=current_task["title"],
            task_description=current_task["description"],
            files_to_create=", ".join(current_task["files_to_create"]),
            existing_files=existing_files_str
        )
        logger.info(f"Coding Agent: Using GENERATION mode for task {current_index + 1}/{len(state['subtasks'])}")

    messages = [
        SystemMessage(content="You are a professional software engineer specializing in web development."),
        HumanMessage(content=prompt)
    ]

    try:
        # 调用 LLM
        logger.debug("=" * 80)
        logger.debug(f"CODING AGENT - INPUT PROMPT (Task {current_index + 1}/{len(state['subtasks'])}):")
        logger.debug("=" * 80)
        logger.debug(prompt)
        logger.debug("=" * 80)

        logger.debug(f"Coding Agent: Invoking LLM for task '{current_task['title']}'")

        # Invoke LLM with tool binding - may result in tool calls
        response = llm_with_tools.invoke(messages)

        # Handle tool calls if present
        while hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"Coding Agent: LLM requested {len(response.tool_calls)} tool call(s)")

            # Execute each tool call
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('args', {})
                tool_id = tool_call.get('id', '')

                logger.info(f"Coding Agent: Executing tool '{tool_name}' with args: {tool_args}")

                # Execute the tool
                if tool_name == 'fetch_api_data':
                    tool_result = fetch_api_data.invoke(tool_args)
                    logger.debug(f"Coding Agent: Tool result: {str(tool_result)[:200]}...")

                    # Create tool message
                    from langchain_core.messages import ToolMessage
                    tool_messages.append(ToolMessage(
                        content=json.dumps(tool_result),
                        tool_call_id=tool_id
                    ))

            # Add tool results to messages and invoke again
            messages.append(response)
            messages.extend(tool_messages)

            logger.debug("Coding Agent: Invoking LLM again with tool results")
            response = llm_with_tools.invoke(messages)

        logger.debug("=" * 80)
        logger.debug(f"CODING AGENT - RAW RESPONSE (Task {current_index + 1}/{len(state['subtasks'])}):")
        logger.debug("=" * 80)
        logger.debug(response.content)
        logger.debug("=" * 80)

        logger.debug(f"Coding Agent: Received response ({len(response.content)} chars)")

        # 解析响应
        content = response.content

        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        # 创建文件
        generated_files = dict(state.get("generated_files", {}))
        success_count = 0
        failed_files = []

        for file_info in result["files"]:
            path = file_info["path"]
            file_content = file_info["content"]

            logger.debug(f"Coding Agent: Creating file {path}")

            # 调用文件系统工具
            create_result = create_file.invoke({"path": path, "content": file_content})

            if create_result["success"]:
                # 记录到 state
                generated_files[path] = {
                    "path": path,
                    "content": file_content,
                    "language": Path(path).suffix[1:] if Path(path).suffix else "txt",
                    "created_at": datetime.now().isoformat()
                }
                success_count += 1
                logger.info(f"Coding Agent: Created {path} successfully")
            else:
                failed_files.append(path)
                logger.error(f"Coding Agent: Failed to create {path}: {create_result['message']}")

        # 更新任务状态
        subtasks = list(state["subtasks"])
        if failed_files:
            subtasks[current_index] = {
                **subtasks[current_index],
                "status": "failed",
                "error": f"Failed to create files: {', '.join(failed_files)}"
            }
        else:
            subtasks[current_index] = {
                **subtasks[current_index],
                "status": "completed"
            }

        logger.info(f"Coding Agent: Task completed. Created {success_count}/{len(result['files'])} files")

        return {
            "generated_files": generated_files,
            "subtasks": subtasks,
            "current_task_index": current_index + 1,
            "messages": [response]
        }

    except json.JSONDecodeError as e:
        logger.error(f"Coding Agent: JSON parsing failed: {str(e)}")
        logger.error(f"Coding Agent: Raw content: {response.content[:500] if 'response' in locals() else 'N/A'}...")

        subtasks = list(state["subtasks"])
        subtasks[current_index] = {
            **subtasks[current_index],
            "status": "failed",
            "error": f"Invalid JSON response: {str(e)}"
        }

        return {
            "subtasks": subtasks,
            "current_task_index": current_index + 1,
            "messages": [response] if 'response' in locals() else []
        }

    except Exception as e:
        logger.error(f"Coding Agent: Unexpected error: {str(e)}")

        subtasks = list(state["subtasks"])
        subtasks[current_index] = {
            **subtasks[current_index],
            "status": "failed",
            "error": str(e)
        }

        return {
            "subtasks": subtasks,
            "current_task_index": current_index + 1,
            "messages": []
        }
