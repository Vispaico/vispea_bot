from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional, List

import httpx


GAMMA_API_BASE = "https://gamma-api.polymarket.com"


@dataclass
class PolymarketConfig:
    builder_name: str
    wallet_address: str
    api_key: str
    api_secret: str
    api_passphrase: str


def get_polymarket_config() -> Optional[PolymarketConfig]:
    """Read Polymarket config from environment. Returns None if anything is missing."""
    builder_name = (os.getenv("POLYMARKET_BUILDER_NAME") or "").strip()
    wallet_address = (os.getenv("POLYMARKET_WALLET_ADDRESS") or "").strip()
    api_key = (os.getenv("POLYMARKET_API_KEY") or "").strip()
    api_secret = (os.getenv("POLYMARKET_API_SECRET") or "").strip()
    api_passphrase = (os.getenv("POLYMARKET_API_PASSPHRASE") or "").strip()

    if not all([builder_name, wallet_address, api_key, api_secret, api_passphrase]):
        return None

    return PolymarketConfig(
        builder_name=builder_name,
        wallet_address=wallet_address,
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
    )


async def _fetch_active_markets(limit: int = 50) -> List[dict]:
    """
    Fetch active, open markets from Gamma API.

    Uses /markets endpoint with filters for active/closed. [web:248][web:259]
    """
    params = {
        "active": True,
        "closed": False,
        "archived": False,
        "limit": limit,
        "order": "volume24hr",
        "ascending": False,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{GAMMA_API_BASE}/markets", params=params)
        resp.raise_for_status()
        return resp.json()  # list of markets


def _parse_outcome_prices(market: dict) -> Optional[list]:
    """
    Outcome prices come as a JSON-stringified list under 'outcomePrices'. [web:160]
    Returns list of floats or None.
    """
    prices_raw = market.get("outcomePrices")
    if not prices_raw:
        return None
    try:
        prices = json.loads(prices_raw)
        return [float(p) for p in prices]
    except Exception:
        return None


async def scan_polymarket_arbitrage() -> str:
    """
    Basic arb scanner:
    - Fetches top active markets by 24h volume.
    - Looks for markets where sum(outcomePrices) < 0.98 (potential edge).
    - Returns a human-readable summary for Telegram. [web:150][web:255]
    """
    try:
        markets = await _fetch_active_markets(limit=200)
    except Exception as exc:
        return f"⚠️ Error fetching Polymarket markets: {exc}"

    candidates = []

    for m in markets:
        prices = _parse_outcome_prices(m)
        if not prices:
            continue

        total = sum(prices)
        edge = 1.0 - total  # > 0 means potential mispricing

        question = m.get("question") or m.get("slug") or "Unknown market"
        volume = float(m.get("volume24hr", 0.0))
        market_id = m.get("marketId") or m.get("id") or ""

        candidates.append(
            {
                "question": question,
                "edge": edge,
                "total": total,
                "volume": volume,
                "market_id": market_id,
                "prices": prices,
            }
        )

    if not candidates:
        return "📊 No markets returned from Polymarket."

    # Sort by edge (absolute value) and volume
    candidates.sort(key=lambda x: (abs(x["edge"]), x["volume"]), reverse=True)
    top = candidates[:8]

    lines = ["📊 Polymarket markets ranked by theoretical edge (sum of outcome prices):\n"]
    for c in top:
        edge_pct = c["edge"] * 100
        prices_str = ", ".join(f"{p:.3f}" for p in c["prices"])
        lines.append(
            f"• {c['question']}\n"
            f"  Market: `{c['market_id']}`\n"
            f"  Outcome prices: [{prices_str}] (sum={c['total']:.3f})\n"
            f"  Theoretical edge: {edge_pct:+.2f}%\n"
            f"  24h volume: ${c['volume']:.0f}\n"
        )

    return "\n".join(lines)


async def track_polymarket_whales() -> str:
    """Stub: will monitor large wallets on Polymarket for whale bets."""
    return "🐋 Polymarket whale tracker not implemented yet."


async def subscribe_polymarket_alerts() -> str:
    """Stub: will subscribe to Polymarket markets for price/volume alerts."""
    return "⏰ Polymarket alerts not implemented yet."
