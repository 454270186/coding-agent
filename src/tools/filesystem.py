"""
Filesystem tools for agent interactions.

Provides secure file operations within the workspace directory.
"""

from pathlib import Path
from typing import Dict, List
from langchain_core.tools import tool

from src.config.settings import get_settings


@tool
def create_file(path: str, content: str) -> Dict[str, any]:
    """
    在 workspace 中创建文件。

    Args:
        path: 相对于 workspace 的文件路径
        content: 文件内容

    Returns:
        结果字典，包含 success, message 和可选的 path
    """
    settings = get_settings()
    workspace = Path(settings.workspace_dir)
    full_path = (workspace / path).resolve()

    # 安全检查：确保路径在 workspace 内
    if not str(full_path).startswith(str(workspace)):
        return {
            "success": False,
            "message": f"Security error: Path outside workspace: {path}"
        }

    try:
        # 创建父目录
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        full_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "message": f"File created successfully: {path}",
            "path": str(full_path)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating file: {str(e)}"
        }


@tool
def read_file(path: str) -> Dict[str, any]:
    """
    读取 workspace 中的文件。

    Args:
        path: 相对于 workspace 的文件路径

    Returns:
        结果字典，包含 success, content/message
    """
    settings = get_settings()
    workspace = Path(settings.workspace_dir)
    full_path = (workspace / path).resolve()

    # 安全检查
    if not str(full_path).startswith(str(workspace)):
        return {
            "success": False,
            "message": "Security error: Path outside workspace"
        }

    try:
        content = full_path.read_text(encoding="utf-8")
        return {
            "success": True,
            "content": content,
            "path": str(full_path)
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": f"File not found: {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error reading file: {str(e)}"
        }


@tool
def list_files(directory: str = ".") -> Dict[str, any]:
    """
    列出 workspace 中指定目录的所有文件。

    Args:
        directory: 相对于 workspace 的目录路径，默认为根目录

    Returns:
        结果字典，包含 success, files 列表和 count
    """
    settings = get_settings()
    workspace = Path(settings.workspace_dir)
    full_path = (workspace / directory).resolve()

    # 安全检查
    if not str(full_path).startswith(str(workspace)):
        return {
            "success": False,
            "message": "Security error: Path outside workspace"
        }

    try:
        # 递归列出所有文件
        files = [
            str(f.relative_to(workspace))
            for f in full_path.rglob("*")
            if f.is_file()
        ]
        return {
            "success": True,
            "files": sorted(files),
            "count": len(files)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error listing files: {str(e)}"
        }


@tool
def delete_file(path: str) -> Dict[str, str]:
    """
    删除 workspace 中的文件。

    Args:
        path: 相对于 workspace 的文件路径

    Returns:
        结果字典，包含 success 和 message
    """
    settings = get_settings()
    workspace = Path(settings.workspace_dir)
    full_path = (workspace / path).resolve()

    # 安全检查
    if not str(full_path).startswith(str(workspace)):
        return {
            "success": False,
            "message": "Security error: Path outside workspace"
        }

    try:
        if not full_path.exists():
            return {
                "success": False,
                "message": f"File not found: {path}"
            }

        full_path.unlink()
        return {
            "success": True,
            "message": f"File deleted successfully: {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting file: {str(e)}"
        }
