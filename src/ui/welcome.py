"""
Welcome screen module.

Displays welcome banner and system information.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def display_welcome(console: Console) -> None:
    """
    Display welcome banner.

    Args:
        console: Rich console for output.
    """
    welcome_text = Text()
    welcome_text.append("Coding Agent System", style="bold cyan")
    welcome_text.append(" v0.1\n", style="dim")
    welcome_text.append("Multi-Agent Code Generation Platform", style="italic")

    panel = Panel(
        welcome_text,
        border_style="blue",
        padding=(1, 2),
    )

    console.print()
    console.print(panel, justify="center")
    console.print()


def display_system_info(console: Console) -> None:
    """
    Display system information.

    Args:
        console: Rich console for output.
    """
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    info_text = Text()
    info_text.append("Python Version: ", style="bold")
    info_text.append(f"{python_version}\n", style="green")
    info_text.append("Status: ", style="bold")
    info_text.append("Ready", style="green bold")

    console.print(info_text)
    console.print()
