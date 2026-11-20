import os, json, time, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MIN_LIQ = float(os.getenv("MIN_LIQUIDITY_USD", "10000"))
MIN_MCAP = float(os.getenv("MIN_MARKET_CAP_USD", "10000"))
MAX_MCAP = float(os.getenv("MAX_MARKET_CAP_USD", "500000"))
MAX_AGE_H = float(os.getenv("MAX_AGE_HOURS", "24"))
MIN_VOL = float(os.getenv("MIN_24H_VOLUME_USD", "5000"))
STATE = Path("seen.json")

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SolanaMemeRadar/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID, "text": message, "disable_web_page_preview": "true"
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=25) as r:
        result = json.loads(r.read().decode())
        if not result.get("ok"):
            raise RuntimeError("Telegram rejected the message")

def load_seen():
    try:
        return set(json.loads(STATE.read_text()))
    except Exception:
        return set()

def fmt(value):
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "n/a"

def main():
    seen = load_seen()
    candidates = {}

    # These endpoints are public discovery feeds, not a complete feed of every new Solana pool.
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/token-boosts/latest/v1",
    ]
    for endpoint in endpoints:
        try:
            rows = get_json(endpoint)
            if isinstance(rows, list):
                for item in rows:
                    if item.get("chainId") == "solana" and item.get("tokenAddress"):
                        candidates[item["tokenAddress"]] = item
        except Exception as exc:
            print(f"Feed error: {exc}")

    new_seen = set(seen)
    alerts = []

    addresses = list(candidates.keys())
    # DexScreener supports up to 30 token addresses per request.
    for start in range(0, len(addresses), 30):
        batch = addresses[start:start+30]
        if not batch:
            continue
        try:
            url = "https://api.dexscreener.com/tokens/v1/solana/" + ",".join(batch)
            pairs = get_json(url)
        except Exception as exc:
            print(f"Pair lookup error: {exc}")
            continue

        best = {}
        for p in pairs if isinstance(pairs, list) else []:
            token = (p.get("baseToken") or {}).get("address")
            if not token:
                continue
            liq = (p.get("liquidity") or {}).get("usd") or 0
            if token not in best or liq > ((best[token].get("liquidity") or {}).get("usd") or 0):
                best[token] = p

        for address, p in best.items():
            if address in seen:
                continue
            liq = (p.get("liquidity") or {}).get("usd") or 0
            mcap = p.get("marketCap") or p.get("fdv") or 0
            vol = (p.get("volume") or {}).get("h24") or 0
            created = p.get("pairCreatedAt")
            age_h = None
            if created:
                age_h = max(0, (time.time() * 1000 - created) / 3600000)

            if liq < MIN_LIQ or not (MIN_MCAP <= mcap <= MAX_MCAP) or vol < MIN_VOL:
                continue
            if age_h is not None and age_h > MAX_AGE_H:
                continue

            # Only mark a token after it qualifies for an alert. This lets it
            # qualify on a later scan if liquidity/volume improves.
            new_seen.add(address)

            tx = p.get("txns") or {}
            h1 = tx.get("h1") or {}
            buys, sells = h1.get("buys", 0), h1.get("sells", 0)
            name = (p.get("baseToken") or {}).get("name", "Unknown")
            symbol = (p.get("baseToken") or {}).get("symbol", "?")
            url = p.get("url") or f"https://dexscreener.com/solana/{address}"
            socials = (p.get("info") or {}).get("socials") or []
            social_text = ", ".join(
                f'{s.get("type","social")}: @{s.get("handle","")}'
                for s in socials if s.get("handle")
            ) or "No social handles listed"

            age_text = f"{age_h:.1f} hours" if age_h is not None else "unknown"
            alerts.append(
                f"🚨 SOLANA MEMECOIN RADAR\n\n"
                f"{name} (${symbol})\n"
                f"Liquidity: {fmt(liq)}\n"
                f"Market cap/FDV: {fmt(mcap)}\n"
                f"24h volume: {fmt(vol)}\n"
                f"Pair age: {age_text}\n"
                f"1h buys/sells: {buys}/{sells}\n"
                f"Socials: {social_text}\n\n"
                f"Chart: {url}\n"
                f"Contract: {address}\n\n"
                f"⚠️ Discovery alert only. Not a buy signal. Verify contract, authorities, holders and liquidity yourself."
            )

    STATE.write_text(json.dumps(sorted(new_seen), indent=2))
    for alert in alerts[:15]:
        try:
            send_telegram(alert)
        except Exception as exc:
            print(f"Telegram error: {exc}")
    print(f"Checked {len(candidates)} candidate tokens; sent {min(len(alerts),15)} alerts.")

if __name__ == "__main__":
    main()
