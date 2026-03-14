#!/usr/bin/env python
"""One-time OZ API key setup. Run from code/backend/:
    python scripts/setup_oz.py
"""
import getpass
import pathlib


def main() -> None:
    env_path = pathlib.Path(".env")
    print("\n=== OZ API Key Setup ===")
    print("Get your key at: https://app.warp.dev/settings (Personal API Keys)")
    print("IMPORTANT: This is credit-billed. Each synthesis run costs credits.")
    print("Recommended: use a lightweight model (see OZ_MODEL_ID below).\n")
    key = getpass.getpass("Paste your OZ API key (input is hidden): ").strip()
    if not key:
        print("No key entered. Aborted.")
        return
    # Read existing .env, update or append OZ_API_KEY
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [line for line in lines if not line.startswith("OZ_API_KEY=")]
    lines.append(f"OZ_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n")
    print(f"\n✓ OZ_API_KEY written to {env_path}")
    print("✓ .env is in .gitignore — key will NOT be committed.")
    print("\nCost tips:")
    print("  - Default model is claude-haiku-4 (cheapest capable model)")
    print("  - Rate limits: 3 synthesis/week, 5 suggestions/day, 3 co-plans/day")
    print("  - Set AI_ENABLED=false in .env to disable all AI endpoints\n")


if __name__ == "__main__":
    main()
