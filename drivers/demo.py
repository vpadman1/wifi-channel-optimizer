"""DemoDriver — returns plausible fake router data so the dashboard can be
run without a real router. Useful for screenshots, README demos, and letting
people try the tool before buying compatible hardware.

The data shapes match what TplinkOidDriver returns so get_all_data() in
BaseDriver does the right band-splitting and client-enrichment.
"""
from __future__ import annotations
from drivers.base import BaseDriver


class DemoDriver(BaseDriver):
    def __init__(self, host: str = "demo", password: str = "demo", username: str = "demo"):
        super().__init__(host, password, username)
        # Mutable so "Apply best channel" (pressing C) actually reflects in
        # the next refresh — makes the demo feel live.
        self._channel_2g = 6
        self._channel_5g = 44

    def login(self) -> str:
        return "demo-session"

    def logout(self) -> None:
        pass

    def get_wireless_config(self) -> list[dict]:
        return [
            {
                "name": "wlan0",
                "SSID": "MyHomeWiFi",
                "BSSID": "AA:BB:CC:11:22:33",
                "X_TP_Band": "2.4GHz",
                "channel": str(self._channel_2g),
                "X_TP_Bandwidth": "2",
                "standard": "11ng",
                "enable": "1",
                "autoChannelEnable": "0",
            },
            {
                "name": "wlan5",
                "SSID": "MyHomeWiFi-5G",
                "BSSID": "AA:BB:CC:11:22:34",
                "X_TP_Band": "5GHz",
                "channel": str(self._channel_5g),
                "X_TP_Bandwidth": "3",
                "standard": "11ac",
                "enable": "1",
                "autoChannelEnable": "0",
            },
        ]

    def get_clients(self) -> list[dict]:
        return [
            {
                "mac": "AA:BB:CC:DD:EE:01",
                "AssociatedDeviceMACAddress": "AA:BB:CC:DD:EE:01",
                "X_TP_HostName": "wlan0",
                "X_TP_TotalPacketsSent": "12420",
                "X_TP_TotalPacketsReceived": "45123",
                "band": "2.4GHz",
            },
            {
                "mac": "AA:BB:CC:DD:EE:02",
                "AssociatedDeviceMACAddress": "AA:BB:CC:DD:EE:02",
                "X_TP_HostName": "wlan5",
                "X_TP_TotalPacketsSent": "98234",
                "X_TP_TotalPacketsReceived": "234561",
                "band": "5GHz",
            },
            {
                "mac": "AA:BB:CC:DD:EE:03",
                "AssociatedDeviceMACAddress": "AA:BB:CC:DD:EE:03",
                "X_TP_HostName": "wlan5",
                "X_TP_TotalPacketsSent": "5621",
                "X_TP_TotalPacketsReceived": "8932",
                "band": "5GHz",
            },
            {
                "mac": "AA:BB:CC:DD:EE:04",
                "AssociatedDeviceMACAddress": "AA:BB:CC:DD:EE:04",
                "X_TP_HostName": "wlan0",
                "X_TP_TotalPacketsSent": "842",
                "X_TP_TotalPacketsReceived": "1203",
                "band": "2.4GHz",
            },
        ]

    def set_channel(self, band_stack: str, channel: int) -> None:
        if band_stack.startswith("1,1"):
            self._channel_2g = int(channel)
        else:
            self._channel_5g = int(channel)
