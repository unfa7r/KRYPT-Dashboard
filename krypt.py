import os
import random
import time
import sys

RESET = "\033[0m"

CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"

COLORS = [CYAN, BLUE, GREEN, YELLOW, RED]


def clear():
    os.system("clear")


def type_text(text, color=CYAN, speed=0.02):
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
            "\r" + CYAN +
            "KRYPT CORE [" + bar + f"] {percent}%" +
            RESET
        )

        sys.stdout.flush()
        time.sleep(0.04)

    print()


def scan_animation():
    for i in range(4):
        clear()

        print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(WHITE + "║              K R Y P T                       ║" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)

        print()
        print(GREEN + "SYSTEM SCAN" + RESET)

        line = " " * (i * 8) + "━━━━━━━━━━━━━━"
        print(CYAN + line + RESET)

        time.sleep(0.12)


def boot_animation():
    clear()

    letters = ["K", "KR", "KRY", "KRYP", "KRYPT"]

    for text in letters:
        clear()

        print("\n\n")
        print(CYAN + "╔══════════════════════════════════════════════╗" + RESET)
        print(CYAN + "║                                              ║" + RESET)
        print(
            WHITE +
            "║              " +
            text.center(14) +
            "              ║" +
            RESET
        )
        print(CYAN + "║                                              ║" + RESET)
        print(CYAN + "╚══════════════════════════════════════════════╝" + RESET)

        time.sleep(0.15)

    time.sleep(0.4)

    scan_animation()

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
    type_text(">> NETWORK INTERFACE ...... CONNECTED", BLUE)
    type_text(">> CRYPTO ENGINE .......... READY", YELLOW)

    print()

    progress_bar()

    print()

    type_text(">> ACCESS GRANTED", GREEN, 0.04)
    type_text(">> KRYPT DASHBOARD ONLINE", WHITE, 0.04)

    time.sleep(1)


def dashboard():
    clear()

    color1 = random.choice(COLORS)
    color2 = random.choice(COLORS)

    print(color1 + "╔══════════════════════════════════════════════╗" + RESET)
    print(color1 + "║                                              ║" + RESET)
    print(color2 + "║              K R Y P T                       ║" + RESET)
    print(color1 + "║          D A S H B O A R D                  ║" + RESET)
    print(color1 + "║                                              ║" + RESET)
    print(color1 + "╠══════════════════════════════════════════════╣" + RESET)
    print(color2 + "║  SYSTEM      ONLINE                          ║" + RESET)
    print(color2 + "║  SECURITY    ACTIVE                          ║" + RESET)
    print(color2 + "║  TERMINAL    CONNECTED                       ║" + RESET)
    print(color1 + "╠══════════════════════════════════════════════╣" + RESET)
    print(color1 + "║                                              ║" + RESET)
    print(color2 + "║  [01]  CRYPTO RADAR                          ║" + RESET)
    print(color2 + "║  [02]  AI ASSISTANT                          ║" + RESET)
    print(color2 + "║  [03]  NOTES                                 ║" + RESET)
    print(color2 + "║  [04]  SYSTEM                                ║" + RESET)
    print(color1 + "║                                              ║" + RESET)
    print(color1 + "║  [00]  EXIT                                  ║" + RESET)
    print(color1 + "║                                              ║" + RESET)
    print(color1 + "╚══════════════════════════════════════════════╝" + RESET)

    return color1


boot_animation()

while True:

    color1 = dashboard()

    choice = input(color1 + "\nKRYPT://ROOT > " + RESET)

    if choice == "1":
        clear()
        print(CYAN + "\n╔════════════════════════════════════╗" + RESET)
        print(CYAN + "║          CRYPTO RADAR             ║" + RESET)
        print(CYAN + "╚════════════════════════════════════╝" + RESET)
        input("\nPress ENTER...")

    elif choice == "2":
        clear()
        print(BLUE + "\n╔════════════════════════════════════╗" + RESET)
        print(BLUE + "║          AI ASSISTANT             ║" + RESET)
        print(BLUE + "╚════════════════════════════════════╝" + RESET)
        input("\nPress ENTER...")

    elif choice == "3":
        clear()
        print(YELLOW + "\n╔════════════════════════════════════╗" + RESET)
        print(YELLOW + "║              NOTES                 ║" + RESET)
        print(YELLOW + "╚════════════════════════════════════╝" + RESET)
        input("\nPress ENTER...")

    elif choice == "4":
        clear()
        print(GREEN + "\n╔════════════════════════════════════╗" + RESET)
        print(GREEN + "║             SYSTEM                ║" + RESET)
        print(GREEN + "╚════════════════════════════════════╝" + RESET)
        input("\nPress ENTER...")

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
