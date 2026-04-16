import sys
import click
import keyring
from devices import load_driver, list_devices
from dashboard import WifiDashboard
from get_password import KEYRING_SERVICE, KEYRING_USERNAME


def get_password_from_keyring() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)


@click.command()
@click.option("--device", default="tplink_archer_c20_v5", show_default=True,
              help="Device config name from devices/ directory.")
@click.option("--host", default=None, help="Router IP (overrides device default).")
@click.option("--password", envvar="ROUTER_PASSWORD", required=False, hide_input=True,
              help="Router admin password. Falls back to keyring.")
@click.option("--username", default=None, help="Router admin username (overrides device default).")
@click.option("--interval", default=5, show_default=True, type=int, help="Polling interval in seconds.")
@click.option("--list-devices", "show_devices", is_flag=True, help="List available device configs and exit.")
def main(device: str, host: str | None, password: str | None,
         username: str | None, interval: int, show_devices: bool) -> None:
    """WiFi Channel Optimizer — terminal dashboard for WiFi monitoring and optimization."""
    if show_devices:
        for d in list_devices():
            click.echo(f"  {d['_file']:30s} {d['name']}")
            if d.get('compatible_models'):
                click.echo(f"    Compatible: {', '.join(d['compatible_models'])}")
        return

    if not password:
        password = get_password_from_keyring()
    if not password:
        click.echo("Error: no password provided. Either:", err=True)
        click.echo("  1. Store in keyring: uv run python -m keyring set wifi-monitor router_admin", err=True)
        click.echo("  2. Pass --password flag", err=True)
        click.echo("  3. Set ROUTER_PASSWORD env var", err=True)
        sys.exit(1)

    try:
        client = load_driver(device, host=host, password=password, username=username or "admin")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Connecting to router ({device})...")
    try:
        client.login()
    except Exception as e:
        click.echo(f"Error: could not authenticate — {e}", err=True)
        sys.exit(1)

    click.echo("Authenticated. Starting dashboard...")
    app = WifiDashboard(client=client, interval=interval)
    try:
        app.run()
    finally:
        try:
            client.logout()
        except Exception as e:
            click.echo(f"Warning: logout failed — {e}", err=True)


if __name__ == "__main__":
    main()
