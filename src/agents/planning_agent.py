"""
Planning Agent implementation.

Analyzes user requirements and creates a structured implementation plan.
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.graph.state import AgentState
from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

PLANNING_PROMPT = """你是一个资深软件架构师。你的任务是分析用户需求，设计系统架构，并将需求分解为可执行的子任务。

用户需求：
{task_description}

请按以下步骤完成规划：

1. **理解需求**：仔细分析用户的核心需求和约束，只关注明确提到的功能
2. **架构设计**：基于实际需求设计系统架构，不要添加未要求的功能
3. **技术选型**：前端选原生html+css+js
4. **任务分解**：将需求分解为2-5个功能模块级别的子任务

**重要规则：**
- 每个子任务应该是一个完整的功能模块（如"用户界面组件"、"数据展示层"、"交互逻辑"等）
- 一个子任务可能包含多个文件（HTML, CSS, JS等）
- 明确标注任务之间的依赖关系
- 如果需要外部数据，根据需求选择合适的API或数据源
- **UI设计要求**：界面要美观、现代化，注重用户体验，使用合理的颜色、间距和布局
- 设计要考虑可扩展性和维护性
- 保持架构简洁，避免过度设计
- **严格按照用户需求，不要臆测或添加额外功能**

请以 JSON 格式返回规划结果，包含以下字段：

```json
{{
  "architecture_plan": "架构设计的详细说明",
  "technology_stack": {{
    "frontend": "技术栈名称",
    "styling": "CSS 方案",
    "data": "数据获取方式"
  }},
  "subtasks": [
    {{
      "id": "task_1",
      "title": "任务标题",
      "description": "详细描述",
      "files_to_create": ["index.html", "styles/main.css", "js/app.js"],
      "dependencies": [],
      "status": "pending"
    }}
  ]
}}
```

请直接返回 JSON，不要添加额外的说明文字。
"""


def planning_node(state: AgentState) -> dict:
    """
    Planning Agent 节点。

    分析用户需求，设计架构，分解任务。

    Args:
        state: 当前状态

    Returns:
        状态更新字典
    """
    logger.info("Planning Agent: Starting task analysis")

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.get_planner_model(),
        temperature=0.3,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key
    )

    # 构建提示
    prompt = PLANNING_PROMPT.format(
        task_description=state["task_description"]
    )

    messages = [
        SystemMessage(content="You are a software architect specializing in web development."),
        HumanMessage(content=prompt)
    ]

    try:
        # 调用 LLM
        logger.debug("Planning Agent: Invoking LLM")
        response = llm.invoke(messages)
        logger.debug(f"Planning Agent: Received response ({len(response.content)} chars)")

        # 解析响应
        content = response.content

        # 提取 JSON（可能在 markdown 代码块中）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())

        logger.info(f"Planning Agent: Created {len(result['subtasks'])} subtasks")
        logger.debug(f"Planning Agent: Architecture: {result['architecture_plan'][:100]}...")

        return {
            "architecture_plan": result["architecture_plan"],
            "technology_stack": result["technology_stack"],
            "subtasks": result["subtasks"],
            "current_phase": "coding",
            "current_task_index": 0,
            "messages": [response]
        }

    except json.JSONDecodeError as e:
        logger.error(f"Planning Agent: JSON parsing failed: {str(e)}")
        logger.error(f"Planning Agent: Raw content: {response.content[:500]}...")
        return {
            "current_phase": "completed",
            "is_success": False,
            "final_message": f"Planning failed: Invalid JSON response from LLM. {str(e)}",
            "messages": [response]
        }

    except Exception as e:
        logger.error(f"Planning Agent: Unexpected error: {str(e)}")
        return {
            "current_phase": "completed",
            "is_success": False,
            "final_message": f"Planning failed: {str(e)}",
            "messages": []
        }
