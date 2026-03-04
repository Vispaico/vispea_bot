# vispea_bot

Async Telegram bot scaffold for future multi-chain trading tools, built with `python-telegram-bot` and FastAPI, deployable on Vercel as a serverless webhook handler.

## Prerequisites
- Python 3.11
- Env vars: `TELEGRAM_BOT_TOKEN`, `WEBHOOK_URL` (public HTTPS base, e.g. `https://your-vercel-app.vercel.app`).

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local development (polling)
```bash
export TELEGRAM_BOT_TOKEN=YOUR_TOKEN
python3 -m app.main
```

## Local webhook testing (with a tunnel like ngrok)
```bash
export TELEGRAM_BOT_TOKEN=YOUR_TOKEN
export WEBHOOK_URL=https://your-public-tunnel.example
python3 -m uvicorn app.main:fastapi_app --reload --host 0.0.0.0 --port 8000
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d url="${WEBHOOK_URL}/webhook"
```

## Deploy to Vercel
1. Set Vercel env vars `TELEGRAM_BOT_TOKEN` and `WEBHOOK_URL`.
2. Deploy: `vercel --prod` (after login). The `vercel.json` maps `/webhook` to `app/main.py`.
3. Set the webhook once deployed:
```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d url="${WEBHOOK_URL}/webhook"
```

## Commands
- `/start`, `/help`, `/status`
- `/connect_solana`, `/connect_evm`, `/polymarket`, `/phoenix` (placeholders)
