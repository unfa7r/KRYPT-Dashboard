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
USER_ID_FILE = "krypt_user_id.json"

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


def send_telegram(signal, user_id):
    if not BOT_TOKEN:
        print("[KRYPT SIGNALS] Telegram bot token missing.")
        return False

    if not user_id:
        print("[KRYPT SIGNALS] Telegram user ID missing.")
        return False

    message = signal

    text = (
        f"🚨 *KRYPT SIGNALS*\n\n"
        f"🚀 *{message['symbol']}* ({message['name']})\n"
        f"🔗 Chain: {message['chain'].upper()}\n"
        f"📊 Score: {message['score']:.1f}\n"
        f"💰 Market Cap: {money(message['market_cap'])}\n"
        f"💵 Price: {message['price']}\n"
        f"💧 Liquidity: {money(message['liquidity'])}\n"
        f"📈 Vol 5m: {money(message['volume_5m'])}\n"
        f"🟢 Buys 5m: {message['buys_5m']}\n"
        f"🔴 Sells 5m: {message['sells_5m']}\n\n"
        f"`{message['address']}`"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": user_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )

        if response.ok:
            print(f"[KRYPT SIGNALS] Telegram sent -> {user_id}")
            return True

        print(f"[KRYPT SIGNALS] Telegram error: {response.status_code} {response.text}")
        return False

    except Exception as e:
        print(f"[KRYPT SIGNALS] Telegram exception: {e}")
        return False

def run_scan(state, user_id):
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


    for signal in candidates:
        if not should_send(signal, state):
            print(
                f"[KRYPT SIGNALS] Already alerted: "
                f"{signal['symbol']} {signal['score']:.1f}"
            )
            continue

        if send_telegram(signal, user_id):
            record_alert(signal, state)

        time.sleep(1)


def main():
    if not BOT_TOKEN:
        print("Set TELEGRAM_BOT_TOKEN first.")
        return

    user_id = os.getenv("TELEGRAM_USER_ID", "").strip()

    if not user_id and os.path.exists(USER_ID_FILE):
        try:
            with open(USER_ID_FILE, "r", encoding="utf-8") as f:
                user_id = json.load(f).get("user_id", "").strip()
        except Exception:
            user_id = ""

    if not user_id:
        print()
        print("[KRYPT SIGNALS] Telegram User ID gerekli.")
        print("User ID'nizi öğrenmek için:")
        print("1. Telegram'da @userinfobot'u açın.")
        print("2. /start gönderin.")
        print("3. Size verilen ID'yi aşağıya girin.")
        print()
        user_id = input("Telegram User ID: ").strip()

        if user_id:
            with open(USER_ID_FILE, "w", encoding="utf-8") as f:
                json.dump({"user_id": user_id}, f)

    if not user_id:
        print("Telegram User ID is required.")
        return

    state = load_state()

    print(f"[KRYPT SIGNALS] Started -> Telegram User ID: {user_id}")
    print(f"[KRYPT SIGNALS] Scan interval: {SCAN_INTERVAL}s")

    while True:
        try:
            run_scan(state, user_id)
            save_state(state)
        except KeyboardInterrupt:
            print("\n[KRYPT SIGNALS] Stopped.")
            break
        except Exception as e:
            print(f"[KRYPT SIGNALS] Scan error: {e}")

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
