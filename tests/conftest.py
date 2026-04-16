import pytest
from drivers.base import BaseDriver


def _make_fake_driver(bands=None, clients=None):
    class FakeDriver(BaseDriver):
        def login(self): return "session"
        def logout(self): pass
        def get_wireless_config(self): return bands or []
        def get_clients(self): return clients or []
        def set_channel(self, band_stack, channel): pass
    return FakeDriver(host="192.168.0.1", password="test")


@pytest.fixture
def fake_driver():
    return _make_fake_driver
