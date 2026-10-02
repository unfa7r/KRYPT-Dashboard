import os
import json
import time
import requests
import io
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone

import krypt

MIN_SCORE = 90
SCAN_INTERVAL = int(os.getenv("KRYPT_SCAN_INTERVAL", "120"))

STATE_FILE = "krypt_signals_state.json"
USERS_FILE = "krypt_signal_users.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def money(value):
    try:
        value = float(value or 0)
    except Exception:
        value = 0

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.1f}K"

    return f"${value:.2f}"


def make_signal(item):
    pair = item.get("pair") or {}
    analysis = item.get("analysis") or {}
    txns = pair.get("txns") or {}
    m5 = txns.get("m5") or {}

    address = item.get("address", "")
    chain = item.get("chain", "unknown")
    score = float(analysis.get("krypt_score", 0) or 0)

    return {
        "signal_id": f"{chain}:{address}",
        "signal": analysis.get("signal"),
        "score": score,
        "symbol": item.get("symbol", "UNKNOWN"),
        "name": item.get("name", "UNKNOWN"),
        "chain": chain,
        "address": address,
        "market_cap": pair.get("marketCap") or 0,
        "price": pair.get("priceUsd") or 0,
        "liquidity": (pair.get("liquidity") or {}).get("usd") or 0,
        "volume_5m": (pair.get("volume") or {}).get("m5") or 0,
        "buys_5m": m5.get("buys") or 0,
        "sells_5m": m5.get("sells") or 0,
        "signal_time": datetime.now(timezone.utc).isoformat()
    }


def should_send(signal, state):
    alerts = state.setdefault("alerts", {})
    key = signal["signal_id"]
    previous = alerts.get(key)

    if not previous:
        return True

    old_score = float(previous.get("score", 0) or 0)
    old_time = float(previous.get("time", 0) or 0)

    if signal["score"] < MIN_SCORE:
        return False

    if signal["score"] >= old_score + 5 and time.time() - old_time >= 900:
        return True

    return False


def record_alert(signal, state):
    alerts = state.setdefault("alerts", {})

    alerts[signal["signal_id"]] = {
        "score": signal["score"],
        "time": time.time()
    }

    cutoff = time.time() - 86400

    state["alerts"] = {
        key: value
        for key, value in alerts.items()
        if float(value.get("time", 0) or 0) >= cutoff
    }

    save_state(state)


def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(set(users)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def poll_users(state):
    users = load_users()
    offset = int(state.get("telegram_update_offset", 0) or 0)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    try:
        response = requests.get(
            url,
            params={
                "offset": offset,
                "timeout": 1
            },
            timeout=5
        )

        if not response.ok:
            return users

        data = response.json()

        if not data.get("ok"):
            return users

        updates = data.get("result") or []

        for update in updates:
            update_id = update.get("update_id")

            if isinstance(update_id, int):
                state["telegram_update_offset"] = update_id + 1

            message = update.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            text = str(message.get("text") or "").strip().lower()

            if chat_id is None:
                continue

            if text.startswith("/start"):
                if chat_id not in users:
                    users.append(chat_id)
                    print(
                        f"[KRYPT SIGNALS] User registered: "
                        f"{chat_id}"
                    )

            elif text.startswith("/stop"):
                if chat_id in users:
                    users.remove(chat_id)
                    print(
                        f"[KRYPT SIGNALS] User removed: "
                        f"{chat_id}"
                    )

        save_users(users)
        save_state(state)

    except Exception as e:
        print(f"[KRYPT SIGNALS] User polling error: {e}")

    return users


def send_telegram(signal, users):
    if not BOT_TOKEN:
        print("[KRYPT SIGNALS] Telegram bot token missing.")
        return False

    if not users:
        print("[KRYPT SIGNALS] No registered users.")
        return False

    message = (
        "🚨 KRYPT SIGNALS\\n\\n"
        f"🪙 {signal['name']} ({signal['symbol']})\\n"
        f"🎯 KRYPT Score: {signal['score']:.1f}\\n"
        "🟢 Signal: BUY\\n\\n"
        f"💰 Market Cap: {money(signal['market_cap'])}\\n"
        f"💵 Price: ${signal['price']}\\n"
        f"💧 Liquidity: {money(signal['liquidity'])}\\n"
        f"📊 Volume 5m: {money(signal['volume_5m'])}\\n"
        f"📈 Buys/Sells: {signal['buys_5m']}/{signal['sells_5m']}\\n\\n"
        f"⛓ Chain: {signal['chain']}\\n"
        f"🕐 {signal['signal_time']}\\n\\n"
        f"📋 Mint:\\n`{signal['address']}`"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    sent = 0
    failed = 0
    invalid_users = []

    for chat_id in list(users):
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=15
            )

            if response.ok:
                sent += 1
            else:
                failed += 1

                try:
                    error = response.json()
                    if error.get("error_code") in (400, 403):
                        invalid_users.append(chat_id)
                except Exception:
                    pass

        except Exception as e:
            failed += 1
            print(
                f"[KRYPT SIGNALS] Telegram error "
                f"for {chat_id}: {e}"
            )

        time.sleep(0.2)

    if invalid_users:
        users[:] = [
            user for user in users
            if user not in invalid_users
        ]
        save_users(users)

    print(
        f"[KRYPT SIGNALS] Telegram sent: "
        f"{signal['symbol']} {signal['score']:.1f} "
        f"| users: {sent} | failed: {failed}"
    )

    return sent > 0


def run_scan(state):
    print()
    print("=" * 56)
    print("              KRYPT SIGNALS SCAN")
    print("=" * 56)
    print(
        f"[KRYPT SIGNALS] Automatic scan started "
        f"| threshold: {MIN_SCORE}"
    )

    try:
        original_clear = krypt.clear
        krypt.clear = lambda: None
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                results = krypt.scan_new_tokens()
        finally:
            krypt.clear = original_clear
    except Exception as e:
        print(f"[KRYPT SIGNALS] Scan error: {e}")
        return

    if not isinstance(results, list):
        print("[KRYPT SIGNALS] No scan results.")
        return

    candidates = []

    for item in results:
        analysis = item.get("analysis") or {}

        if (
            analysis.get("signal") == "BUY"
            and float(analysis.get("krypt_score", 0) or 0) >= MIN_SCORE
        ):
            candidates.append(make_signal(item))

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    print(
        f"[KRYPT SIGNALS] Scan complete | "
        f"tokens: {len(results)} | "
        f"90+ BUY: {len(candidates)}"
    )

    users = poll_users(state)

    for signal in candidates:
        if not should_send(signal, state):
            print(
                f"[KRYPT SIGNALS] Already alerted: "
                f"{signal['symbol']} {signal['score']:.1f}"
            )
            continue

        if send_telegram(signal, users):
            record_alert(signal, state)

        time.sleep(1)


def main():
    print("========================================")
    print("          KRYPT SIGNALS")
    print("========================================")
    print(f"Minimum score : {MIN_SCORE}")
    print(f"Scan interval : {SCAN_INTERVAL}s")
    print("Automatic mode: ON")
    print()

    if not BOT_TOKEN:
        print("[KRYPT SIGNALS] Telegram bot token missing.")
        print()
        print("Set TELEGRAM_BOT_TOKEN first.")
        return

    state = load_state()

    while True:
        run_scan(state)

        print()
        print(
            f"[KRYPT SIGNALS] Next scan in "
            f"{SCAN_INTERVAL} seconds..."
        )

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
