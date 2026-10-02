import os
import sys
import time
import requests
import json
import threading
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
DEX_RECENT_UPDATES_URL = "https://api.dexscreener.com/token-profiles/recent-updates/v1"
DEX_COMMUNITY_TAKEOVERS_URL = "https://api.dexscreener.com/community-takeovers/latest/v1"
DEX_ADS_URL = "https://api.dexscreener.com/ads/latest/v1"
GECKO_NEW_POOLS_URL = "https://api.geckoterminal.com/api/v2/networks/new_pools"
DEX_TOKEN_PAIRS_URL = "https://api.dexscreener.com/token-pairs/v1/{chain}/{address}"
GOPLUS_SOLANA_URL = "https://api.gopluslabs.io/api/v1/solana/token_security/"
GOPLUS_EVM_URL = "https://api.gopluslabs.io/api/v1/token_security/{chain_id}"
RUGCHECK_REPORT_URL = "https://api.rugcheck.xyz/v1/tokens/{mint}/report"
RUGCHECK_CACHE = {}

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
FORECAST_MEMORY_FILE = "krypt_forecast_memory.json"
SIGNAL_FILE = "krypt_signal.json"
SIGNAL_HISTORY_FILE = "krypt_signal_history.json"
SIGNAL_MIN_SCORE = 90
SIGNAL_HISTORY_LOCK = threading.Lock()

def publish_krypt_signal(item):
    try:
        analysis = item.get("analysis") or {}
        score = float(analysis.get("krypt_score") or 0)

        if analysis.get("signal") != "BUY" or score < SIGNAL_MIN_SCORE:
            return

        pair = item.get("pair") or {}
        base = pair.get("baseToken") or {}
        liquidity = pair.get("liquidity") or {}
        volume = pair.get("volume") or {}
        txns = pair.get("txns") or {}
        txns_5m = txns.get("m5") or {}

        now = datetime.now(timezone.utc).isoformat()
        address = item.get("address") or base.get("address") or ""

        signal = {
            "signal_id": f"{item.get('chain', 'unknown')}:{address}:{score:.1f}",
            "signal": "BUY",
            "score": score,
            "symbol": item.get("symbol") or base.get("symbol") or "UNKNOWN",
            "name": item.get("name") or base.get("name") or "UNKNOWN",
            "chain": item.get("chain") or pair.get("chainId") or "unknown",
            "address": address,
            "market_cap": pair.get("marketCap"),
            "price": pair.get("priceUsd"),
            "liquidity": liquidity.get("usd"),
            "volume_5m": volume.get("m5"),
            "buys_5m": txns_5m.get("buys", 0),
            "sells_5m": txns_5m.get("sells", 0),
            "security": analysis.get("security") or {},
            "whale": analysis.get("whale") or {},
            "signal_time": now
        }

        tmp = SIGNAL_FILE + ".tmp"

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(signal, f, ensure_ascii=False, indent=2)

        os.replace(tmp, SIGNAL_FILE)

        try:
            with SIGNAL_HISTORY_LOCK:
                history = []

                if os.path.exists(SIGNAL_HISTORY_FILE):
                    try:
                        with open(
                            SIGNAL_HISTORY_FILE,
                            "r",
                            encoding="utf-8"
                        ) as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                history = data
                    except Exception:
                        history = []

                duplicate = False

                for saved in reversed(history):
                    if not isinstance(saved, dict):
                        continue

                    if (
                        str(saved.get("chain", "")).lower()
                        == str(signal.get("chain", "")).lower()
                        and str(saved.get("address", "")).lower()
                        == str(signal.get("address", "")).lower()
                    ):
                        duplicate = True
                        break

                if not duplicate:
                    history.append({
                        **signal,
                        "entry_price": safe_float(signal.get("price")),
                        "evaluated": False,
                        "5m": None,
                        "15m": None,
                        "30m": None,
                        "60m": None,
                        "max_gain": None,
                        "max_drawdown": None,
                        "validation_status": "PENDING"
                    })

                    tmp_history = SIGNAL_HISTORY_FILE + ".tmp"

                    with open(
                        tmp_history,
                        "w",
                        encoding="utf-8"
                    ) as f:
                        json.dump(
                            history,
                            f,
                            ensure_ascii=False,
                            indent=2
                        )
                        f.flush()
                        os.fsync(f.fileno())

                    os.replace(
                        tmp_history,
                        SIGNAL_HISTORY_FILE
                    )

        except Exception as e:
            print(
                f"{RED}[KRYPT VALIDATION] "
                f"History error: {e}{RESET}"
            )

        print(
            f"{GREEN}[KRYPT SIGNALS] "
            f"{signal['symbol']} BUY {score:.1f} "
            f"published.{RESET}"
        )

    except Exception as e:
        print(
            f"{RED}[KRYPT SIGNALS] Publish error: "
            f"{e}{RESET}"
        )


FORECAST_MEMORY_LOCK = threading.Lock()


def write_forecast_memory(memory):
    temp_file = FORECAST_MEMORY_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_file, FORECAST_MEMORY_FILE)


def save_forecast_memory(record):
    try:
        with FORECAST_MEMORY_LOCK:
            memory = []

            if os.path.exists(FORECAST_MEMORY_FILE):
                with open(
                    FORECAST_MEMORY_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:
                    data = json.load(f)

                    if isinstance(data, list):
                        memory = data

            chain = str(
                record.get("chainId") or ""
            ).lower()

            address = str(
                record.get("tokenAddress") or ""
            ).lower()

            engine = str(
                record.get("direction_engine") or ""
            ).upper()

            saved_at = record.get("saved_at")

            if chain and address and saved_at:
                try:
                    current_time = datetime.fromisoformat(
                        saved_at
                    )

                    for existing in reversed(memory):
                        if not isinstance(existing, dict):
                            continue

                        existing_chain = str(
                            existing.get("chainId") or ""
                        ).lower()

                        existing_address = str(
                            existing.get("tokenAddress") or ""
                        ).lower()

                        existing_engine = str(
                            existing.get("direction_engine") or ""
                        ).upper()

                        if (
                            existing_chain != chain
                            or existing_address != address
                            or existing_engine != engine
                        ):
                            continue

                        existing_time = existing.get("saved_at")

                        if not existing_time:
                            continue

                        try:
                            previous_time = datetime.fromisoformat(
                                existing_time
                            )
                        except Exception:
                            continue

                        age_seconds = (
                            current_time - previous_time
                        ).total_seconds()

                        if 0 <= age_seconds < 600:
                            return

                        break

                except Exception:
                    pass

            memory.append(record)
            write_forecast_memory(memory)

    except Exception:
        pass
MAX_MEMORY_TOKENS = 20



def classify_forecast_outcome(actual_change, forecast):

    low = safe_float(forecast.get("low"))
    high = safe_float(forecast.get("high"))

    if high < low:
        low, high = high, low

    if low >= 0:
        expected_direction = "UP"
    elif high <= 0:
        expected_direction = "DOWN"
    else:
        expected_direction = "MIXED"

    if actual_change > 0:
        actual_direction = "UP"
    elif actual_change < 0:
        actual_direction = "DOWN"
    else:
        actual_direction = "FLAT"

    direction_hit = (
        expected_direction == "MIXED"
        or expected_direction == actual_direction
    )

    range_hit = (
        low <= actual_change <= high
    )

    return {
        "expected_direction": expected_direction,
        "actual_direction": actual_direction,
        "direction_hit": direction_hit,
        "range_hit": range_hit
    }


def evaluate_krypt_signal_record(record):
    try:
        signal_time = datetime.fromisoformat(
            record["signal_time"]
        )

        now = datetime.now(timezone.utc)

        horizons = {
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "60m": 60
        }

        tolerance = 2

        chain = record.get("chain")
        address = record.get("address")
        entry_price = safe_float(
            record.get("entry_price")
        )

        if not chain or not address or entry_price <= 0:
            return record

        for horizon, minutes in horizons.items():

            if record.get(horizon) is not None:
                continue

            age_minutes = (
                now - signal_time
            ).total_seconds() / 60

            if age_minutes < minutes:
                continue

            if age_minutes >= minutes + tolerance:
                record[f"{horizon}_status"] = "MISSED"
                continue

            pairs = get_token_pairs(
                chain,
                address
            )

            pair = choose_best_pair(pairs)

            if not pair:
                continue

            current_price = safe_float(
                pair.get("priceUsd")
            )

            if current_price <= 0:
                continue

            actual_change = (
                (current_price - entry_price)
                / entry_price
            ) * 100

            record[horizon] = round(
                actual_change,
                2
            )

            record[f"{horizon}_status"] = "VALID"

            record[f"{horizon}_evaluated_at"] = (
                now.isoformat()
            )

        valid = all(
            record.get(
                f"{horizon}_status"
            ) == "VALID"
            for horizon in horizons
        )

        missed = any(
            record.get(
                f"{horizon}_status"
            ) == "MISSED"
            for horizon in horizons
        )

        if valid:
            record["validation_status"] = "COMPLETE"
            record["evaluated"] = True
            record["evaluated_at"] = (
                now.isoformat()
            )
        elif missed:
            record["validation_status"] = "INCOMPLETE"
            record["evaluated"] = False

        return record

    except Exception:
        return record

def evaluate_forecast_record(record, target_horizon=None):
    try:
        saved_at = datetime.fromisoformat(
            record["saved_at"]
        )

        now = datetime.now(timezone.utc)

        horizons = {
            "1H": 1,
            "6H": 6,
            "1D": 24,
            "1W": 24 * 7,
            "1M": 24 * 30
        }

        if record.get("direction_engine") == "V4":
            forecasts = record.get(
                "forecasts_v4",
                {}
            )
        else:
            forecasts = record.get(
                "forecasts",
                {}
            )

        selected_horizons = (
            [target_horizon]
            if target_horizon in horizons
            else list(horizons.keys())
        )

        for horizon in selected_horizons:

            hours = horizons[horizon]

            forecast = forecasts.get(horizon)

            if not forecast:
                continue

            evaluated_key = f"evaluated_{horizon}"

            if record.get(evaluated_key):
                continue

            age_hours = (
                now - saved_at
            ).total_seconds() / 3600

            if age_hours < hours:
                continue

            chain = record.get("chainId")
            address = record.get("tokenAddress")

            if not chain or not address:
                continue

            pairs = get_token_pairs(
                chain,
                address
            )

            pair = choose_best_pair(pairs)

            if not pair:
                continue

            current_price = safe_float(
                pair.get("priceUsd")
            )

            start_price = safe_float(
                record.get("price")
            )

            if current_price <= 0 or start_price <= 0:
                continue

            actual_change = (
                (current_price - start_price)
                / start_price
            ) * 100

            outcome = classify_forecast_outcome(
                actual_change,
                forecast
            )

            direction_signal = record.get(
                "direction_signal",
                {}
            )

            recorded_direction = (
                direction_signal.get("direction")
                if isinstance(direction_signal, dict)
                else None
            )

            if recorded_direction in (
                "UP",
                "DOWN",
                "MIXED"
            ):
                outcome["expected_direction"] = (
                    recorded_direction
                )

                if recorded_direction == "MIXED":
                    outcome["direction_hit"] = False
                else:
                    outcome["direction_hit"] = (
                        recorded_direction
                        == outcome["actual_direction"]
                    )

            record[evaluated_key] = True

            record[f"actual_{horizon}"] = round(
                actual_change,
                2
            )

            record[f"hit_{horizon}"] = (
                outcome["range_hit"]
            )

            record[f"direction_hit_{horizon}"] = (
                outcome["direction_hit"]
            )

            record[f"expected_direction_{horizon}"] = (
                outcome["expected_direction"]
            )

            record[f"actual_direction_{horizon}"] = (
                outcome["actual_direction"]
            )

            record[f"evaluated_at_{horizon}"] = (
                now.isoformat()
            )

        return record

    except Exception:
        return record

def evaluate_forecast_memory(target_horizon=None):
    try:
        if not os.path.exists(
            FORECAST_MEMORY_FILE
        ):
            return 0

        with open(
            FORECAST_MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            memory = json.load(f)

        if not isinstance(memory, list):
            return 0

        valid_horizons = {
            "1H",
            "6H",
            "1D",
            "1W",
            "1M"
        }

        if (
            target_horizon is not None
            and target_horizon not in valid_horizons
        ):
            return 0

        evaluated_count = 0

        for index, record in enumerate(memory):

            if not isinstance(record, dict):
                continue

            before = dict(record)

            memory[index] = evaluate_forecast_record(
                record,
                target_horizon=target_horizon
            )

            if memory[index] != before:
                evaluated_count += 1

        with FORECAST_MEMORY_LOCK:
            write_forecast_memory(memory)

        return evaluated_count

    except Exception:
        return 0

def calculate_forecast_accuracy():
    try:
        if not os.path.exists(
            FORECAST_MEMORY_FILE
        ):
            return {}

        with open(
            FORECAST_MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            memory = json.load(f)

        if not isinstance(memory, list):
            return {}

        horizons = (
            "1H",
            "6H",
            "1D",
            "1W",
            "1M"
        )

        accuracy = {}

        for horizon in horizons:

            evaluated = [
                record
                for record in memory
                if isinstance(record, dict)
                and record.get(
                    f"evaluated_{horizon}"
                )
            ]

            if not evaluated:
                accuracy[horizon] = {
                    "samples": 0,
                    "direction_accuracy": None,
                    "range_accuracy": None
                }
                continue

            direction_hits = sum(
                1
                for record in evaluated
                if record.get(
                    f"direction_hit_{horizon}"
                )
            )

            range_hits = sum(
                1
                for record in evaluated
                if record.get(
                    f"hit_{horizon}"
                )
            )

            total = len(evaluated)

            accuracy[horizon] = {
                "samples": total,
                "direction_accuracy": round(
                    direction_hits / total * 100,
                    2
                ),
                "range_accuracy": round(
                    range_hits / total * 100,
                    2
                )
            }

        return accuracy

    except Exception:
        return {}



def calculate_v4_forward_accuracy():
    """
    KRYPT Direction V4 forward-test accuracy.

    Only evaluates records explicitly tagged as V4.
    Historical/non-V4 records are excluded.
    """

    try:
        if not os.path.exists(FORECAST_MEMORY_FILE):
            return {}

        with open(
            FORECAST_MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            memory = json.load(f)

        if not isinstance(memory, list):
            return {}

        horizons = (
            "1H",
            "6H",
            "1D",
            "1W",
            "1M"
        )

        result = {}

        for horizon in horizons:

            evaluated = [
                record
                for record in memory
                if isinstance(record, dict)
                and record.get("direction_engine") == "V4"
                and record.get(
                    f"evaluated_{horizon}"
                )
            ]

            if not evaluated:
                result[horizon] = {
                    "samples": 0,
                    "direction_accuracy": None
                }
                continue

            direction_hits = sum(
                1
                for record in evaluated
                if record.get(
                    f"direction_hit_{horizon}"
                )
            )

            total = len(evaluated)

            result[horizon] = {
                "samples": total,
                "direction_accuracy": round(
                    direction_hits / total * 100,
                    2
                )
            }

        return result

    except Exception:
        return {}

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

        try:

            recent_response = SESSION.get(
                DEX_RECENT_UPDATES_URL,
                timeout=15
            )

            if recent_response.status_code == 200:

                recent_updates = recent_response.json()

                if isinstance(recent_updates, list):
                    profiles.extend(recent_updates)

        except Exception:
            pass

        try:

            takeover_response = SESSION.get(
                DEX_COMMUNITY_TAKEOVERS_URL,
                timeout=15
            )

            if takeover_response.status_code == 200:

                takeovers = takeover_response.json()

                if isinstance(takeovers, list):
                    profiles.extend(takeovers)

        except Exception:
            pass

        try:

            ads_response = SESSION.get(
                DEX_ADS_URL,
                timeout=15
            )

            if ads_response.status_code == 200:

                ads = ads_response.json()

                if isinstance(ads, list):
                    profiles.extend(ads)

        except Exception:
            pass

        gecko_networks = (
            ("bsc", "bsc"),
            ("eth", "ethereum"),
            ("base", "base"),
        )

        for gecko_network, display_chain in gecko_networks:

            try:

                gecko_response = SESSION.get(
                    f"https://api.geckoterminal.com/api/v2/networks/{gecko_network}/new_pools",
                    headers={"Accept": "application/json;version=20230203"},
                    timeout=15
                )

                if gecko_response.status_code != 200:
                    continue

                gecko_data = gecko_response.json()
                gecko_pools = gecko_data.get("data", [])

                if not isinstance(gecko_pools, list):
                    continue

                for pool in gecko_pools:

                    if not isinstance(pool, dict):
                        continue

                    attrs = pool.get("attributes", {})
                    relationships = pool.get("relationships", {})

                    base_token = relationships.get(
                        "base_token",
                        {}
                    )

                    token_data = base_token.get("data", {})
                    token_id = token_data.get("id")

                    if not token_id:
                        continue

                    token_parts = str(token_id).split("_", 1)

                    if len(token_parts) != 2:
                        continue

                    chain_id = token_parts[0]
                    token_address = token_parts[1]

                    if not chain_id or not token_address:
                        continue

                    profiles.append({
                        "chainId": chain_id,
                        "tokenAddress": token_address,
                        "source": "geckoterminal",
                        "poolAddress": attrs.get("address"),
                        "poolName": attrs.get("name")
                    })

            except Exception:
                pass

            time.sleep(2)

        # Re-add recently strong BUY candidates.
        try:
            memory = load_radar_memory()

            for saved in memory:
                if isinstance(saved, dict):
                    profiles.append(saved)

        except Exception:
            pass

        # Deduplicate by token contract first.
        # The same symbol may legitimately exist on different contracts,
        # so symbol alone is not enough for identity.
        unique = []
        seen_contracts = set()

        for profile in profiles:
            chain = profile.get("chainId")
            address = profile.get("tokenAddress")

            if not chain or not address:
                continue

            key = (
                str(chain).lower(),
                str(address).lower()
            )

            if key in seen_contracts:
                continue

            seen_contracts.add(key)
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


def calculate_pair_quality(pair):
    """
    Rank individual trading pairs by market quality.
    This does not create BUY signals.
    """

    if not isinstance(pair, dict):
        return 0

    liquidity = safe_float(
        (pair.get("liquidity") or {}).get("usd")
    )

    volume = safe_float(
        (pair.get("volume") or {}).get("h24")
    )

    volume_5m = safe_float(
        (pair.get("volume") or {}).get("m5")
    )

    txns = pair.get("txns") or {}
    txns_5m = txns.get("m5") or {}

    buys_5m = safe_int(txns_5m.get("buys"))
    sells_5m = safe_int(txns_5m.get("sells"))

    total_txns_5m = buys_5m + sells_5m

    score = 0

    if liquidity >= 500000:
        score += 30
    elif liquidity >= 100000:
        score += 25
    elif liquidity >= 50000:
        score += 18
    elif liquidity >= MIN_LIQUIDITY:
        score += 10
    else:
        score -= 15

    if volume >= 5000000:
        score += 25
    elif volume >= 1000000:
        score += 20
    elif volume >= 100000:
        score += 14
    elif volume >= MIN_VOLUME:
        score += 7
    else:
        score -= 10

    if volume_5m >= 100000:
        score += 20
    elif volume_5m >= 10000:
        score += 14
    elif volume_5m >= 1000:
        score += 7

    if total_txns_5m >= 500:
        score += 15
    elif total_txns_5m >= 200:
        score += 10
    elif total_txns_5m >= 50:
        score += 6
    elif total_txns_5m >= 10:
        score += 3

    return max(0, min(score, 100))


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
        key=lambda p: (
            calculate_pair_quality(p),
            safe_float(
                (p.get("liquidity") or {}).get("usd")
            )
        )
    )


def get_rugcheck_security(token_address):

    if token_address in RUGCHECK_CACHE:
        return RUGCHECK_CACHE[token_address]

    try:
        response = SESSION.get(
            RUGCHECK_REPORT_URL.format(
                mint=token_address
            ),
            headers={
                "Accept": "application/json"
            },
            timeout=15
        )

        if response.status_code != 200:
            RUGCHECK_CACHE[token_address] = None
            return None

        data = response.json()

        if not isinstance(data, dict):
            RUGCHECK_CACHE[token_address] = None
            return None

        RUGCHECK_CACHE[token_address] = data
        return data

    except Exception:
        RUGCHECK_CACHE[token_address] = None
        return None

def get_solana_security(token_address):

    goplus_security = None

    try:
        response = SESSION.get(
            GOPLUS_SOLANA_URL,
            params={
                "contract_addresses": token_address
            },
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            result = data.get("result")

            if isinstance(result, dict):
                if token_address in result:
                    goplus_security = result[token_address]
                elif len(result) == 1:
                    goplus_security = next(iter(result.values()))

    except Exception:
        pass

    if isinstance(goplus_security, dict):
        result = dict(goplus_security)
    else:
        result = {}

    rugcheck = get_rugcheck_security(token_address)

    if not isinstance(rugcheck, dict):
        if isinstance(goplus_security, dict):
            result["_rugcheck"] = {
                "available": False
            }
        else:
            return None

    if isinstance(rugcheck, dict):

        rug_holders = rugcheck.get("topHolders")

        if (
            not isinstance(result.get("holders"), list)
            or not result.get("holders")
        ):
            if isinstance(rug_holders, list) and rug_holders:
                holders = []

                for holder in rug_holders:
                    if not isinstance(holder, dict):
                        continue

                    item = dict(holder)

                    if "percent" not in item:
                        pct = item.get("pct")

                        if pct is not None:
                            item["percent"] = pct

                    holders.append(item)

                if holders:
                    result["holders"] = holders

        if not result.get("holder_count"):
            total_holders = rugcheck.get("totalHolders")

            if total_holders is not None:
                result["holder_count"] = total_holders

        if "mint_authority" not in result:
            result["mint_authority"] = rugcheck.get(
                "mintAuthority"
            )

        if "freeze_authority" not in result:
            result["freeze_authority"] = rugcheck.get(
                "freezeAuthority"
            )

        result["_rugcheck"] = {
            "available": True,
            "score": rugcheck.get("score"),
            "score_normalised": rugcheck.get(
                "score_normalised"
            ),
            "risks": rugcheck.get("risks") or [],
            "rugged": rugcheck.get("rugged"),
            "creator": rugcheck.get("creator"),
            "mint_authority": rugcheck.get(
                "mintAuthority"
            ),
            "freeze_authority": rugcheck.get(
                "freezeAuthority"
            )
        }

    if not result:
        return None

    return result

def get_token_security(chain, token_address):

    chain_name = str(chain).lower().strip()

    if chain_name == "eth":
        chain_name = "ethereum"

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
        result["reasons"].append("Holder data unavailable")
        return result

    holders = security.get("holders")

    if not isinstance(holders, list) or not holders:
        result["reasons"].append("Top holder data unavailable")
        return result

    percentages = []
    locked_percent = 0.0

    for holder in holders:
        if not isinstance(holder, dict):
            continue

        percent = safe_float(holder.get("percent"))

        if 0 <= percent <= 1:
            percent *= 100

        if percent > 0:
            percentages.append(percent)

        locked = holder.get("is_locked")

        if str(locked).lower() in ("1", "true"):
            locked_percent += percent

    if not percentages:
        result["reasons"].append("Holder percentages unavailable")
        return result

    result["available"] = True

    result["holder_count"] = safe_int(
        security.get("holder_count")
    )

    if result["holder_count"] <= 0:
        result["holder_count"] = len(holders)

    percentages.sort(reverse=True)

    result["top_holder_percent"] = percentages[0]
    result["top10_percent"] = sum(percentages[:10])
    result["locked_percent"] = locked_percent

    top = result["top_holder_percent"]
    top10 = result["top10_percent"]

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

    if locked_percent >= 30:
        result["reasons"].append(
            f"{locked_percent:.2f}% of top holders locked"
        )

    if not result["reasons"]:
        result["reasons"].append(
            "Holder distribution looks acceptable"
        )

    result["risk"] = min(result["risk"], 100)

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

    rugcheck = security.get("_rugcheck")

    if isinstance(rugcheck, dict):
        if rugcheck.get("available") is False:
            result["available"] = False
            result["reasons"].append(
                "RugCheck data unavailable"
            )
            return result

        rugged = rugcheck.get("rugged")

        if str(rugged).lower() in ("true", "1", "yes"):
            result["risk"] += 100
            result["reasons"].append(
                "RugCheck reports token as rugged"
            )

        mint_authority = rugcheck.get("mint_authority")
        freeze_authority = rugcheck.get("freeze_authority")

        if mint_authority:
            result["risk"] += 8
            result["reasons"].append(
                "RugCheck mint authority detected"
            )

        if freeze_authority:
            result["risk"] += 8
            result["reasons"].append(
                "RugCheck freeze authority detected"
            )

        risk_weights = {
            "creator history of rugged tokens": 40,
            "large amount of lp unlocked": 20,
            "fee config enabled": 12,
            "low amount of lp providers": 8,
            "mutable metadata": 4
        }

        risks = rugcheck.get("risks")

        if isinstance(risks, list):
            for risk_item in risks:
                if not isinstance(risk_item, dict):
                    continue

                name = str(
                    risk_item.get("name") or ""
                ).strip()

                if not name:
                    continue

                normalized_name = name.lower()
                weight = risk_weights.get(normalized_name)

                if weight is None:
                    level = str(
                        risk_item.get("level") or ""
                    ).lower()

                    if level == "danger":
                        weight = 20
                    elif level == "warn":
                        weight = 5
                    else:
                        weight = 3

                result["risk"] += weight
                result["reasons"].append(
                    f"RugCheck: {name}"
                )

    solana_fields = (
        "mintable",
        "freezable",
        "closable",
        "metadata_mutable",
        "non_transferable"
    )

    is_solana = (
        any(field in security for field in solana_fields)
        or isinstance(security.get("_rugcheck"), dict)
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

    result["risk"] = min(result["risk"], 100)

    result["safe"] = (
        result["available"]
        and result["risk"] == 0
    )

    if result["safe"]:
        result["reasons"].append(
            "Core security checks passed"
        )

    return result


# ============================================================
# ANALYSIS ENGINE
# ============================================================

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


def calculate_direction_signal(
    price_change_5m,
    price_change_1h,
    price_change_24h,
    buy_ratio_5m,
    buy_ratio_1h,
    volume,
    liquidity
):
    """
    KRYPT Direction V4

    Historical reversal-first direction model.
    Positive recent momentum is treated as potential exhaustion
    rather than automatic bullish continuation.

    This signal is directional context only.
    It does not create a BUY signal.
    """

    score = 0

    # 1H HISTORICAL REVERSAL BIAS
    if price_change_1h > 100:
        score -= 70
    elif price_change_1h > 50:
        score -= 55
    elif price_change_1h > 25:
        score -= 60
    elif price_change_1h > 10:
        score -= 58
    elif price_change_1h > 0:
        score -= 50
    elif price_change_1h > -20:
        score -= 25
    elif price_change_1h > -50:
        score += 0
    else:
        score -= 20

    # 5M MOMENTUM
    if price_change_5m >= 20:
        score -= 15
    elif price_change_5m >= 10:
        score -= 10
    elif price_change_5m >= 5:
        score -= 5
    elif price_change_5m <= -10:
        score += 8
    elif price_change_5m <= -5:
        score += 4

    # 24H CONTEXT
    if price_change_24h >= 300:
        score -= 15
    elif price_change_24h >= 100:
        score -= 10
    elif price_change_24h >= 50:
        score -= 5
    elif price_change_24h <= -50:
        score += 5

    # BUY FLOW
    if buy_ratio_5m >= 0.70:
        score += 5
    elif buy_ratio_5m >= 0.60:
        score += 3
    elif buy_ratio_5m < 0.40:
        score -= 5

    if buy_ratio_1h >= 0.65:
        score += 5
    elif buy_ratio_1h >= 0.55:
        score += 2
    elif buy_ratio_1h < 0.40:
        score -= 5

    # MARKET QUALITY
    if volume >= 1_000_000:
        score += 3
    elif volume < 5_000:
        score -= 3

    if liquidity >= 500_000:
        score += 3
    elif liquidity < 10_000:
        score -= 3

    score = max(-100, min(score, 100))

    # V4 is intentionally selective.
    # Historical testing strongly supports DOWN in the
    # positive 1H momentum region. UP is not yet sufficiently
    # validated, so uncertain cases remain MIXED.
    if score <= -40:
        direction = "DOWN"
    elif score >= 40:
        direction = "UP"
    else:
        direction = "MIXED"

    # V5 MIXED reversal rule.
    # Forward-test result: MIXED + 24H <= -20% -> DOWN
    # 34 samples: 31 DOWN / 3 UP = 91.18% DOWN.
    if direction == "MIXED" and price_change_24h <= -20:
        direction = "DOWN"

    # Historical confidence calibration.
    # Based on 679 evaluated 1H samples.
    if direction == "DOWN":
        if score <= -70:
            confidence = 94
        elif score <= -60:
            confidence = 83
        elif score <= -50:
            confidence = 86
        elif score <= -40:
            confidence = 77
        else:
            confidence = 68
    else:
        confidence = min(95, round(abs(score)))


    return {
        "direction": direction,
        "score": score,
        "confidence": confidence
    }


def calculate_grow_forecast_v4(
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
    """
    GROW FORECAST ENGINE V4 — experimental.

    V4 is regime-first.
    It does not use Grow Score as a direct growth multiplier.

    Current validated candidate:
        1H:  -50% <= 1H < -20%
        5M:    0% <= 5M < +10%
        24H:   0% <= 24H < +100%
        Liquidity >= $100K
        Volume >= $1M

    Base forecast:
        -2% -> +12%

    Extreme upside is kept separate from the base range.
    This function is experimental and is NOT a BUY signal.
    """

    try:
        p5 = float(price_change_5m or 0)
        p1 = float(price_change_1h or 0)
        p24 = float(price_change_24h or 0)
        vol = float(volume or 0)
        liq = float(liquidity or 0)

        recovery = (
            -50 <= p1 < -20
            and 0 <= p5 < 10
            and 0 <= p24 < 100
        )

        quality = (
            liq >= 100_000
            and vol >= 1_000_000
        )

        forecasts = {
            "1H": {
                "low": 0.0,
                "high": 0.0,
                "confidence": 20
            },
            "6H": {
                "low": 0.0,
                "high": 0.0,
                "confidence": 20
            },
            "1D": {
                "low": 0.0,
                "high": 0.0,
                "confidence": 15
            },
            "1W": {
                "low": 0.0,
                "high": 0.0,
                "confidence": 10
            },
            "1M": {
                "low": 0.0,
                "high": 0.0,
                "confidence": 10
            }
        }

        if recovery and quality:

            # Validated 1H base candidate.
            forecasts["1H"] = {
                "low": -2.0,
                "high": 12.0,
                "confidence": 60
            }

            # 6H currently has insufficient independent
            # validation, therefore keep it conservative.
            forecasts["6H"] = {
                "low": -15.0,
                "high": 15.0,
                "confidence": 35
            }

            # 1D currently has insufficient data.
            forecasts["1D"] = {
                "low": -25.0,
                "high": 25.0,
                "confidence": 20
            }

        return forecasts

    except Exception:
        return None


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

    market_cap = safe_float(
        pair.get("marketCap") or pair.get("fdv")
    )

    txns = pair.get("txns") or {}

    txns_5m = txns.get("m5") or {}
    txns_1h = txns.get("h1") or {}

    buys_5m = safe_int(txns_5m.get("buys"))
    sells_5m = safe_int(txns_5m.get("sells"))

    buys_1h = safe_int(txns_1h.get("buys"))
    sells_1h = safe_int(txns_1h.get("sells"))

    total_5m = buys_5m + sells_5m
    total_1h = buys_1h + sells_1h

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

    age_hours = get_token_age_hours(pair)

    whale = analyze_holders(security)
    security_result = analyze_security(security)

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

    if volume_5m <= 0:
        risk += 8
        risk_reasons.append("No recent volume")
    elif liquidity > 0:
        volume_liquidity_ratio = volume_5m / liquidity

        if volume_liquidity_ratio < 0.005:
            risk += 6
            risk_reasons.append("Weak recent volume")

    if price_change_5m <= -20:
        risk += 15
        risk_reasons.append("Heavy 5m dump")
    elif price_change_5m <= -10:
        risk += 8
        risk_reasons.append("Short-term weakness")

    if price_change_1h >= 300:
        risk += 20
        risk_reasons.append("Extreme 1h overextension")
    elif price_change_1h >= 200:
        risk += 15
        risk_reasons.append("Severe 1h overextension")
    elif price_change_1h >= 100:
        risk += 9
        risk_reasons.append("Strong 1h overextension")

    if price_change_24h >= 1000:
        risk += 20
        risk_reasons.append("Extreme 24h run-up")
    elif price_change_24h >= 500:
        risk += 15
        risk_reasons.append("Severe 24h run-up")
    elif price_change_24h >= 250:
        risk += 10
        risk_reasons.append("Large 24h run-up")
    elif price_change_24h >= 100:
        risk += 5
        risk_reasons.append("Elevated 24h run-up")

    if total_5m >= 20 and buy_ratio_5m < 0.40:
        risk += 10
        risk_reasons.append("Sell pressure")
    elif total_5m < 20 and buy_ratio_5m >= 0.70:
        risk += 3
        risk_reasons.append("Small buy-side sample")

    if age_hours > 0 and age_hours < 1:
        risk += 5
        risk_reasons.append("Extremely new token")
    elif age_hours > 0 and age_hours < 6:
        risk += 2
        risk_reasons.append("Very new token")

    risk += whale["risk"]

    for reason in whale["reasons"]:
        if "acceptable" not in reason.lower():
            risk_reasons.append(f"Whale: {reason}")

    if security_result["available"]:
        risk += security_result["risk"]

        for reason in security_result["reasons"]:
            if "passed" not in reason.lower():
                risk_reasons.append(f"Security: {reason}")
    else:
        risk += 15
        risk_reasons.append("Security data unavailable")

    risk = min(risk, 100)

    opportunity = 0
    opportunity_reasons = []

    if liquidity >= 100_000:
        opportunity += 20
        opportunity_reasons.append("Strong liquidity")
    elif liquidity >= 50_000:
        opportunity += 16
        opportunity_reasons.append("Good liquidity")
    elif liquidity >= MIN_LIQUIDITY:
        opportunity += 10
        opportunity_reasons.append("Acceptable liquidity")

    if volume >= 1_000_000:
        opportunity += 16
        opportunity_reasons.append("Exceptional volume")
    elif volume >= 100_000:
        opportunity += 14
        opportunity_reasons.append("Strong volume")
    elif volume >= MIN_VOLUME:
        opportunity += 9
        opportunity_reasons.append("Healthy volume")

    if liquidity > 0 and volume_5m > 0:
        volume_liquidity_ratio = volume_5m / liquidity

        if volume_liquidity_ratio >= 1:
            opportunity += 12
            opportunity_reasons.append("Strong recent volume")
        elif volume_liquidity_ratio >= 0.25:
            opportunity += 8
            opportunity_reasons.append("Good recent volume")
        elif volume_liquidity_ratio >= 0.05:
            opportunity += 4
            opportunity_reasons.append("Moderate recent volume")

    if 5 <= price_change_1h <= 50:
        opportunity += 12
        opportunity_reasons.append("Healthy 1h momentum")
    elif 0 < price_change_1h < 5:
        opportunity += 6
        opportunity_reasons.append("Positive 1h momentum")

    if 0 < price_change_5m <= 10:
        opportunity += 7
        opportunity_reasons.append("Controlled 5m momentum")
    elif price_change_5m > 10:
        opportunity += 3
        opportunity_reasons.append("Fast 5m momentum")

    if total_5m >= 100:
        opportunity += 8
        opportunity_reasons.append("High recent activity")
    elif total_5m >= 30:
        opportunity += 5
        opportunity_reasons.append("Good recent activity")
    elif total_5m >= 10:
        opportunity += 2
        opportunity_reasons.append("Usable recent activity")

    if 1 <= age_hours <= 48:
        opportunity += 8
        opportunity_reasons.append("Early-stage opportunity")

    if security_result["safe"]:
        opportunity += 6
        opportunity_reasons.append("Security checks passed")

    if whale["available"]:
        if whale["top_holder_percent"] < 15:
            opportunity += 5
            opportunity_reasons.append("Healthy top-holder distribution")

        if whale["top10_percent"] < 50:
            opportunity += 4
            opportunity_reasons.append("Healthy top-10 distribution")

    opportunity = min(opportunity, 100)

    entry_quality = 100
    entry_reasons = []

    if price_change_1h >= 300:
        entry_quality -= 35
        entry_reasons.append("Extreme 1h extension")
    elif price_change_1h >= 200:
        entry_quality -= 25
        entry_reasons.append("Severe 1h extension")
    elif price_change_1h >= 100:
        entry_quality -= 15
        entry_reasons.append("Strong 1h extension")
    elif price_change_1h >= 50:
        entry_quality -= 8
        entry_reasons.append("Elevated 1h extension")

    if price_change_24h >= 1000:
        entry_quality -= 30
        entry_reasons.append("Extreme 24h run-up")
    elif price_change_24h >= 500:
        entry_quality -= 22
        entry_reasons.append("Severe 24h run-up")
    elif price_change_24h >= 250:
        entry_quality -= 14
        entry_reasons.append("Large 24h run-up")
    elif price_change_24h >= 100:
        entry_quality -= 7
        entry_reasons.append("Elevated 24h run-up")

    if price_change_5m > 20:
        entry_quality -= 8
        entry_reasons.append("Fast short-term expansion")

    if liquidity > 0:
        volume_liquidity_ratio = volume_5m / liquidity

        if volume_liquidity_ratio < 0.01:
            entry_quality -= 12
            entry_reasons.append("Weak immediate liquidity flow")
        elif volume_liquidity_ratio < 0.05:
            entry_quality -= 5
            entry_reasons.append("Moderate immediate liquidity flow")

    if total_5m < 10:
        entry_quality -= 12
        entry_reasons.append("Small transaction sample")
    elif total_5m < 20:
        entry_quality -= 6
        entry_reasons.append("Limited transaction sample")

    if (
        total_5m >= 20
        and 0.55 <= buy_ratio_5m <= 0.70
        and price_change_5m > 0
        and price_change_1h < 100
    ):
        entry_quality += 6
        entry_reasons.append("Balanced positive momentum")

    if (
        price_change_5m < 0
        and price_change_1h > 0
        and price_change_1h < 100
    ):
        entry_quality += 5
        entry_reasons.append("Controlled pullback")

    entry_quality = max(0, min(entry_quality, 100))

    confidence = 100
    confidence_reasons = []

    if liquidity <= 0:
        confidence -= 20
        confidence_reasons.append("Liquidity data missing")

    if volume <= 0:
        confidence -= 15
        confidence_reasons.append("Volume data missing")

    if total_5m < 10:
        confidence -= 10
        confidence_reasons.append("Low transaction sample")

    if total_5m < 20:
        confidence -= 5
        confidence_reasons.append("Limited transaction sample")

    if not security_result["available"]:
        confidence -= 20
        confidence_reasons.append("Security data unavailable")

    if not whale["available"]:
        confidence -= 15
        confidence_reasons.append("Holder data unavailable")

    if age_hours <= 0:
        confidence -= 10
        confidence_reasons.append("Token age unknown")

    confidence = max(0, min(confidence, 100))

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

    grow_forecast_v4 = calculate_grow_forecast_v4(
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

    direction_signal = calculate_direction_signal(
        price_change_5m,
        price_change_1h,
        price_change_24h,
        buy_ratio_5m,
        buy_ratio_1h,
        volume,
        liquidity
    )

    critical_ok = (
        liquidity >= MIN_LIQUIDITY
        and volume >= MIN_VOLUME
        and security_result["available"]
        and security_result["safe"]
        and whale["available"]
        and whale["risk"] < 20
    )

    buy = (
        risk <= MAX_BUY_RISK
        and opportunity >= MIN_BUY_OPPORTUNITY
        and confidence >= MIN_BUY_CONFIDENCE
        and entry_quality >= 60
        and critical_ok
    )

    signal = "BUY" if buy else "RISK"

    krypt_score = (
        opportunity * 0.35
        + entry_quality * 0.30
        + (100 - min(risk, 100)) * 0.20
        + confidence * 0.15
    )

    if grow_forecast:
        try:
            forecast_saved_at = datetime.now(timezone.utc).isoformat()

            save_forecast_memory({
                "forecast_id": (
                    f"{pair.get('chainId', 'unknown')}_"
                    f"{pair.get('baseToken', {}).get('address', 'unknown')}_"
                    f"{forecast_saved_at}"
                ),
                "saved_at": forecast_saved_at,
                "evaluated": False,
                "chainId": pair.get("chainId"),
                "tokenAddress": (
                    pair.get("baseToken", {}).get("address")
                    if isinstance(pair.get("baseToken"), dict)
                    else None
                ),
                "symbol": (
                    pair.get("baseToken", {}).get("symbol")
                    if isinstance(pair.get("baseToken"), dict)
                    else None
                ),
                "price": safe_float(pair.get("priceUsd")),
                "market_cap": market_cap,
                "liquidity": liquidity,
                "volume": volume,
                "volume_5m": volume_5m,
                "price_change_5m": price_change_5m,
                "price_change_1h": price_change_1h,
                "price_change_24h": price_change_24h,
                "buy_ratio_5m": buy_ratio_5m,
                "buy_ratio_1h": buy_ratio_1h,
                "total_5m": total_5m,
                "total_1h": total_1h,
                "age_hours": age_hours,
                "entry_quality": entry_quality,
                "entry_reasons": entry_reasons,
                "risk": min(risk, 100),
                "opportunity": opportunity,
                "confidence": confidence,
                "krypt_score": round(krypt_score, 1),
                "signal": signal,
                "critical_ok": critical_ok,
                "grow_score": grow_score,
                "direction_signal": direction_signal,
                "direction_engine": "V4",
                "forecasts": grow_forecast,
                "forecasts_v4": grow_forecast_v4
            })
        except Exception:
            pass

    return {
        "risk": min(risk, 100),
        "opportunity": opportunity,
        "confidence": confidence,
        "entry_quality": entry_quality,
        "entry_reasons": entry_reasons,
        "market_cap": market_cap,
        "krypt_score": round(krypt_score, 1),
        "grow_score": grow_score,
        "grow_forecast": grow_forecast,
        "direction_signal": direction_signal,
        "signal": signal,
        "whale_risk": whale["risk"],
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
        "security_available": security_result["available"],
        "security_safe": security_result["safe"],
        "security": security_result,
        "whale": whale,
        "risk_reasons": risk_reasons,
        "opportunity_reasons": opportunity_reasons,
        "confidence_reasons": confidence_reasons
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
            invalid_profile_count += 1
            continue

        chain_key = str(chain).lower()

        if chain_key not in chain_stats:
            chain_stats[chain_key] = {
                "total": 0,
                "pairs": 0,
                "missing": 0
            }

        chain_stats[chain_key]["total"] += 1

        lookup_chain = "ethereum" if chain_key == "eth" else chain

        pairs = get_token_pairs(
            lookup_chain,
            address
        )

        pair = choose_best_pair(
            pairs
        )

        if not pair:
            chain_stats[chain_key]["missing"] += 1
            pair_missing_count += 1
            continue

        chain_stats[chain_key]["pairs"] += 1

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

        discovery_quality = calculate_discovery_quality(pair)
        base_token = pair.get("baseToken") or {}

        symbol = base_token.get("symbol") or "UNKNOWN"
        name = base_token.get("name") or "UNKNOWN"

        results.append({
            "symbol": symbol,
            "name": name,
            "chain": chain,
            "address": address,
            "pair": pair,
            "discovery_quality": discovery_quality,
            "analysis": analysis
        })

    # Remove duplicate token symbols.
    # Keep the strongest market-quality candidate for each symbol.
    unique_results = {}

    for item in results:
        symbol_key = str(
            item.get("symbol") or "UNKNOWN"
        ).strip().lower()

        if symbol_key not in unique_results:
            unique_results[symbol_key] = item
            continue

        current = unique_results[symbol_key]

        current_quality = current.get(
            "discovery_quality", 0
        )
        new_quality = item.get(
            "discovery_quality", 0
        )

        if new_quality > current_quality:
            unique_results[symbol_key] = item
        elif new_quality == current_quality:
            current_liquidity = safe_float(
                (current.get("pair") or {})
                .get("liquidity", {})
                .get("usd")
            )
            new_liquidity = safe_float(
                (item.get("pair") or {})
                .get("liquidity", {})
                .get("usd")
            )

            if new_liquidity > current_liquidity:
                unique_results[symbol_key] = item

    results = list(unique_results.values())

    results.sort(
        key=lambda x: (
            x["analysis"]["risk"] <= MAX_BUY_RISK,
            (
                0.35 * x.get("discovery_quality", 0)
                + 0.65 * x["analysis"]["krypt_score"]
            ),
            x["analysis"]["opportunity"],
            x["analysis"]["confidence"],
            x["analysis"]["krypt_score"]
        ),
        reverse=True
    )

    print(
        f"{GRAY}[RADAR] Pair missing      : {pair_missing_count}{RESET}"
    )
    print(
        f"{GRAY}[RADAR] Age filtered      : {age_filtered_count}{RESET}"
    )
    print(
        f"{GRAY}[RADAR] Invalid profiles  : {invalid_profile_count}{RESET}"
    )
    print(
        f"{GRAY}[RADAR] Actually analyzed : {analyzed_count}{RESET}"
    )

    return results


def calculate_discovery_quality(pair):
    """
    Discovery V3.1
    Rank discovery candidates by market quality.
    This is a ranking/context score, not a BUY signal.
    """

    if not isinstance(pair, dict):
        return 0

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

    txns = pair.get("txns") or {}
    txns_5m = txns.get("m5") or {}

    buys_5m = safe_int(txns_5m.get("buys"))
    sells_5m = safe_int(txns_5m.get("sells"))

    total_txns_5m = buys_5m + sells_5m

    buy_ratio_5m = (
        buys_5m / total_txns_5m
        if total_txns_5m > 0
        else 0
    )

    volume_liquidity_ratio = (
        volume / liquidity
        if liquidity > 0
        else 0
    )

    age_hours = 0

    try:
        created_at = pair.get("pairCreatedAt")

        if created_at:
            created_ms = float(created_at)

            if created_ms > 100000000000:
                created_ms /= 1000

            age_hours = max(
                0,
                (time.time() - created_ms) / 3600
            )

    except Exception:
        age_hours = 0

    score = 0

    # Liquidity quality /20
    if liquidity >= 500000:
        score += 20
    elif liquidity >= 250000:
        score += 18
    elif liquidity >= 100000:
        score += 15
    elif liquidity >= 50000:
        score += 11
    elif liquidity >= 20000:
        score += 6
    elif liquidity >= MIN_LIQUIDITY:
        score += 3

    # Volume quality /15
    if volume >= 5000000:
        score += 15
    elif volume >= 1000000:
        score += 12
    elif volume >= 500000:
        score += 9
    elif volume >= 100000:
        score += 6
    elif volume >= 50000:
        score += 3

    # 5m activity /15
    if volume_5m >= 100000:
        score += 15
    elif volume_5m >= 50000:
        score += 12
    elif volume_5m >= 10000:
        score += 9
    elif volume_5m >= 5000:
        score += 6
    elif volume_5m >= 1000:
        score += 3

    # Transactions + buy/sell balance /10
    if total_txns_5m >= 500:
        score += 7
    elif total_txns_5m >= 200:
        score += 5
    elif total_txns_5m >= 50:
        score += 3
    elif total_txns_5m >= 10:
        score += 1

    if total_txns_5m > 0:
        if buy_ratio_5m >= 0.65:
            score += 3
        elif buy_ratio_5m >= 0.55:
            score += 2
        elif buy_ratio_5m >= 0.45:
            score += 1
        elif buy_ratio_5m < 0.35:
            score -= 3

    # Momentum /15
    if 2 <= price_change_1h <= 20:
        score += 8
    elif 20 < price_change_1h <= 50:
        score += 7
    elif 50 < price_change_1h <= 100:
        score += 5
    elif price_change_1h > 100:
        score += 1
    elif price_change_1h < -30:
        score -= 5

    if -5 <= price_change_5m <= 8:
        score += 7
    elif 8 < price_change_5m <= 15:
        score += 5
    elif 15 < price_change_5m <= 25:
        score += 3
    elif 25 < price_change_5m <= 40:
        score += 1
    elif price_change_5m > 40:
        score -= 3
    elif price_change_5m < -15:
        score -= 4

    # Volume / liquidity health /10
    if 3 <= volume_liquidity_ratio <= 30:
        score += 10
    elif 1 <= volume_liquidity_ratio < 3:
        score += 6
    elif 30 < volume_liquidity_ratio <= 50:
        score += 8
    elif 50 < volume_liquidity_ratio <= 80:
        score += 5
    elif volume_liquidity_ratio > 80:
        score += 2

    # Freshness /10
    if 1 <= age_hours <= 24:
        score += 10
    elif 24 < age_hours <= 48:
        score += 8
    elif 48 < age_hours <= 168:
        score += 5
    elif age_hours < 1:
        score += 4
    elif age_hours > 720:
        score -= 10

    # Additional extreme-movement penalty
    if price_change_5m > 40 or price_change_1h > 150:
        score -= 3

    return max(0, min(round(score), 100))

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

    # Diversify discovery candidates across chains.
    # Keep the original discovery order inside each chain.
    chain_groups = {}

    for profile in profiles:
        chain = profile.get("chainId")

        if not chain:
            continue

        chain_key = str(chain).lower()

        if chain_key not in chain_groups:
            chain_groups[chain_key] = []

        chain_groups[chain_key].append(profile)

    balanced_profiles = []

    max_rounds = max(
        (len(group) for group in chain_groups.values()),
        default=0
    )

    for round_index in range(max_rounds):

        for chain_key in chain_groups:

            group = chain_groups[chain_key]

            if round_index < len(group):
                balanced_profiles.append(
                    group[round_index]
                )

    profiles = balanced_profiles

    print(
        f"{GRAY}[RADAR] Discovery candidates: "
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

    analyzed_count = 0
    pair_missing_count = 0
    age_filtered_count = 0
    invalid_profile_count = 0
    chain_stats = {}

    for profile in profiles:

        if analyzed_count >= 100:
            break

        chain = profile.get(
            "chainId"
        )

        address = profile.get(
            "tokenAddress"
        )

        if not chain or not address:
            invalid_profile_count += 1
            continue

        pairs = get_token_pairs(
            chain,
            address
        )

        pair = choose_best_pair(
            pairs
        )

        if not pair:
            pair_missing_count += 1
            continue

        discovery_quality = calculate_discovery_quality(
            pair
        )

        if str((pair.get("baseToken") or {}).get("symbol") or "").strip().lower() == "xsol":
            print(
                f"\\nDEBUG XSOL | CHAIN={chain} | "
                f"ADDRESS={address} | "
                f"DEX={pair.get('dexId')} | "
                f"LIQ={(pair.get('liquidity') or {}).get('usd')} | "
                f"VOL24={(pair.get('volume') or {}).get('h24')} | "
                f"DISCOVERY={discovery_quality}\\n"
            )

        # Deep Scan focuses on recent discovery candidates.
        # Older tokens remain available through Radar Memory / Positions.
        try:
            created_at = pair.get("pairCreatedAt")

            if created_at:
                created_ms = float(created_at)

                if created_ms > 100000000000:
                    created_ms /= 1000

                age_hours = max(
                    0,
                    (time.time() - created_ms) / 3600
                )

                if age_hours > 720:
                    age_filtered_count += 1
                    continue

        except Exception:
            pass

        analyzed_count += 1

        print(
            f"{GRAY}"
            f"[{analyzed_count:02d}/100] "
            f"Security + Whale scan... "
            f"Discovery: {discovery_quality}/100"
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

        if str(symbol).strip().lower() == "xsol":
            print(
                f"\\nDEBUG XSOL | "
                f"CHAIN={chain} | "
                f"ADDRESS={address} | "
                f"DEX={pair.get('dexId')} | "
                f"LIQ={(pair.get('liquidity') or {}).get('usd')} | "
                f"VOL24={(pair.get('volume') or {}).get('h24')} | "
                f"VOL5M={(pair.get('volume') or {}).get('m5')} | "
                f"DISCOVERY={discovery_quality} | "
                f"PAIR_QUALITY={calculate_pair_quality(pair)}\\n"
            )

        results.append({

            "symbol": symbol,

            "name": name,

            "chain": chain,

            "address": address,

            "pair": pair,
            "discovery_quality": discovery_quality,

            "analysis": analysis

        })

        publish_krypt_signal(
            results[-1]
        )

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

    print(
        f"{GRAY}[RADAR] Pair missing      : {pair_missing_count}{RESET}"
    )
    print(
        f"{GRAY}[RADAR] Age filtered      : {age_filtered_count}{RESET}"
    )
    print(
        f"{GRAY}[RADAR] Invalid profiles  : {invalid_profile_count}{RESET}"
    )
    print(
        f"{GRAY}[RADAR] Actually analyzed : {analyzed_count}{RESET}"
    )

    for chain_key, stats in chain_stats.items():
        print(
            f"{GRAY}[RADAR] {chain_key:<12} "
            f"TOTAL={stats['total']:<3} "
            f"PAIRS={stats['pairs']:<3} "
            f"MISSING={stats['missing']:<3}"
            f"{RESET}"
        )

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
    print(f'\\n[DEBUG SHOW_RESULTS] COUNT={len(results) if results else 0}')

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

            direction_signal = analysis.get("direction_signal") or {}
            direction = direction_signal.get("direction", "MIXED")
            direction_score = direction_signal.get("score", 0)
            direction_confidence = direction_signal.get("confidence", 0)

            direction_icon = (
                "🟢" if direction == "UP"
                else "🔴" if direction == "DOWN"
                else "🟡"
            )

            print(
                f"    Direction: {direction_icon} {direction}   "
                f"Score: {direction_score:+d}   "
                f"C: {direction_confidence}%"
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

            f"Discovery: "
            f"{item.get('discovery_quality', 0)}/100   "

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
        "Showing top 10 candidates by combined KRYPT + Discovery score."
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

def krypt_signal_evaluator_worker():
    while True:
        try:
            if os.path.exists(
                SIGNAL_HISTORY_FILE
            ):
                with SIGNAL_HISTORY_LOCK:
                    with open(
                        SIGNAL_HISTORY_FILE,
                        "r",
                        encoding="utf-8"
                    ) as f:
                        history = json.load(f)

                if isinstance(history, list):
                    changed = False

                    for index, record in enumerate(history):

                        if not isinstance(record, dict):
                            continue

                        if record.get(
                            "validation_status"
                        ) in (
                            "COMPLETE",
                            "INVALID_HISTORICAL",
                            "INCOMPLETE"
                        ):
                            continue

                        before = dict(record)

                        history[index] = (
                            evaluate_krypt_signal_record(
                                record
                            )
                        )

                        if history[index] != before:
                            changed = True

                    if changed:
                        with SIGNAL_HISTORY_LOCK:
                            tmp = (
                                SIGNAL_HISTORY_FILE
                                + ".tmp"
                            )

                            with open(
                                tmp,
                                "w",
                                encoding="utf-8"
                            ) as f:
                                json.dump(
                                    history,
                                    f,
                                    ensure_ascii=False,
                                    indent=2
                                )
                                f.flush()
                                os.fsync(f.fileno())

                            os.replace(
                                tmp,
                                SIGNAL_HISTORY_FILE
                            )

        except Exception:
            pass

        time.sleep(60)


def forecast_evaluator_worker():
    """
    Background V4 forecast evaluator.

    Checks only unfinished V4 horizons.
    The worker never evaluates multiple horizons
    from the same record in one API snapshot.
    """

    horizons = (
        "1H",
        "6H",
        "1D",
        "1W",
        "1M"
    )

    while True:

        try:
            if os.path.exists(
                FORECAST_MEMORY_FILE
            ):

                with FORECAST_MEMORY_LOCK:
                    with open(
                        FORECAST_MEMORY_FILE,
                        "r",
                        encoding="utf-8"
                    ) as f:
                        memory = json.load(f)

                if isinstance(memory, list):

                    changed = False

                    for horizon in horizons:

                        for index, record in enumerate(memory):

                            if not isinstance(record, dict):
                                continue

                            if record.get(
                                "direction_engine"
                            ) != "V4":
                                continue

                            if record.get(
                                f"evaluated_{horizon}"
                            ):
                                continue

                            before = dict(record)

                            memory[index] = (
                                evaluate_forecast_record(
                                    record,
                                    target_horizon=horizon
                                )
                            )

                            if memory[index] != before:
                                changed = True

                    if changed:
                        with FORECAST_MEMORY_LOCK:
                            write_forecast_memory(memory)

        except Exception:
            pass

        time.sleep(60)



def main():

    boot_animation()

    try:
        evaluator_thread = threading.Thread(
            target=forecast_evaluator_worker,
            daemon=True
        )

        evaluator_thread.start()

        signal_evaluator_thread = threading.Thread(
            target=krypt_signal_evaluator_worker,
            daemon=True
        )

        signal_evaluator_thread.start()

    except Exception:
        pass

    dashboard()


if __name__ == "__main__":

    main()
