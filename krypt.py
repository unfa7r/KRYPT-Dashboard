import os
import time
import sys

# ============================================================
# KRYPT DASHBOARD
# Crypto Radar Core
# ============================================================

RESET = "\033[0m"

CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"

# BUY için sıkı kriterler
MAX_BUY_RISK = 20
MIN_BUY_OPPORTUNITY = 75
MIN_BUY_CONFIDENCE = 75

# ============================================================
# TERMINAL
# ============================================================

def clear():
    os.system("clear")


def type_text(text, color=CYAN, speed=0.015):
    for char in text:
        sys.stdout.write(color + char + RESET)
        sys.stdout.flush()
        time.sleep(speed)
    print()


def progress_bar():
    for i in range(31):
        bar = "█" * i + "░" * (30 - i)
        percent = int((i / 30) * 100)

        sys.stdout.write(
            "\r"
            + CYAN
            + "KRYPT CORE ["
            + bar
            + f"] {percent}%"
            + RESET
        )

        sys.stdout.flush()
        time.sleep(0.025)

    print()


# ============================================================
# BOOT ANIMATION
# ============================================================

def boot_animation():
    clear()

    letters = [
        "K",
        "KR",
        "KRY",
        "KRYP",
        "KRYPT"
    ]

    for text in letters:
        clear()
        print("\n\n")
        print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(
            WHITE
            + "║              "
            + text.center(14)
            + "              ║"
            + RESET
        )
        print(CYAN + "║                                              ║" + RESET)
        print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)
        time.sleep(0.12)

    clear()

    print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
    print(CYAN + "║                                              ║" + RESET)
    print(WHITE + "║              K R Y P T                       ║" + RESET)
    print(CYAN + "║          D A S H B O A R D                  ║" + RESET)
    print(CYAN + "║                                              ║" + RESET)
    print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)

    print()

    type_text(">> INITIALIZING KRYPT CORE...", CYAN)
    type_text(">> SECURITY MODULE ........ ONLINE", GREEN)
    type_text(">> MARKET ENGINE .......... READY", BLUE)
    type_text(">> RISK ENGINE ............ READY", YELLOW)

    print()

    progress_bar()

    print()

    type_text(">> ACCESS GRANTED", GREEN)
    type_text(">> KRYPT DASHBOARD ONLINE", WHITE)

    time.sleep(0.8)


# ============================================================
# ANALYSIS ENGINE
# ============================================================

def calculate_signal(risk, opportunity, confidence):
    if (
        risk <= MAX_BUY_RISK
        and opportunity >= MIN_BUY_OPPORTUNITY
        and confidence >= MIN_BUY_CONFIDENCE
    ):
        return "BUY", GREEN

    return "RISK", RED


def show_analysis_result(
    coin,
    risk,
    opportunity,
    confidence
):
    signal, signal_color = calculate_signal(
        risk,
        opportunity,
        confidence
    )

    clear()

    print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
    print(WHITE + "║              KRYPT ANALYSIS                 ║" + RESET)
    print(CYAN + "╠══════════════════════════════════════════════╣" + RESET)
    print(f"║  COIN          : {coin:<27}║")
    print(f"║  RISK          : {risk:>3}%                         ║")
    print(f"║  OPPORTUNITY   : {opportunity:>3}/100                      ║")
    print(f"║  CONFIDENCE    : {confidence:>3}%                         ║")
    print(CYAN + "╠══════════════════════════════════════════════╣" + RESET)
    print(signal_color + f"║  SIGNAL        : {signal:<27}║" + RESET)
    print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)

    print()

    if signal == "BUY":
        print(GREEN + "LOW RISK + HIGH OPPORTUNITY" + RESET)
    else:
        print(RED + "RISK TOO HIGH OR CONDITIONS INSUFFICIENT" + RESET)

    input("\nPress ENTER...")


# ============================================================
# CRYPTO RADAR
# ============================================================

def crypto_radar():
    while True:
        clear()

        print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
        print(WHITE + "║              CRYPTO RADAR                   ║" + RESET)
        print(CYAN + "╠══════════════════════════════════════════════╣" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(WHITE + "║  [01] MEMECOIN RADAR                        ║" + RESET)
        print(WHITE + "║  [02] NEW COIN HUNTER                       ║" + RESET)
        print(WHITE + "║  [03] LOW RISK TOP PICKS                    ║" + RESET)
        print(WHITE + "║  [04] MARKET OVERVIEW                        ║" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(CYAN + "║  [00] BACK                                   ║" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)

        choice = input(CYAN + "\nKRYPT://RADAR > " + RESET)

        if choice == "1":
            clear()
            type_text(">> MEMECOIN RADAR", CYAN)
            print()
            print(YELLOW + "REAL MARKET DATA MODULE: WAITING" + RESET)
            print()
            print(WHITE + "The radar will scan:" + RESET)
            print("• Liquidity")
            print("• Volume")
            print("• Momentum")
            print("• Holder concentration")
            print("• Contract security")
            print("• Volatility")
            print("• Market conditions")
            input("\nPress ENTER...")

        elif choice == "2":
            clear()
            type_text(">> NEW COIN HUNTER", BLUE)
            print()
            print(WHITE + "New token analysis will check:" + RESET)
            print("• Token age")
            print("• Liquidity")
            print("• Volume")
            print("• Holder growth")
            print("• Whale concentration")
            print("• Contract security")
            print("• Momentum")
            input("\nPress ENTER...")

        elif choice == "3":
            clear()
            type_text(">> LOW RISK TOP PICKS", GREEN)
            print()
            print(WHITE + "BUY requires:" + RESET)
            print(f"Risk <= {MAX_BUY_RISK}%")
            print(f"Opportunity >= {MIN_BUY_OPPORTUNITY}/100")
            print(f"Confidence >= {MIN_BUY_CONFIDENCE}%")
            print()
            print(YELLOW + "No coin is considered risk-free." + RESET)
            input("\nPress ENTER...")

        elif choice == "4":
            clear()
            type_text(">> MARKET OVERVIEW", CYAN)
            print()
            print(YELLOW + "LIVE MARKET DATA MODULE: WAITING" + RESET)
            input("\nPress ENTER...")

        elif choice == "00":
            break


# ============================================================
# NOTES
# ============================================================

def notes():
    clear()

    print(YELLOW + "╔══════════════════════════════════════════════╗" + RESET)
    print(YELLOW + "║                  NOTES                       ║" + RESET)
    print(YELLOW + "╚══════════════════════════════════════════════╝" + RESET)

    print()
    print("Notes module coming soon.")

    input("\nPress ENTER...")


# ============================================================
# SYSTEM
# ============================================================

def system_info():
    clear()

    print(GREEN + "╔══════════════════════════════════════════════╗" + RESET)
    print(GREEN + "║                  SYSTEM                      ║" + RESET)
    print(GREEN + "╚══════════════════════════════════════════════╝" + RESET)

    print()
    print("KRYPT CORE      : ONLINE")
    print("RISK ENGINE     : ACTIVE")
    print("MARKET ENGINE   : READY")
    print("SECURITY        : ACTIVE")
    print("AI ASSISTANT    : REMOVED")

    input("\nPress ENTER...")


# ============================================================
# MAIN DASHBOARD
# ============================================================

def dashboard():
    clear()

    print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
    print(CYAN + "║                                              ║" + RESET)
    print(WHITE + "║              K R Y P T                       ║" + RESET)
    print(CYAN + "║          D A S H B O A R D                  ║" + RESET)
    print(CYAN + "║                                              ║" + RESET)
    print(CYAN + "╠══════════════════════════════════════════════╣" + RESET)
    print(GREEN + "║  SYSTEM      ONLINE                          ║" + RESET)
    print(GREEN + "║  SECURITY    ACTIVE                          ║" + RESET)
    print(BLUE + "║  MARKET      READY                           ║" + RESET)
    print(CYAN + "╠══════════════════════════════════════════════╣" + RESET)
    print(WHITE + "║                                              ║" + RESET)
    print(WHITE + "║  [01]  CRYPTO RADAR                          ║" + RESET)
    print(WHITE + "║  [02]  NOTES                                 ║" + RESET)
    print(WHITE + "║  [03]  SYSTEM                                ║" + RESET)
    print(WHITE + "║                                              ║" + RESET)
    print(RED + "║  [00]  EXIT                                  ║" + RESET)
    print(CYAN + "║                                              ║" + RESET)
    print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)


# ============================================================
# START
# ============================================================

boot_animation()

while True:
    dashboard()

    choice = input(CYAN + "\nKRYPT://ROOT > " + RESET)

    if choice == "1":
        crypto_radar()

    elif choice == "2":
        notes()

    elif choice == "3":
        system_info()

    elif choice == "00":
        clear()
        type_text(">> TERMINATING KRYPT CORE...", RED)
        time.sleep(0.5)
        print(RED + "\nKRYPT SYSTEM OFFLINE" + RESET)
        time.sleep(1)
        break

    else:
        clear()
        type_text(">> INVALID COMMAND", RED)
        time.sleep(0.8)
