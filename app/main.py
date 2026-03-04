"""ASGI entrypoint for the Telegram trading bot webhook."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from app.handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env.local", override=True)


WEBHOOK_PATH = "/webhook"

fastapi_app = FastAPI(title="Telegram Trading Bot")

telegram_application: Optional[Application] = None
_app_init_lock = asyncio.Lock()


def _get_token() -> str:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token or token == "YOUR_TOKEN":
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing or still set to placeholder; "
            "update .env.local or your environment."
        )
    return token


def _get_webhook_url() -> Optional[str]:
    url = os.getenv("WEBHOOK_URL")
    return url.strip() if url else None


def create_application() -> Application:
    application = ApplicationBuilder().token(_get_token()).build()
    register_handlers(application)
    return application


async def ensure_webhook(application: Application) -> None:
    webhook_url = _get_webhook_url()
    if not webhook_url:
        return

    target_url = webhook_url.rstrip("/") + WEBHOOK_PATH
    info = await application.bot.get_webhook_info()
    if info.url != target_url:
        await application.bot.set_webhook(url=target_url)
        logger.info("Webhook set to %s", target_url)


async def get_application() -> Application:
    global telegram_application
    if telegram_application is None:
        async with _app_init_lock:
            if telegram_application is None:
                telegram_application = create_application()
                await telegram_application.initialize()
                await telegram_application.start()
                await ensure_webhook(telegram_application)
    return telegram_application


@fastapi_app.on_event("shutdown")
async def on_shutdown() -> None:
    if telegram_application:
        await telegram_application.stop()
        await telegram_application.shutdown()


@fastapi_app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    application = await get_application()

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON payload") from exc

    try:
        update = Update.de_json(data=payload, bot=application.bot)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Telegram update") from exc

    await application.process_update(update)
    return {"ok": True}


def run_polling() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = create_application()
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    run_polling()
