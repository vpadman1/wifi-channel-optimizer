from __future__ import annotations
from dataclasses import dataclass

try:
    from CoreWLAN import CWWiFiClient
except ImportError:
    CWWiFiClient = None


@dataclass
class ScanResult:
    ssid: str
    channel: int
    rssi: int
    channel_width: int  # 1=20MHz, 2=40MHz, 3=80MHz, 4=160MHz


def scan_networks() -> list[ScanResult]:
    """Scan for nearby WiFi networks using macOS CoreWLAN."""
    if CWWiFiClient is None:
        return []

    client = CWWiFiClient.sharedWiFiClient()
    iface = client.interface()
    if not iface:
        return []

    networks, error = iface.scanForNetworksWithName_error_(None, None)
    if error or not networks:
        return []

    results = []
    for net in networks:
        results.append(ScanResult(
            ssid=net.ssid() or "(hidden)",
            channel=net.wlanChannel().channelNumber(),
            rssi=net.rssiValue(),
            channel_width=net.wlanChannel().channelWidth(),
        ))
    return sorted(results, key=lambda r: r.channel)


@dataclass
class ChannelRecommendation:
    channel: int
    network_count: int
    current_channel: int
    current_count: int

BAND_2G = "2.4GHz"
BAND_5G = "5GHz"

CHANNELS_2G = [1, 6, 11]
CHANNELS_2G_ALL = list(range(1, 14))
CHANNELS_5G = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112,
               116, 120, 124, 128, 132, 136, 140, 149, 153, 157, 161, 165]


def count_networks_per_channel(networks: list[ScanResult], channels: list[int]) -> dict[int, int]:
    counts: dict[int, int] = {ch: 0 for ch in channels}
    for net in networks:
        if net.channel in counts:
            counts[net.channel] += 1
    return counts


def recommend_channel(
    networks: list[ScanResult],
    band: str,
    current_channel: int,
) -> ChannelRecommendation:
    channels = CHANNELS_2G if band == BAND_2G else CHANNELS_5G
    counts = count_networks_per_channel(networks, channels)
    current_count = counts.get(current_channel, 0)
    best_ch = min(channels, key=lambda ch: (counts[ch], ch != current_channel))
    return ChannelRecommendation(
        channel=best_ch,
        network_count=counts[best_ch],
        current_channel=current_channel,
        current_count=current_count,
    )
