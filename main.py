from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

from runners.run_attack_campaign import run_campaign
from target_parser import main as target_parser_main


CONFIG_PATH = "configs/app.config.json"
DEFAULT_OUTPUT_ROOT = "results/app"


def config_exists() -> bool:
    return Path(CONFIG_PATH).exists()


def print_main_help() -> None:
    print("\nHelp")
    print("----")
    print("1  -> Build/update target config from curl")
    print("2  -> Run selected datasets from config")
    print("3  -> Exit")
    print("h  -> Show this help")
    print("")
    print("During a running campaign, you can type:")
    print("  p  -> pause")
    print("  r  -> resume")
    print("  q  -> stop cleanly after current case")
    print("")


def ask_max_requests(default: int = 100) -> int:
    raw = input(f"Enter max total requests per each dataset [{default}]: ").strip()
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


def ask_max_turns(default: int = 5) -> int:
    raw = input(f"Enter max turns per case [{default}]: ").strip()
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


def ask_output_root(default: str = DEFAULT_OUTPUT_ROOT) -> str:
    raw = input(f"Enter output directory [{default}]: ").strip()
    return raw or default


def run_selected_datasets() -> None:
    if not config_exists():
        print(f"[-] Config not found: {CONFIG_PATH}")
        print("[*] Please run option 1 first.")
        return

    max_total_requests = ask_max_requests(100)
    max_turns = ask_max_turns(5)
    output_root = ask_output_root(DEFAULT_OUTPUT_ROOT)

    print(f"\n[+] Using config      : {CONFIG_PATH}")
    print(f"[+] Output directory  : {output_root}")
    print(f"[+] Max turns/case    : {max_turns}")
    print(f"[+] Max total requests: {max_total_requests}")
    print("")

    run_campaign(
        config_path=CONFIG_PATH,
        output_root=output_root,
        max_turns=max_turns,
        max_total_requests=max_total_requests,
    )


def main() -> None:
    while True:
        print("\nChoose an option:")
        print("1. Build/update target config from curl")
        print("2. Run selected datasets from config")
        print("3. Exit")
        print("h. Help")

        choice = input("Enter choice [1/2/3/h]: ").strip().lower()

        if choice == "1":
            target_parser_main()

        elif choice == "2":
            run_selected_datasets()

        elif choice == "3":
            print("[+] Exiting")
            break

        elif choice == "h":
            print_main_help()

        else:
            print("[-] Invalid choice")
            print_main_help()


if __name__ == "__main__":
    main()