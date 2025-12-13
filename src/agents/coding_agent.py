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

CODING_PROMPT = """你是一个专业的软件工程师。你的任务是根据需求和架构设计实现具体的代码。

**当前任务：**
{task_title}

**任务描述：**
{task_description}

**需要创建的文件：**
{files_to_create}

**架构设计：**
{architecture_plan}

**技术栈：**
{technology_stack}

**已有文件（供参考）：**
{existing_files}

**要求：**
1. 为每个文件生成完整、可运行的代码
2. 遵循最佳实践（代码规范、注释适当、结构清晰）
3. **UI设计要求**：
   - 使用现代化、美观的设计风格
   - 合理的颜色搭配（可使用渐变、阴影等）
   - 充足的间距和留白
   - 响应式布局（flexbox/grid）
   - 交互反馈（hover效果、过渡动画等）
4. 确保代码之间的一致性和协调
5. 如果需要调用外部API，根据具体需求使用合适的端点和参数
6. 考虑基本的错误处理
7. 保持代码简洁实用，避免过度工程化
8. **只实现当前任务要求的功能，不要添加额外特性**

**输出格式：**
对于每个文件，使用以下 JSON 格式：

```json
{{
  "files": [
    {{
      "path": "index.html",
      "content": "文件完整内容..."
    }},
    {{
      "path": "styles/main.css",
      "content": "文件完整内容..."
    }}
  ]
}}
```

请直接返回 JSON，不要添加额外的说明文字。确保所有文件内容都是完整的、可直接使用的。
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

    # 准备已有文件信息
    existing_files_str = "无"
    if state.get("generated_files"):
        existing_files_str = "\n".join([
            f"- {path} ({info['language']})"
            for path, info in state["generated_files"].items()
        ])

    # 构建提示
    prompt = CODING_PROMPT.format(
        task_title=current_task["title"],
        task_description=current_task["description"],
        files_to_create=", ".join(current_task["files_to_create"]),
        architecture_plan=state.get("architecture_plan", "N/A"),
        technology_stack=json.dumps(state.get("technology_stack", {}), indent=2, ensure_ascii=False),
        existing_files=existing_files_str
    )

    messages = [
        SystemMessage(content="You are a professional software engineer specializing in web development."),
        HumanMessage(content=prompt)
    ]

    try:
        # 调用 LLM
        logger.debug(f"Coding Agent: Invoking LLM for task '{current_task['title']}'")
        response = llm.invoke(messages)
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
