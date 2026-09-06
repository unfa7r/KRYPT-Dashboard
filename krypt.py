import os
import sys
import time
import requests
from datetime import datetime, timezone

# ============================================================
# KRYPT DASHBOARD
# REAL CRYPTO RADAR ENGINE
# ============================================================

RESET = "\033[0m"
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"

DEX_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
DEX_TOKEN_PAIRS_URL = "https://api.dexscreener.com/token-pairs/v1"
GOPLUS_SOLANA_URL = "https://api.gopluslabs.io/api/v1/solana/token_security/"

MAX_BUY_RISK = 20
MIN_BUY_OPPORTUNITY = 75
MIN_BUY_CONFIDENCE = 75
MIN_LIQUIDITY = 10000
MIN_VOLUME = 5000

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "KRYPT-Dashboard/1.0"
})


# ============================================================
# TERMINAL
# ============================================================

def clear():
    os.system("clear")


def type_text(text, color=CYAN, speed=0.01):
    for char in text:
        sys.stdout.write(color + char + RESET)
        sys.stdout.flush()
        time.sleep(speed)
    print()


def line(char="═"):
    print(CYAN + char * 54 + RESET)


def pause():
    input("\nPress ENTER...")


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# BOOT
# ============================================================

def boot_animation():
    clear()

    for text in ["K", "KR", "KRY", "KRYP", "KRYPT"]:
        clear()
        print("\n")
        print(CYAN + "╔════════════════════════════════════════════════════╗" + RESET)
        print(CYAN + "║                                                    ║" + RESET)
        print(WHITE + f"║{text.center(52)}║" + RESET)
        print(CYAN + "║                                                    ║" + RESET)
        print(CYAN + "╚════════════════════════════════════════════════════╝" + RESET)
        time.sleep(0.10)

    clear()

    print(CYAN + "╔════════════════════════════════════════════════════╗" + RESET)
    print(CYAN + "║                                                    ║" + RESET)
    print(WHITE + "║                    K R Y P T                       ║" + RESET)
    print(CYAN + "║                D A S H B O A R D                   ║" + RESET)
    print(CYAN + "║                                                    ║" + RESET)
    print(CYAN + "╚════════════════════════════════════════════════════╝" + RESET)

    print()
    type_text(">> INITIALIZING KRYPT CORE...", CYAN)
    type_text(">> MARKET ENGINE .......... ONLINE", BLUE)
    type_text(">> SECURITY ENGINE ........ ONLINE", GREEN)
    type_text(">> RISK ENGINE ............ ONLINE", YELLOW)
    type_text(">> ACCESS GRANTED", GREEN)

    time.sleep(0.5)


# ============================================================
# API FUNCTIONS
# ============================================================

def get_latest_profiles():
    try:
        response = SESSION.get(DEX_PROFILES_URL, timeout=15)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            return data

        return []

    except requests.RequestException:
        return []


def get_token_pairs(chain_id, token_address):
    try:
        url = f"{DEX_TOKEN_PAIRS_URL}/{chain_id}/{token_address}"

        response = SESSION.get(url, timeout=15)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            return data

        return []

    except requests.RequestException:
        return []


def choose_best_pair(pairs):
    if not pairs:
        return None

    return max(
        pairs,
        key=lambda pair: safe_float(
            pair.get("liquidity", {}).get("usd")
        )
    )


def get_solana_security(token_address):
    result = {
        "available": False,
        "safe": False,
        "issues": []
    }

    try:
        response = SESSION.get(
            GOPLUS_SOLANA_URL,
            params={"contract_addresses": token_address},
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        token_data = (
            data.get("result", {})
            .get(token_address, {})
        )

        if not token_data:
            return result

        result["available"] = True

        checks = [
            "mintable",
            "freezable",
            "closable",
            "non_transferable"
        ]

        for check in checks:
            value = token_data.get(check)

            if isinstance(value, dict):
                value = value.get("status", "1")

            value = str(value)

            if check == "non_transferable":
                if value != "0":
                    result["issues"].append(check)
            else:
                if value != "0":
                    result["issues"].append(check)

        result["safe"] = len(result["issues"]) == 0

        return result

    except (
        requests.RequestException,
        ValueError
    ):
        return result


# ============================================================
# ANALYSIS ENGINE
# ============================================================

def get_token_age_hours(pair):
    created_at = pair.get("pairCreatedAt")

    if not created_at:
        return None

    try:
        created = datetime.fromtimestamp(
            int(created_at) / 1000,
            tz=timezone.utc
        )

        now = datetime.now(timezone.utc)

        age_seconds = (
            now - created
        ).total_seconds()

        return max(age_seconds / 3600, 0)

    except (ValueError, TypeError, OSError):
        return None


def calculate_analysis(pair, security):
    liquidity = safe_float(
        pair.get("liquidity", {}).get("usd")
    )

    volume_24h = safe_float(
        pair.get("volume", {}).get("h24")
    )

    volume_1h = safe_float(
        pair.get("volume", {}).get("h1")
    )

    volume_5m = safe_float(
        pair.get("volume", {}).get("m5")
    )

    price_5m = safe_float(
        pair.get("priceChange", {}).get("m5")
    )

    price_1h = safe_float(
        pair.get("priceChange", {}).get("h1")
    )

    price_24h = safe_float(
        pair.get("priceChange", {}).get("h24")
    )

    market_cap = safe_float(
        pair.get("marketCap")
    )

    if market_cap <= 0:
        market_cap = safe_float(
            pair.get("fdv")
        )

    txns_5m = pair.get("txns", {}).get("m5", {})

    buys_5m = safe_int(
        txns_5m.get("buys")
    )

    sells_5m = safe_int(
        txns_5m.get("sells")
    )

    age_hours = get_token_age_hours(pair)

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk = 0

    # Liquidity risk
    if liquidity < 5000:
        risk += 35
    elif liquidity < 10000:
        risk += 25
    elif liquidity < 25000:
        risk += 15
    elif liquidity < 50000:
        risk += 8

    # Volume quality
    if volume_24h < 1000:
        risk += 20
    elif volume_24h < 5000:
        risk += 12
    elif volume_24h < 10000:
        risk += 6

    # Extreme short-term crash
    if price_5m <= -30:
        risk += 30
    elif price_5m <= -15:
        risk += 18
    elif price_5m <= -8:
        risk += 8

    # Extreme pump risk
    if price_1h >= 200:
        risk += 20
    elif price_1h >= 100:
        risk += 12
    elif price_1h >= 50:
        risk += 6

    # Buy/sell imbalance
    total_txns = buys_5m + sells_5m

    if total_txns >= 10:
        sell_ratio = sells_5m / total_txns

        if sell_ratio >= 0.70:
            risk += 15
        elif sell_ratio >= 0.60:
            risk += 8

    # New token uncertainty
    if age_hours is None:
        risk += 10
    elif age_hours < 1:
        risk += 15
    elif age_hours < 6:
        risk += 10
    elif age_hours < 24:
        risk += 5

    # Security
    if not security["available"]:
        risk += 20
    elif not security["safe"]:
        risk += 40

    # Missing critical data
    if liquidity <= 0:
        risk += 25

    risk = min(max(risk, 0), 100)

    # --------------------------------------------------------
    # OPPORTUNITY
    # --------------------------------------------------------

    opportunity = 0

    # Liquidity score
    if liquidity >= 100000:
        opportunity += 20
    elif liquidity >= 50000:
        opportunity += 16
    elif liquidity >= 25000:
        opportunity += 12
    elif liquidity >= 10000:
        opportunity += 8

    # Volume
    if volume_24h >= 500000:
        opportunity += 20
    elif volume_24h >= 100000:
        opportunity += 16
    elif volume_24h >= 25000:
        opportunity += 12
    elif volume_24h >= 5000:
        opportunity += 6

    # Momentum
    if 0 < price_1h <= 50:
        opportunity += 15
    elif 50 < price_1h <= 100:
        opportunity += 10
    elif price_1h > 100:
        opportunity += 5

    # 5 minute momentum
    if 0 < price_5m <= 20:
        opportunity += 10
    elif -5 <= price_5m <= 0:
        opportunity += 5

    # Buy pressure
    if total_txns >= 10:
        buy_ratio = buys_5m / total_txns

        if buy_ratio >= 0.65:
            opportunity += 10
        elif buy_ratio >= 0.55:
            opportunity += 6

    # Activity
    if total_txns >= 500:
        opportunity += 10
    elif total_txns >= 100:
        opportunity += 7
    elif total_txns >= 25:
        opportunity += 4

    # Early discovery bonus
    if age_hours is not None:
        if 1 <= age_hours <= 24:
            opportunity += 10
        elif 24 < age_hours <= 72:
            opportunity += 5

    # Security bonus
    if security["available"] and security["safe"]:
        opportunity += 15

    opportunity = min(max(opportunity, 0), 100)

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    confidence = 100

    if liquidity <= 0:
        confidence -= 30

    if volume_24h <= 0:
        confidence -= 20

    if age_hours is None:
        confidence -= 10

    if not security["available"]:
        confidence -= 25

    if total_txns < 5:
        confidence -= 10

    confidence = min(max(confidence, 0), 100)

    # --------------------------------------------------------
    # STRICT BUY FILTER
    # --------------------------------------------------------

    buy_allowed = (
        risk <= MAX_BUY_RISK
        and opportunity >= MIN_BUY_OPPORTUNITY
        and confidence >= MIN_BUY_CONFIDENCE
        and liquidity >= MIN_LIQUIDITY
        and volume_24h >= MIN_VOLUME
        and security["available"]
        and security["safe"]
    )

    signal = "BUY" if buy_allowed else "RISK"

    krypt_score = (
        opportunity * 0.55
        + (100 - risk) * 0.30
        + confidence * 0.15
    )

    return {
        "risk": round(risk),
        "opportunity": round(opportunity),
        "confidence": round(confidence),
        "krypt_score": round(krypt_score),
        "signal": signal,
        "liquidity": liquidity,
        "volume_24h": volume_24h,
        "volume_1h": volume_1h,
        "volume_5m": volume_5m,
        "price_5m": price_5m,
        "price_1h": price_1h,
        "price_24h": price_24h,
        "market_cap": market_cap,
        "buys_5m": buys_5m,
        "sells_5m": sells_5m,
        "age_hours": age_hours,
        "security": security
    }


# ============================================================
# TOKEN SCANNER
# ============================================================

def scan_new_tokens():
    profiles = get_latest_profiles()

    results = []

    if not profiles:
        return results

    # İlk sürümde gereksiz API yükünü azaltmak için
    # en fazla 30 yeni token taranıyor.
    for profile in profiles[:30]:
        chain_id = profile.get("chainId")
        token_address = profile.get("tokenAddress")

        if not chain_id or not token_address:
            continue

        pairs = get_token_pairs(
            chain_id,
            token_address
        )

        pair = choose_best_pair(pairs)

        if not pair:
            continue

        # Şimdilik güvenlik motoru Solana için aktif.
        if chain_id == "solana":
            security = get_solana_security(
                token_address
            )
        else:
            security = {
                "available": False,
                "safe": False,
                "issues": ["security_check_unavailable"]
            }

        analysis = calculate_analysis(
            pair,
            security
        )

        results.append({
            "chain": chain_id,
            "address": token_address,
            "pair": pair,
            "analysis": analysis
        })

        # Rate limit için kısa bekleme
        time.sleep(0.15)

    results.sort(
        key=lambda item: item["analysis"]["krypt_score"],
        reverse=True
    )

    return results


# ============================================================
# DISPLAY
# ============================================================

def format_money(value):
    value = safe_float(value)

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.1f}K"

    return f"${value:.2f}"


def format_age(hours):
    if hours is None:
        return "UNKNOWN"

    if hours < 1:
        return f"{int(hours * 60)} min"

    if hours < 24:
        return f"{hours:.1f}h"

    return f"{hours / 24:.1f}d"


def show_results(results):
    clear()

    print(CYAN + "╔════════════════════════════════════════════════════╗" + RESET)
    print(WHITE + "║             KRYPT LOW RISK RADAR                   ║" + RESET)
    print(CYAN + "╠════════════════════════════════════════════════════╣" + RESET)

    if not results:
        print(RED + "║        NO ANALYZABLE TOKENS FOUND                  ║" + RESET)
        print(CYAN + "╚════════════════════════════════════════════════════╝" + RESET)
        pause()
        return

    top_results = results[:10]

    for index, item in enumerate(top_results, start=1):
        pair = item["pair"]
        analysis = item["analysis"]

        token = pair.get("baseToken", {})
        symbol = token.get("symbol", "UNKNOWN")
        name = token.get("name", "UNKNOWN")

        signal = analysis["signal"]

        signal_color = (
            GREEN if signal == "BUY"
            else RED
        )

        print(
            WHITE
            + f"\n#{index} {symbol} | {name[:25]}"
            + RESET
        )

        print(
            f"   CHAIN: {item['chain']}"
        )

        print(
            f"   RISK: {analysis['risk']}% | "
            f"OPPORTUNITY: {analysis['opportunity']}/100"
        )

        print(
            f"   CONFIDENCE: {analysis['confidence']}% | "
            f"KRYPT SCORE: {analysis['krypt_score']}/100"
        )

        print(
            f"   LIQUIDITY: {format_money(analysis['liquidity'])} | "
            f"VOLUME: {format_money(analysis['volume_24h'])}"
        )

        print(
            f"   5M: {analysis['price_5m']:+.2f}% | "
            f"1H: {analysis['price_1h']:+.2f}%"
        )

        print(
            f"   AGE: {format_age(analysis['age_hours'])}"
        )

        print(
            signal_color
            + f"   SIGNAL: {signal}"
            + RESET
        )

        print(
            CYAN
            + "   ─────────────────────────────────────────────"
            + RESET
        )

    print()
    print(YELLOW + "BUY requires strict low-risk conditions." + RESET)
    print(YELLOW + "RISK means one or more safety conditions failed." + RESET)

    pause()


# ============================================================
# CRYPTO RADAR
# ============================================================

def crypto_radar():
    while True:
        clear()

        print(CYAN + "╔════════════════════════════════════════════════════╗" + RESET)
        print(WHITE + "║                 CRYPTO RADAR                       ║" + RESET)
        print(CYAN + "╠════════════════════════════════════════════════════╣" + RESET)
        print(WHITE + "║                                                    ║" + RESET)
        print(WHITE + "║  [01] SCAN NEW / UNKNOWN COINS                     ║" + RESET)
        print(WHITE + "║  [02] LOW RISK TOP PICKS                           ║" + RESET)
        print(WHITE + "║  [03] BUY RULES                                    ║" + RESET)
        print(WHITE + "║                                                    ║" + RESET)
        print(RED + "║  [00] BACK                                         ║" + RESET)
        print(CYAN + "╚════════════════════════════════════════════════════╝" + RESET)

        choice = input(CYAN + "\nKRYPT://RADAR > " + RESET)

        if choice in ["1", "01", "2", "02"]:
            clear()

            type_text(
                ">> SEARCHING NEW TOKEN PROFILES...",
                CYAN
            )

            type_text(
                ">> CHECKING MARKET PAIRS...",
                BLUE
            )

            type_text(
                ">> ANALYZING SECURITY...",
                GREEN
            )

            type_text(
                ">> CALCULATING RISK...",
                YELLOW
            )

            results = scan_new_tokens()

            show_results(results)

        elif choice in ["3", "03"]:
            clear()

            print(GREEN + "KRYPT BUY RULES" + RESET)
            print()
            print(f"RISK <= {MAX_BUY_RISK}%")
            print(f"OPPORTUNITY >= {MIN_BUY_OPPORTUNITY}/100")
            print(f"CONFIDENCE >= {MIN_BUY_CONFIDENCE}%")
            print(f"LIQUIDITY >= ${MIN_LIQUIDITY:,}")
            print(f"24H VOLUME >= ${MIN_VOLUME:,}")
            print("SECURITY = AVAILABLE + SAFE")
            print()
            print(RED + "Any critical failure = RISK" + RESET)

            pause()

        elif choice in ["00", "0"]:
            break

        else:
            type_text(
                ">> INVALID COMMAND",
                RED
            )
            time.sleep(0.8)


# ============================================================
# NOTES
# ============================================================

def notes():
    clear()

    print(YELLOW + "╔════════════════════════════════════════════════════╗" + RESET)
    print(YELLOW + "║                     NOTES                          ║" + RESET)
    print(YELLOW + "╚════════════════════════════════════════════════════╝" + RESET)

    print()
    print("KRYPT NOTES MODULE")
    print("Coming soon.")

    pause()


# ============================================================
# SYSTEM
# ============================================================

def system_info():
    clear()

    print(GREEN + "╔════════════════════════════════════════════════════╗" + RESET)
    print(GREEN + "║                    SYSTEM                          ║" + RESET)
    print(GREEN + "╚════════════════════════════════════════════════════╝" + RESET)

    print()
    print("KRYPT CORE        : ONLINE")
    print("MARKET ENGINE     : DEX SCREENER")
    print("SECURITY ENGINE   : GOPLUS")
    print("RISK ENGINE       : ACTIVE")
    print("SIGNAL ENGINE     : BUY / RISK")
    print("AI ASSISTANT      : REMOVED")

    pause()


# ============================================================
# MAIN DASHBOARD
# ============================================================

def dashboard():
    clear()

    print(CYAN + "╔════════════════════════════════════════════════════╗" + RESET)
    print(CYAN + "║                                                    ║" + RESET)
    print(WHITE + "║                    K R Y P T                       ║" + RESET)
    print(CYAN + "║                D A S H B O A R D                   ║" + RESET)
    print(CYAN + "║                                                    ║" + RESET)
    print(CYAN + "╠════════════════════════════════════════════════════╣" + RESET)
    print(GREEN + "║  SYSTEM      ONLINE                                ║" + RESET)
    print(GREEN + "║  SECURITY    ACTIVE                                ║" + RESET)
    print(BLUE + "║  MARKET      LIVE                                  ║" + RESET)
    print(CYAN + "╠════════════════════════════════════════════════════╣" + RESET)
    print(WHITE + "║                                                    ║" + RESET)
    print(WHITE + "║  [01]  CRYPTO RADAR                                ║" + RESET)
    print(WHITE + "║  [02]  NOTES                                       ║" + RESET)
    print(WHITE + "║  [03]  SYSTEM                                      ║" + RESET)
    print(WHITE + "║                                                    ║" + RESET)
    print(RED + "║  [00]  EXIT                                        ║" + RESET)
    print(CYAN + "╚════════════════════════════════════════════════════╝" + RESET)


# ============================================================
# START
# ============================================================

def main():
    boot_animation()

    while True:
        dashboard()

        choice = input(
            CYAN
            + "\nKRYPT://ROOT > "
            + RESET
        )

        if choice in ["1", "01"]:
            crypto_radar()

        elif choice in ["2", "02"]:
            notes()

        elif choice in ["3", "03"]:
            system_info()

        elif choice in ["00", "0"]:
            clear()
            type_text(
                ">> TERMINATING KRYPT CORE...",
                RED
            )

            print(
                RED
                + "\nKRYPT SYSTEM OFFLINE"
                + RESET
            )

            break

        else:
            type_text(
                ">> INVALID COMMAND",
                RED
            )

            time.sleep(0.8)


if __name__ == "__main__":
    main()
