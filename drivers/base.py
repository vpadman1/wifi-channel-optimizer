import re
from abc import ABC, abstractmethod
from wifi_scanner import BAND_2G, BAND_5G


# Accept a bare hostname or IP with an optional :port. Rejects anything
# containing a scheme, path, query, or fragment so drivers can't be tricked
# into sending credentials to an attacker-controlled URL via --host.
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]*(?::\d{1,5})?$")


def _validate_host(host: str) -> str:
    if not isinstance(host, str) or not _HOST_RE.fullmatch(host):
        raise ValueError(
            f"Invalid host {host!r}: expected a hostname or IP with optional :port, "
            "no scheme/path/query."
        )
    return host


class BaseDriver(ABC):

    def __init__(self, host: str, password: str, username: str = "admin"):
        self.host = _validate_host(host)
        self.password = password
        self.username = username

    @abstractmethod
    def login(self) -> str:
        ...

    @abstractmethod
    def logout(self) -> None:
        ...

    @abstractmethod
    def get_wireless_config(self) -> list[dict]:
        ...

    @abstractmethod
    def get_clients(self) -> list[dict]:
        ...

    @abstractmethod
    def set_channel(self, band_stack: str, channel: int) -> None:
        ...

    def get_all_data(self) -> dict:
        bands = self.get_wireless_config()
        band_2g = {}
        band_5g = {}
        iface_to_ssid = {}
        for band in bands:
            name = band.get("name", "")
            ssid = band.get("SSID", "")
            if name and ssid:
                iface_to_ssid[name] = ssid
            if band.get("X_TP_Band") == BAND_2G:
                band_2g = band
            elif band.get("X_TP_Band") == BAND_5G:
                band_5g = band
        if not band_2g and bands:
            band_2g = bands[0]
        if not band_5g and len(bands) > 1:
            band_5g = bands[1]
        clients = self.get_clients()
        for c in clients:
            iface = c.get("X_TP_HostName", "")
            c["network"] = iface_to_ssid.get(iface, iface)
        return {"band_2g": band_2g, "band_5g": band_5g, "clients": clients}
