import os
import random
import time

RESET = "\033[0m"

COLORS = [
    "\033[96m",
    "\033[94m",
    "\033[92m",
    "\033[93m",
    "\033[91m"
]


def clear():
    os.system("clear")


def dashboard():
    clear()

    color1 = random.choice(COLORS)
    color2 = random.choice(COLORS)

    print(color1 + "╔══════════════════════════════════════════════╗" + RESET)
    print(color1 + "║                                              ║" + RESET)
    print(color2 + "║              K R Y P T                       ║" + RESET)
    print(color1 + "║           C Y B E R  D A S H                ║" + RESET)
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


while True:

    dashboard()

    choice = input(color1 + "\nKRYPT://ROOT > " + RESET)

    if choice == "1":
        clear()
        print(random.choice(COLORS) + "\nCRYPTO RADAR" + RESET)
        input("\nPress ENTER...")

    elif choice == "2":
        clear()
        print(random.choice(COLORS) + "\nAI ASSISTANT" + RESET)
        input("\nPress ENTER...")

    elif choice == "3":
        clear()
        print(random.choice(COLORS) + "\nNOTES" + RESET)
        input("\nPress ENTER...")

    elif choice == "4":
        clear()
        print(random.choice(COLORS) + "\nSYSTEM" + RESET)
        input("\nPress ENTER...")

    elif choice == "00":
        clear()
        print("\033[91mKRYPT SYSTEM OFFLINE\033[0m")
        time.sleep(1)
        break

    else:
        clear()
        print("\033[91mINVALID COMMAND\033[0m")
        time.sleep(1)
