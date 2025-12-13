"""
Task input module.

Handles user input for task descriptions.
"""

from typing import Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text


def get_task_input(console: Console) -> Optional[str]:
    """
    Get task description from user input.

    Args:
        console: Rich console for output.

    Returns:
        Optional[str]: Task description, or None if user cancels.
    """
    console.print()
    console.rule("[bold cyan]Task Input")
    console.print()

    # Display instructions
    instructions = Text()
    instructions.append("Please describe your development task.\n", style="yellow")
    instructions.append(
        "Be as specific as possible. Include requirements, features, and constraints.\n",
        style="dim"
    )
    instructions.append(
        "Press Ctrl+C to cancel.\n",
        style="dim italic"
    )

    console.print(instructions)
    console.print()

    try:
        # Get single-line input
        task = Prompt.ask(
            "[bold green]Task Description",
            console=console
        )

        # Validate input
        task = task.strip()
        if not task:
            console.print("[red]Error: Task description cannot be empty.[/red]")
            return None

        return task

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Task input cancelled.[/yellow]")
        return None


def display_task_confirmation(task: str, console: Console) -> None:
    """
    Display the received task for confirmation.

    Args:
        task: The task description to display.
        console: Rich console for output.
    """
    console.print()
    console.rule("[bold cyan]Task Received")
    console.print()

    console.print("[bold]Task Description:[/bold]")
    console.print(f"[green]{task}[/green]")
    console.print()

    console.print("[bold green]Task received successfully![/bold green]")
    console.print()
