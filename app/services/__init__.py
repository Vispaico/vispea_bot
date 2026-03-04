"""Service layer for trading bot."""

from .polymarket import (
    get_polymarket_config,
    scan_polymarket_arbitrage,
    track_polymarket_whales,
    subscribe_polymarket_alerts,
)

__all__ = [
    "get_polymarket_config",
    "scan_polymarket_arbitrage",
    "track_polymarket_whales",
    "subscribe_polymarket_alerts",
]
