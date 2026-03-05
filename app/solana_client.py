# app/solana_client.py

import os
import aiohttp
from typing import Dict, List, Any

# You can override this with your own RPC (Helius, QuickNode, etc.). [web:318][web:320]
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# Minimal curated list of mints to display in the bot.
# Replace with your preferred set. Symbols are just for display.
TRACKED_MINTS: Dict[str, str] = {
    # USDC (example mainnet mint – adjust if you want another). [web:343]
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    # USDT
    "Es9vMFrzaCERaM8KkG2Z9GqzeuL1NVr7DiJ9NspGQhZW": "USDT",
    # Example meme token (replace with what you care about)
    "7WifgQvThhGx2jykGZLrVU4k3QfGZp9VHtX1hXtF8Wif": "WIF",
}


async def _rpc_post(payload: dict) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.post(SOLANA_RPC_URL, json=payload, timeout=10) as resp:
            resp.raise_for_status()
            return await resp.json()


async def get_sol_balance(address: str) -> float:
    """Return SOL balance for address, in SOL (not lamports)."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address, {"commitment": "finalized"}],
    }
    data = await _rpc_post(payload)
    value = data["result"]["value"]  # lamports per Solana RPC docs. [web:316][web:328]
    return value / 1_000_000_000


async def get_tracked_token_balances(address: str) -> Dict[str, float]:
    """
    Return balances for TRACKED_MINTS for this owner, as {symbol: amount}.
    Uses getTokenAccountsByOwner with encoding=jsonParsed. [web:330][web:343]
    """
    balances: Dict[str, float] = {}

    # For each mint we care about, query its token accounts.
    for mint, symbol in TRACKED_MINTS.items():
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                address,
                {"mint": mint},
                {"encoding": "jsonParsed"},
            ],
        }
        data = await _rpc_post(payload)

        result = data.get("result", {})
        value_list = result.get("value", [])  # list of accounts. [web:330][web:333]

        total = 0.0
        for acc in value_list:
            info = (
                acc.get("account", {})
                .get("data", {})
                .get("parsed", {})
                .get("info", {})
            )
            token_amount = info.get("tokenAmount", {})
            # uiAmount is already adjusted by decimals in jsonParsed. [web:343][web:346]
            ui_amount = token_amount.get("uiAmount")
            if ui_amount:
                total += float(ui_amount)

        if total > 0:
            balances[symbol] = total

    return balances

