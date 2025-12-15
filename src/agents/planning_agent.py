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

PLANNING_PROMPT = """You are a senior software architect. Your task is to analyze user requirements, design a simple and practical system architecture, and decompose them into executable subtasks.

User Requirements:
{task_description}

Please follow these steps:

1. **Understand Requirements**: Strictly focus on explicitly stated requirements and constraints. Do NOT add unrequested features.
2. **Architecture Design**: Keep it simple, scalable, and maintainable. Avoid over-engineering.
3. **Technology Selection**:
   - Frontend: Native HTML + CSS + JavaScript (no frameworks unless requested).
   - If external APIs are involved and there is risk of CORS issues in browser, design a lightweight backend proxy (Flask or FastAPI).
   - If the external API supports CORS or the project is simple, frontend can call APIs directly.
4. **Task Decomposition**: Break down into 2-5 functional module-level subtasks.
   - Each subtask can contain multiple files.
   - Clearly indicate dependencies between subtasks.
   - If the project involves multiple pages, include a navigation bar unless explicitly not needed.
   - If displaying lists of items (e.g., papers, products), include both list and detail views ONLY if it meaningfully improves user experience or is explicitly required.

**Key Rules**:
- Prioritize real data from external APIs. Use mock data ONLY if explicitly allowed by the user or if the API is unreliable/unavailable.
- UI must be modern, clean, responsive, with good spacing, colors, and interactive feedback.
- Strictly follow user requirements — do not speculate or add extra functionality.

Return ONLY valid JSON in this format:

{{
  "architecture_plan": "Detailed but concise architecture description",
  "technology_stack": {{
    "frontend": "HTML/CSS/JS",
    "styling": "Pure CSS (or Tailwind if requested)",
    "backend": "None / Flask / FastAPI (with reason)",
    "data": "Direct API calls or backend proxy (with reason)"
  }},
  "subtasks": [
    {{
      "id": "task_1",
      "title": "Clear task title",
      "description": "Detailed description of what this subtask achieves",
      "files_to_create": ["index.html", "styles/main.css", "js/app.js"],
      "dependencies": [],
      "status": "pending"
    }}
  ]
}}
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
        temperature=0.1,  # Lower temperature for more consistent planning
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
