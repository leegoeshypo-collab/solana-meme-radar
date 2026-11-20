import os
import json
import time
import requests
from datetime import datetime, timezone

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY_USD", "8000"))
MIN_MARKET_CAP = float(os.getenv("MIN_MARKET_CAP_USD", "10000"))
MAX_MARKET_CAP = float(os.getenv("MAX_MARKET_CAP_USD", "800000"))
MAX_AGE_HOURS = float(os.getenv("MAX_AGE_HOURS", "36"))
MIN_VOLUME = float(os.getenv("MIN_24H_VOLUME_USD", "3000"))

SEEN_FILE = "seen.json"

def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_latest_profiles():
    try:
        r = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Error fetching profiles: {e}")
    return []

def get_token_data(token_address):
    try:
        url = f"https://api.dexscreener.com/tokens/v1/solana/{token_address}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                return data[0]  # best pair
    except Exception as e:
        print(f"Error fetching token {token_address}: {e}")
    return None

def is_interesting(pair):
    if not pair:
        return False

    # Liquidity
    liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
    if liquidity < MIN_LIQUIDITY:
        return False

    # Market Cap / FDV
    mcap = float(pair.get("marketCap") or pair.get("fdv") or 0)
    if mcap < MIN_MARKET_CAP or mcap > MAX_MARKET_CAP:
        return False

    # Volume
    volume = float(pair.get("volume", {}).get("h24") or 0)
    if volume < MIN_VOLUME:
        return False

    # Age
    created = pair.get("pairCreatedAt")
    if created:
        age_hours = (time.time() * 1000 - created) / (1000 * 60 * 60)
        if age_hours > MAX_AGE_HOURS:
            return False

    return True

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Solana Meme Radar scan...")

    seen = load_seen()
    profiles = get_latest_profiles()
    new_alerts = 0

    for profile in profiles:
        if profile.get("chainId") != "solana":
            continue

        address = profile.get("tokenAddress")
        if not address or address in seen:
            continue

        pair = get_token_data(address)
        if not is_interesting(pair):
            continue

        # Build alert
        base = pair.get("baseToken", {})
        symbol = base.get("symbol", "???")
        name = base.get("name", "Unknown")
        price = pair.get("priceUsd", "0")
        liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
        mcap = float(pair.get("marketCap") or pair.get("fdv") or 0)
        volume = float(pair.get("volume", {}).get("h24") or 0)
        url = pair.get("url", f"https://dexscreener.com/solana/{address}")

        message = (
            f"🚀 <b>New Solana Meme Detected</b>\n\n"
            f"<b>{symbol}</b> — {name}\n"
            f"💰 Price: ${price}\n"
            f"💧 Liquidity: ${liquidity:,.0f}\n"
            f"📊 Market Cap: ${mcap:,.0f}\n"
            f"📈 24h Volume: ${volume:,.0f}\n\n"
            f"<a href='{url}'>View on DexScreener</a>"
        )

        send_telegram(message)
        seen.add(address)
        new_alerts += 1
        print(f"Alert sent for {symbol} ({address})")

        time.sleep(1.2)  # be nice to the API

    save_seen(seen)
    print(f"Scan finished. New alerts: {new_alerts}")

if __name__ == "__main__":
    main()
