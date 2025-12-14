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
    Supports multi-line input for pasting long text.

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
        "\nYou can paste multi-line text or type multiple lines.\n",
        style="dim"
    )
    instructions.append(
        "Press Ctrl+D (Unix/Mac) or Ctrl+Z+Enter (Windows) when done.\n",
        style="dim italic"
    )
    instructions.append(
        "Press Ctrl+C to cancel.\n",
        style="dim italic"
    )

    console.print(instructions)
    console.print()
    console.print("[bold green]Task Description:[/bold green]", end=" ")

    try:
        # Get multi-line input
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                # User pressed Ctrl+D, finish input
                break

        # Join lines and validate
        task = "\n".join(lines).strip()
        if not task:
            console.print("\n[red]Error: Task description cannot be empty.[/red]")
            return None

        return task

    except KeyboardInterrupt:
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
