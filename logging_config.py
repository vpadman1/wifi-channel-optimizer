"""Centralized logging configuration using loguru.

Console: WARNING+ by default, INFO+ with --verbose.
File: ~/.config/wifi-channel-optimizer/wifi-monitor.log, rotation 1 MB, level DEBUG.
"""
from __future__ import annotations
import sys
from pathlib import Path
from loguru import logger

CONFIG_DIR = Path.home() / ".config" / "wifi-channel-optimizer"
LOG_FILE = CONFIG_DIR / "wifi-monitor.log"


def configure_logging(verbose: bool = False) -> None:
    logger.remove()
    console_level = "INFO" if verbose else "WARNING"
    logger.add(
        sys.stderr,
        level=console_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan> — <level>{message}</level>",
    )
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_FILE,
        level="DEBUG",
        rotation="1 MB",
        retention=3,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
    )


__all__ = ["logger", "configure_logging", "LOG_FILE"]
