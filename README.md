# Solana Meme Coin Radar (free starter)

A small scheduled scanner that checks DexScreener's latest token-profile and latest-boost feeds for Solana tokens, looks up their market data, and sends Telegram alerts when they pass your filters.

## Important limitations
- This is a discovery aid, not a trading signal or safety checker.
- DexScreener's profile/boost feeds are **not** a complete feed of every newly-created Solana pool. This will miss many tokens.
- Boost/profile appearance can be paid promotion. A boost is not evidence of organic demand.
- It does not currently search X/Twitter posts. X API access is pay-per-use; this starter avoids paid X access.
- Market cap may fall back to FDV when market cap is unavailable.
- The scanner's filters are rough starting values. A token passing them can still be a scam or rug pull.

## Set up from an iPhone

1. Create a Telegram bot:
   - Open Telegram and search for `@BotFather`.
   - Send `/newbot`, follow the prompts, and copy the bot token. Keep it secret.
2. Open your new bot using the link BotFather gives you, press **Start**, and send it a message such as `hello`.
3. Get your Telegram chat ID:
   - In a browser, open `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates` (replace the placeholder with your token).
   - Find `"chat":{"id": ...}` in the response. Copy that number.
   - Do not share the token or the full URL with anyone. If exposed, revoke it with BotFather and create a new one.
4. Create a GitHub account if you don't have one.
5. Create a **public** GitHub repository (for example `solana-meme-radar`). GitHub Actions standard runners are free for public repositories.
6. Upload all files from this ZIP, preserving the `.github/workflows/radar.yml` folder path.
7. In the repository, open **Settings → Secrets and variables → Actions → New repository secret**:
   - `TELEGRAM_BOT_TOKEN` = your BotFather token
   - `TELEGRAM_CHAT_ID` = your chat ID
8. Open **Actions**, enable workflows if prompted, select **Solana Meme Coin Radar**, and press **Run workflow** to test it.
9. Check Telegram for alerts. The scheduled workflow runs approximately every 15 minutes, though GitHub may delay scheduled runs.

## Current filters
- Solana only
- Minimum liquidity: $10,000
- Market cap (or FDV fallback): $10,000–$500,000
- Pair age: up to 24 hours when the API supplies a creation time
- 24-hour volume: at least $5,000

You can edit these values in `.github/workflows/radar.yml`.

## Security
- Never put bot tokens in the Python file or commit them to GitHub.
- Add secrets only in GitHub repository secrets.
- If the repository is public, remember that the source code and `seen.json` are public; your Telegram credentials are not.
- Do not connect a wallet or give this bot permission to trade. This starter only sends alerts.

## What it checks
- DexScreener latest token profiles
- DexScreener latest boosted tokens
- DexScreener token pair data (liquidity, market cap/FDV, volume, pair age, 1-hour buys/sells, listed social handles)
