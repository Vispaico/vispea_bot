"""Telegram command handlers."""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional, Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.services import (
    get_polymarket_config,
    scan_polymarket_arbitrage,
    track_polymarket_whales,
    subscribe_polymarket_alerts,
)
from app.solana_client import get_sol_balance, get_tracked_token_balances


WELCOME_TEXT = (
    "Welcome to the multi-chain trading assistant. "
    "Use /help to see available commands."
)

# Very simple per-chat state for now. Replace with DB later.
AWAITING_SOL_ADDRESS: dict[int, bool] = {}

# Basic Solana address shape: base58, 32–44 chars.
SOL_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _looks_like_solana_address(text: str) -> bool:
    return bool(SOL_ADDRESS_RE.match(text.strip()))


# -----------------------------
# Mock whale trade for step 1
# -----------------------------

# In step 2 this will come from your worker (latest whale record).
# Structure example for our simulation.
MOCK_LAST_WHALE_TRADE: Dict[str, Any] = {
    "market_title": "Will Donald Trump win the 2028 US Presidential Election?",
    "market_id": "0xdeadbeef"[:64],
    "outcome": "YES",
    "side": "BUY",
    "size_usdc": 1000.0,
    "price": 0.42,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = [
        "/start - Welcome message",
        "/help - List commands",
        "/status - Health check",
        "/connect_solana - Connect Phantom / Solana wallets",
        "/connect_evm - Connect MetaMask / Trust Wallet (placeholder)",
        "/sol_balance - View Solana balance",
        "/polymarket - Polymarket tools (arb, whales, alerts menu)",
        "/phoenix - Phoenix V2 arbitrage tools (placeholder)",
    ]
    await update.message.reply_text("Available commands:\n" + "\n".join(commands))


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    await update.message.reply_text(f"alive ({now})")


# -----------------------------
# Solana / Phantom connect
# -----------------------------

async def connect_solana(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    AWAITING_SOL_ADDRESS[chat_id] = True

    text = (
        "🔑 Solana / Phantom connect\n\n"
        "I work best with a **burner** Solana wallet: small balance only, "
        "never your main vault.\n\n"
        "1) Open Phantom and choose the wallet you want to use.\n"
        "2) Tap the wallet name → Copy address.\n"
        "3) Paste the **public** address here in this chat.\n\n"
        "I will never ask for your seed phrase or private key. "
        "Send only a Solana address (base58 string, 32–44 chars)."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_solana_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not AWAITING_SOL_ADDRESS.get(chat_id):
        # Not currently in Solana connect flow; ignore here.
        return

    addr = (update.message.text or "").strip()

    if not _looks_like_solana_address(addr):
        await update.message.reply_text(
            "That doesn’t look like a valid Solana address.\n\n"
            "Make sure you:\n"
            "- Open Phantom → tap wallet name → Copy address\n"
            "- Paste the address here (no extra text)."
        )
        return

    # Persist in per-chat data for now; later swap to DB.
    context.chat_data["sol_address"] = addr
    AWAITING_SOL_ADDRESS.pop(chat_id, None)

    await update.message.reply_text(
        f"Got it. I’ll treat this as your Solana trading wallet:\n`{addr}`\n\n"
        "Later I’ll use this to show balances, PnL and positions.",
        parse_mode="Markdown",
    )


async def sol_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    addr = context.chat_data.get("sol_address")
    if not addr:
        await update.message.reply_text(
            "No Solana wallet connected yet.\n\n"
            "Run /connect_solana and send your Phantom address first."
        )
        return

    try:
        sol = await get_sol_balance(addr)
        tokens = await get_tracked_token_balances(addr)
    except Exception:
        await update.message.reply_text(
            "Could not fetch balances from Solana RPC right now. Try again later."
        )
        return

    lines = [f"Wallet: `{addr}`", f"SOL: {sol:.4f}"]
    if tokens:
        lines.append("")
        lines.append("Tracked tokens:")
        for symbol, amount in tokens.items():
            lines.append(f"- {symbol}: {amount:.4f}")
    else:
        lines.append("")
        lines.append("No balance in tracked tokens yet.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# -----------------------------
# EVM placeholder
# -----------------------------

async def connect_evm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here we will connect MetaMask / Trust Wallet (EVM) via WalletConnect."
    )


# -----------------------------
# Polymarket module
# -----------------------------

async def polymarket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = get_polymarket_config()

    if cfg is None:
        await update.message.reply_text(
            "⚠️ Polymarket is not fully configured yet.\n"
            "Missing one or more of:\n"
            "POLYMARKET_BUILDER_NAME, POLYMARKET_WALLET_ADDRESS,\n"
            "POLYMARKET_API_KEY, POLYMARKET_API_SECRET, POLYMARKET_API_PASSPHRASE."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("📊 Arb scanner", callback_data="poly_arb"),
        ],
        [
            InlineKeyboardButton("🐋 Whale copy", callback_data="poly_whales_menu"),
        ],
        [
            InlineKeyboardButton("⏰ Bet alerts", callback_data="poly_alerts"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Polymarket module ready.\n"
        f"Builder: {cfg.builder_name}\n"
        f"Wallet: `{cfg.wallet_address}`\n\n"
        "Choose a feature (stubs for now):"
    )

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def polymarket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "poly_arb":
        msg = await scan_polymarket_arbitrage()
        await query.edit_message_text(msg)
        return

    if data == "poly_alerts":
        msg = await subscribe_polymarket_alerts()
        await query.edit_message_text(msg)
        return

    # Whale copy submenu (step 1)
    if data == "poly_whales_menu":
        # For now, just show the worker text plus copy options for a mock trade.
        whales_text = await track_polymarket_whales()

        keyboard = [
            [
                InlineKeyboardButton("Copy 10%", callback_data="poly_whale_copy_10"),
                InlineKeyboardButton("Copy full", callback_data="poly_whale_copy_100"),
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="poly_back"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            whales_text + "\n\nSelect a copy size for the latest whale trade (simulated):",
            reply_markup=reply_markup,
        )
        return

    if data == "poly_back":
        # Simple back: re-run polymarket menu.
        # We call polymarket() using the same chat.
        fake_update = Update(
            update.update_id,
            message=None,
            callback_query=None,
        )
        fake_update._effective_chat = update.effective_chat  # type: ignore[attr-defined]
        await polymarket(update, context)
        return

    # Handle simulated copy sizes
    if data in ("poly_whale_copy_10", "poly_whale_copy_100"):
        pct = 0.1 if data.endswith("10") else 1.0
        trade = MOCK_LAST_WHALE_TRADE

        size_to_copy = trade["size_usdc"] * pct

        # Store in user data for confirm/cancel step.
        context.user_data["pending_poly_copy"] = {
            "market_title": trade["market_title"],
            "market_id": trade["market_id"],
            "outcome": trade["outcome"],
            "side": trade["side"],
            "size_usdc": size_to_copy,
            "price": trade["price"],
            "pct": pct,
        }

        text = (
            "Simulated copy trade (no real order yet):\n"
            f"Market: {trade['market_title']}\n"
            f"Outcome: {trade['outcome']} ({trade['side']})\n"
            f"Price: {trade['price']:.4f}\n"
            f"Size to copy: {size_to_copy:.2f} USDC ({int(pct*100)}% of whale)\n\n"
            "Confirm this simulated copy?"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="poly_whale_copy_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="poly_whale_copy_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)
        return

    if data == "poly_whale_copy_confirm":
        pending = context.user_data.get("pending_poly_copy")
        if not pending:
            await query.edit_message_text("No pending whale copy trade found.")
            return

        # Here we ONLY simulate; later we will call a real trader service.
        msg = (
            "✅ Simulated copy executed (no real order):\n"
            f"Market: {pending['market_title']}\n"
            f"Outcome: {pending['outcome']} ({pending['side']})\n"
            f"Price: {pending['price']:.4f}\n"
            f"Size: {pending['size_usdc']:.2f} USDC\n\n"
            "In step 2, this will place a real order on Polymarket."
        )
        context.user_data.pop("pending_poly_copy", None)
        await query.edit_message_text(msg)
        return

    if data == "poly_whale_copy_cancel":
        context.user_data.pop("pending_poly_copy", None)
        await query.edit_message_text("❌ Copy trade cancelled (no order sent).")
        return

    # Fallback
    await query.edit_message_text("Unknown Polymarket action.")


# -----------------------------
# Phoenix placeholder
# -----------------------------

async def phoenix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here we will add Phoenix V2 Solana arbitrage tools."
    )


# -----------------------------
# Register handlers
# -----------------------------

def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("connect_solana", connect_solana))
    application.add_handler(CommandHandler("connect_evm", connect_evm))
    application.add_handler(CommandHandler("sol_balance", sol_balance))
    application.add_handler(CommandHandler("polymarket", polymarket))
    application.add_handler(CommandHandler("phoenix", phoenix))

    # Callback handler for Polymarket inline buttons
    application.add_handler(CallbackQueryHandler(polymarket_callback, pattern=r"^poly_"))

    # Plain-text messages (used mainly for Solana address capture).
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_solana_address)
    )
