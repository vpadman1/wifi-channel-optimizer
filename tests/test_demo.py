from drivers.demo import DemoDriver
from wifi_scanner import demo_scan_networks, ScanResult, BAND_2G, BAND_5G


class TestDemoDriver:
    def test_default_construction(self):
        driver = DemoDriver()
        assert driver.host == "demo"

    def test_login_and_logout_no_op(self):
        driver = DemoDriver()
        assert driver.login() == "demo-session"
        driver.logout()

    def test_get_all_data_returns_both_bands(self):
        driver = DemoDriver()
        data = driver.get_all_data()
        assert data["band_2g"]["X_TP_Band"] == BAND_2G
        assert data["band_5g"]["X_TP_Band"] == BAND_5G
        assert data["band_2g"]["SSID"] == "MyHomeWiFi"
        assert data["band_5g"]["SSID"] == "MyHomeWiFi-5G"

    def test_get_all_data_enriches_clients_with_ssid(self):
        driver = DemoDriver()
        data = driver.get_all_data()
        assert len(data["clients"]) >= 2
        for c in data["clients"]:
            assert c["network"] in {"MyHomeWiFi", "MyHomeWiFi-5G"}

    def test_set_channel_2g_updates_internal_state(self):
        driver = DemoDriver()
        driver.set_channel("1,1,0,0,0,0", 11)
        assert driver.get_all_data()["band_2g"]["channel"] == "11"

    def test_set_channel_5g_updates_internal_state(self):
        driver = DemoDriver()
        driver.set_channel("1,2,0,0,0,0", 149)
        assert driver.get_all_data()["band_5g"]["channel"] == "149"


class TestDemoScanNetworks:
    def test_returns_scan_results(self):
        results = demo_scan_networks()
        assert len(results) > 0
        for r in results:
            assert isinstance(r, ScanResult)

    def test_includes_own_ssid(self):
        ssids = {r.ssid for r in demo_scan_networks()}
        assert "MyHomeWiFi" in ssids
        assert "MyHomeWiFi-5G" in ssids

    def test_spans_both_bands(self):
        channels = {r.channel for r in demo_scan_networks()}
        assert any(c <= 13 for c in channels)
        assert any(c >= 36 for c in channels)
