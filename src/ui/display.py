"""
Configuration display module.

Displays configuration information in a formatted table.
"""

from rich.console import Console
from rich.table import Table

from src.config.settings import Settings


def mask_api_key(api_key: str, show_chars: int = 7) -> str:
    """
    Mask API key for display, showing only first and last few characters.

    Args:
        api_key: The API key to mask.
        show_chars: Number of characters to show at start and end.

    Returns:
        str: Masked API key string.
    """
    if len(api_key) <= show_chars * 2:
        return api_key[:3] + "..." + api_key[-3:]

    return api_key[:show_chars] + "..." + api_key[-show_chars:]


def display_config(settings: Settings, console: Console) -> None:
    """
    Display configuration in a formatted table.

    Args:
        settings: The settings object to display.
        console: Rich console for output.
    """
    table = Table(
        title="System Configuration",
        show_header=True,
        header_style="bold magenta",
        title_style="bold cyan",
    )

    table.add_column("Configuration", style="cyan", width=20)
    table.add_column("Value", style="green", width=40)

    # Add configuration rows
    table.add_row("API Provider", "OpenAI Compatible")
    table.add_row("Model", settings.openai_model)
    table.add_row("Base URL", settings.openai_base_url)
    table.add_row("API Key", mask_api_key(settings.openai_api_key))
    table.add_row("Workspace", settings.workspace_dir)
    table.add_row("Log Level", settings.log_level)
    table.add_row("Log File", settings.log_file)

    # Add agent-specific models if configured
    if settings.planner_model:
        table.add_row("Planner Model", settings.planner_model)
    if settings.coder_model:
        table.add_row("Coder Model", settings.coder_model)
    if settings.evaluator_model:
        table.add_row("Evaluator Model", settings.evaluator_model)

    # Add web search config if available
    if settings.brave_api_key:
        table.add_row(
            "Brave API Key",
            mask_api_key(settings.brave_api_key)
        )

    console.print()
    console.print(table)
    console.print()
