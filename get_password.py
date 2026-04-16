"""Retrieve router password from macOS Keychain via keyring.

Usage in probe scripts:
    from get_password import get_router_password
    PASSWORD = get_router_password()

To store your password (one-time setup):
    ~/.local/bin/uv run python -m keyring set wifi-monitor router_admin
"""
import sys
import keyring

KEYRING_SERVICE = "wifi-monitor"
KEYRING_USERNAME = "router_admin"


def get_router_password() -> str:
    password = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if not password:
        print("No password found in keyring. Store it first:")
        print("  ~/.local/bin/uv run python -m keyring set wifi-monitor router_admin")
        sys.exit(1)
    return password
