import os
import sys
import time
import requests
from datetime import datetime, timezone

RESET = "\033[0m"
BOLD = "\033[1m"

CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"

DEX_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
DEX_TOKEN_PAIRS_URL = "https://api.dexscreener.com/token-pairs/v1/{chain}/{address}"
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
# HELPERS
# ============================================================

def clear():
    os.system("clear")


def type_text(text, delay=0.015):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def line(char="─", length=62):
    print(char * length)


def pause():
    input(f"\n{GRAY}Press ENTER to continue...{RESET}")


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except:
        return default


def format_money(value):
    value = safe_float(value)

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.1f}K"

    return f"${value:.2f}"


def format_age(hours):
    if hours <= 0:
        return "UNKNOWN"

    if hours < 1:
        return f"{int(hours * 60)}m"

    if hours < 24:
        return f"{hours:.1f}h"

    return f"{hours / 24:.1f}d"


# ============================================================
# BOOT
# ============================================================

def boot_animation():
    clear()

    for logo in ["K", "KR", "KRY", "KRYP", "KRYPT"]:
        clear()
        print(f"{CYAN}{BOLD}{logo}{RESET}")
        time.sleep(0.15)

    clear()

    print(f"{CYAN}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                         KRYPT                                ║")
    print("║                    CRYPTO DASHBOARD                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(RESET)

    type_text(f"{BLUE}[SYSTEM] Initializing radar...", 0.01)
    type_text(f"{BLUE}[SYSTEM] Connecting market feeds...", 0.01)
    type_text(f"{BLUE}[SYSTEM] Loading security engine...", 0.01)
    type_text(f"{BLUE}[SYSTEM] Loading whale engine...", 0.01)
    type_text(f"{BLUE}[SYSTEM] Loading opportunity engine...", 0.01)
    type_text(f"{GREEN}[SYSTEM] ACCESS GRANTED{RESET}", 0.01)

    time.sleep(0.5)


# ============================================================
# API
# ============================================================

def get_latest_profiles():
    try:
        response = SESSION.get(
            DEX_PROFILES_URL,
            timeout=15
        )

        if response.status_code != 200:
            return []

        data = response.json()

        return data if isinstance(data, list) else []

    except Exception:
        return []


def get_token_pairs(chain, address):
    try:
        url = DEX_TOKEN_PAIRS_URL.format(
            chain=chain,
            address=address
        )

        response = SESSION.get(
            url,
            timeout=15
        )

        if response.status_code != 200:
            return []

        data = response.json()

        if isinstance(data, dict):
            return data.get("pairs", [])

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def choose_best_pair(pairs):
    if not pairs:
        return None

    valid = [
        p for p in pairs
        if isinstance(p, dict)
    ]

    if not valid:
        return None

    return max(
        valid,
        key=lambda p: safe_float(
            (p.get("liquidity") or {}).get("usd")
        )
    )


def get_solana_security(token_address):
    try:
        response = SESSION.get(
            GOPLUS_SOLANA_URL,
            params={
                "contract_addresses": token_address
            },
            timeout=15
        )

        if response.status_code != 200:
            return None

        data = response.json()
        result = data.get("result")

        if not isinstance(result, dict):
            return None

        if token_address in result:
            return result[token_address]

        if len(result) == 1:
            return next(iter(result.values()))

        return None

    except Exception:
        return None


# ============================================================
# TOKEN AGE
# ============================================================

def get_token_age_hours(pair):
    created = pair.get("pairCreatedAt")

    if not created:
        return 0

    try:
        created_seconds = float(created) / 1000
        now = datetime.now(timezone.utc).timestamp()

        age_hours = (now - created_seconds) / 3600

        if age_hours < 0:
            return 0

        return age_hours

    except:
        return 0


# ============================================================
# WHALE ENGINE
# ============================================================

def analyze_holders(security):

    result = {
        "available": False,
        "holder_count": 0,
        "top_holder_percent": 0.0,
        "top10_percent": 0.0,
        "locked_percent": 0.0,
        "risk": 0,
        "reasons": []
    }

    if not security:
        result["reasons"].append(
            "Holder data unavailable"
        )
        return result

    holders = security.get("holders")

    if not isinstance(holders, list) or not holders:
        result["reasons"].append(
            "Top holder data unavailable"
        )
        return result

    result["available"] = True

    result["holder_count"] = safe_int(
        security.get("holder_count")
    )

    percentages = []

    for holder in holders:

        if not isinstance(holder, dict):
            continue

        percent = safe_float(
            holder.get("percent")
        )

        percentages.append(percent)

    if not percentages:
        result["available"] = False
        result["reasons"].append(
            "Holder percentages unavailable"
        )
        return result

    percentages.sort(reverse=True)

    result["top_holder_percent"] = percentages[0] * 100
    result["top10_percent"] = sum(percentages) * 100

    locked_percent = 0.0

    for holder in holders:

        if not isinstance(holder, dict):
            continue

        if str(holder.get("is_locked")) == "1":

            locked_percent += (
                safe_float(holder.get("percent")) * 100
            )

    result["locked_percent"] = locked_percent

    top = result["top_holder_percent"]
    top10 = result["top10_percent"]

    if top >= 40:
        result["risk"] += 20
        result["reasons"].append(
            f"Extreme top-holder concentration ({top:.1f}%)"
        )

    elif top >= 25:
        result["risk"] += 12
        result["reasons"].append(
            f"High top-holder concentration ({top:.1f}%)"
        )

    elif top >= 15:
        result["risk"] += 6
        result["reasons"].append(
            f"Moderate top-holder concentration ({top:.1f}%)"
        )

    if top10 >= 80:
        result["risk"] += 15
        result["reasons"].append(
            f"Top 10 control {top10:.1f}%"
        )

    elif top10 >= 65:
        result["risk"] += 10
        result["reasons"].append(
            f"Top 10 control {top10:.1f}%"
        )

    elif top10 >= 50:
        result["risk"] += 5
        result["reasons"].append(
            f"Top 10 control {top10:.1f}%"
        )

    if locked_percent >= 30:
        result["reasons"].append(
            f"{locked_percent:.1f}% of top holders locked"
        )

    if not result["reasons"]:
        result["reasons"].append(
            "Holder distribution looks acceptable"
        )

    return result


# ============================================================
# WHALE ENGINE TEST
# ============================================================

def whale_test():

    clear()

    print(f"{CYAN}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                     WHALE ENGINE TEST                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(RESET)

    print(
        f"{GRAY}[WHALE] Searching live Solana tokens...{RESET}"
    )

    profiles = get_latest_profiles()

    if not profiles:
        print(
            f"{RED}[ERROR] Could not retrieve token profiles.{RESET}"
        )
        pause()
        return

    checked = 0

    for profile in profiles:

        chain = profile.get("chainId")
        address = profile.get("tokenAddress")

        if not chain or not address:
            continue

        if chain.lower() != "solana":
            continue

        pairs = get_token_pairs(
            chain,
            address
        )

        pair = choose_best_pair(pairs)

        if not pair:
            continue

        checked += 1

        print(
            f"{GRAY}[WHALE] Checking "
            f"{address[:8]}...{address[-6:]}{RESET}"
        )

        security = get_solana_security(address)

        if not security:
            continue

        whale = analyze_holders(security)

        if not whale["available"]:
            continue

        base_token = pair.get("baseToken") or {}

        symbol = base_token.get("symbol") or "UNKNOWN"
        name = base_token.get("name") or "UNKNOWN"

        clear()

        print(f"{CYAN}{BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                     WHALE ENGINE TEST                       ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(RESET)

        print(
            f"{WHITE}{BOLD}{symbol} — {name}{RESET}"
        )

        print(
            f"{GRAY}Solana{RESET}"
        )

        line()

        print(
            f"{WHITE}Token Address:{RESET}"
        )

        print(
            f"{GRAY}{address}{RESET}"
        )

        line()

        print(f"{CYAN}{BOLD}HOLDER DATA{RESET}")

        print(
            f"  Holder Count : "
            f"{whale['holder_count']:,}"
        )

        print(
            f"  Top Holder   : "
            f"{whale['top_holder_percent']:.2f}%"
        )

        print(
            f"  Top 10       : "
            f"{whale['top10_percent']:.2f}%"
        )

        print(
            f"  Locked       : "
            f"{whale['locked_percent']:.2f}%"
        )

        line()

        print(f"{CYAN}{BOLD}WHALE RISK{RESET}")

        print(
            f"  Risk Score   : "
            f"{whale['risk']}"
        )

        if whale["risk"] == 0:

            print(
                f"  Status       : "
                f"{GREEN}LOW{RESET}"
            )

        elif whale["risk"] < 20:

            print(
                f"  Status       : "
                f"{YELLOW}MODERATE{RESET}"
            )

        else:

            print(
                f"  Status       : "
                f"{RED}HIGH{RESET}"
            )

        print()

        print(f"{CYAN}{BOLD}ANALYSIS{RESET}")

        for reason in whale["reasons"]:

            print(
                f"  • {reason}"
            )

        line()

        print(f"{CYAN}{BOLD}RAW ENGINE STATUS{RESET}")

        print(
            f"  GoPlus       : "
            f"{GREEN}CONNECTED{RESET}"
        )

        print(
            f"  Holder Data  : "
            f"{GREEN}AVAILABLE{RESET}"
        )

        print(
            f"  Engine       : "
            f"{GREEN}OPERATIONAL{RESET}"
        )

        line()

        if whale["risk"] < 20:

            print(
                f"{GREEN}"
                "✓ Whale concentration is currently acceptable."
                f"{RESET}"
            )

        else:

            print(
                f"{RED}"
                "✗ Whale concentration is too high."
                f"{RESET}"
            )

        pause()

        return

    clear()

    print(
        f"{RED}[WHALE] No suitable live Solana token "
        f"with holder data was found.{RESET}"
    )

    print()

    print(
        f"{GRAY}"
        f"Solana candidates checked: {checked}"
        f"{RESET}"
    )

    print(
        f"{GRAY}"
        "GoPlus holder data may be unavailable for "
        "current candidates."
        f"{RESET}"
    )

    pause()


# ============================================================
# ANALYSIS ENGINE
# ============================================================

def calculate_analysis(pair, security):

    liquidity = safe_float(
        (pair.get("liquidity") or {}).get("usd")
    )

    volume = safe_float(
        (pair.get("volume") or {}).get("h24")
    )

    volume_5m = safe_float(
        (pair.get("volume") or {}).get("m5")
    )

    price_change_5m = safe_float(
        (pair.get("priceChange") or {}).get("m5")
    )

    price_change_1h = safe_float(
        (pair.get("priceChange") or {}).get("h1")
    )

    price_change_24h = safe_float(
        (pair.get("priceChange") or {}).get("h24")
    )

    txns = pair.get("txns") or {}

    txns_5m = txns.get("m5") or {}
    txns_1h = txns.get("h1") or {}

    buys_5m = safe_int(txns_5m.get("buys"))
    sells_5m = safe_int(txns_5m.get("sells"))

    buys_1h = safe_int(txns_1h.get("buys"))
    sells_1h = safe_int(txns_1h.get("sells"))

    age_hours = get_token_age_hours(pair)

    total_5m = buys_5m + sells_5m
    total_1h = buys_1h + sells_1h

    buy_ratio_5m = (
        buys_5m / total_5m
        if total_5m > 0 else 0
    )

    buy_ratio_1h = (
        buys_1h / total_1h
        if total_1h > 0 else 0
    )

    whale = analyze_holders(security)

    risk = 0
    risk_reasons = []

    if liquidity < 5000:
        risk += 15
        risk_reasons.append("Very low liquidity")

    elif liquidity < MIN_LIQUIDITY:
        risk += 8
        risk_reasons.append("Low liquidity")

    if volume < 1000:
        risk += 12
        risk_reasons.append("Very low volume")

    elif volume < MIN_VOLUME:
        risk += 6
        risk_reasons.append("Low volume")

    if price_change_5m <= -20:
        risk += 15
        risk_reasons.append("Heavy 5m dump")

    elif price_change_5m <= -10:
        risk += 8
        risk_reasons.append("Short-term weakness")

    if price_change_1h >= 200:
        risk += 12
        risk_reasons.append("Extreme 1h pump")

    elif price_change_1h >= 100:
        risk += 7
        risk_reasons.append("Strong 1h pump")

    if total_5m > 0 and buy_ratio_5m < 0.40:
        risk += 10
        risk_reasons.append("Sell pressure")

    if age_hours > 0 and age_hours < 1:
        risk += 5
        risk_reasons.append("Extremely new token")

    elif age_hours > 0 and age_hours < 6:
        risk += 2
        risk_reasons.append("Very new token")

    risk += whale["risk"]

    for reason in whale["reasons"]:
        if "acceptable" not in reason.lower():
            risk_reasons.append(
                f"Whale: {reason}"
            )

    security_available = security is not None
    security_safe = False

    if security is not None:

        mintable = safe_int(
            (security.get("mintable") or {}).get("status")
        )

        freezable = safe_int(
            (security.get("freezable") or {}).get("status")
        )

        closable = safe_int(
            (security.get("closable") or {}).get("status")
        )

        metadata_mutable = safe_int(
            (security.get("metadata_mutable") or {}).get("status")
        )

        non_transferable = safe_int(
            security.get("non_transferable")
        )

        security_safe = (
            mintable == 0
            and freezable == 0
            and closable == 0
            and metadata_mutable == 0
            and non_transferable == 0
        )

        if not security_safe:
            risk += 20
            risk_reasons.append(
                "Security flags detected"
            )

    else:
        risk += 15
        risk_reasons.append(
            "Security data unavailable"
        )

    opportunity = 0
    opportunity_reasons = []

    if liquidity >= 100_000:
        opportunity += 20
        opportunity_reasons.append(
            "Strong liquidity"
        )

    elif liquidity >= 50_000:
        opportunity += 16
        opportunity_reasons.append(
            "Good liquidity"
        )

    elif liquidity >= MIN_LIQUIDITY:
        opportunity += 10
        opportunity_reasons.append(
            "Acceptable liquidity"
        )

    if volume >= 1_000_000:
        opportunity += 20
        opportunity_reasons.append(
            "Exceptional volume"
        )

    elif volume >= 100_000:
        opportunity += 16
        opportunity_reasons.append(
            "Strong volume"
        )

    elif volume >= MIN_VOLUME:
        opportunity += 10
        opportunity_reasons.append(
            "Healthy volume"
        )

    if 10 <= price_change_1h <= 100:
        opportunity += 15
        opportunity_reasons.append(
            "Healthy 1h momentum"
        )

    elif 0 < price_change_1h < 10:
        opportunity += 7
        opportunity_reasons.append(
            "Positive 1h momentum"
        )

    if price_change_5m > 0:
        opportunity += 8
        opportunity_reasons.append(
            "Positive 5m momentum"
        )

    if buy_ratio_5m >= 0.60:
        opportunity += 12
        opportunity_reasons.append(
            "Strong buy pressure"
        )

    elif buy_ratio_5m >= 0.52:
        opportunity += 7
        opportunity_reasons.append(
            "Buy pressure positive"
        )

    if total_5m >= 100:
        opportunity += 8
        opportunity_reasons.append(
            "High recent activity"
        )

    elif total_5m >= 30:
        opportunity += 5
        opportunity_reasons.append(
            "Good recent activity"
        )

    if 1 <= age_hours <= 48:
        opportunity += 8
        opportunity_reasons.append(
            "Early-stage opportunity"
        )

    if security_safe:
        opportunity += 6
        opportunity_reasons.append(
            "Security checks passed"
        )

    if whale["available"]:

        if whale["top_holder_percent"] < 15:
            opportunity += 5
            opportunity_reasons.append(
                "Healthy top-holder distribution"
            )

        if whale["top10_percent"] < 50:
            opportunity += 4
            opportunity_reasons.append(
                "Healthy top-10 distribution"
            )

    opportunity = min(opportunity, 100)

    confidence = 100
    confidence_reasons = []

    if liquidity <= 0:
        confidence -= 20
        confidence_reasons.append(
            "Liquidity data missing"
        )

    if volume <= 0:
        confidence -= 15
        confidence_reasons.append(
            "Volume data missing"
        )

    if total_5m < 10:
        confidence -= 10
        confidence_reasons.append(
            "Low transaction sample"
        )

    if not security_available:
        confidence -= 20
        confidence_reasons.append(
            "Security data unavailable"
        )

    if not whale["available"]:
        confidence -= 15
        confidence_reasons.append(
            "Holder data unavailable"
        )

    if age_hours <= 0:
        confidence -= 10
        confidence_reasons.append(
            "Token age unknown"
        )

    confidence = max(
        0,
        min(confidence, 100)
    )

    critical_ok = (
        liquidity >= MIN_LIQUIDITY
        and volume >= MIN_VOLUME
        and security_available
        and security_safe
        and whale["available"]
        and whale["risk"] < 20
    )

    buy = (
        risk <= MAX_BUY_RISK
        and opportunity >= MIN_BUY_OPPORTUNITY
        and confidence >= MIN_BUY_CONFIDENCE
        and critical_ok
    )

    signal = "BUY" if buy else "RISK"

    krypt_score = (
        opportunity * 0.55
        + (100 - risk) * 0.30
        + confidence * 0.15
    )

    return {
        "risk": min(risk, 100),
        "opportunity": opportunity,
        "confidence": confidence,
        "krypt_score": round(krypt_score, 1),
        "signal": signal,

        "liquidity": liquidity,
        "volume": volume,
        "volume_5m": volume_5m,

        "price_change_5m": price_change_5m,
        "price_change_1h": price_change_1h,
        "price_change_24h": price_change_24h,

        "buys_5m": buys_5m,
        "sells_5m": sells_5m,
        "buys_1h": buys_1h,
        "sells_1h": sells_1h,

        "buy_ratio_5m": buy_ratio_5m,
        "buy_ratio_1h": buy_ratio_1h,

        "age_hours": age_hours,

        "security_available": security_available,
        "security_safe": security_safe,

        "whale": whale,

        "risk_reasons": risk_reasons,
        "opportunity_reasons": opportunity_reasons,
        "confidence_reasons": confidence_reasons
    }


# ============================================================
# SCANNER
# ============================================================

def scan_new_tokens():

    print(
        f"\n{CYAN}[RADAR] Scanning latest token profiles...{RESET}"
    )

    profiles = get_latest_profiles()

    if not profiles:
        print(
            f"{RED}[ERROR] Could not retrieve token profiles.{RESET}"
        )
        return []

    results = []

    profiles = profiles[:30]

    print(
        f"{GRAY}[RADAR] Profiles received: "
        f"{len(profiles)}{RESET}"
    )

    for index, profile in enumerate(profiles, 1):

        chain = profile.get("chainId")
        address = profile.get("tokenAddress")

        if not chain or not address:
            continue

        pairs = get_token_pairs(
            chain,
            address
        )

        pair = choose_best_pair(pairs)

        if not pair:
            continue

        security = None

        if chain.lower() == "solana":
            security = get_solana_security(address)

        analysis = calculate_analysis(
            pair,
            security
        )

        base_token = pair.get("baseToken") or {}

        symbol = base_token.get("symbol") or "UNKNOWN"
        name = base_token.get("name") or "UNKNOWN"

        results.append({
            "symbol": symbol,
            "name": name,
            "chain": chain,
            "address": address,
            "pair": pair,
            "analysis": analysis
        })

        signal_color = (
            GREEN
            if analysis["signal"] == "BUY"
            else RED
        )

        print(
            f"{GRAY}[{index:02d}/{len(profiles)}] "
            f"{symbol:<12} "
            f"KRYPT {analysis['krypt_score']:>5.1f} "
            f"{signal_color}"
            f"{analysis['signal']}"
            f"{RESET}"
        )

        time.sleep(0.15)

    results.sort(
        key=lambda x: x["analysis"]["krypt_score"],
        reverse=True
    )

    return results


# ============================================================
# BUY EXPLANATION
# ============================================================

def show_buy_explanation(item):

    analysis = item["analysis"]
    whale = analysis["whale"]

    clear()

    print(f"{GREEN}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    KRYPT BUY SIGNAL                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(RESET)

    print(
        f"{WHITE}{BOLD}"
        f"{item['symbol']} — {item['name']}"
        f"{RESET}"
    )

    print(
        f"{GRAY}Chain: {item['chain']}{RESET}"
    )

    line()

    print(
        f"{GREEN}🟢 BUY{RESET}"
        f"    "
        f"{WHITE}KRYPT SCORE: "
        f"{analysis['krypt_score']:.1f}/100{RESET}"
    )

    print()

    print(
        f"{WHITE}RISK        : "
        f"{GREEN}{analysis['risk']}%{RESET}"
    )

    print(
        f"{WHITE}OPPORTUNITY : "
        f"{GREEN}{analysis['opportunity']}/100{RESET}"
    )

    print(
        f"{WHITE}CONFIDENCE  : "
        f"{GREEN}{analysis['confidence']}%{RESET}"
    )

    line()

    print(f"{CYAN}{BOLD}WHY KRYPT LIKES IT{RESET}")

    for reason in analysis["opportunity_reasons"]:
        print(f"{GREEN}  + {reason}{RESET}")

    line()

    print(f"{CYAN}{BOLD}WHALE ANALYSIS{RESET}")

    if whale["available"]:

        print(
            f"  Holders       : "
            f"{whale['holder_count']:,}"
        )

        print(
            f"  Top holder    : "
            f"{whale['top_holder_percent']:.2f}%"
        )

        print(
            f"  Top 10        : "
            f"{whale['top10_percent']:.2f}%"
        )

        print(
            f"  Locked        : "
            f"{whale['locked_percent']:.2f}%"
        )

        if whale["risk"] == 0:
            print(
                f"  Whale Risk    : "
                f"{GREEN}LOW{RESET}"
            )

        elif whale["risk"] < 20:
            print(
                f"  Whale Risk    : "
                f"{YELLOW}MODERATE{RESET}"
            )

        else:
            print(
                f"  Whale Risk    : "
                f"{RED}HIGH{RESET}"
            )

        for reason in whale["reasons"]:
            print(
                f"  {GRAY}• {reason}{RESET}"
            )

    else:

        print(
            f"{RED}  Holder data unavailable{RESET}"
        )

    line()

    print(f"{CYAN}{BOLD}MARKET DATA{RESET}")

    print(
        f"  Liquidity : "
        f"{format_money(analysis['liquidity'])}"
    )

    print(
        f"  Volume 24h: "
        f"{format_money(analysis['volume'])}"
    )

    print(
        f"  Volume 5m : "
        f"{format_money(analysis['volume_5m'])}"
    )

    print(
        f"  5m Change : "
        f"{analysis['price_change_5m']:+.2f}%"
    )

    print(
        f"  1h Change : "
        f"{analysis['price_change_1h']:+.2f}%"
    )

    print(
        f"  24h Change: "
        f"{analysis['price_change_24h']:+.2f}%"
    )

    print(
        f"  Buy/Sell 5m: "
        f"{analysis['buys_5m']}/{analysis['sells_5m']}"
    )

    print(
        f"  Buy Pressure: "
        f"{analysis['buy_ratio_5m'] * 100:.1f}%"
    )

    print(
        f"  Token Age : "
        f"{format_age(analysis['age_hours'])}"
    )

    line()

    print(f"{CYAN}{BOLD}SECURITY{RESET}")

    if analysis["security_available"]:

        if analysis["security_safe"]:
            print(
                f"{GREEN}  ✓ Security checks passed{RESET}"
            )
        else:
            print(
                f"{RED}  ✗ Security flags detected{RESET}"
            )

    else:

        print(
            f"{RED}  ✗ Security data unavailable{RESET}"
        )

    line()

    print(f"{CYAN}{BOLD}DECISION LOGIC{RESET}")

    checks = [
        (
            f"Risk <= {MAX_BUY_RISK}%",
            analysis["risk"] <= MAX_BUY_RISK
        ),
        (
            f"Opportunity >= {MIN_BUY_OPPORTUNITY}",
            analysis["opportunity"] >= MIN_BUY_OPPORTUNITY
        ),
        (
            f"Confidence >= {MIN_BUY_CONFIDENCE}%",
            analysis["confidence"] >= MIN_BUY_CONFIDENCE
        ),
        (
            f"Liquidity >= {format_money(MIN_LIQUIDITY)}",
            analysis["liquidity"] >= MIN_LIQUIDITY
        ),
        (
            f"Volume >= {format_money(MIN_VOLUME)}",
            analysis["volume"] >= MIN_VOLUME
        ),
        (
            "Security = PASS",
            analysis["security_available"]
            and analysis["security_safe"]
        ),
        (
            "Whale risk acceptable",
            whale["available"]
            and whale["risk"] < 20
        )
    ]

    for label, passed in checks:

        color = GREEN if passed else RED
        status = "PASS" if passed else "FAIL"

        print(
            f"  {label:<34} "
            f"{color}{status}{RESET}"
        )

    print()

    print(
        f"{YELLOW}"
        "⚠ BUY = model signal, NOT a guaranteed profit."
        f"{RESET}"
    )

    pause()


# ============================================================
# RESULTS
# ============================================================

def show_results(results):

    clear()

    print(f"{CYAN}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                     CRYPTO RADAR                            ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(RESET)

    if not results:

        print(
            f"{RED}No valid tokens found.{RESET}"
        )

        pause()
        return

    buy_count = sum(
        1
        for item in results
        if item["analysis"]["signal"] == "BUY"
    )

    print(
        f"{WHITE}Candidates: {len(results)}    "
        f"{GREEN}BUY: {buy_count}{RESET}"
    )

    line()

    for index, item in enumerate(results[:10], 1):

        analysis = item["analysis"]

        if analysis["signal"] == "BUY":
            signal_color = GREEN
            signal_icon = "🟢"
        else:
            signal_color = RED
            signal_icon = "🔴"

        print(
            f"{WHITE}{index:02d}. "
            f"{BOLD}{item['symbol']}{RESET}"
            f" {GRAY}({item['chain']}){RESET}"
        )

        print(
            f"    Risk: {analysis['risk']:>3}%   "
            f"Opportunity: {analysis['opportunity']:>3}/100   "
            f"Confidence: {analysis['confidence']:>3}%"
        )

        print(
            f"    Liquidity: "
            f"{format_money(analysis['liquidity']):>9}   "
            f"Volume: "
            f"{format_money(analysis['volume']):>9}"
        )

        print(
            f"    5m: {analysis['price_change_5m']:+7.2f}%   "
            f"1h: {analysis['price_change_1h']:+7.2f}%   "
            f"Age: {format_age(analysis['age_hours'])}"
        )

        print(
            f"    Whale Top: "
            f"{analysis['whale']['top_holder_percent']:.1f}%   "
            f"Top10: "
            f"{analysis['whale']['top10_percent']:.1f}%"
        )

        print(
            f"    {signal_color}{signal_icon} "
            f"{analysis['signal']}{RESET}"
            f"   "
            f"KRYPT: {analysis['krypt_score']:.1f}"
        )

        if analysis["signal"] == "BUY":

            print(
                f"    {GREEN}"
                f"→ BUY explanation available"
                f"{RESET}"
            )

        print()

    line()

    print(
        f"{GREEN}BUY signals found: {buy_count}{RESET}"
    )

    print(
        f"{GRAY}"
        "Showing top 10 candidates by KRYPT score."
        f"{RESET}"
    )

    buy_items = [
        item
        for item in results
        if item["analysis"]["signal"] == "BUY"
    ]

    if buy_items:

        print()
        print(
            f"{CYAN}[B] View BUY explanation{RESET}"
        )

        choice = input(
            f"\n{WHITE}Selection: {RESET}"
        ).strip().lower()

        if choice == "b":

            show_buy_explanation(
                buy_items[0]
            )

            return

    pause()


# ============================================================
# CRYPTO RADAR
# ============================================================

def crypto_radar():

    while True:

        clear()

        print(f"{CYAN}{BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                      CRYPTO RADAR                           ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(RESET)

        print(
            f"{WHITE}[01] SCAN NEW / UNKNOWN COINS{RESET}"
        )

        print(
            f"{WHITE}[02] LOW RISK TOP PICKS{RESET}"
        )

        print(
            f"{WHITE}[03] BUY RULES{RESET}"
        )

        print(
            f"{WHITE}[04] WHALE ENGINE TEST{RESET}"
        )

        print(
            f"{WHITE}[00] BACK{RESET}"
        )

        choice = input(
            f"\n{CYAN}KRYPT > {RESET}"
        ).strip()

        if choice in ("01", "1"):

            results = scan_new_tokens()
            show_results(results)

        elif choice in ("02", "2"):

            results = scan_new_tokens()

            low_risk = [
                item
                for item in results
                if item["analysis"]["risk"] <= MAX_BUY_RISK
            ]

            low_risk.sort(
                key=lambda x: (
                    x["analysis"]["opportunity"],
                    x["analysis"]["confidence"]
                ),
                reverse=True
            )

            show_results(low_risk)

        elif choice in ("03", "3"):

            clear()

            print(
                f"{CYAN}{BOLD}KRYPT BUY RULES{RESET}"
            )

            line()

            print(
                f"{GREEN}"
                "BUY requires ALL of the following:"
                f"{RESET}\n"
            )

            print(
                f"  Risk         <= {MAX_BUY_RISK}%"
            )

            print(
                f"  Opportunity  >= "
                f"{MIN_BUY_OPPORTUNITY}/100"
            )

            print(
                f"  Confidence   >= "
                f"{MIN_BUY_CONFIDENCE}%"
            )

            print(
                f"  Liquidity    >= "
                f"{format_money(MIN_LIQUIDITY)}"
            )

            print(
                f"  Volume 24h   >= "
                f"{format_money(MIN_VOLUME)}"
            )

            print(
                "  Security     = PASS"
            )

            print(
                "  Whale Risk   = ACCEPTABLE"
            )

            print()

            print(
                f"{YELLOW}"
                "Fırsatı kaçırmak, kötü bir işlemi önermekten daha iyidir."
                f"{RESET}"
            )

            print(
                f"{GRAY}"
                "BUY is a model signal, not a guarantee."
                f"{RESET}"
            )

            pause()

        elif choice in ("04", "4"):

            whale_test()

        elif choice in ("00", "0"):

            return

        else:

            print(
                f"{RED}Invalid selection.{RESET}"
            )

            time.sleep(1)


# ============================================================
# NOTES
# ============================================================

def notes():

    clear()

    print(
        f"{CYAN}{BOLD}NOTES{RESET}"
    )

    line()

    print(
        f"{GRAY}"
        "Notes module will be expanded later."
        f"{RESET}"
    )

    pause()


# ============================================================
# SYSTEM
# ============================================================

def system_menu():

    clear()

    print(
        f"{CYAN}{BOLD}SYSTEM{RESET}"
    )

    line()

    print(
        f"{GREEN}KRYPT Dashboard online{RESET}"
    )

    print(
        f"{WHITE}Radar Engine : ONLINE{RESET}"
    )

    print(
        f"{WHITE}Security     : ONLINE{RESET}"
    )

    print(
        f"{WHITE}Whale Engine : ONLINE{RESET}"
    )

    print(
        f"{WHITE}Opportunity  : ONLINE{RESET}"
    )

    print(
        f"{WHITE}Signal Mode  : BUY / RISK{RESET}"
    )

    pause()


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():

    while True:

        clear()

        print(f"{CYAN}{BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                         KRYPT                                ║")
        print("║                    CRYPTO DASHBOARD                          ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║                                                              ║")
        print("║  [01] CRYPTO RADAR                                           ║")
        print("║  [02] NOTES                                                  ║")
        print("║  [03] SYSTEM                                                 ║")
        print("║  [00] EXIT                                                   ║")
        print("║                                                              ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(RESET)

        choice = input(
            f"{CYAN}KRYPT > {RESET}"
        ).strip()

        if choice in ("01", "1"):

            crypto_radar()

        elif choice in ("02", "2"):

            notes()

        elif choice in ("03", "3"):

            system_menu()

        elif choice in ("00", "0"):

            clear()

            print(
                f"{CYAN}KRYPT shutting down...{RESET}"
            )

            time.sleep(0.5)

            sys.exit()

        else:

            print(
                f"{RED}Invalid selection.{RESET}"
            )

            time.sleep(1)


# ============================================================
# START
# ============================================================

def main():

    boot_animation()
    dashboard()


if __name__ == "__main__":
    main()
