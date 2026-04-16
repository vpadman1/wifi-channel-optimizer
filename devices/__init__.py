import yaml
from pathlib import Path

DEVICES_DIR = Path(__file__).parent
DRIVER_MAP = {
    "tplink_oid": "drivers.tplink_oid.TplinkOidDriver",
}


def list_devices() -> list[dict]:
    devices = []
    for f in sorted(DEVICES_DIR.glob("*.yaml")):
        with open(f) as fh:
            cfg = yaml.safe_load(fh)
            cfg["_file"] = f.stem
            devices.append(cfg)
    return devices


def load_driver(device_name: str, host: str, password: str, username: str = "admin"):
    config_path = DEVICES_DIR / f"{device_name}.yaml"
    if not config_path.exists():
        raise ValueError(f"Unknown device: {device_name}. Available: {[d['_file'] for d in list_devices()]}")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    driver_key = cfg["driver"]
    if driver_key not in DRIVER_MAP:
        raise ValueError(f"Unknown driver: {driver_key}")
    module_path, class_name = DRIVER_MAP[driver_key].rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    driver_class = getattr(mod, class_name)
    return driver_class(
        host=host or cfg.get("default_host", "192.168.0.1"),
        password=password,
        username=username or cfg.get("default_username", "admin"),
    )
