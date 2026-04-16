import pytest
from devices import load_driver, list_devices

DEVICE = "tplink_archer_c20_v5"


def _load(**overrides):
    defaults = dict(host="192.168.0.1", password="test", username="admin")
    return load_driver(DEVICE, **{**defaults, **overrides})


class TestListDevices:
    def test_returns_known_device(self):
        names = [d["_file"] for d in list_devices()]
        assert DEVICE in names

    def test_each_device_has_required_fields(self):
        for d in list_devices():
            assert "name" in d
            assert "driver" in d
            assert "_file" in d


class TestLoadDriver:
    def test_loads_tplink_driver(self):
        from drivers.tplink_oid import TplinkOidDriver
        driver = _load()
        assert isinstance(driver, TplinkOidDriver)
        assert driver.host == "192.168.0.1"
        assert driver.username == "admin"

    def test_applies_yaml_default_username_when_none(self):
        assert _load(username=None).username == "admin"

    def test_applies_yaml_default_host_when_none(self):
        assert _load(host=None).host == "192.168.0.1"

    def test_cli_username_overrides_yaml_default(self):
        assert _load(username="custom_user").username == "custom_user"

    def test_unknown_device_raises(self):
        with pytest.raises(ValueError, match="Unknown device"):
            load_driver("nonexistent_device", host="x", password="test", username="admin")
