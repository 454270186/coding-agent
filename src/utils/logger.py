"""
Logging configuration module.

Sets up logging with Rich handlers for beautiful console output
and file output for persistent logs.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from src.config.settings import get_settings


def setup_logger(
    name: str = "code_agent",
    force_level: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure a logger with Rich handler.

    Args:
        name: Name of the logger.
        force_level: Force a specific log level (overrides settings).

    Returns:
        logging.Logger: Configured logger instance.
    """
    settings = get_settings()
    log_level = force_level or settings.log_level

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Logger 本身设置为 DEBUG，让 handler 来过滤

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console handler with Rich
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=False,
        console=Console(stderr=True),
    )
    console_handler.setLevel(log_level)  # 使用配置的级别（默认 INFO）
    console_format = logging.Formatter(
        "%(message)s",
        datefmt="[%X]"
    )
    console_handler.setFormatter(console_format)

    # File handler - 始终使用 DEBUG 级别以记录详细日志
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # 文件始终记录 DEBUG 级别
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "code_agent") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Name of the logger.

    Returns:
        logging.Logger: Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
