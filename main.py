from __future__ import annotations

from pathlib import Path

from runners.run_attack_campaign import run_campaign
from target_parser import main as target_parser_main


CONFIG_PATH = "configs/app.config.json"
DATASETS_ROOT = "datasets"
TARGET_NAME = "app"


def config_exists() -> bool:
    return Path(CONFIG_PATH).exists()


def print_main_help() -> None:
    print("\nHelp")
    print("----")
    print("1  -> Build/update target config from curl")
    print("2  -> Run prompt injection")
    print("3  -> Run rule disclosure")
    print("4  -> Run both categories")
    print("5  -> Exit")
    print("h  -> Show this help")
    print("")
    print("During a running campaign, you can type:")
    print("  p  -> pause")
    print("  r  -> resume")
    print("  q  -> stop cleanly after current case")
    print("")


def ask_max_requests(default: int = 100) -> int:
    raw = input(f"Enter max total requests [{default}]: ").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        print(f"[-] Invalid value. Using default: {default}")
        return default


def run_prompt_injection() -> None:
    max_total_requests = ask_max_requests(100)
    run_campaign(
        config_path=CONFIG_PATH,
        datasets_root=DATASETS_ROOT,
        target_name=TARGET_NAME,
        category="prompt_injection",
        output_root="results",
        max_turns=5,
        max_total_requests=max_total_requests,
    )


def run_rule_disclosure() -> None:
    max_total_requests = ask_max_requests(100)
    run_campaign(
        config_path=CONFIG_PATH,
        datasets_root=DATASETS_ROOT,
        target_name=TARGET_NAME,
        category="rule_disclosure",
        output_root="results",
        max_turns=5,
        max_total_requests=max_total_requests,
    )


def run_both() -> None:
    max_total_requests = ask_max_requests(100)

    print("\n[+] Running prompt injection\n")
    run_campaign(
        config_path=CONFIG_PATH,
        datasets_root=DATASETS_ROOT,
        target_name=TARGET_NAME,
        category="prompt_injection",
        output_root="results",
        max_turns=5,
        max_total_requests=max_total_requests,
    )

    print("\n[+] Running rule disclosure\n")
    run_campaign(
        config_path=CONFIG_PATH,
        datasets_root=DATASETS_ROOT,
        target_name=TARGET_NAME,
        category="rule_disclosure",
        output_root="results",
        max_turns=5,
        max_total_requests=max_total_requests,
    )


def main() -> None:
    while True:
        print("\nChoose an option:")
        print("1. Build/update target config from curl")
        print("2. Run prompt injection")
        print("3. Run rule disclosure")
        print("4. Run both")
        print("5. Exit")
        print("h. Help")

        choice = input("Enter choice [1/2/3/4/5/h]: ").strip().lower()

        if choice == "1":
            target_parser_main()

        elif choice == "2":
            if not config_exists():
                print(f"[-] Config not found: {CONFIG_PATH}")
                print("[*] Please run option 1 first.")
                continue
            run_prompt_injection()

        elif choice == "3":
            if not config_exists():
                print(f"[-] Config not found: {CONFIG_PATH}")
                print("[*] Please run option 1 first.")
                continue
            run_rule_disclosure()

        elif choice == "4":
            if not config_exists():
                print(f"[-] Config not found: {CONFIG_PATH}")
                print("[*] Please run option 1 first.")
                continue
            run_both()

        elif choice == "5":
            print("[+] Exiting")
            break

        elif choice == "h":
            print_main_help()

        else:
            print("[-] Invalid choice")
            print_main_help()


if __name__ == "__main__":
    main()