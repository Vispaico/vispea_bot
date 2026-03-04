"""Telegram command handlers."""

from __future__ import annotations

import datetime as dt

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


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
        "/polymarket - Polymarket tools (placeholder)",
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
    await update.message.reply_text(
        "Here we will add Polymarket tools (arb, whale copy, bet alerts)."
    )


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
