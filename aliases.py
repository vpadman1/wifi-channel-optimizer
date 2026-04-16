"""MAC address → friendly name aliases, stored in ~/.config/wifi-channel-optimizer/aliases.json."""
from __future__ import annotations
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "wifi-channel-optimizer"
ALIASES_FILE = CONFIG_DIR / "aliases.json"


def _normalize(mac: str) -> str:
    """Uppercase and strip whitespace so lookups don't depend on input casing."""
    return mac.strip().upper()


def load_aliases(path: Path = ALIASES_FILE) -> dict[str, str]:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {_normalize(k): str(v) for k, v in data.items()}


def save_aliases(aliases: dict[str, str], path: Path = ALIASES_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {_normalize(k): str(v) for k, v in aliases.items()}
    path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n")


def set_alias(mac: str, name: str, path: Path = ALIASES_FILE) -> None:
    aliases = load_aliases(path)
    aliases[_normalize(mac)] = name
    save_aliases(aliases, path)


def remove_alias(mac: str, path: Path = ALIASES_FILE) -> bool:
    """Returns True if an alias was removed, False if it wasn't present."""
    aliases = load_aliases(path)
    key = _normalize(mac)
    if key not in aliases:
        return False
    del aliases[key]
    save_aliases(aliases, path)
    return True


def resolve(mac: str, aliases: dict[str, str]) -> str:
    """Returns the friendly name if one exists, otherwise the original MAC."""
    return aliases.get(_normalize(mac), mac)
