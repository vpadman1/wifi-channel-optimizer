import pytest
from unittest.mock import MagicMock, patch
from requests.cookies import RequestsCookieJar
from router_client import RouterClient


FAKE_N = "00b3510a083aef6a49571c3c7e1d2443" * 4
FAKE_E = "010001"
FAKE_GETPARM_RESPONSE = f'var userSetting=1;\nvar ee="{FAKE_E}";\nvar nn="{FAKE_N}";\n$.ret=0;'
FAKE_TOKEN = "abc123tokendef456"
FAKE_INDEX_HTML = f'<html><script>var token="{FAKE_TOKEN}";</script></html>'


def _make_authed_client() -> RouterClient:
    client = RouterClient(host="192.168.0.1", password="testpass")
    client._token = FAKE_TOKEN
    return client


class TestRouterClientLogin:
    def _setup_login_mocks(self, client):
        """Set up mocks for the full login flow (getParm → login → index.htm)."""
        getparm_response = MagicMock()
        getparm_response.text = FAKE_GETPARM_RESPONSE
        getparm_response.status_code = 200

        login_response = MagicMock()
        login_response.text = "$.ret=0;"
        login_response.status_code = 200

        index_response = MagicMock()
        index_response.text = FAKE_INDEX_HTML
        index_response.status_code = 200

        jar = RequestsCookieJar()
        jar.set("JSESSIONID", "abc123session")

        return getparm_response, login_response, index_response, jar

    def test_login_full_flow(self):
        """login() does getParm → login → fetch token from index.htm."""
        client = RouterClient(host="192.168.0.1", password="testpass")
        getparm, login, index, jar = self._setup_login_mocks(client)

        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = [getparm, login]
            with patch.object(client._session, "get") as mock_get:
                mock_get.return_value = index
                with patch.object(client._session, "cookies", jar):
                    token = client.login()

        assert token == "abc123session"
        assert client._token == FAKE_TOKEN
        assert mock_post.call_count == 2
        mock_get.assert_called_once()

    def test_login_first_post_hits_getParm(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        getparm, login, index, jar = self._setup_login_mocks(client)

        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = [getparm, login]
            with patch.object(client._session, "get", return_value=index):
                with patch.object(client._session, "cookies", jar):
                    client.login()

        assert "/cgi/getParm" in mock_post.call_args_list[0][0][0]

    def test_login_second_post_hits_cgi_login(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        getparm, login, index, jar = self._setup_login_mocks(client)

        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = [getparm, login]
            with patch.object(client._session, "get", return_value=index):
                with patch.object(client._session, "cookies", jar):
                    client.login()

        second_url = mock_post.call_args_list[1][0][0]
        assert "/cgi/login" in second_url
        assert "UserName=" in second_url
        assert "Passwd=" in second_url
        assert "Action=1" in second_url

    def test_login_raises_on_missing_rsa_keys(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        bad_getparm = MagicMock()
        bad_getparm.text = "$.ret=1;"

        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = bad_getparm
            with pytest.raises(RuntimeError, match="Login failed"):
                client.login()

    def test_login_raises_on_missing_jsessionid(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        getparm = MagicMock()
        getparm.text = FAKE_GETPARM_RESPONSE
        login = MagicMock()
        login.text = "$.ret=0;"

        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = [getparm, login]
            with pytest.raises(RuntimeError, match="Login failed"):
                client.login()

    def test_login_raises_on_missing_token(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        getparm, login, _, jar = self._setup_login_mocks(client)
        bad_index = MagicMock()
        bad_index.text = "<html>no token here</html>"

        with patch.object(client._session, "post") as mock_post:
            mock_post.side_effect = [getparm, login]
            with patch.object(client._session, "get", return_value=bad_index):
                with patch.object(client._session, "cookies", jar):
                    with pytest.raises(RuntimeError, match="could not parse token"):
                        client.login()

    def test_logout_posts_to_cgi_logout(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        client._token = "sometoken"

        with patch.object(client._session, "post") as mock_post:
            with patch.object(client._session.cookies, "clear") as mock_clear:
                mock_post.return_value = MagicMock()
                client.logout()

        assert "/cgi/logout" in mock_post.call_args[0][0]
        mock_clear.assert_called_once()
        assert client._token is None


class TestRouterClientData:
    def test_get_wireless_config_posts_to_cgi_5(self):
        client = _make_authed_client()
        mock_resp = MagicMock()
        mock_resp.text = (
            "[1,1,0,0,0,0]0\n"
            "name=wlan0\nSSID=TestNet_2g\nX_TP_Band=2.4GHz\nchannel=6\n"
            "[1,2,0,0,0,0]0\n"
            "name=wlan5\nSSID=TestNet_5g\nX_TP_Band=5GHz\nchannel=36\n"
            "[error]0\n"
        )

        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            result = client.get_wireless_config()

        url = mock_post.call_args[0][0]
        assert "/cgi?5" in url
        assert mock_post.call_args[1]["headers"]["TokenID"] == FAKE_TOKEN
        assert len(result) == 2
        assert result[0]["SSID"] == "TestNet_2g"
        assert result[1]["SSID"] == "TestNet_5g"

    def test_get_wireless_2g_returns_correct_band(self):
        client = _make_authed_client()
        mock_resp = MagicMock()
        mock_resp.text = (
            "[1,1,0,0,0,0]0\n"
            "SSID=MyNet_2g\nX_TP_Band=2.4GHz\nchannel=6\n"
            "[1,2,0,0,0,0]0\n"
            "SSID=MyNet_5g\nX_TP_Band=5GHz\nchannel=149\n"
            "[error]0\n"
        )

        with patch.object(client._session, "post", return_value=mock_resp):
            result = client.get_wireless_2g()

        assert result["SSID"] == "MyNet_2g"
        assert result["channel"] == "6"

    def test_get_wireless_5g_returns_correct_band(self):
        client = _make_authed_client()
        mock_resp = MagicMock()
        mock_resp.text = (
            "[1,1,0,0,0,0]0\n"
            "SSID=MyNet_2g\nX_TP_Band=2.4GHz\nchannel=6\n"
            "[1,2,0,0,0,0]0\n"
            "SSID=MyNet_5g\nX_TP_Band=5GHz\nchannel=149\n"
            "[error]0\n"
        )

        with patch.object(client._session, "post", return_value=mock_resp):
            result = client.get_wireless_5g()

        assert result["SSID"] == "MyNet_5g"
        assert result["channel"] == "149"

    def test_get_clients_queries_both_bands(self):
        client = _make_authed_client()
        refresh_resp = MagicMock()
        refresh_resp.text = "[error]0\n"
        resp_2g = MagicMock()
        resp_2g.text = (
            "[1,1,1,0,0,0]0\n"
            "AssociatedDeviceMACAddress=AA:BB:CC:DD:EE:FF\n"
            "X_TP_HostName=Phone\n"
            "X_TP_TotalPacketsSent=1000\n"
            "X_TP_TotalPacketsReceived=2000\n"
            "[error]0\n"
        )
        resp_5g = MagicMock()
        resp_5g.text = (
            "[1,2,1,0,0,0]0\n"
            "AssociatedDeviceMACAddress=11:22:33:44:55:66\n"
            "X_TP_HostName=Laptop\n"
            "X_TP_TotalPacketsSent=5000\n"
            "X_TP_TotalPacketsReceived=8000\n"
            "[error]0\n"
        )

        with patch.object(client._session, "post", side_effect=[refresh_resp, resp_2g, resp_5g]):
            result = client.get_clients()

        assert len(result) == 2
        assert result[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert result[0]["band"] == "2.4GHz"
        assert result[1]["mac"] == "11:22:33:44:55:66"
        assert result[1]["band"] == "5GHz"

    def test_get_clients_handles_no_clients(self):
        client = _make_authed_client()
        empty_resp = MagicMock()
        empty_resp.text = "[error]0\n"

        with patch.object(client._session, "post", return_value=empty_resp):
            result = client.get_clients()

        assert result == []

    def test_cgi_post_raises_without_login(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.get_wireless_config()

    def test_parse_oid_response(self):
        raw = (
            "[1,1,0,0,0,0]0\n"
            "SSID=TestNet\n"
            "channel=6\n"
            "enable=1\n"
            "[error]0\n"
        )
        result = RouterClient._parse_oid_response(raw)
        assert len(result) == 1
        assert result[0]["SSID"] == "TestNet"
        assert result[0]["channel"] == "6"
        assert result[0]["__stack"] == "1,1,0,0,0,0"


class TestRouterClientSetChannel:
    def test_set_channel_2g_posts_act_set(self):
        client = _make_authed_client()
        mock_resp = MagicMock()
        mock_resp.text = "[error]0\n"

        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            client.set_channel("1,1,0,0,0,0", 6)

        url = mock_post.call_args[0][0]
        assert "/cgi?2" in url
        body = mock_post.call_args[1]["data"].decode("utf-8")
        assert "Channel=6" in body
        assert "1,1,0,0,0,0" in body

    def test_set_channel_5g_posts_correct_stack(self):
        client = _make_authed_client()
        mock_resp = MagicMock()
        mock_resp.text = "[error]0\n"

        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            client.set_channel("1,2,0,0,0,0", 44)

        body = mock_post.call_args[1]["data"].decode("utf-8")
        assert "Channel=44" in body
        assert "1,2,0,0,0,0" in body

    def test_set_channel_disables_auto_channel(self):
        client = _make_authed_client()
        mock_resp = MagicMock()
        mock_resp.text = "[error]0\n"

        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            client.set_channel("1,1,0,0,0,0", 11)

        body = mock_post.call_args[1]["data"].decode("utf-8")
        assert "AutoChannelEnable=0" in body

    def test_set_channel_raises_without_login(self):
        client = RouterClient(host="192.168.0.1", password="testpass")
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.set_channel("1,1,0,0,0,0", 6)
