import os

os.system("clear")

while True:
    print("        KRYPT DASHBOARD")
    print()
    print("   [1] Crypto")
    print("   [2] AI")
    print("   [3] Notes")
    print("   [4] System")
    print()
    print("   [0] Exit")
    print()

    choice = input("   KRYPT > ")

    if choice == "1":
        print("\n   Crypto")
    elif choice == "2":
        print("\n   AI")
    elif choice == "3":
        print("\n   Notes")
    elif choice == "4":
        print("\n   System")
    elif choice == "0":
        os.system("clear")
        break
    else:
        print("\n   Invalid option")

    input("\n   Enter...")
    os.system("clear")
