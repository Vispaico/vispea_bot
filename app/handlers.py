"""Telegram command handlers."""

from __future__ import annotations

import datetime as dt

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
)

from app.services import (
    get_polymarket_config,
    scan_polymarket_arbitrage,
    track_polymarket_whales,
    subscribe_polymarket_alerts,
)


WELCOME_TEXT = (
    "Welcome to the multi-chain trading assistant. "
    "Use /help to see available commands."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = [
        "/start - Welcome message",
        "/help - List commands",
        "/status - Health check",
        "/connect_solana - Connect Phantom / Solana wallets (placeholder)",
        "/connect_evm - Connect MetaMask / Trust Wallet (placeholder)",
        "/polymarket - Polymarket tools (arb, whales, alerts menu)",
        "/phoenix - Phoenix V2 arbitrage tools (placeholder)",
    ]
    await update.message.reply_text("Available commands:\n" + "\n".join(commands))


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    await update.message.reply_text(f"alive ({now})")


async def connect_solana(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Here we will connect Phantom / Solana wallets.")


async def connect_evm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here we will connect MetaMask / Trust Wallet (EVM) via WalletConnect."
    )


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
            InlineKeyboardButton("🐋 Whale copy", callback_data="poly_whales"),
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
    elif data == "poly_whales":
        msg = await track_polymarket_whales()
    elif data == "poly_alerts":
        msg = await subscribe_polymarket_alerts()
    else:
        msg = "Unknown Polymarket action."

    await query.edit_message_text(msg)


async def phoenix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here we will add Phoenix V2 Solana arbitrage tools."
    )


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("connect_solana", connect_solana))
    application.add_handler(CommandHandler("connect_evm", connect_evm))
    application.add_handler(CommandHandler("polymarket", polymarket))
    application.add_handler(CommandHandler("phoenix", phoenix))

    # Callback handler for Polymarket inline buttons
    application.add_handler(CallbackQueryHandler(polymarket_callback, pattern=r"^poly_"))
