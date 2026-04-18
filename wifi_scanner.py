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


def demo_scan_networks() -> list[ScanResult]:
    """Fake scan data for --demo mode. Crafted so the recommender has a
    clear winner on each band: ch 1 is heavily contended, ch 11 is clean,
    ch 44 has a strong neighbor, ch 149 is clean on 5 GHz."""
    return [
        ScanResult(ssid="MyHomeWiFi", channel=6, rssi=-42, channel_width=2),
        ScanResult(ssid="MyHomeWiFi-5G", channel=44, rssi=-48, channel_width=3),
        ScanResult(ssid="NETGEAR_07", channel=1, rssi=-58, channel_width=1),
        ScanResult(ssid="LinksysSetup", channel=6, rssi=-68, channel_width=1),
        ScanResult(ssid="ATT-WIFI-4821", channel=1, rssi=-62, channel_width=1),
        ScanResult(ssid="xfinitywifi", channel=1, rssi=-75, channel_width=1),
        ScanResult(ssid="CoffeeShop-Guest", channel=11, rssi=-82, channel_width=1),
        ScanResult(ssid="Upstairs-5G", channel=44, rssi=-55, channel_width=3),
        ScanResult(ssid="Neighbor-5G", channel=48, rssi=-70, channel_width=3),
        ScanResult(ssid="Guest-Network", channel=36, rssi=-72, channel_width=3),
    ]


def count_networks_per_channel(networks: list[ScanResult], channels: list[int]) -> dict[int, int]:
    """Raw count of networks whose primary channel matches each target channel.

    Used for the dashboard chart. Does not account for RSSI or overlap —
    see score_channels() for recommendation scoring.
    """
    counts: dict[int, int] = {ch: 0 for ch in channels}
    for net in networks:
        if net.channel in counts:
            counts[net.channel] += 1
    return counts


def _rssi_weight(rssi: int) -> float:
    """Weight a neighbor's congestion contribution by signal strength.

    Stronger signals disrupt us more. Thresholds are picked to mirror how macOS
    reports "excellent / good / weak" in the Wi-Fi menu bar.
    """
    if rssi > -55:
        return 3.0
    if rssi > -75:
        return 1.5
    return 0.5


# Adjacent-channel spill weights for 2.4 GHz (20 MHz width). A network on
# channel N leaks into channels within ±4 because adjacent 2.4 GHz channels
# overlap by design — only 1/6/11 are truly non-overlapping.
# 5 GHz channels at 20 MHz width don't overlap, so we don't apply spill there.
_OVERLAP_2G = {0: 1.0, 1: 0.5, 2: 0.5, 3: 0.25, 4: 0.25}


def score_channels(
    networks: list[ScanResult],
    channels: list[int],
    band: str,
) -> dict[int, float]:
    """Compute a congestion score per channel, lower is better.

    Weights each nearby network by signal strength (RSSI), and on 2.4 GHz also
    by how far its channel is from the candidate (adjacent-channel interference).
    """
    scores: dict[int, float] = {ch: 0.0 for ch in channels}
    if band == BAND_2G:
        for net in networks:
            rssi_w = _rssi_weight(net.rssi)
            for ch in channels:
                overlap = _OVERLAP_2G.get(abs(ch - net.channel), 0.0)
                if overlap:
                    scores[ch] += rssi_w * overlap
    else:
        for net in networks:
            if net.channel in scores:
                scores[net.channel] += _rssi_weight(net.rssi)
    return scores


def recommend_channel(
    networks: list[ScanResult],
    band: str,
    current_channel: int,
) -> ChannelRecommendation:
    channels = CHANNELS_2G if band == BAND_2G else CHANNELS_5G
    scores = score_channels(networks, channels, band)
    # The dashboard chart still uses raw counts, so expose those for display.
    counts = count_networks_per_channel(networks, channels)
    current_count = counts.get(current_channel, 0)
    # Tiebreaker: prefer staying on current channel (False sorts before True)
    # to avoid disrupting clients when no better option exists.
    best_ch = min(channels, key=lambda ch: (scores[ch], ch != current_channel))
    return ChannelRecommendation(
        channel=best_ch,
        network_count=counts[best_ch],
        current_channel=current_channel,
        current_count=current_count,
    )
