"""Backward-compatible wrapper. Use drivers.tplink_oid.TplinkOidDriver directly."""
from drivers.tplink_oid import TplinkOidDriver as RouterClient

__all__ = ["RouterClient"]
