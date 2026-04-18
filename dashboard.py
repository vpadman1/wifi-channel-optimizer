from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, DataTable, Static, Label
from textual.reactive import reactive
from textual import work
from textual_plotext import PlotextPlot
from drivers.base import BaseDriver
from wifi_scanner import (
    BAND_2G, BAND_5G, CHANNELS_2G_ALL, CHANNELS_5G,
    count_networks_per_channel,
)
from aliases import load_aliases, resolve


BAND_FIELDS = [
    ("SSID", "SSID"),
    ("channel", "Channel"),
    ("X_TP_Bandwidth", "Width"),
    ("standard", "Mode"),
    ("enable", "Radio"),
    ("X_TP_Band", "Band"),
    ("autoChannelEnable", "Auto Ch."),
]


class BandPanel(Static):
    """A panel showing config info for one WiFi band."""

    band_data: reactive[dict] = reactive({})

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self._title = title

    def compose(self) -> ComposeResult:
        yield Label(f"[bold]{self._title}[/bold]", id="band-title")
        yield DataTable(id="band-table", show_header=False, cursor_type="none")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Field", "Value")
        self._render_rows({})

    def watch_band_data(self, old_data: dict, data: dict) -> None:
        if data == old_data:
            return
        self._render_rows(data)

    def _render_rows(self, data: dict) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for key, label in BAND_FIELDS:
            value = data.get(key, "—")
            table.add_row(label, str(value))


class ClientsPanel(Static):
    """A panel showing all connected wireless clients."""

    clients_data: reactive[list] = reactive([])

    def __init__(self, *args, aliases: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases = aliases or {}

    def compose(self) -> ComposeResult:
        yield Label("[bold]Connected Clients[/bold]", id="clients-title")
        yield DataTable(id="clients-table", cursor_type="none")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Device", "MAC Address", "Network", "Band", "TX Packets", "RX Packets")

    def watch_clients_data(self, old_clients: list, clients: list) -> None:
        if clients == old_clients:
            return
        table = self.query_one(DataTable)
        table.clear()
        if not clients:
            table.add_row("No clients connected", "—", "—", "—", "—", "—")
            return
        for c in clients:
            mac = c.get("mac", c.get("AssociatedDeviceMACAddress", "—"))
            device = resolve(mac, self._aliases) if mac != "—" else "—"
            table.add_row(
                device,
                mac,
                c.get("network", c.get("X_TP_HostName", "—")),
                c.get("band", "—"),
                str(c.get("X_TP_TotalPacketsSent", "—")),
                str(c.get("X_TP_TotalPacketsReceived", "—")),
            )


class ChannelChartPanel(Static):
    """Bar chart showing network count per WiFi channel with recommendations."""

    scan_data: reactive[dict] = reactive({})

    def compose(self) -> ComposeResult:
        yield Label("[bold]Channel Scanner[/bold] — press S to scan", id="chart-title")
        yield Horizontal(
            PlotextPlot(id="chart-2g"),
            PlotextPlot(id="chart-5g"),
            id="chart-row",
        )
        yield Label("Press S to scan channels", id="chart-recommendation")

    def watch_scan_data(self, data: dict) -> None:
        if not data:
            return
        self._render_charts(data)

    def _render_band_chart(
        self, widget_id: str, channels: list[int], networks, current_ch: int, title: str,
    ) -> None:
        counts = count_networks_per_channel(networks, channels)
        chart = self.query_one(f"#{widget_id}", PlotextPlot)
        plt = chart.plt
        plt.clear_data()
        plt.clear_figure()
        colors = ["red" if ch == current_ch else "cyan" for ch in channels]
        plt.bar(channels, [counts[ch] for ch in channels], color=colors)
        plt.title(title)
        plt.xlabel("Channel")
        plt.ylabel("Networks")
        chart.refresh()

    def _render_charts(self, data: dict) -> None:
        networks = data.get("networks", [])
        current_2g = data.get("current_2g_channel", 0)
        current_5g = data.get("current_5g_channel", 0)

        self._render_band_chart("chart-2g", CHANNELS_2G_ALL, networks, current_2g, "2.4 GHz Channels")
        self._render_band_chart("chart-5g", CHANNELS_5G, networks, current_5g, "5 GHz Channels")

        rec_label = self.query_one("#chart-recommendation", Label)
        parts = []
        for band_label, rec in [(BAND_2G, data.get("rec_2g")), (BAND_5G, data.get("rec_5g"))]:
            if rec and rec.channel != rec.current_channel:
                parts.append(
                    f"[green]{band_label}: Switch ch {rec.current_channel} "
                    f"({rec.current_count} networks) → ch {rec.channel} "
                    f"({rec.network_count} networks)[/green]"
                )
            elif rec:
                parts.append(f"[dim]{band_label}: ch {rec.channel} is optimal[/dim]")
        rec_label.update(" | ".join(parts) if parts else "Press S to scan channels")


class StatusBar(Static):
    """Shows last-updated timestamp and error state."""

    status: reactive[str] = reactive("Initializing...")

    def render(self) -> str:
        return self.status


class WifiDashboard(App):
    """Textual TUI app for live WiFi channel monitoring."""

    CSS = """
    Screen {
        layout: vertical;
    }
    Horizontal {
        height: auto;
        margin: 1 0;
    }
    BandPanel {
        width: 1fr;
        border: solid $accent;
        padding: 1;
        margin: 0 1;
    }
    ClientsPanel {
        border: solid $accent;
        padding: 1;
        margin: 0 1;
        height: auto;
    }
    ChannelChartPanel {
        border: solid $accent;
        padding: 1;
        margin: 0 1;
        height: auto;
    }
    #chart-row {
        height: 15;
    }
    #chart-2g, #chart-5g {
        width: 1fr;
    }
    #chart-recommendation {
        height: 1;
        margin: 1 0 0 0;
        color: $text;
    }
    StatusBar {
        height: 1;
        background: $surface;
        color: $text-disabled;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh now"),
        ("s", "scan", "Scan channels"),
        ("c", "apply_recommendation", "Apply best channel"),
    ]

    def __init__(self, client: BaseDriver, interval: int = 5,
                 aliases: dict[str, str] | None = None,
                 scan_fn=None, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._interval = interval
        self._last_scan: dict | None = None
        self._aliases_override = aliases
        # Injectable WiFi scanner so --demo can swap in canned data instead
        # of calling CoreWLAN. None → use the real scanner at run time.
        self._scan_fn = scan_fn

    def compose(self) -> ComposeResult:
        aliases = self._aliases_override if self._aliases_override is not None else load_aliases()
        yield Header(show_clock=True)
        yield Horizontal(
            BandPanel("2.4 GHz", id="panel-2g"),
            BandPanel("5 GHz", id="panel-5g"),
        )
        yield ClientsPanel(id="panel-clients", aliases=aliases)
        yield ChannelChartPanel(id="panel-channels")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(self._interval, self.refresh_data)

    def action_refresh(self) -> None:
        self.refresh_data()

    def action_scan(self) -> None:
        self.query_one(StatusBar).status = "[yellow]Scanning WiFi channels...[/yellow]"
        self.run_scan()

    @work(thread=True)
    def refresh_data(self) -> None:
        import time
        from requests.exceptions import ConnectionError as ReqConnectionError
        try:
            data = self._client.get_all_data()
            self.call_from_thread(self._apply_data, data)
        except (ReqConnectionError, OSError):
            time.sleep(3)
            try:
                data = self._client.get_all_data()
                self.call_from_thread(self._apply_data, data)
            except Exception as retry_err:
                self.call_from_thread(self._set_error, f"Connection lost: {retry_err}")
        except Exception as e:
            self.call_from_thread(self._set_error, str(e))

    @work(thread=True)
    def run_scan(self) -> None:
        from wifi_scanner import scan_networks, recommend_channel
        scan = self._scan_fn or scan_networks
        try:
            networks = scan()
            panel_2g = self.query_one("#panel-2g", BandPanel)
            panel_5g = self.query_one("#panel-5g", BandPanel)
            current_2g = int(panel_2g.band_data.get("channel", 0) or 0)
            current_5g = int(panel_5g.band_data.get("channel", 0) or 0)

            rec_2g = recommend_channel(networks, BAND_2G, current_2g)
            rec_5g = recommend_channel(networks, BAND_5G, current_5g)

            scan_data = {
                "networks": networks,
                "current_2g_channel": current_2g,
                "current_5g_channel": current_5g,
                "rec_2g": rec_2g,
                "rec_5g": rec_5g,
            }
            self.call_from_thread(self._apply_scan, scan_data)
        except Exception as e:
            self.call_from_thread(self._set_error, f"Scan failed: {e}")

    def _set_error(self, message: str) -> None:
        self.query_one(StatusBar).status = f"[red]Error: {message}[/red]"

    def _apply_data(self, data: dict) -> None:
        panel_2g = self.query_one("#panel-2g", BandPanel)
        panel_5g = self.query_one("#panel-5g", BandPanel)
        clients_panel = self.query_one("#panel-clients", ClientsPanel)
        status_bar = self.query_one(StatusBar)

        panel_2g.band_data = data.get("band_2g", {})
        panel_5g.band_data = data.get("band_5g", {})
        clients_panel.clients_data = data.get("clients", [])
        now = datetime.now().strftime("%H:%M:%S")
        client_count = len(data.get("clients", []))
        status_bar.status = (
            f"Last updated: {now} — {client_count} client(s) connected "
            f"— R: refresh, S: scan channels, Q: quit"
        )

    def _apply_scan(self, scan_data: dict) -> None:
        self._last_scan = scan_data
        chart_panel = self.query_one("#panel-channels", ChannelChartPanel)
        chart_panel.scan_data = scan_data
        net_count = len(scan_data["networks"])
        now = datetime.now().strftime("%H:%M:%S")
        self.query_one(StatusBar).status = (
            f"Scan complete at {now} — {net_count} networks found — "
            f"C: apply recommendation, S: rescan"
        )

    def action_apply_recommendation(self) -> None:
        if not self._last_scan:
            self.notify("Run a scan first (press S)", severity="warning")
            return

        rec_2g = self._last_scan.get("rec_2g")
        rec_5g = self._last_scan.get("rec_5g")

        changes = []
        if rec_2g and rec_2g.channel != rec_2g.current_channel:
            changes.append(("2.4GHz", "1,1,0,0,0,0", rec_2g.channel, rec_2g.current_channel))
        if rec_5g and rec_5g.channel != rec_5g.current_channel:
            changes.append(("5GHz", "1,2,0,0,0,0", rec_5g.channel, rec_5g.current_channel))

        if not changes:
            self.notify("Channels are already optimal — no changes needed", severity="information")
            return

        desc = ", ".join(f"{band} ch {old}→{new}" for band, _, new, old in changes)
        self.notify(
            f"Switching: {desc}\nClients will briefly disconnect.",
            title="Applying channel change...",
            severity="warning",
        )
        self.apply_channel_changes(changes)

    @work(thread=True)
    def apply_channel_changes(self, changes: list[tuple]) -> None:
        import time
        try:
            for _band_name, stack, new_channel, _old in changes:
                self._client.set_channel(stack, new_channel)
            time.sleep(2)
            data = self._client.get_all_data()
            self.call_from_thread(self._apply_data, data)
            applied = ", ".join(f"{b} → ch {ch}" for b, _, ch, _ in changes)
            self.call_from_thread(
                self.notify,
                f"Done! {applied}. Press S to rescan and verify.",
                title="Channel changed",
                severity="information",
            )
        except Exception as e:
            self.call_from_thread(self._set_error, f"Channel change failed: {e}")
