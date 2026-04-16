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

    def test_subclass_with_all_methods_works(self, fake_driver):
        driver = fake_driver()
        assert driver.host == "192.168.0.1"


class TestGetAllData:
    def test_splits_bands_by_x_tp_band(self, fake_driver):
        bands = [
            {"name": "wlan0", "SSID": "MyNet_2g", "X_TP_Band": "2.4GHz", "channel": "6"},
            {"name": "wlan5", "SSID": "MyNet_5g", "X_TP_Band": "5GHz", "channel": "36"},
        ]
        data = fake_driver(bands=bands).get_all_data()
        assert data["band_2g"]["SSID"] == "MyNet_2g"
        assert data["band_5g"]["SSID"] == "MyNet_5g"

    def test_falls_back_to_index_when_band_label_missing(self, fake_driver):
        bands = [
            {"name": "wlan0", "SSID": "First", "channel": "6"},
            {"name": "wlan5", "SSID": "Second", "channel": "36"},
        ]
        data = fake_driver(bands=bands).get_all_data()
        assert data["band_2g"]["SSID"] == "First"
        assert data["band_5g"]["SSID"] == "Second"

    def test_enriches_clients_with_ssid(self, fake_driver):
        bands = [
            {"name": "wlan0", "SSID": "MyNet_2g", "X_TP_Band": "2.4GHz"},
            {"name": "wlan5", "SSID": "MyNet_5g", "X_TP_Band": "5GHz"},
        ]
        clients = [
            {"mac": "AA:BB:CC:DD:EE:FF", "X_TP_HostName": "wlan0", "band": "2.4GHz"},
            {"mac": "11:22:33:44:55:66", "X_TP_HostName": "wlan5", "band": "5GHz"},
        ]
        data = fake_driver(bands=bands, clients=clients).get_all_data()
        assert data["clients"][0]["network"] == "MyNet_2g"
        assert data["clients"][1]["network"] == "MyNet_5g"

    def test_unknown_client_iface_falls_back_to_raw_name(self, fake_driver):
        bands = [{"name": "wlan0", "SSID": "MyNet_2g", "X_TP_Band": "2.4GHz"}]
        clients = [{"mac": "AA:BB:CC:DD:EE:FF", "X_TP_HostName": "unknown-iface"}]
        data = fake_driver(bands=bands, clients=clients).get_all_data()
        assert data["clients"][0]["network"] == "unknown-iface"

    def test_empty_bands_and_clients(self, fake_driver):
        data = fake_driver().get_all_data()
        assert data["band_2g"] == {}
        assert data["band_5g"] == {}
        assert data["clients"] == []
