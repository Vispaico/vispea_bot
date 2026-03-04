"""ASGI entrypoint for the Telegram trading bot webhook."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from app.handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


WEBHOOK_PATH = "/webhook"

fastapi_app = FastAPI(title="Telegram Trading Bot")


def _get_token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token or token == "YOUR_TOKEN":
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing or still set to placeholder; "
            "update .env.local or your environment."
        )
    return token


def create_application() -> Application:
    application = ApplicationBuilder().token(_get_token()).build()
    register_handlers(application)
    return application


@fastapi_app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON payload") from exc

    application = create_application()

    try:
        update = Update.de_json(data=payload, bot=application.bot)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Telegram update") from exc

    await application.initialize()
    await application.process_update(update)
    await application.shutdown()
    return {"ok": True}


def run_polling() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = create_application()
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    run_polling()
