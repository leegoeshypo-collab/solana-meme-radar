import os
import json
import time
import requests
from datetime import datetime, timezone

# === CONFIG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Filters tuned for small account early plays
MIN_LIQUIDITY = 15000          # Higher = safer
MIN_MARKET_CAP = 25000
MAX_MARKET_CAP = 450000
MAX_AGE_HOURS = 28
MIN_VOLUME_24H = 8000
MIN_BUY_SELL_RATIO = 1.15      # Must have more buys than sells

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
        print("Missing Telegram credentials")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=12)
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

def get_best_pair(token_address):
    try:
        url = f"https://api.dexscreener.com/tokens/v1/solana/{token_address}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            pairs = r.json()
            if pairs:
                # Prefer the pair with highest liquidity
                return max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd") or 0))
    except Exception as e:
        print(f"Error getting pair for {token_address}: {e}")
    return None

def is_good_candidate(pair, profile):
    if not pair:
        return False

    # Liquidity
    liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
    if liquidity < MIN_LIQUIDITY:
        return False

    # Market Cap
    mcap = float(pair.get("marketCap") or pair.get("fdv") or 0)
    if mcap < MIN_MARKET_CAP or mcap > MAX_MARKET_CAP:
        return False

    # 24h Volume
    volume = float(pair.get("volume", {}).get("h24") or 0)
    if volume < MIN_VOLUME_24H:
        return False

    # Age
    created = pair.get("pairCreatedAt")
    if created:
        age_hours = (time.time() * 1000 - created) / (1000 * 60 * 60)
        if age_hours > MAX_AGE_HOURS or age_hours < 0.4:  # Avoid brand new (<25 mins)
            return False

    # Buy pressure (last hour)
    txns = pair.get("txns", {}).get("h1", {})
    buys = txns.get("buys", 0)
    sells = txns.get("sells", 0)
    if sells == 0:
        ratio = 999
    else:
        ratio = buys / sells

    if ratio < MIN_BUY_SELL_RATIO:
        return False

    # Prefer tokens that have social links
    links = profile.get("links") or []
    has_social = any(link.get("type") in ["twitter", "telegram"] or "x.com" in str(link.get("url", "")).lower() for link in links)

    # Score it lightly
    score = 0
    if has_social:
        score += 2
    if liquidity > 30000:
        score += 1
    if ratio > 1.4:
        score += 1
    if volume > 25000:
        score += 1

    return score >= 2  # Must hit at least 2 quality points

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting improved scan...")

    seen = load_seen()
    profiles = get_latest_profiles()
    new_alerts = 0

    for profile in profiles:
        if profile.get("chainId") != "solana":
            continue

        address = profile.get("tokenAddress")
        if not address or address in seen:
            continue

        pair = get_best_pair(address)
        if not is_good_candidate(pair, profile):
            continue

        # Build nice alert
        base = pair.get("baseToken", {})
        symbol = base.get("symbol", "???")
        name = base.get("name", "Unknown")
        price = pair.get("priceUsd", "0")
        liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
        mcap = float(pair.get("marketCap") or pair.get("fdv") or 0)
        volume = float(pair.get("volume", {}).get("h24") or 0)
        url = pair.get("url", f"https://dexscreener.com/solana/{address}")

        txns = pair.get("txns", {}).get("h1", {})
        buys = txns.get("buys", 0)
        sells = txns.get("sells", 0)

        message = (
            f"🚀 <b>Early Solana Candidate</b>\n\n"
            f"<b>{symbol}</b> — {name}\n\n"
            f"💰 Price: ${price}\n"
            f"💧 Liquidity: ${liquidity:,.0f}\n"
            f"📊 Market Cap: ${mcap:,.0f}\n"
            f"📈 24h Vol: ${volume:,.0f}\n"
            f"🟢 Buys (1h): {buys} | 🔴 Sells: {sells}\n\n"
            f"<a href='{url}'>Open on DexScreener</a>"
        )

        send_telegram(message)
        seen.add(address)
        new_alerts += 1
        print(f"Alert: {symbol} | Liq: ${liquidity:,.0f} | MCap: ${mcap:,.0f}")

        time.sleep(1.3)

    save_seen(seen)
    print(f"Scan complete. New alerts sent: {new_alerts}")

if __name__ == "__main__":
    main()
