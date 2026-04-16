from unittest.mock import MagicMock, patch
from wifi_scanner import scan_networks, ScanResult, recommend_channel


class TestScanNetworks:
    def test_returns_list_of_scan_results(self):
        mock_net = MagicMock()
        mock_net.wlanChannel().channelNumber.return_value = 6
        mock_net.wlanChannel().channelWidth.return_value = 1
        mock_net.rssiValue.return_value = -55
        mock_net.ssid.return_value = "TestNet"

        mock_iface = MagicMock()
        mock_iface.scanForNetworksWithName_error_.return_value = ({mock_net}, None)

        with patch("wifi_scanner.CWWiFiClient") as mock_client:
            mock_client.sharedWiFiClient().interface.return_value = mock_iface
            results = scan_networks()

        assert len(results) == 1
        assert results[0].channel == 6
        assert results[0].rssi == -55
        assert results[0].ssid == "TestNet"

    def test_returns_empty_on_scan_error(self):
        mock_iface = MagicMock()
        mock_iface.scanForNetworksWithName_error_.return_value = (None, "scan failed")

        with patch("wifi_scanner.CWWiFiClient") as mock_client:
            mock_client.sharedWiFiClient().interface.return_value = mock_iface
            results = scan_networks()

        assert results == []


class TestRecommendChannel:
    def test_recommends_empty_channel(self):
        networks = [
            ScanResult(ssid="A", channel=1, rssi=-50, channel_width=1),
            ScanResult(ssid="B", channel=1, rssi=-60, channel_width=1),
            ScanResult(ssid="C", channel=6, rssi=-55, channel_width=1),
        ]
        rec = recommend_channel(networks, band="2.4GHz", current_channel=1)
        assert rec.channel == 11
        assert rec.network_count == 0
        assert rec.current_channel == 1
        assert rec.current_count == 2

    def test_returns_current_if_already_best(self):
        networks = [
            ScanResult(ssid="A", channel=6, rssi=-50, channel_width=1),
        ]
        rec = recommend_channel(networks, band="2.4GHz", current_channel=11)
        assert rec.channel == 11
        assert rec.network_count == 0

    def test_5ghz_recommendation(self):
        networks = [
            ScanResult(ssid="A", channel=36, rssi=-50, channel_width=3),
            ScanResult(ssid="B", channel=36, rssi=-60, channel_width=3),
        ]
        rec = recommend_channel(networks, band="5GHz", current_channel=36)
        assert rec.channel != 36
        assert rec.network_count == 0

    def test_empty_scan_keeps_current(self):
        rec = recommend_channel([], band="2.4GHz", current_channel=6)
        assert rec.channel == 6
        assert rec.network_count == 0

    def test_tiebreaker_prefers_current_channel(self):
        """When multiple channels have equal congestion, stay on current."""
        networks = [
            ScanResult(ssid="A", channel=1, rssi=-50, channel_width=1),
            ScanResult(ssid="B", channel=6, rssi=-55, channel_width=1),
            ScanResult(ssid="C", channel=11, rssi=-60, channel_width=1),
        ]
        rec = recommend_channel(networks, band="2.4GHz", current_channel=6)
        assert rec.channel == 6
