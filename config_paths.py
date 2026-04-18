"""Shared paths and permission helpers for user config/data files."""
from __future__ import annotations
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "wifi-channel-optimizer"


def secure_dir(path: Path) -> None:
    """chmod a directory to 0o700 (owner-only). Best-effort on non-POSIX."""
    try:
        path.chmod(0o700)
    except OSError:
        pass


def secure_file(path: Path) -> None:
    """chmod a file to 0o600 (owner-only). Best-effort on non-POSIX."""
    try:
        path.chmod(0o600)
    except OSError:
        pass
