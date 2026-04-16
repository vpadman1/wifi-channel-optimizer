import pytest
from drivers.base import BaseDriver


class TestBaseDriver:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseDriver(host="192.168.0.1", password="test")

    def test_subclass_must_implement_methods(self):
        class IncompleteDriver(BaseDriver):
            pass
        with pytest.raises(TypeError):
            IncompleteDriver(host="192.168.0.1", password="test")

    def test_subclass_with_all_methods_works(self):
        class FakeDriver(BaseDriver):
            def login(self): return "session"
            def logout(self): pass
            def get_wireless_config(self): return []
            def get_clients(self): return []
            def set_channel(self, band_stack, channel): pass

        driver = FakeDriver(host="192.168.0.1", password="test")
        assert driver.host == "192.168.0.1"
