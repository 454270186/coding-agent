"""
Main entry point for the Coding Agent System.

This module initializes the system and handles the main control flow.
"""

import sys
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config.settings import get_settings
from src.utils.logger import setup_logger
from src.ui.welcome import display_welcome, display_system_info
from src.ui.display import display_config
from src.ui.input import get_task_input, display_task_confirmation
from src.graph.workflow import create_workflow


def main() -> int:
    """
    Main application entry point.

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    console = Console()

    try:
        # Load configuration
        console.print("[dim]Loading configuration...[/dim]")
        settings = get_settings()

        # Setup logging
        logger = setup_logger()
        logger.info("Coding Agent System starting...")

        # Display welcome screen
        display_welcome(console)

        # Display system information
        display_system_info(console)

        # Display configuration
        display_config(settings, console)

        console.print("[bold green]Configuration loaded successfully![/bold green]")
        console.print()

        # Separator
        console.rule(style="dim")

        # Get task input from user
        task = get_task_input(console)

        if task is None:
            console.print("[yellow]No task provided. Exiting.[/yellow]")
            logger.info("Application terminated: no task provided")
            return 0

        # Display confirmation
        display_task_confirmation(task, console)

        # Log the task
        logger.info(f"Task received: {task}")

        # ====== Phase 2: 启动 LangGraph 工作流 ======
        console.print("\n[bold cyan]Starting code generation workflow...[/bold cyan]\n")

        # 创建工作流
        logger.info("Creating workflow")
        workflow = create_workflow()

        # 初始化状态
        initial_state = {
            "task_description": task,
            "architecture_plan": "",
            "technology_stack": {},
            "subtasks": [],
            "generated_files": {},
            "current_task_index": 0,
            "evaluation_results": [],
            "current_phase": "planning",
            "iteration_count": 0,
            "max_iterations": 3,
            "messages": [],
            "is_success": False,
            "final_message": ""
        }

        # 执行工作流
        session_id = f"session-{int(datetime.now().timestamp())}"
        config = {"configurable": {"thread_id": session_id}}

        logger.info(f"Starting workflow execution (session: {session_id})")

        try:
            # 使用 Progress 显示实时进度
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task_progress = progress.add_task("[green]Agents are working...", total=None)

                # 流式执行工作流
                for output in workflow.stream(initial_state, config=config):
                    for node_name, node_output in output.items():
                        phase = node_output.get("current_phase", node_name)

                        # 显示进度
                        if node_name == "planning":
                            progress.update(task_progress, description="[cyan]Planning: Analyzing requirements...")
                        elif node_name == "coding":
                            task_idx = node_output.get("current_task_index", 0)
                            total_tasks = len(node_output.get("subtasks", []))
                            progress.update(task_progress, description=f"[yellow]Coding: Task {task_idx}/{total_tasks}...")
                        elif node_name == "evaluation":
                            progress.update(task_progress, description="[magenta]Evaluating: Checking code quality...")
                        elif node_name == "fix":
                            iteration = node_output.get("iteration_count", 0)
                            progress.update(task_progress, description=f"[red]Fixing: Iteration {iteration}...")

                        logger.debug(f"Node '{node_name}' completed, phase: {phase}")

            # 获取最终状态
            # Note: Without checkpointer, we need to track state manually
            # For now, we'll use the last output
            final_state = {}
            for output in [output]:  # Get last output
                for node_name, node_output in output.items():
                    final_state = node_output

            # 显示结果
            console.print()
            console.rule("[bold]Workflow Results[/bold]")
            console.print()

            if final_state.get("is_success"):
                console.print("[bold green]✓ Code generation completed successfully![/bold green]")
                console.print()
                console.print(f"[bold]Summary:[/bold] {final_state.get('final_message', 'No message')}")
                console.print()

                # 显示生成的文件列表
                files = list(final_state.get("generated_files", {}).keys())
                if files:
                    console.print(f"[bold]Generated {len(files)} files:[/bold]")
                    for f in sorted(files):
                        console.print(f"  [green]✓[/green] {f}")
                    console.print()
                    console.print(f"[dim]Files saved to: {settings.workspace_dir}[/dim]")
                else:
                    console.print("[yellow]No files were generated.[/yellow]")

            else:
                console.print("[bold red]✗ Code generation failed[/bold red]")
                console.print()
                console.print(f"[bold]Error:[/bold] {final_state.get('final_message', 'Unknown error')}")
                console.print()

                # 显示评估结果（如果有）
                eval_results = final_state.get("evaluation_results", [])
                if eval_results:
                    console.print("[bold]Issues found:[/bold]")
                    for result in eval_results:
                        if not result.get("passed"):
                            console.print(f"\n[yellow]Task: {result.get('task_id')}[/yellow]")
                            for issue in result.get("issues", []):
                                console.print(f"  • {issue}")

            console.print()
            logger.info("Workflow completed")
            return 0 if final_state.get("is_success") else 1

        except Exception as workflow_error:
            console.print(f"\n[bold red]Workflow Error:[/bold red] {str(workflow_error)}")
            logger.error(f"Workflow execution failed: {str(workflow_error)}")
            if "--debug" in sys.argv:
                console.print_exception()
            return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user.[/yellow]")
        return 0

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        if "--debug" in sys.argv:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
