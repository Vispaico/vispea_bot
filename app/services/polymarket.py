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
    """
    Show top wallets by recent trading volume (simple whale discovery).

    Phase 1: read-only.
    We look at recent markets, aggregate volume by wallet (maker/taker),
    and return the top few as a formatted list. [web:263][web:265]
    """
    try:
        markets = await _fetch_active_markets(limit=200)
    except Exception as exc:
        return f"⚠️ Error fetching Polymarket markets for whales: {exc}"

    # For phase 1 we just use market-level fields as a proxy:
    # - 'creator' (market creator)
    # - 'volume24hr' as "influence" on that market.
    # Later we will switch to trade-level WebSocket/user data. [web:268][web:272]
    wallet_scores: dict[str, float] = {}

    for m in markets:
        creator = m.get("creator") or m.get("creatorAddress") or ""
        volume = float(m.get("volume24hr", 0.0))

        if not creator or volume <= 0:
            continue

        wallet_scores[creator] = wallet_scores.get(creator, 0.0) + volume

    if not wallet_scores:
        return "🐋 No whale-like activity detected from market data."

    # Rank by total 24h volume across markets
    ranked = sorted(wallet_scores.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:10]

    lines = ["🐋 Top Polymarket wallets by aggregated 24h market volume (rough whale proxy):\n"]
    for addr, vol in top:
        lines.append(f"• `{addr}` — approx ${vol:.0f} 24h volume\n")

    lines.append(
        "\nPhase 1: using market creators as a rough proxy.\n"
        "Next step: switch to trade-level data and real PnL / win-rate based ranking."
    )

    return "\n".join(lines)


async def subscribe_polymarket_alerts() -> str:
    """Stub: will subscribe to Polymarket markets for price/volume alerts."""
    return "⏰ Polymarket alerts not implemented yet."
