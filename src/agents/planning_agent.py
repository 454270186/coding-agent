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

PLANNING_PROMPT = """You are a senior software architect. Your task is to analyze user requirements, design system architecture, and decompose requirements into executable subtasks.

User Requirements:
{task_description}

Please complete the planning following these steps:

1. **Understand Requirements**: Carefully analyze the user's core requirements and constraints, focus only on explicitly mentioned features
2. **Architecture Design**: Design system architecture based on actual requirements, don't add unrequested features
3. **Technology Selection**: For frontend, use native HTML + CSS + JS
4. **Task Decomposition**: Decompose requirements into 2-5 functional module-level subtasks

**Important Rules:**
- Each subtask should be a complete functional module (e.g., "User Interface Components", "Data Display Layer", "Interaction Logic", etc.)
- One subtask may contain multiple files (HTML, CSS, JS, etc.)
- Clearly mark dependency relationships between tasks
- If external data is needed, note that the Coding Agent will fetch real API data during code generation (20-50 items minimum) and embed it as static data (no runtime fetch() calls)
- **No Mock Data**: Unless explicitly specified by user, do NOT use mock/fake data. Real data will be fetched via API and embedded statically with sufficient quantity
- **Navigation Bar Required**: If the project has multiple pages, MUST include a navigation bar for page switching
- **UI Design Requirements**: Interface should be beautiful and modern, focus on user experience, use reasonable colors, spacing, and layout
- Design should consider scalability and maintainability
- Keep architecture simple, avoid over-design
- **Strictly follow user requirements, don't speculate or add extra features**

Please return the planning results in JSON format with the following fields:

```json
{{
  "architecture_plan": "Detailed description of architecture design",
  "technology_stack": {{
    "frontend": "Technology stack name",
    "styling": "CSS solution",
    "data": "Data acquisition method"
  }},
  "subtasks": [
    {{
      "id": "task_1",
      "title": "Task title",
      "description": "Detailed description",
      "files_to_create": ["index.html", "styles/main.css", "js/app.js"],
      "dependencies": [],
      "status": "pending"
    }}
  ]
}}
```

Please return JSON directly without additional explanatory text.
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
        logger.debug("=" * 80)
        logger.debug("PLANNING AGENT - INPUT PROMPT:")
        logger.debug("=" * 80)
        logger.debug(prompt)
        logger.debug("=" * 80)

        logger.debug("Planning Agent: Invoking LLM")
        response = llm.invoke(messages)

        logger.debug("=" * 80)
        logger.debug("PLANNING AGENT - RAW RESPONSE:")
        logger.debug("=" * 80)
        logger.debug(response.content)
        logger.debug("=" * 80)

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
