import os
import sys
import time
import requests
import json
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
DEX_BOOSTS_URL = "https://api.dexscreener.com/token-boosts/latest/v1"
DEX_TOP_BOOSTS_URL = "https://api.dexscreener.com/token-boosts/top/v1"
DEX_TOKEN_PAIRS_URL = "https://api.dexscreener.com/token-pairs/v1/{chain}/{address}"
GOPLUS_SOLANA_URL = "https://api.gopluslabs.io/api/v1/solana/token_security/"
GOPLUS_EVM_URL = "https://api.gopluslabs.io/api/v1/token_security/{chain_id}"

GOPLUS_CHAIN_IDS = {
    "ethereum": "1",
    "bsc": "56",
    "arbitrum": "42161",
    "polygon": "137",
    "base": "8453",
    "optimism": "10",
    "avalanche": "43114",
    "fantom": "250",
    "linea": "59144",
    "scroll": "534352",
    "zksync": "324",
    "mantle": "5000",
    "blast": "81457",
    "mode": "34443",
    "manta": "169",
    "gnosis": "100",
    "celo": "42220",
    "moonbeam": "1284",
    "moonriver": "1285",
    "opbnb": "204",
    "berachain": "80094",
    "unichain": "130",
    "sonic": "146",
    "monad": "143",
    "plasma": "9745",
    "robinhood": "4663",
}

MAX_BUY_RISK = 20
MIN_BUY_OPPORTUNITY = 75
MIN_BUY_CONFIDENCE = 75

MIN_LIQUIDITY = 10000
MIN_VOLUME = 5000

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "KRYPT-Dashboard/2.0"
})


# ============================================================
# RADAR MEMORY
# ============================================================

RADAR_MEMORY_FILE = "krypt_radar_memory.json"
POSITIONS_FILE = "krypt_positions.json"
NOTES_FILE = "krypt_notes.json"
MAX_MEMORY_TOKENS = 20


def load_positions():
    if not os.path.exists(POSITIONS_FILE):
        return []

    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_positions(positions):
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)



def load_radar_memory():

    try:

        if not os.path.exists(
            RADAR_MEMORY_FILE
        ):
            return []

        with open(
            RADAR_MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):
            return []

        now = datetime.now(timezone.utc)
        valid = []

        for item in data:

            if not isinstance(item, dict):
                continue

            saved_at = item.get("saved_at")

            if not saved_at:

                item["saved_at"] = now.isoformat()
                valid.append(item)
                continue

            try:

                saved_time = datetime.fromisoformat(
                    saved_at
                )

                if saved_time.tzinfo is None:
                    saved_time = saved_time.replace(
                        tzinfo=timezone.utc
                    )

                age = (
                    now - saved_time
                ).total_seconds()

                if age < 86400:
                    valid.append(item)

            except Exception:
                continue

        if len(valid) != len(data):

            with open(
                RADAR_MEMORY_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    valid,
                    file,
                    indent=2
                )

        return valid

    except Exception:
        return []


def save_radar_memory(results):

    try:

        memory = []

        for item in results:

            analysis = item.get(
                "analysis",
                {}
            )

            if analysis.get("signal") != "BUY":
                continue

            chain = item.get("chain")
            address = item.get("address")

            if not chain or not address:
                continue

            memory.append({
                "chainId": chain,
                "tokenAddress": address,
                "saved_at": datetime.now(
                    timezone.utc
                ).isoformat()
            })

        old_memory = load_radar_memory()

        combined = memory + old_memory

        # Re-add recently strong BUY candidates so they are
        # not lost when DexScreener discovery results rotate.
        try:
            memory = load_radar_memory()

            for saved in memory:

                if isinstance(saved, dict):
                    profiles.append(saved)

        except Exception:
            pass

        unique = []
        seen = set()

        for item in combined:

            chain = item.get("chainId")
            address = item.get("tokenAddress")

            if not chain or not address:
                continue

            key = (
                str(chain).lower(),
                str(address).lower()
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(item)

        with open(
            RADAR_MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                unique[:MAX_MEMORY_TOKENS],
                file,
                indent=2
            )

    except Exception:
        pass


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

        print(
            f"{CYAN}{BOLD}{logo}{RESET}"
        )

        time.sleep(0.15)

    clear()

    print(f"{CYAN}{BOLD}")

    print(
        "╔══════════════════════════════════════════════════════════════╗"
    )

    print(
        "║                         KRYPT                                ║"
    )

    print(
        "║                    CRYPTO DASHBOARD                          ║"
    )

    print(
        "╚══════════════════════════════════════════════════════════════╝"
    )

    print(RESET)

    type_text(
        f"{BLUE}[SYSTEM] Initializing radar...",
        0.01
    )

    type_text(
        f"{BLUE}[SYSTEM] Connecting market feeds...",
        0.01
    )

    type_text(
        f"{BLUE}[SYSTEM] Loading security engine...",
        0.01
    )

    type_text(
        f"{BLUE}[SYSTEM] Loading whale engine...",
        0.01
    )

    type_text(
        f"{BLUE}[SYSTEM] Loading opportunity engine...",
        0.01
    )

    type_text(
        f"{GREEN}[SYSTEM] ACCESS GRANTED{RESET}",
        0.01
    )

    time.sleep(0.5)


# ============================================================
# NOTES STORAGE
# ============================================================

def load_notes():

    try:

        if not os.path.exists(
            NOTES_FILE
        ):
            return []

        with open(
            NOTES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data if isinstance(data, list) else []

    except Exception:
        return []


def save_notes(notes):

    try:

        with open(
            NOTES_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                notes,
                file,
                indent=2,
                ensure_ascii=False
            )

        return True

    except Exception:
        return False


def add_note():

    clear()

    print(
        f"{CYAN}{BOLD}"
        "NEW NOTE"
        f"{RESET}"
    )

    line()

    note = input(
        f"{WHITE}Write note: {RESET}"
    ).strip()

    if not note:

        print(
            f"{RED}Note cannot be empty.{RESET}"
        )

        pause()

        return

    notes = load_notes()

    notes.append({
        "text": note,
        "created": datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    })

    if save_notes(notes):

        print(
            f"{GREEN}Note saved successfully.{RESET}"
        )

    else:

        print(
            f"{RED}Could not save note.{RESET}"
        )

    pause()


def view_notes():

    clear()

    print(
        f"{CYAN}{BOLD}"
        "YOUR NOTES"
        f"{RESET}"
    )

    line()

    notes = load_notes()

    if not notes:

        print(
            f"{GRAY}No notes found.{RESET}"
        )

        pause()

        return

    for index, note in enumerate(
        notes,
        1
    ):

        print(
            f"{CYAN}[{index:02d}]{RESET} "
            f"{WHITE}{note.get('text', '')}{RESET}"
        )

        print(
            f"{GRAY}"
            f"     {note.get('created', '')}"
            f"{RESET}"
        )

        print()

    pause()


def delete_note():

    clear()

    print(
        f"{CYAN}{BOLD}"
        "DELETE NOTE"
        f"{RESET}"
    )

    line()

    notes = load_notes()

    if not notes:

        print(
            f"{GRAY}No notes to delete.{RESET}"
        )

        pause()

        return

    for index, note in enumerate(
        notes,
        1
    ):

        print(
            f"{CYAN}[{index:02d}]{RESET} "
            f"{note.get('text', '')}"
        )

    print()

    choice = input(
        f"{WHITE}Select note number (0 cancel): {RESET}"
    ).strip()

    if choice == "0":

        return

    try:

        index = int(choice) - 1

        if index < 0 or index >= len(notes):
            raise ValueError

    except ValueError:

        print(
            f"{RED}Invalid selection.{RESET}"
        )

        pause()

        return

    deleted = notes.pop(index)

    if save_notes(notes):

        print(
            f"{GREEN}"
            f"Deleted: {deleted.get('text', '')}"
            f"{RESET}"
        )

    else:

        print(
            f"{RED}Could not update notes.{RESET}"
        )

    pause()


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
        profiles = data if isinstance(data, list) else []

        try:
            boost_response = SESSION.get(
                DEX_BOOSTS_URL,
                timeout=15
            )

            if boost_response.status_code == 200:
                boosts = boost_response.json()

                if isinstance(boosts, list):
                    profiles.extend(boosts)

        except Exception:
            pass

        try:
            top_boost_response = SESSION.get(
                DEX_TOP_BOOSTS_URL,
                timeout=15
            )

            if top_boost_response.status_code == 200:
                top_boosts = top_boost_response.json()

                if isinstance(top_boosts, list):
                    profiles.extend(top_boosts)

        except Exception:
            pass

        # Expand discovery with DexScreener search.
        # Search is used only to discover additional candidates;
        # existing BUY / RISK logic remains unchanged.
        search_terms = [
            "pump",
            "ai",
            "cat",
            "dog",
            "meme",
            "swap"
        ]

        for term in search_terms:

            try:
                search_response = SESSION.get(
                    "https://api.dexscreener.com/latest/dex/search",
                    params={"q": term},
                    timeout=15
                )

                if search_response.status_code != 200:
                    continue

                pairs = search_response.json().get(
                    "pairs",
                    []
                )

                if not isinstance(pairs, list):
                    continue

                for pair in pairs:

                    if not isinstance(pair, dict):
                        continue

                    chain = pair.get("chainId")
                    base_token = pair.get(
                        "baseToken",
                        {}
                    )

                    address = (
                        base_token.get("address")
                        if isinstance(base_token, dict)
                        else None
                    )

                    if chain and address:
                        profiles.append({
                            "chainId": chain,
                            "tokenAddress": address,
                            "description": base_token.get(
                                "name",
                                ""
                            )
                        })

            except Exception:
                pass

        # Re-add recently strong BUY candidates.
        try:
            memory = load_radar_memory()

            for saved in memory:
                if isinstance(saved, dict):
                    profiles.append(saved)

        except Exception:
            pass

        unique = []
        seen = set()

        for profile in profiles:
            chain = profile.get("chainId")
            address = profile.get("tokenAddress")

            if chain and address:
                key = (chain.lower(), address.lower())

                if key not in seen:
                    seen.add(key)
                    unique.append(profile)

        return unique

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


def get_token_security(chain, token_address):

    chain_name = str(chain).lower().strip()

    if chain_name == "solana":
        return get_solana_security(token_address)

    chain_id = GOPLUS_CHAIN_IDS.get(chain_name)

    if not chain_id:
        return None

    try:
        response = SESSION.get(
            GOPLUS_EVM_URL.format(chain_id=chain_id),
            params={
                "contract_addresses": token_address
            },
            timeout=15
        )

        if response.status_code != 200:
            print(f"{GRAY}[GOPLUS] HTTP {response.status_code} for {chain}:{token_address}{RESET}")
            return None

        data = response.json()
        result = data.get("result")

        if not result:
            print(f"{GRAY}[GOPLUS] Empty result for {chain}:{token_address}{RESET}")

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

        now = datetime.now(
            timezone.utc
        ).timestamp()

        age_hours = (
            now - created_seconds
        ) / 3600

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

    if not isinstance(holders, list):

        result["reasons"].append(
            "Top holder data unavailable"
        )

        return result

    if not holders:

        result["reasons"].append(
            "Top holder data unavailable"
        )

        return result

    percentages = []

    locked_percent = 0.0

    for holder in holders:

        if not isinstance(holder, dict):
            continue

        # ====================================================
        # IMPORTANT GOPLUS FORMAT
        #
        # GoPlus returns:
        #
        # "percent": "0.7679"
        #
        # This already means 0.7679%.
        #
        # Therefore DO NOT multiply by 100.
        # ====================================================

        percent = safe_float(
            holder.get("percent")
        )

        # GoPlus holder percent is a ratio:
        # 1.0 = 100%, 0.7502 = 75.02%
        if 0 <= percent <= 1:
            percent *= 100

        if percent > 0:
            percentages.append(percent)

        # GoPlus may return integer 0/1 or string "0"/"1".
        locked = holder.get("is_locked")

        if str(locked).lower() in (
            "1",
            "true"
        ):

            locked_percent += percent

    if not percentages:

        result["reasons"].append(
            "Holder percentages unavailable"
        )

        return result

    result["available"] = True

    result["holder_count"] = safe_int(
        security.get("holder_count")
    )

    percentages.sort(
        reverse=True
    )

    # IMPORTANT:
    # percentages are already actual percentage values.

    result["top_holder_percent"] = (
        percentages[0]
    )

    result["top10_percent"] = (
        sum(percentages[:10])
    )

    result["locked_percent"] = (
        locked_percent
    )

    top = result["top_holder_percent"]
    top10 = result["top10_percent"]

    # --------------------------------------------------------
    # TOP HOLDER RISK
    # --------------------------------------------------------

    if top >= 40:

        result["risk"] += 20

        result["reasons"].append(
            f"Extreme top-holder concentration ({top:.2f}%)"
        )

    elif top >= 25:

        result["risk"] += 12

        result["reasons"].append(
            f"High top-holder concentration ({top:.2f}%)"
        )

    elif top >= 15:

        result["risk"] += 6

        result["reasons"].append(
            f"Moderate top-holder concentration ({top:.2f}%)"
        )

    # --------------------------------------------------------
    # TOP 10 RISK
    # --------------------------------------------------------

    if top10 >= 80:

        result["risk"] += 15

        result["reasons"].append(
            f"Top 10 control {top10:.2f}%"
        )

    elif top10 >= 65:

        result["risk"] += 10

        result["reasons"].append(
            f"Top 10 control {top10:.2f}%"
        )

    elif top10 >= 50:

        result["risk"] += 5

        result["reasons"].append(
            f"Top 10 control {top10:.2f}%"
        )

    # --------------------------------------------------------
    # LOCKED
    # --------------------------------------------------------

    if locked_percent >= 30:

        result["reasons"].append(
            f"{locked_percent:.2f}% of top holders locked"
        )

    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    if not result["reasons"]:

        result["reasons"].append(
            "Holder distribution looks acceptable"
        )

    return result


# ============================================================
# SECURITY ENGINE
# ============================================================

def analyze_security(security):

    result = {
        "available": False,
        "safe": False,
        "risk": 0,
        "reasons": []
    }

    if not security:
        result["reasons"].append(
            "Security data unavailable"
        )
        return result

    result["available"] = True

    # ========================================================
    # SOLANA SECURITY
    # ========================================================

    solana_fields = (
        "mintable",
        "freezable",
        "closable",
        "metadata_mutable",
        "non_transferable"
    )

    is_solana = any(
        field in security
        for field in solana_fields
    )

    if is_solana:

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

        if mintable != 0:
            result["risk"] += 8
            result["reasons"].append(
                "Mint authority risk detected"
            )

        if freezable != 0:
            result["risk"] += 8
            result["reasons"].append(
                "Freeze authority risk detected"
            )

        if closable != 0:
            result["risk"] += 8
            result["reasons"].append(
                "Token close authority detected"
            )

        if metadata_mutable != 0:
            result["risk"] += 4
            result["reasons"].append(
                "Metadata remains mutable"
            )

        if non_transferable != 0:
            result["risk"] += 15
            result["reasons"].append(
                "Token is non-transferable"
            )

    # ========================================================
    # EVM SECURITY
    # ========================================================

    else:

        is_open_source = safe_int(
            security.get("is_open_source")
        )

        cannot_buy = safe_int(
            security.get("cannot_buy")
        )

        buy_tax = safe_float(
            security.get("buy_tax")
        )

        sell_tax = safe_float(
            security.get("sell_tax")
        )

        is_in_dex = safe_int(
            security.get("is_in_dex")
        )

        if is_open_source == 0:
            result["risk"] += 12
            result["reasons"].append(
                "Contract is not open source"
            )

        if cannot_buy != 0:
            result["risk"] += 20
            result["reasons"].append(
                "Buying may be restricted"
            )

        if buy_tax >= 10:
            result["risk"] += 15
            result["reasons"].append(
                f"High buy tax ({buy_tax:.2f}%)"
            )

        elif buy_tax > 5:
            result["risk"] += 8
            result["reasons"].append(
                f"Elevated buy tax ({buy_tax:.2f}%)"
            )

        if sell_tax >= 10:
            result["risk"] += 20
            result["reasons"].append(
                f"High sell tax ({sell_tax:.2f}%)"
            )

        elif sell_tax > 5:
            result["risk"] += 10
            result["reasons"].append(
                f"Elevated sell tax ({sell_tax:.2f}%)"
            )

        if is_in_dex == 0:
            result["risk"] += 5
            result["reasons"].append(
                "Token not detected in DEX"
            )

    result["risk"] = min(
        result["risk"],
        100
    )

    result["safe"] = (
        result["risk"] == 0
    )

    if result["safe"]:
        result["reasons"].append(
            "Core security checks passed"
        )

    return result


# ============================================================
# ANALYSIS ENGINE
# ============================================================


def calculate_position_status(
    analysis,
    entry_price,
    current_price
):

    risk = analysis["risk"]
    opportunity = analysis["opportunity"]
    confidence = analysis["confidence"]

    liquidity = analysis["liquidity"]
    volume = analysis["volume"]

    price_change_5m = analysis["price_change_5m"]
    price_change_1h = analysis["price_change_1h"]

    whale_risk = analysis.get(
        "whale_risk",
        100
    )

    security_safe = analysis.get(
        "security_safe",
        False
    )

    if entry_price > 0:

        pnl_percent = (
            (current_price - entry_price)
            / entry_price
        ) * 100

    else:

        pnl_percent = 0

    # ========================================================
    # EXIT SCORE
    # ========================================================

    exit_score = 0
    exit_reasons = []

    if not security_safe:

        exit_score += 40

        exit_reasons.append(
            "Security deterioration"
        )

    if whale_risk >= 20:

        exit_score += 30

        exit_reasons.append(
            "High whale risk"
        )

    if liquidity < 5000:

        exit_score += 30

        exit_reasons.append(
            "Critical liquidity"
        )

    elif liquidity < MIN_LIQUIDITY:

        exit_score += 10

        exit_reasons.append(
            "Liquidity weakened"
        )

    if volume < 1000:

        exit_score += 25

        exit_reasons.append(
            "Critical volume"
        )

    elif volume < MIN_VOLUME:

        exit_score += 8

        exit_reasons.append(
            "Volume weakened"
        )

    if risk >= 50:

        exit_score += 25

        exit_reasons.append(
            "Severe risk"
        )

    elif risk > MAX_BUY_RISK:

        exit_score += 10

        exit_reasons.append(
            "Risk increased"
        )

    if (
        price_change_5m <= -20
        and price_change_1h <= -10
    ):

        exit_score += 25

        exit_reasons.append(
            "Momentum breakdown"
        )

    elif (
        price_change_5m <= -10
        and price_change_1h < 0
    ):

        exit_score += 10

        exit_reasons.append(
            "Momentum weakening"
        )

    # ========================================================
    # HARD EXIT
    # ========================================================

    if (
        not security_safe
        and whale_risk >= 20
    ):

        return {
            "status": "EXIT",
            "reason": "Security + whale risk",
            "reasons": exit_reasons,
            "score": exit_score,
            "pnl_percent": pnl_percent
        }

    if (
        liquidity < 5000
        and volume < 1000
    ):

        return {
            "status": "EXIT",
            "reason": "Liquidity + volume collapse",
            "reasons": exit_reasons,
            "score": exit_score,
            "pnl_percent": pnl_percent
        }

    if exit_score >= 60:

        return {
            "status": "EXIT",
            "reason": exit_reasons[0],
            "reasons": exit_reasons,
            "score": exit_score,
            "pnl_percent": pnl_percent
        }

    # ========================================================
    # WATCH SCORE
    # ========================================================

    watch_score = 0
    watch_reasons = []

    if risk > MAX_BUY_RISK:

        watch_score += 15

        watch_reasons.append(
            "Risk above BUY threshold"
        )

    if opportunity < MIN_BUY_OPPORTUNITY:

        watch_score += 15

        watch_reasons.append(
            "Opportunity weakened"
        )

    if confidence < MIN_BUY_CONFIDENCE:

        watch_score += 15

        watch_reasons.append(
            "Confidence weakened"
        )

    if (
        price_change_5m < 0
        and price_change_1h < 0
    ):

        watch_score += 15

        watch_reasons.append(
            "Momentum weakening"
        )

    if liquidity < MIN_LIQUIDITY:

        watch_score += 10

        watch_reasons.append(
            "Liquidity weakening"
        )

    if volume < MIN_VOLUME:

        watch_score += 10

        watch_reasons.append(
            "Volume weakening"
        )

    if watch_score >= 25:

        return {
            "status": "WATCH",
            "reason": watch_reasons[0],
            "reasons": watch_reasons,
            "score": watch_score,
            "pnl_percent": pnl_percent
        }

    # ========================================================
    # HOLD
    # ========================================================

    return {
        "status": "HOLD",
        "reason": "Position structure remains strong",
        "reasons": [],
        "score": 0,
        "pnl_percent": pnl_percent
    }


def calculate_grow_score(
    liquidity,
    volume,
    volume_5m,
    price_change_5m,
    price_change_1h,
    price_change_24h,
    buy_ratio_5m,
    buy_ratio_1h,
    total_5m,
    total_1h,
    age_hours,
    whale,
    security_result
):

    score = 0

    # LIQUIDITY
    if liquidity >= 100_000:
        score += 15
    elif liquidity >= 50_000:
        score += 12
    elif liquidity >= MIN_LIQUIDITY:
        score += 8

    # VOLUME
    if volume >= 1_000_000:
        score += 15
    elif volume >= 100_000:
        score += 12
    elif volume >= MIN_VOLUME:
        score += 7

    # MOMENTUM
    if 5 <= price_change_1h <= 100:
        score += 12
    elif 0 < price_change_1h < 5:
        score += 7

    if 2 <= price_change_5m <= 20:
        score += 8
    elif price_change_5m > 0:
        score += 4

    if 10 <= price_change_24h <= 300:
        score += 8
    elif 0 < price_change_24h < 10:
        score += 4

    # BUY PRESSURE
    if buy_ratio_5m >= 0.60:
        score += 8
    elif buy_ratio_5m >= 0.52:
        score += 4

    if buy_ratio_1h >= 0.55:
        score += 6
    elif buy_ratio_1h >= 0.50:
        score += 3

    # ACTIVITY
    if total_5m >= 100:
        score += 6
    elif total_5m >= 30:
        score += 3

    if total_1h >= 500:
        score += 5
    elif total_1h >= 100:
        score += 3

    # TOKEN AGE
    if 1 <= age_hours <= 48:
        score += 5
    elif 48 < age_hours <= 168:
        score += 2

    # SECURITY
    if security_result.get("available"):
        if security_result.get("safe"):
            score += 5
        else:
            score -= 15
    else:
        score -= 10

    # WHALE
    if whale.get("available"):
        if whale.get("risk", 100) < 20:
            score += 5
        elif whale.get("risk", 100) >= 50:
            score -= 10
    else:
        score -= 10

    return max(0, min(round(score), 100))


def calculate_grow_forecast(
    grow_score,
    price_change_5m,
    price_change_1h,
    price_change_24h,
    volume,
    liquidity,
    buy_ratio_5m,
    buy_ratio_1h,
    age_hours
):

    # ========================================================
    # GROW FORECAST ENGINE V3
    # ========================================================

    if grow_score < 40:
        return None

    momentum = (
        price_change_5m * 0.20
        + price_change_1h * 0.35
        + price_change_24h * 0.45
    )

    flow = (
        buy_ratio_5m * 0.55
        + buy_ratio_1h * 0.45
    )

    activity = 0

    if volume >= 10_000_000:
        activity += 20
    elif volume >= 1_000_000:
        activity += 15
    elif volume >= 100_000:
        activity += 10
    elif volume >= MIN_VOLUME:
        activity += 5

    if liquidity >= 500_000:
        activity += 20
    elif liquidity >= 100_000:
        activity += 15
    elif liquidity >= 50_000:
        activity += 10
    elif liquidity >= MIN_LIQUIDITY:
        activity += 5

    momentum_factor = max(
        -1.0,
        min(momentum / 100.0, 3.0)
    )

    flow_factor = max(
        0.0,
        min((flow - 0.50) * 4.0, 1.0)
    )

    strength = (
        grow_score * 0.60
        + activity * 0.20
        + flow_factor * 20
        + momentum_factor * 20
    )

    strength = max(
        0,
        min(strength, 100)
    ) / 100.0

    # ========================================================
    # GROWTH PRESSURE
    # ========================================================

    growth_pressure = 0
    # DOWNSIDE PRESSURE
    if price_change_1h <= -50:
        growth_pressure -= 30
    elif price_change_1h <= -30:
        growth_pressure -= 20
    elif price_change_1h <= -20:
        growth_pressure -= 12
    elif price_change_1h <= -10:
        growth_pressure -= 6

    if price_change_5m <= -10:
        growth_pressure -= 8
    elif price_change_5m <= -5:
        growth_pressure -= 4

    if grow_score >= 90:
        growth_pressure += 25
    elif grow_score >= 80:
        growth_pressure += 18
    elif grow_score >= 70:
        growth_pressure += 10

    if price_change_1h >= 150:
        growth_pressure += 25
    elif price_change_1h >= 100:
        growth_pressure += 18
    elif price_change_1h >= 50:
        growth_pressure += 12
    elif price_change_1h >= 25:
        growth_pressure += 6

    if price_change_5m >= 30:
        growth_pressure += 20
    elif price_change_5m >= 20:
        growth_pressure += 15
    elif price_change_5m >= 10:
        growth_pressure += 10
    elif price_change_5m >= 5:
        growth_pressure += 5

    if price_change_24h >= 500:
        growth_pressure += 20
    elif price_change_24h >= 300:
        growth_pressure += 15
    elif price_change_24h >= 100:
        growth_pressure += 10
    elif price_change_24h >= 50:
        growth_pressure += 5

    if volume >= 10_000_000:
        growth_pressure += 15
    elif volume >= 1_000_000:
        growth_pressure += 10

    if liquidity >= 500_000:
        growth_pressure += 15
    elif liquidity >= 100_000:
        growth_pressure += 8

    if buy_ratio_5m >= 0.70:
        growth_pressure += 15
    elif buy_ratio_5m >= 0.65:
        growth_pressure += 10
    elif buy_ratio_5m >= 0.60:
        growth_pressure += 6

    if buy_ratio_1h >= 0.65:
        growth_pressure += 15
    elif buy_ratio_1h >= 0.60:
        growth_pressure += 10
    elif buy_ratio_1h >= 0.55:
        growth_pressure += 6

    growth_pressure = min(
        growth_pressure,
        150
    )

    # ========================================================
    # EXTREME MULTIPLIER
    # ========================================================

    if growth_pressure >= 100:

        extreme_multiplier = (
            2.0
            + ((growth_pressure - 100) / 50.0) * 8.0
        )

    elif growth_pressure >= 75:

        extreme_multiplier = (
            1.25
            + ((growth_pressure - 75) / 25.0) * 0.75
        )

    elif growth_pressure >= 50:

        extreme_multiplier = (
            1.0
            + ((growth_pressure - 50) / 25.0) * 0.25
        )

    else:

        extreme_multiplier = 1.0

    confidence_base = max(
        20,
        min(
            round(
                grow_score * 0.55
                + activity * 0.20
                + flow_factor * 25
            ),
            95
        )
    )

    # ========================================================
    # HORIZONS
    # ========================================================

    horizons = {
        "1H": (0.08, 0.25),
        "6H": (0.20, 0.70),
        "1D": (0.40, 1.50),
        "1W": (1.00, 6.00),
        "1M": (2.00, 10.00)
    }

    forecasts = {}

    for horizon, (low_factor, high_factor) in horizons.items():

        low = (
            low_factor
            * strength
            * 100
        )

        high = (
            high_factor
            * strength
            * 100
            * extreme_multiplier
        )

        confidence = confidence_base

        if horizon in ("1W", "1M"):
            confidence = max(
                15,
                confidence - 20
            )

        if age_hours < 1:
            confidence = max(
                10,
                confidence - 15
            )

        forecasts[horizon] = {
            "low": round(low, 2),
            "high": round(high, 2),
            "confidence": confidence
        }

    return forecasts


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

    buys_5m = safe_int(
        txns_5m.get("buys")
    )

    sells_5m = safe_int(
        txns_5m.get("sells")
    )

    buys_1h = safe_int(
        txns_1h.get("buys")
    )

    sells_1h = safe_int(
        txns_1h.get("sells")
    )

    age_hours = get_token_age_hours(
        pair
    )

    total_5m = (
        buys_5m + sells_5m
    )

    total_1h = (
        buys_1h + sells_1h
    )

    buy_ratio_5m = (
        buys_5m / total_5m
        if total_5m > 0
        else 0
    )

    buy_ratio_1h = (
        buys_1h / total_1h
        if total_1h > 0
        else 0
    )

    whale = analyze_holders(
        security
    )

    security_result = analyze_security(
        security
    )

    # ========================================================
    # RISK
    # ========================================================

    risk = 0

    risk_reasons = []

    if liquidity < 5000:

        risk += 15

        risk_reasons.append(
            "Very low liquidity"
        )

    elif liquidity < MIN_LIQUIDITY:

        risk += 8

        risk_reasons.append(
            "Low liquidity"
        )

    if volume < 1000:

        risk += 12

        risk_reasons.append(
            "Very low volume"
        )

    elif volume < MIN_VOLUME:

        risk += 6

        risk_reasons.append(
            "Low volume"
        )

    if price_change_5m <= -20:

        risk += 15

        risk_reasons.append(
            "Heavy 5m dump"
        )

    elif price_change_5m <= -10:

        risk += 8

        risk_reasons.append(
            "Short-term weakness"
        )

    if price_change_1h >= 200:

        risk += 12

        risk_reasons.append(
            "Extreme 1h pump"
        )

    elif price_change_1h >= 100:

        risk += 7

        risk_reasons.append(
            "Strong 1h pump"
        )

    if (
        total_5m > 0
        and buy_ratio_5m < 0.40
    ):

        risk += 10

        risk_reasons.append(
            "Sell pressure"
        )

    if (
        age_hours > 0
        and age_hours < 1
    ):

        risk += 5

        risk_reasons.append(
            "Extremely new token"
        )

    elif (
        age_hours > 0
        and age_hours < 6
    ):

        risk += 2

        risk_reasons.append(
            "Very new token"
        )

    # --------------------------------------------------------
    # WHALE
    # --------------------------------------------------------

    risk += whale["risk"]

    for reason in whale["reasons"]:

        if "acceptable" not in reason.lower():

            risk_reasons.append(
                f"Whale: {reason}"
            )

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    if security_result["available"]:

        risk += security_result["risk"]

        for reason in security_result["reasons"]:

            if "passed" not in reason.lower():

                risk_reasons.append(
                    f"Security: {reason}"
                )

    else:

        risk += 15

        risk_reasons.append(
            "Security data unavailable"
        )

    risk = min(
        risk,
        100
    )

    # ========================================================
    # OPPORTUNITY
    # ========================================================

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

    if security_result["safe"]:

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

    opportunity = min(
        opportunity,
        100
    )

    # ========================================================
    # CONFIDENCE
    # ========================================================

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

    if not security_result["available"]:

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
        min(
            confidence,
            100
        )
    )

    grow_score = calculate_grow_score(
        liquidity,
        volume,
        volume_5m,
        price_change_5m,
        price_change_1h,
        price_change_24h,
        buy_ratio_5m,
        buy_ratio_1h,
        total_5m,
        total_1h,
        age_hours,
        whale,
        security_result
    )

    grow_forecast = calculate_grow_forecast(
        grow_score,
        price_change_5m,
        price_change_1h,
        price_change_24h,
        volume,
        liquidity,
        buy_ratio_5m,
        buy_ratio_1h,
        age_hours
    )

    # ========================================================
    # CRITICAL BUY GATE
    # ========================================================

    critical_ok = (

        liquidity >= MIN_LIQUIDITY

        and volume >= MIN_VOLUME

        and security_result["available"]

        and security_result["safe"]

        and whale["available"]

        and whale["risk"] < 20

    )

    # ========================================================
    # FINAL SIGNAL
    # ========================================================

    buy = (

        risk <= MAX_BUY_RISK

        and opportunity >= MIN_BUY_OPPORTUNITY

        and confidence >= MIN_BUY_CONFIDENCE

        and critical_ok

    )

    signal = (
        "BUY"
        if buy
        else
        "RISK"
    )

    # ========================================================
    # KRYPT SCORE
    # ========================================================

    krypt_score = (

        opportunity * 0.55

        + (100 - min(risk, 100)) * 0.30

        + confidence * 0.15

    )

    return {

        "risk": min(risk, 100),

        "opportunity": opportunity,

        "confidence": confidence,

        "krypt_score": round(
            krypt_score,
            1
        ),

        "grow_score": grow_score,
        "grow_forecast": grow_forecast,
        "signal": signal,

        "whale_risk": whale["risk"],

        "security_safe": security_result["safe"],

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

        "security_available":
            security_result["available"],

        "security_safe":
            security_result["safe"],

        "security":
            security_result,

        "whale":
            whale,

        "risk_reasons":
            risk_reasons,

        "opportunity_reasons":
            opportunity_reasons,

        "confidence_reasons":
            confidence_reasons

    }


# ============================================================
# SCANNER
# ============================================================

def scan_memory_tokens():

    clear()

    print(f"{CYAN}{BOLD}")
    print(
        "╔══════════════════════════════════════════════════════════════╗"
    )
    print(
        "║                 KRYPT LOW RISK TOP PICKS                    ║"
    )
    print(
        "╚══════════════════════════════════════════════════════════════╝"
    )
    print(RESET)

    memory = load_radar_memory()

    if not memory:
        print(
            f"{RED}[ERROR] Radar memory is empty.{RESET}"
        )
        return []

    results = []

    print(
        f"{CYAN}[RADAR] Checking saved BUY candidates... "
        f"{len(memory)}{RESET}"
    )

    line()

    for index, saved in enumerate(memory, 1):

        chain = saved.get("chainId")
        address = saved.get("tokenAddress")

        if not chain or not address:
            continue

        pairs = get_token_pairs(
            chain,
            address
        )

        pair = choose_best_pair(
            pairs
        )

        if not pair:
            continue

        print(
            f"{GRAY}[{index:02d}/{len(memory)}] "
            f"Live security + whale scan...{RESET}"
        )

        security = get_token_security(
            chain,
            address
        )

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

    results.sort(
        key=lambda x: (
            x["analysis"]["risk"] <= MAX_BUY_RISK,
            x["analysis"]["opportunity"],
            x["analysis"]["confidence"],
            x["analysis"]["krypt_score"]
        ),
        reverse=True
    )

    return results


def scan_new_tokens():

    clear()

    print(f"{CYAN}{BOLD}")

    print(
        "╔══════════════════════════════════════════════════════════════╗"
    )

    print(
        "║                  KRYPT DEEP RADAR SCAN                      ║"
    )

    print(
        "╚══════════════════════════════════════════════════════════════╝"
    )

    print(RESET)

    print(
        f"{CYAN}[RADAR] Discovering new / unknown tokens...{RESET}"
    )

    profiles = get_latest_profiles()

    if not profiles:

        print(
            f"{RED}[ERROR] Could not retrieve token profiles.{RESET}"
        )

        return []

    results = []

    profiles = profiles[:100]

    print(
        f"{GRAY}[RADAR] Profiles received: "
        f"{len(profiles)}{RESET}"
    )

    print(
        f"{BLUE}[ENGINE] Security Engine      : ONLINE{RESET}"
    )

    print(
        f"{BLUE}[ENGINE] Whale Engine         : ONLINE{RESET}"
    )

    print(
        f"{BLUE}[ENGINE] Opportunity Engine   : ONLINE{RESET}"
    )

    print(
        f"{BLUE}[ENGINE] Confidence Engine    : ONLINE{RESET}"
    )

    print(
        f"{BLUE}[ENGINE] Signal Engine        : ONLINE{RESET}"
    )

    line()

    for index, profile in enumerate(
        profiles,
        1
    ):

        chain = profile.get(
            "chainId"
        )

        address = profile.get(
            "tokenAddress"
        )

        if not chain or not address:
            continue

        pairs = get_token_pairs(
            chain,
            address
        )

        pair = choose_best_pair(
            pairs
        )

        if not pair:
            continue

        print(
            f"{GRAY}"
            f"[{index:02d}/{len(profiles)}] "
            f"Security + Whale scan..."
            f"{RESET}"
        )

        security = get_token_security(
            chain,
            address
        )

        if not security:
            pass

        print(
            f"{GRAY}[DEBUG] Security: "
            f"{"OK" if security else "NONE"}{RESET}"
        )

        analysis = calculate_analysis(
            pair,
            security
        )

        base_token = (
            pair.get("baseToken")
            or {}
        )

        symbol = (
            base_token.get("symbol")
            or "UNKNOWN"
        )

        name = (
            base_token.get("name")
            or "UNKNOWN"
        )

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
            else
            RED

        )

        whale = analysis["whale"]

        if whale["available"]:

            whale_text = (
                f"WHALE {whale['risk']:02d}"
            )

        else:

            whale_text = (
                "WHALE --"
            )

        print(

            f"  {WHITE}"
            f"{symbol:<12}"
            f"{RESET}"

            f" "

            f"KRYPT "
            f"{analysis['krypt_score']:>5.1f}"

            f" "

            f"RISK "
            f"{analysis['risk']:>3}%"

            f" "

            f"OPP "
            f"{analysis['opportunity']:>3}"

            f" "

            f"CONF "
            f"{analysis['confidence']:>3}%"

            f" "

            f"{CYAN}"
            f"{whale_text}"
            f"{RESET}"

            f" "

            f"{signal_color}"
            f"{analysis['signal']}"
            f"{RESET}"

        )

        time.sleep(
            0.15
        )

    results.sort(

        key=lambda x:
        x["analysis"]["krypt_score"],

        reverse=True

    )

    print()

    line()

    buy_count = sum(

        1

        for item in results

        if item["analysis"]["signal"]
        == "BUY"

    )

    whale_available = sum(

        1

        for item in results

        if item["analysis"]["whale"]["available"]

    )

    print(

        f"{WHITE}"
        f"Tokens analyzed : "
        f"{len(results)}"
        f"{RESET}"

    )

    print(

        f"{CYAN}"
        f"Whale data      : "
        f"{whale_available}/{len(results)}"
        f"{RESET}"

    )

    print(

        f"{GREEN}"
        f"BUY signals     : "
        f"{buy_count}"
        f"{RESET}"

    )

    print()

    save_radar_memory(results)

    return results


# ============================================================
# BUY EXPLANATION
# ============================================================

def show_buy_explanation(item):

    analysis = item["analysis"]

    whale = analysis["whale"]

    security = analysis["security"]

    clear()

    print(f"{GREEN}{BOLD}")

    print(
        "╔══════════════════════════════════════════════════════════════╗"
    )

    print(
        "║                    KRYPT BUY SIGNAL                         ║"
    )

    print(
        "╚══════════════════════════════════════════════════════════════╝"
    )

    print(RESET)

    print(

        f"{WHITE}{BOLD}"

        f"{item['symbol']} — "
        f"{item['name']}"

        f"{RESET}"

    )

    print(

        f"{GRAY}"
        f"Chain: {item['chain']}"
        f"{RESET}"

    )

    line()

    print(

        f"{GREEN}"
        "🟢 BUY"
        f"{RESET}"

        f"    "

        f"{WHITE}"
        "KRYPT SCORE: "
        f"{analysis['krypt_score']:.1f}/100"
        f"{RESET}"

    )

    print()

    print(

        f"{WHITE}"
        "RISK        : "
        f"{GREEN}"
        f"{analysis['risk']}%"
        f"{RESET}"

    )

    print(

        f"{WHITE}"
        "OPPORTUNITY : "
        f"{GREEN}"
        f"{analysis['opportunity']}/100"
        f"{RESET}"

    )

    print(

        f"{WHITE}"
        "CONFIDENCE  : "
        f"{GREEN}"
        f"{analysis['confidence']}%"
        f"{RESET}"

    )

    line()

    print(
        f"{CYAN}{BOLD}"
        "WHY KRYPT LIKES IT"
        f"{RESET}"
    )

    for reason in (
        analysis["opportunity_reasons"]
    ):

        print(
            f"{GREEN}  + {reason}{RESET}"
        )

    line()

    print(
        f"{CYAN}{BOLD}"
        "WHALE ANALYSIS"
        f"{RESET}"
    )

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

                f"  {GRAY}• "
                f"{reason}"
                f"{RESET}"

            )

    else:

        print(
            f"{RED}"
            "  Holder data unavailable"
            f"{RESET}"
        )

    line()

    print(
        f"{CYAN}{BOLD}"
        "MARKET DATA"
        f"{RESET}"
    )

    pair = item.get("pair") or {}

    print(

        f"  Market Cap: "
        f"{format_money(pair.get('marketCap') or pair.get('fdv') or 0)}"

    )

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
        f"{analysis['buys_5m']}/"
        f"{analysis['sells_5m']}"

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

    print(
        f"{CYAN}{BOLD}"
        "SECURITY"
        f"{RESET}"
    )

    if analysis["security_available"]:

        if analysis["security_safe"]:

            print(
                f"{GREEN}"
                "  ✓ Security checks passed"
                f"{RESET}"
            )

        else:

            print(
                f"{RED}"
                "  ✗ Security flags detected"
                f"{RESET}"
            )

            for reason in security["reasons"]:

                print(
                    f"  {GRAY}• "
                    f"{reason}"
                    f"{RESET}"
                )

    else:

        print(
            f"{RED}"
            "  ✗ Security data unavailable"
            f"{RESET}"
        )

    line()

    print(
        f"{CYAN}{BOLD}"
        "DECISION LOGIC"
        f"{RESET}"
    )

    checks = [

        (
            f"Risk <= {MAX_BUY_RISK}%",
            analysis["risk"]
            <= MAX_BUY_RISK
        ),

        (
            f"Opportunity >= "
            f"{MIN_BUY_OPPORTUNITY}",
            analysis["opportunity"]
            >= MIN_BUY_OPPORTUNITY
        ),

        (
            f"Confidence >= "
            f"{MIN_BUY_CONFIDENCE}%",
            analysis["confidence"]
            >= MIN_BUY_CONFIDENCE
        ),

        (
            f"Liquidity >= "
            f"{format_money(MIN_LIQUIDITY)}",
            analysis["liquidity"]
            >= MIN_LIQUIDITY
        ),

        (
            f"Volume >= "
            f"{format_money(MIN_VOLUME)}",
            analysis["volume"]
            >= MIN_VOLUME
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

        color = (
            GREEN
            if passed
            else
            RED
        )

        status = (
            "PASS"
            if passed
            else
            "FAIL"
        )

        print(

            f"  {label:<34} "
            f"{color}"
            f"{status}"
            f"{RESET}"

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

def show_coin_details(item):

    analysis = item["analysis"]
    pair = item.get("pair") or {}

    clear()

    print(f"{CYAN}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                       COIN DETAILS                           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(RESET)

    print(
        f"{WHITE}{BOLD}"
        f"{item['name']}"
        f"{RESET}"
    )

    print(f"{GRAY}Chain       : {item['chain']}{RESET}")
    print(f"{GRAY}Contract    : {item['address']}{RESET}")
    print(
        f"{GRAY}Pair Address: "
        f"{pair.get('pairAddress') or 'UNAVAILABLE'}"
        f"{RESET}"
    )

    line()

    print(f"{CYAN}{BOLD}MARKET DATA{RESET}")

    print(
        f"  Market Cap : "
        f"{format_money(pair.get('marketCap') or pair.get('fdv') or 0)}"
    )

    print(
        f"  Price      : "
        f"${pair.get('priceUsd') or 'N/A'}"
    )

    print(
        f"  Liquidity  : "
        f"{format_money(analysis['liquidity'])}"
    )

    print(
        f"  Volume 24h : "
        f"{format_money(analysis['volume'])}"
    )

    print(
        f"  Volume 5m  : "
        f"{format_money(analysis['volume_5m'])}"
    )

    print(
        f"  5m         : "
        f"{analysis['price_change_5m']:+.2f}%"
    )

    print(
        f"  1h         : "
        f"{analysis['price_change_1h']:+.2f}%"
    )

    print(
        f"  24h        : "
        f"{analysis['price_change_24h']:+.2f}%"
    )

    print(
        f"  Token Age  : "
        f"{format_age(analysis['age_hours'])}"
    )

    line()

    print(f"{CYAN}{BOLD}KRYPT INTELLIGENCE{RESET}")

    print(
        f"  Risk        : "
        f"{analysis['risk']}%"
    )

    print(
        f"  Opportunity : "
        f"{analysis['opportunity']}/100"
    )

    print(
        f"  Confidence  : "
        f"{analysis['confidence']}%"
    )

    print(
        f"  Grow Score  : "
        f"{analysis['grow_score']}/100"
    )

    signal = analysis["signal"]

    if signal == "BUY":
        signal_color = GREEN
        signal_icon = "🟢"
    else:
        signal_color = RED
        signal_icon = "🔴"

    print(
        f"  Signal      : "
        f"{signal_color}"
        f"{signal_icon} {signal}"
        f"{RESET}"
    )

    line()

    forecast = analysis.get("grow_forecast")

    print(f"{YELLOW}{BOLD}GROW FORECAST{RESET}")

    if forecast:

        for horizon in ("1H", "6H", "1D", "1W", "1M"):

            data = forecast.get(horizon)

            if not data:
                continue

            print(
                f"  {horizon:<3}: "
                f"{data['low']:+.1f}% → "
                f"{data['high']:+.1f}%   "
                f"C: {data['confidence']}%"
            )

    else:

        print(
            f"  {GRAY}"
            "DATA INSUFFICIENT"
            f"{RESET}"
        )

    line()

    whale = analysis["whale"]

    print(f"{CYAN}{BOLD}WHALE{RESET}")

    if whale["available"]:

        print(
            f"  Holders     : "
            f"{whale['holder_count']:,}"
        )

        print(
            f"  Top Holder  : "
            f"{whale['top_holder_percent']:.2f}%"
        )

        print(
            f"  Top 10      : "
            f"{whale['top10_percent']:.2f}%"
        )

        print(
            f"  Whale Risk  : "
            f"{whale['risk']}"
        )

    else:

        print(
            f"  {RED}"
            "Whale data unavailable"
            f"{RESET}"
        )

    line()

    print(f"{CYAN}{BOLD}SECURITY{RESET}")

    if analysis["security_available"]:

        if analysis["security_safe"]:

            print(
                f"  {GREEN}"
                "✓ PASS"
                f"{RESET}"
            )

        else:

            print(
                f"  {RED}"
                "✗ RISK"
                f"{RESET}"
            )

    else:

        print(
            f"  {RED}"
            "✗ DATA UNAVAILABLE"
            f"{RESET}"
        )

    pause()


def show_results(results):

    clear()

    print(f"{CYAN}{BOLD}")

    print(
        "╔══════════════════════════════════════════════════════════════╗"
    )

    print(
        "║                     CRYPTO RADAR                            ║"
    )

    print(
        "╚══════════════════════════════════════════════════════════════╝"
    )

    print(RESET)

    if not results:

        print(
            f"{RED}"
            "No valid tokens found."
            f"{RESET}"
        )

        pause()

        return

    buy_count = sum(

        1

        for item in results

        if item["analysis"]["signal"]
        == "BUY"

    )

    print(

        f"{WHITE}"
        f"Candidates: {len(results)}    "
        f"{GREEN}"
        f"BUY: {buy_count}"
        f"{RESET}"

    )

    line()

    for index, item in enumerate(
        results[:10],
        1
    ):

        analysis = item["analysis"]

        if analysis["signal"] == "BUY":

            signal_color = GREEN
            signal_icon = "🟢"

        else:

            signal_color = RED
            signal_icon = "🔴"

        print(

            f"{WHITE}"
            f"{index:02d}. "
            f"{BOLD}"
            f"{item['symbol']}"
            f"{RESET}"

            f" "
            f"{GRAY}"
            f"({item['chain']})"
            f"{RESET}"

        )

        print(

            f"    Risk: "
            f"{analysis['risk']:>3}%   "

            f"Opportunity: "
            f"{analysis['opportunity']:>3}/100   "

            f"Confidence: "
            f"{analysis['confidence']:>3}%   "

            f"Grow Score: "
            f"{analysis['grow_score']:>3}/100"

        )

        print(

            f"    Liquidity: "
            f"{format_money(analysis['liquidity']):>9}   "

            f"Volume: "
            f"{format_money(analysis['volume']):>9}"

        )

        print(

            f"    5m: "
            f"{analysis['price_change_5m']:+7.2f}%   "

            f"1h: "
            f"{analysis['price_change_1h']:+7.2f}%   "

            f"Age: "
            f"{format_age(analysis['age_hours'])}"

        )

        forecast = analysis.get("grow_forecast")

        if forecast:

            print(
                f"    {YELLOW}GROW FORECAST{RESET}"
            )

            for horizon in ("1H", "6H", "1D", "1W", "1M"):

                data = forecast.get(horizon)

                if not data:
                    continue

                print(
                    f"    {horizon:<3}: "
                    f"{data['low']:+.1f}% → "
                    f"{data['high']:+.1f}%   "
                    f"C: {data['confidence']}%"
                )

        else:

            print(
                f"    {GRAY}"
                "GROW FORECAST: DATA INSUFFICIENT"
                f"{RESET}"
            )

        whale = analysis["whale"]

        if whale["available"]:

            whale_info = (

                f"Top: "
                f"{whale['top_holder_percent']:.2f}%   "

                f"Top10: "
                f"{whale['top10_percent']:.2f}%   "

                f"Whale Risk: "
                f"{whale['risk']}"

            )

        else:

            whale_info = (
                "Whale data unavailable"
            )

        print(
            f"    🐋 {whale_info}"
        )

        print(

            f"    "
            f"{signal_color}"
            f"{signal_icon} "
            f"{analysis['signal']}"
            f"{RESET}"

            f"   "

            f"KRYPT: "
            f"{analysis['krypt_score']:.1f}"

        )

        if analysis["signal"] == "BUY":

            print(

                f"    {GREEN}"
                "→ BUY explanation available"
                f"{RESET}"

            )

        print()

    line()

    print(

        f"{GREEN}"
        f"BUY signals found: "
        f"{buy_count}"
        f"{RESET}"

    )

    print(

        f"{GRAY}"
        "Showing top 10 candidates by KRYPT score."
        f"{RESET}"

    )

    buy_items = [

        item

        for item in results

        if item["analysis"]["signal"]
        == "BUY"

    ]

    if buy_items:

        print()

        print(
            f"{CYAN}"
            "[B] BUY explanation"
            f"{RESET}"
        )

        print(
            f"{CYAN}"
            "[D] COIN DETAILS"
            f"{RESET}"
        )

        choice = input(
            f"\n{WHITE}Selection: {RESET}"
        ).strip().lower()

        if choice == "b":

            clear()

            print(f"{CYAN}{BOLD}")
            print("╔══════════════════════════════════════════════════════════════╗")
            print("║                     BUY EXPLANATION                          ║")
            print("╚══════════════════════════════════════════════════════════════╝")
            print(RESET)

            for i, item in enumerate(buy_items, 1):

                print(
                    f"{GREEN}[{i:02d}] "
                    f"{item['name']}"
                    f"{RESET}"
                )

            print()
            print(
                f"{GRAY}[00] BACK{RESET}"
            )

            number = input(
                f"\n{WHITE}BUY coin number: {RESET}"
            ).strip()

            if number == "00":
                return

            if number.isdigit():

                index = int(number) - 1

                if 0 <= index < len(buy_items):

                    show_buy_explanation(
                        buy_items[index]
                    )

                    return

            print(
                f"{RED}Invalid BUY coin number.{RESET}"
            )

            pause()

        elif choice == "d":

            clear()

            print(f"{CYAN}{BOLD}")
            print("╔══════════════════════════════════════════════════════════════╗")
            print("║                       COIN DETAILS                           ║")
            print("╚══════════════════════════════════════════════════════════════╝")
            print(RESET)

            for i, item in enumerate(results[:10], 1):

                print(
                    f"{WHITE}[{i:02d}] "
                    f"{item['name']}"
                    f"{RESET}"
                )

            print()
            print(
                f"{GRAY}[00] BACK{RESET}"
            )

            number = input(
                f"\n{WHITE}Coin number: {RESET}"
            ).strip()

            if number == "00":
                return

            if number.isdigit():

                index = int(number) - 1

                if 0 <= index < min(
                    len(results),
                    10
                ):

                    show_coin_details(
                        results[index]
                    )

                    return

            print(
                f"{RED}Invalid coin number.{RESET}"
            )

            pause()

    else:

        print()

        print(
            f"{CYAN}"
            "[D] COIN DETAILS"
            f"{RESET}"
        )

        choice = input(
            f"\n{WHITE}Selection: {RESET}"
        ).strip().lower()

        if choice == "d":

            number = input(
                f"{WHITE}Coin number: {RESET}"
            ).strip()

            if number.isdigit():

                index = int(number) - 1

                if 0 <= index < min(
                    len(results),
                    10
                ):

                    show_coin_details(
                        results[index]
                    )

                    return

            print(
                f"{RED}Invalid coin number.{RESET}"
            )

            pause()

    pause()


# ============================================================
# CRYPTO RADAR
# ============================================================

def crypto_radar():

    while True:

        clear()

        print(f"{CYAN}{BOLD}")

        print(
            "╔══════════════════════════════════════════════════════════════╗"
        )

        print(
            "║                      CRYPTO RADAR                           ║"
        )

        print(
            "╚══════════════════════════════════════════════════════════════╝"
        )

        print(RESET)

        print(
            f"{WHITE}"
            "[01] DEEP SCAN — NEW / UNKNOWN COINS"
            f"{RESET}"
        )

        print(
            f"{WHITE}"
            "[02] LOW RISK TOP PICKS"
            f"{RESET}"
        )

        print(
            f"{WHITE}"
            "[03] BUY RULES"
            f"{RESET}"
        )

        print(
            f"{WHITE}"
            "[00] BACK"
            f"{RESET}"
        )

        choice = input(
            f"\n{CYAN}KRYPT > {RESET}"
        ).strip()

        if choice in ("01", "1"):

            results = scan_new_tokens()

            show_results(
                results
            )

        elif choice in ("02", "2"):

            results = scan_memory_tokens()

            show_results(
                results
            )

        elif choice in ("03", "3"):

            clear()

            print(
                f"{CYAN}{BOLD}"
                "KRYPT BUY RULES"
                f"{RESET}"
            )

            line()

            print(

                f"{GREEN}"
                "BUY requires ALL of the following:"
                f"{RESET}\n"

            )

            print(
                f"  Risk         <= "
                f"{MAX_BUY_RISK}%"
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
                f"{CYAN}{BOLD}"
                "WHALE ENGINE"
                f"{RESET}"
            )

            print(
                "  Holder data  = REQUIRED"
            )

            print(
                "  Top holder   = concentration monitored"
            )

            print(
                "  Top 10       = concentration monitored"
            )

            print(
                "  Whale Risk   < 20"
            )

            print()

            print(

                f"{YELLOW}"
                "Fırsatı kaçırmak, kötü bir işlemi "
                "önermekten daha iyidir."
                f"{RESET}"

            )

            print(

                f"{GRAY}"
                "BUY is a model signal, not a guarantee."
                f"{RESET}"

            )

            pause()

        elif choice in ("00", "0"):

            return

        else:

            print(
                f"{RED}"
                "Invalid selection."
                f"{RESET}"
            )

            time.sleep(1)


# ============================================================
# NOTES
# ============================================================

def notes():

    while True:

        clear()

        print(
            f"{CYAN}{BOLD}"
            "NOTES"
            f"{RESET}"
        )

        line()

        print(
            f"{WHITE}[01]{RESET} NEW NOTE"
        )

        print(
            f"{WHITE}[02]{RESET} VIEW NOTES"
        )

        print(
            f"{WHITE}[03]{RESET} DELETE NOTE"
        )

        print()

        print(
            f"{GRAY}[00] BACK{RESET}"
        )

        line()

        choice = input(
            f"{WHITE}Selection: {RESET}"
        ).strip()

        if choice in ("01", "1"):

            add_note()

        elif choice in ("02", "2"):

            view_notes()

        elif choice in ("03", "3"):

            delete_note()

        elif choice in ("00", "0"):

            return

        else:

            print(
                f"{RED}Invalid selection.{RESET}"
            )

            time.sleep(1)


# ============================================================
# SYSTEM
# ============================================================

def system_menu():

    clear()

    print(
        f"{CYAN}{BOLD}"
        "SYSTEM"
        f"{RESET}"
    )

    line()

    print(
        f"{GREEN}"
        "KRYPT Dashboard online"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "Radar Engine : ONLINE"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "Security     : ONLINE"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "Whale Engine : ONLINE"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "Opportunity  : ONLINE"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "Confidence   : ONLINE"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "Signal Mode  : BUY / RISK"
        f"{RESET}"
    )

    pause()


# ============================================================
# DASHBOARD
# ============================================================

def my_positions():

    while True:

        clear()

        print(f"{CYAN}{BOLD}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                       MY POSITIONS                          ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(RESET)

        print(f"{WHITE}[01]{RESET} I BOUGHT")
        print(f"{WHITE}[02]{RESET} MY POSITIONS")
        print(f"{WHITE}[03]{RESET} I SOLD")
        print()
        print(f"{GRAY}[00] BACK{RESET}")
        line()

        choice = input(f"{WHITE}Selection: {RESET}").strip()

        if choice in ("01", "1"):
            buy_position()

        elif choice in ("02", "2"):
            live_positions()

        elif choice in ("03", "3"):
            sell_position()

        elif choice in ("00", "0"):
            return

        else:
            print(f"{RED}Invalid selection.{RESET}")
            time.sleep(1)


def buy_position():

    results = scan_memory_tokens()

    if not results:
        pause()
        return

    clear()

    print(f"{CYAN}{BOLD}SELECT COIN TO BUY{RESET}")
    line()

    for index, item in enumerate(results, 1):
        print(
            f"{WHITE}[{index:02d}]{RESET} "
            f"{BOLD}{item['symbol']}{RESET} "
            f"{GRAY}({item['chain']}){RESET}"
        )

    print()
    print(f"{GRAY}[00] BACK{RESET}")
    line()

    choice = input(f"{WHITE}Selection: {RESET}").strip()

    if choice in ("00", "0"):
        return

    try:
        index = int(choice) - 1
        item = results[index]
    except (ValueError, IndexError):
        print(f"{RED}Invalid selection.{RESET}")
        time.sleep(1)
        return

    price = float(item['pair'].get('priceUsd') or 0)

    if price <= 0:
        print(f"{RED}Live price unavailable.{RESET}")
        pause()
        return

    clear()

    print(f"{CYAN}{BOLD}I BOUGHT — {item['symbol']}{RESET}")
    line()

    print(f"{WHITE}Current price : ${price:.12g}{RESET}")

    invested_input = input(f"{WHITE}USD INVESTMENT: ${RESET}").strip()

    try:
        invested = float(invested_input)
        if invested <= 0:
            raise ValueError
    except ValueError:
        print(f"{RED}Invalid USD amount.{RESET}")
        time.sleep(1)
        return

    amount = invested / price

    positions = load_positions()

    positions.append({
        "chainId": item["chain"],
        "tokenAddress": item["address"],
        "symbol": item["symbol"],
        "name": item["name"],
        "invested_usd": invested,
        "entry_price": price,
        "entry_market_cap": float(
            item["pair"].get("marketCap")
            or item["pair"].get("fdv")
            or 0
        ),
        "amount": amount,
        "bought_at": datetime.now(timezone.utc).isoformat()
    })

    save_positions(positions)

    print()
    print(f"{GREEN}✓ POSITION SAVED{RESET}")
    print(f"{WHITE}Coin      : {item['symbol']}{RESET}")
    print(f"{WHITE}Invested  : ${invested:.2f}{RESET}")
    print(f"{WHITE}Entry     : ${price:.12g}{RESET}")
    print(f"{WHITE}Amount    : {amount:.8g} {item['symbol']}{RESET}")

    pause()


def view_positions():

    positions = load_positions()

    clear()

    print(f"{CYAN}{BOLD}MY POSITIONS  •  LIVE{RESET}" + " " * 38 + "Exit: Ctrl+C")
    line()

    if not positions:
        print(f"{GRAY}No open positions.{RESET}")
        return
        return

    total_invested = 0.0
    total_value = 0.0

    for index, position in enumerate(positions, 1):

        chain = position.get("chainId")
        address = position.get("tokenAddress")

        pairs = get_token_pairs(
            chain,
            address
        )

        pair = choose_best_pair(
            pairs
        )

        if not pair:
            print(
                f"{RED}[{index:02d}] "
                f"{position['symbol']} - price unavailable{RESET}"
            )
            print()
            continue

        current_price = float(
            pair.get("priceUsd") or 0
        )

        current_market_cap = float(
            pair.get("marketCap")
            or pair.get("fdv")
            or 0
        )

        invested = float(
            position.get("invested_usd") or 0
        )

        amount = float(
            position.get("amount") or 0
        )

        current_value = (
            amount * current_price
        )

        pnl_usd = (
            current_value - invested
        )

        pnl_percent = (
            (pnl_usd / invested) * 100
            if invested > 0
            else 0
        )

        total_invested += invested
        total_value += current_value

        pnl_color = (
            GREEN
            if pnl_usd >= 0
            else RED
        )

        print(
            f"{WHITE}[{index:02d}] "
            f"{BOLD}{position['symbol']}{RESET}"
        )

        print(
            f"    Invested : "
            f"${invested:.2f}"
        )

        print(
            f"    Entry    : "
            f"${float(position['entry_price']):.12g}"
        )

        print(
            f"    Current  : "
            f"${current_price:.12g}"
        )

        entry_market_cap = float(
            position.get("entry_market_cap") or 0
        )

        print(
            f"    Entry MC : "
            f"{format_money(entry_market_cap)}"
        )

        print(
            f"    Current MC: "
            f"{format_money(current_market_cap)}"
        )

        print(
            f"    Amount   : "
            f"{amount:.8g}"
        )

        print(
            f"    Value    : "
            f"${current_value:.2f}"
        )

        print(
            f"    P/L      : "
            f"{pnl_color}"
            f"${pnl_usd:+.2f} "
            f"({pnl_percent:+.2f}%)"
            f"{RESET}"
        )

        security = get_token_security(
            chain,
            address
        )

        analysis = calculate_analysis(
            pair,
            security
        )

        position_status = calculate_position_status(
            analysis,
            float(position.get("entry_price") or 0),
            current_price
        )

        status = position_status["status"]

        if status == "HOLD":
            status_color = GREEN
            status_icon = "🟢"

        elif status == "WATCH":
            status_color = YELLOW
            status_icon = "🟡"

        else:
            status_color = RED
            status_icon = "🔴"

        print(
            f"    KRYPT     : "
            f"{status_color}"
            f"{status_icon} {status}"
            f"{RESET}"
        )

        print(
            f"    Reason    : "
            f"{position_status['reason']}"
        )

        print()

    total_pnl = total_value - total_invested

    total_pnl_percent = (
        (total_pnl / total_invested) * 100
        if total_invested > 0
        else 0
    )

    total_color = (
        GREEN
        if total_pnl >= 0
        else RED
    )

    line()

    print(
        f"{WHITE}{BOLD}"
        f"TOTAL INVESTED : "
        f"${total_invested:.2f}"
        f"{RESET}"
    )

    print(
        f"{WHITE}{BOLD}"
        f"TOTAL VALUE    : "
        f"${total_value:.2f}"
        f"{RESET}"
    )

    print(
        f"{WHITE}{BOLD}"
        f"TOTAL P/L      : "
        f"{total_color}"
        f"${total_pnl:+.2f} "
        f"({total_pnl_percent:+.2f}%)"
        f"{RESET}"
    )



def live_positions():
    try:
        while True:
            clear()
            view_positions()
            time.sleep(15)
    except KeyboardInterrupt:
        clear()
        print(f"{GRAY}Live positions closed.{RESET}")
        time.sleep(1)


def sell_position():

    positions = load_positions()

    clear()

    print(f"{CYAN}{BOLD}I SOLD{RESET}")
    line()

    if not positions:
        print(f"{GRAY}No open positions.{RESET}")
        pause()
        return

    for index, position in enumerate(positions, 1):
        print(
            f"{WHITE}[{index:02d}]{RESET} "
            f"{BOLD}{position["symbol"]}{RESET} "
            f"{GRAY}${position["invested_usd"]:.2f} invested{RESET}"
        )

    print()
    print(f"{GRAY}[00] BACK{RESET}")
    line()

    choice = input(
        f"{WHITE}Select position to sell: {RESET}"
    ).strip()

    if choice in ("00", "0"):
        return

    try:
        index = int(choice) - 1
        position = positions[index]
    except (ValueError, IndexError):
        print(f"{RED}Invalid selection.{RESET}")
        time.sleep(1)
        return

    print()
    print(
        f"{WHITE}Sell {BOLD}{position["symbol"]}{RESET}"
        f"{WHITE} and remove it from MY POSITIONS?{RESET}"
    )

    confirm = input(
        f"{WHITE}Confirm (y/n): {RESET}"
    ).strip().lower()

    if confirm not in ("y", "yes"):
        print(f"{GRAY}Sale cancelled.{RESET}")
        pause()
        return

    removed = positions.pop(index)
    save_positions(positions)

    print()
    print(
        f"{GREEN}✓ {removed["symbol"]} removed from "
        f"I BOUGHT Memory.{RESET}"
    )

    pause()



def dashboard():

    while True:

        clear()

        print(f"{CYAN}{BOLD}")

        print(
            "╔══════════════════════════════════════════════════════════════╗"
        )

        print(
            "║                         KRYPT                                ║"
        )

        print(
            "║                    CRYPTO DASHBOARD                          ║"
        )

        print(
            "╠══════════════════════════════════════════════════════════════╣"
        )

        print(
            "║                                                              ║"
        )

        print(
            "║  [01] CRYPTO RADAR                                           ║"
        )

        print(
            "║  [02] MY POSITIONS                                           ║"
        )

        print(
            "║  [03] NOTES                                                  ║"
        )

        print(
            "║  [04] SYSTEM                                                 ║"
        )

        print(
            "║  [00] EXIT                                                   ║"
        )

        print(
            "║                                                              ║"
        )

        print(
            "╚══════════════════════════════════════════════════════════════╝"
        )

        print(RESET)

        choice = input(
            f"{CYAN}KRYPT > {RESET}"
        ).strip()

        if choice in ("01", "1"):

            crypto_radar()

        elif choice in ("02", "2"):

            my_positions()

        elif choice in ("03", "3"):

            notes()

        elif choice in ("04", "4"):

            system_menu()

        elif choice in ("00", "0"):

            clear()

            print(
                f"{CYAN}"
                "KRYPT shutting down..."
                f"{RESET}"
            )

            time.sleep(0.5)

            sys.exit()

        else:

            print(
                f"{RED}"
                "Invalid selection."
                f"{RESET}"
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
