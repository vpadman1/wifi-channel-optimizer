# Contributing

## Adding a New Device (same protocol family)

If your router uses the same web UI framework as an existing driver (e.g., other TP-Link models with OID-based CGI), you just need a YAML config:

1. Create `devices/your_router_model.yaml`:

```yaml
name: Your Router Model
driver: tplink_oid
default_host: 192.168.0.1
default_username: admin
description: Short description of the router
compatible_models:
  - Model Name v1
```

2. Test it: `uv run python main.py --device your_router_model`
3. Submit a PR with the YAML file

## Adding a New Driver (different protocol)

If your router uses a completely different protocol (e.g., Netgear SOAP, OpenWrt LuCI/ubus):

1. Create `drivers/your_protocol.py` implementing `BaseDriver`:

```python
from drivers.base import BaseDriver

class YourProtocolDriver(BaseDriver):
    def login(self) -> str: ...
    def logout(self) -> None: ...
    def get_wireless_config(self) -> list[dict]: ...
    def get_clients(self) -> list[dict]: ...
    def set_channel(self, band_stack: str, channel: int) -> None: ...
```

2. Register it in `devices/__init__.py` DRIVER_MAP
3. Create a YAML config in `devices/`
4. Add tests in `tests/`
5. Submit a PR

### Required fields in get_wireless_config() response

Each dict must include: `SSID`, `channel`, `X_TP_Band` (use "2.4GHz" or "5GHz"), `enable`, `name`

### Required fields in get_clients() response

Each dict must include: `mac`, `band`

## Running Tests

```bash
uv run pytest -v
```
