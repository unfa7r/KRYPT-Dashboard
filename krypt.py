while True:
    print("\n=== KRYPT DASHBOARD ===")
    print("1 - Crypto")
    print("2 - AI")
    print("3 - Notes")
    print("4 - System")
    print("0 - Exit")

    choice = input("\nKRYPT > ")

    if choice == "1":
        print("Crypto")
    elif choice == "2":
        print("AI")
    elif choice == "3":
        print("Notes")
    elif choice == "4":
        print("System")
    elif choice == "0":
        break
    else:
        print("Invalid option.")
