from __future__ import annotations

import argparse
from pregnancy_copilot.data_init import initialize_data_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="./pregnancy-data")
    args = parser.parse_args()
    root = initialize_data_dir(args.target)
    print(f"Initialized pregnancy data directory: {root}")

if __name__ == "__main__":
    main()
