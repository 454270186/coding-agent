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


CODING_PROMPT = """You are a professional full-stack software engineer.

**User Requirements**: {user_requirement}
**Architecture Plan**: {architecture_plan}
**Technology Stack**: {technology_stack}
**All Subtasks Status**: {all_subtasks_status}

**Current Task**: {current_task_index}/{total_tasks} — {task_title}
**Task Description**: {task_description}
**Files to Create/Modify**: {files_to_create}
**Existing Files (reference only)**: {existing_files}

**Requirements**:
1. Fully understand the overall context from user requirements and completed subtasks.
2. Reuse existing code, styles, and components whenever possible.
3. Write complete, runnable, clean code following modern best practices.
4. UI: Modern, responsive (flexbox/grid), good color scheme, spacing, hover effects, and transitions.
5. Data handling:
   - Prefer real data from external APIs.
   - If architecture specifies a backend proxy, implement it (Flask/FastAPI) with proper CORS enabled.
   - If direct frontend calls are allowed, use them.
   - ONLY use mock data if explicitly permitted in requirements.
6. Backend (if needed):
   - Simple structure, use requests to fetch real data.
   - Enable CORS properly (Flask: CORS(app, resources={{"/*": {{"origins": "*"}}}}) ).
   - Include requirements.txt with necessary dependencies.
   - Run on host='0.0.0.0', port=5000 (or similar).
7. JavaScript best practices:
   - Use <script defer> for external scripts OR place scripts at end of <body>.
   - Add null checks for DOM elements when necessary.
   - Ensure DOM operations run after page load.
8. Navigation: If multiple pages exist, include consistent navigation bar with links.
9. List/Detail pages: Implement both only if specified in plan.

**Output Format** (pure JSON, no extra text):
{{
  "files": [
    {{
      "path": "path/to/file.html",
      "content": "Complete file content..."
    }}
  ]
}}
"""


MODIFICATION_PROMPT = """You are an expert code fixer.

**User Requirements**: {user_requirement}
**Architecture Plan**: {architecture_plan}
**File to Fix**: {file_path}
**Current Content**: {current_content}

**Issues**: {issues}
**Suggestions**: {suggestions}
**Other Files Summary**: {other_files_summary}

**Tasks**:
1. Make minimal, targeted changes to fix only the reported issues.
2. Preserve existing style and structure.
3. Ensure compatibility with other files.
4. Key fixes to consider:
   - Add defer to script tags or move to body end.
   - Add null checks for DOM elements.
   - Correct paths/selectors.
   - Properly configure CORS if backend exists.
   - Remove mock data unless explicitly allowed; implement real API calls.
   - Ensure consistent field names between backend response and frontend usage.

**Output** (pure JSON):
{{
  "files": [
    {{
      "path": "{{file_path}}",
      "content": "Full modified file content..."
    }}
  ]
}}
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
        temperature=0.1,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key
    )

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

        # Invoke LLM
        response = llm.invoke(messages)

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
