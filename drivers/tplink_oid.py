import re
import base64
import binascii
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from logging_config import logger
from drivers.base import BaseDriver
from wifi_scanner import BAND_2G, BAND_5G


class TplinkOidDriver(BaseDriver):
    """Driver for TP-Link routers using the OID-based CGI protocol.

    Tested on: Archer C20 v5
    Likely compatible with: Archer C50, C60, A5, and other TP-Link models
    using the same web UI framework.
    """

    def __init__(self, host: str, password: str, username: str = "admin"):
        super().__init__(host, password, username)
        self._session = requests.Session()
        self._session.headers.update({"Referer": f"http://{host}/"})
        self._token: str | None = None

    @property
    def _base_url(self) -> str:
        return f"http://{self.host}"

    def _encrypt_rsa(self, text: str, nn: str, ee: str) -> str:
        n = int(nn, 16)
        e = int(ee, 16)
        key = RSA.construct((n, e))
        cipher = PKCS1_v1_5.new(key)
        encrypted = cipher.encrypt(text.encode("utf-8"))
        return binascii.hexlify(encrypted).decode("utf-8")

    def login(self) -> str:
        logger.info(f"Logging in to router at {self.host} as user '{self.username}'")
        r = self._session.post(f"{self._base_url}/cgi/getParm")
        r.raise_for_status()
        nn_match = re.search(r'var nn="([0-9a-fA-F]+)"', r.text)
        ee_match = re.search(r'var ee="([0-9a-fA-F]+)"', r.text)
        if not nn_match or not ee_match:
            raise RuntimeError(
                f"Login failed — could not parse RSA keys from /cgi/getParm: {r.text[:200]}"
            )
        nn, ee = nn_match.group(1), ee_match.group(1)
        pwd_b64 = base64.b64encode(self.password.encode("utf-8")).decode("utf-8")
        encrypted_pwd = self._encrypt_rsa(pwd_b64, nn, ee)
        encrypted_user = self._encrypt_rsa(self.username, nn, ee)
        login_url = (
            f"{self._base_url}/cgi/login"
            f"?UserName={encrypted_user}&Passwd={encrypted_pwd}&Action=1&LoginStatus=0"
        )
        r = self._session.post(login_url)
        r.raise_for_status()
        jsessionid = self._session.cookies.get("JSESSIONID")
        if not jsessionid:
            raise RuntimeError(
                f"Login failed — no JSESSIONID cookie in response. Body: {r.text[:200]}"
            )
        self._token = self._fetch_token()
        logger.info("Login successful, token acquired")
        return jsessionid

    def _fetch_token(self) -> str:
        r = self._session.get(f"{self._base_url}/index.htm")
        r.raise_for_status()
        match = re.search(r'var\s+token\s*=\s*"([^"]+)"', r.text)
        if not match:
            raise RuntimeError("Login failed — could not parse token from /index.htm")
        return match.group(1)

    def logout(self) -> None:
        try:
            self._session.post(f"{self._base_url}/cgi/logout")
        except Exception as e:
            logger.debug(f"Logout request failed (ignored): {e}")
        self._session.cookies.clear()
        self._token = None

    # HTTP statuses that indicate the session cookie/token is no longer valid.
    _AUTH_FAIL_STATUSES = (401, 403)

    @staticmethod
    def _looks_like_session_expiry(response: requests.Response) -> bool:
        """True when the router is telling us our session is gone.

        The TP-Link CGI sometimes returns a 200 with an HTML redirect to the
        login page instead of a proper 401. We catch both shapes.
        """
        if response.status_code in TplinkOidDriver._AUTH_FAIL_STATUSES:
            return True
        # Skip the body sniff on clearly-successful non-HTML responses.
        content_type = response.headers.get("content-type", "")
        if response.ok and "html" not in content_type.lower():
            return False
        body = response.text[:500].lower()
        return "login" in body and ("jsp" in body or "htm" in body)

    def _cgi_post(self, action_types: str, body: str) -> str:
        if not self._token:
            raise RuntimeError("Not authenticated — call login() first")
        url = f"{self._base_url}/cgi?{action_types}"
        for attempt in range(2):
            r = self._session.post(
                url,
                data=body.encode("utf-8"),
                headers={"TokenID": self._token, "Content-Type": "text/plain"},
            )
            if attempt == 0 and self._looks_like_session_expiry(r):
                self._token = None
                self._session.cookies.clear()
                self.login()
                continue
            r.raise_for_status()
            return r.text
        # Unreachable: loop either returns or raises.
        raise RuntimeError("CGI retry loop exited unexpectedly")

    @staticmethod
    def _parse_oid_response(text: str) -> list[dict]:
        results = []
        current: dict | None = None
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("[error]"):
                break
            if line.startswith("["):
                if current is not None:
                    results.append(current)
                stack_match = re.match(r'\[([^\]]+)\](\d+)', line)
                current = {"__stack": stack_match.group(1) if stack_match else ""}
            elif current is not None and "=" in line:
                key, _, value = line.partition("=")
                current[key] = value
        if current is not None:
            results.append(current)
        return results

    def get_wireless_config(self) -> list[dict]:
        body = (
            "[LAN_WLAN#0,0,0,0,0,0#0,0,0,0,0,0]0,12\r\n"
            "name\r\nStandard\r\nSSID\r\nBSSID\r\nX_TP_Band\r\n"
            "PossibleChannels\r\nAutoChannelEnable\r\nChannel\r\n"
            "X_TP_Bandwidth\r\nEnable\r\nBasicEncryptionModes\r\nBeaconType\r\n"
        )
        return self._parse_oid_response(self._cgi_post("5", body))

    def get_wireless_2g(self) -> dict:
        bands = self.get_wireless_config()
        for band in bands:
            if band.get("X_TP_Band") == BAND_2G:
                return band
        return bands[0] if bands else {}

    def get_wireless_5g(self) -> dict:
        bands = self.get_wireless_config()
        for band in bands:
            if band.get("X_TP_Band") == BAND_5G:
                return band
        return bands[1] if len(bands) > 1 else {}

    def get_clients(self) -> list[dict]:
        refresh_body = (
            "[ACT_WLAN_UPDATE_ASSOC#1,1,0,0,0,0#0,0,0,0,0,0]0,0\r\n"
            "[ACT_WLAN_UPDATE_ASSOC#1,2,0,0,0,0#0,0,0,0,0,0]1,0\r\n"
        )
        self._cgi_post("7&7", refresh_body)
        clients = []
        for band_stack in ["1,1,0,0,0,0", "1,2,0,0,0,0"]:
            body = (
                f"[LAN_WLAN_ASSOC_DEV#0,0,0,0,0,0#{band_stack}]0,4\r\n"
                "AssociatedDeviceMACAddress\r\nX_TP_TotalPacketsSent\r\n"
                "X_TP_TotalPacketsReceived\r\nX_TP_HostName\r\n"
            )
            raw = self._cgi_post("6", body)
            band_clients = self._parse_oid_response(raw)
            band_label = BAND_2G if band_stack.startswith("1,1") else BAND_5G
            for c in band_clients:
                c["band"] = band_label
                mac = c.get("AssociatedDeviceMACAddress") or c.get("associatedDeviceMACAddress", "")
                c["mac"] = mac
            clients.extend(c for c in band_clients if c.get("mac"))
        return clients

    def set_channel(self, band_stack: str, channel: int) -> None:
        logger.info(f"Setting channel: band_stack={band_stack} channel={channel}")
        body = (
            f"[LAN_WLAN#{band_stack}#0,0,0,0,0,0]0,2\r\n"
            f"AutoChannelEnable=0\r\nChannel={channel}\r\n"
        )
        self._cgi_post("2", body)
