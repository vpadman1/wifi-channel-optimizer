"""Centralized logging configuration using loguru.

Console: WARNING+ by default, INFO+ with --verbose.
File: ~/.config/wifi-channel-optimizer/wifi-monitor.log, rotation 1 MB, level DEBUG.
"""
from __future__ import annotations
import sys
from loguru import logger

from config_paths import CONFIG_DIR, secure_dir, secure_file

LOG_FILE = CONFIG_DIR / "wifi-monitor.log"


def configure_logging(verbose: bool = False) -> None:
    logger.remove()
    console_level = "INFO" if verbose else "WARNING"
    logger.add(
        sys.stderr,
        level=console_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan> — <level>{message}</level>",
    )
    # Restrict the config dir and log file to the current user. The log can
    # contain the router host, username, and error-body snippets — nothing
    # critical, but no reason to share it with every account on the machine.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    secure_dir(CONFIG_DIR)
    logger.add(
        LOG_FILE,
        level="DEBUG",
        rotation="1 MB",
        retention=3,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
    )
    # loguru opens the file lazily on first write; pre-touch + chmod so the
    # first record doesn't land in a world-readable file. touch(mode=...)
    # only applies perms on create (and is subject to umask), so the
    # explicit chmod afterwards handles pre-existing-file cases too.
    try:
        LOG_FILE.touch(mode=0o600, exist_ok=True)
    except OSError:
        pass
    secure_file(LOG_FILE)


__all__ = ["logger", "configure_logging", "LOG_FILE"]
