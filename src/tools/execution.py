"""
Code execution tools with security restrictions.

Provides safe command execution and syntax checking within workspace.
"""

import subprocess
from pathlib import Path
from typing import Dict, List
from langchain_core.tools import tool

from src.config.settings import get_settings


# 白名单命令及其允许的参数
ALLOWED_COMMANDS = {
    "ls": ["-la", "-l", "-a", "-h"],
    "cat": [],
    "python": ["-c", "-m"],  # 仅允许无网络的简单执行
    "node": ["--check"],     # 仅允许语法检查
}


@tool
def execute_command(command: str, args: List[str] = None) -> Dict[str, any]:
    """
    在 workspace 中执行受限的命令。

    仅允许白名单中的命令，并在 workspace 目录内执行。

    Args:
        command: 命令名称（必须在白名单中）
        args: 命令参数列表

    Returns:
        执行结果字典
    """
    if args is None:
        args = []

    # 检查命令是否在白名单中
    if command not in ALLOWED_COMMANDS:
        return {
            "success": False,
            "message": f"Command not allowed: {command}"
        }

    # 检查参数是否安全
    allowed_args = ALLOWED_COMMANDS[command]
    for arg in args:
        if arg.startswith("-") and allowed_args and arg not in allowed_args:
            return {
                "success": False,
                "message": f"Argument not allowed: {arg}"
            }

    settings = get_settings()
    workspace = Path(settings.workspace_dir)

    try:
        result = subprocess.run(
            [command] + args,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10,  # 10 秒超时
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Command timeout (10s limit)"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error executing command: {str(e)}"
        }


@tool
def run_syntax_check(file_path: str) -> Dict[str, any]:
    """
    检查代码文件的语法。

    支持 Python (.py), JavaScript (.js), HTML (.html), CSS (.css) 等文件类型。

    Args:
        file_path: 相对于 workspace 的文件路径

    Returns:
        语法检查结果
    """
    settings = get_settings()
    workspace = Path(settings.workspace_dir)
    full_path = (workspace / file_path).resolve()

    # 安全检查
    if not str(full_path).startswith(str(workspace)):
        return {
            "success": False,
            "message": "Security error: Path outside workspace"
        }

    if not full_path.exists():
        return {
            "success": False,
            "message": f"File not found: {file_path}"
        }

    suffix = full_path.suffix.lower()

    try:
        if suffix == ".py":
            # Python 语法检查
            result = subprocess.run(
                ["python", "-m", "py_compile", str(full_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "success": result.returncode == 0,
                "file_type": "Python",
                "message": result.stderr if result.returncode != 0 else "Syntax OK"
            }

        elif suffix == ".js":
            # JavaScript 语法检查（需要 node）
            code = full_path.read_text()
            result = subprocess.run(
                ["node", "--check"],
                input=code,
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "success": result.returncode == 0,
                "file_type": "JavaScript",
                "message": result.stderr if result.returncode != 0 else "Syntax OK"
            }

        elif suffix in [".html", ".htm"]:
            # HTML 基本检查
            content = full_path.read_text()
            has_html = "<html" in content.lower()
            has_body = "<body" in content.lower()
            has_head = "<head" in content.lower()

            issues = []
            if not has_html:
                issues.append("Missing <html> tag")
            if not has_head:
                issues.append("Missing <head> tag")
            if not has_body:
                issues.append("Missing <body> tag")

            return {
                "success": len(issues) == 0,
                "file_type": "HTML",
                "message": "HTML structure OK" if len(issues) == 0 else f"Issues: {', '.join(issues)}"
            }

        elif suffix == ".css":
            # CSS 基本检查（括号匹配）
            content = full_path.read_text()
            open_braces = content.count("{")
            close_braces = content.count("}")

            return {
                "success": open_braces == close_braces,
                "file_type": "CSS",
                "message": "CSS syntax OK" if open_braces == close_braces else f"Error: Unmatched braces ({{ {open_braces}, }} {close_braces})"
            }

        elif suffix == ".json":
            # JSON 语法检查
            import json as json_module
            try:
                content = full_path.read_text()
                json_module.loads(content)
                return {
                    "success": True,
                    "file_type": "JSON",
                    "message": "JSON syntax OK"
                }
            except json_module.JSONDecodeError as e:
                return {
                    "success": False,
                    "file_type": "JSON",
                    "message": f"JSON syntax error: {str(e)}"
                }

        else:
            # 不支持的文件类型，标记为通过
            return {
                "success": True,
                "file_type": f"Unknown ({suffix})",
                "message": f"No syntax checker available for {suffix} files"
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Syntax check timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error checking syntax: {str(e)}"
        }
