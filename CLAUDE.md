# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the dashboard
uv run python main.py
# Run tests
uv run pytest -v
# List supported devices
uv run python main.py --list-devices
```

## Architecture

- `drivers/base.py` — BaseDriver ABC that all router drivers implement
- `drivers/tplink_oid.py` — TP-Link OID-based CGI driver (Archer C20 v5 and compatible)
- `devices/*.yaml` — Device config files mapping device models to drivers
- `devices/__init__.py` — Device loader with `load_driver()` and `list_devices()`
- `dashboard.py` — Textual TUI with band panels, client table, channel charts
- `wifi_scanner.py` — macOS CoreWLAN WiFi scanner and channel recommendation engine
- `main.py` — Click CLI entry point with `--device`, `--host`, `--password` flags
- `router_client.py` — Backward-compatible wrapper (imports TplinkOidDriver as RouterClient)
