#!/usr/bin/env python
"""One-time OZ setup. Run from code/backend/:
    python scripts/setup_oz.py

Configures:
  - OZ_API_KEY          (required) — your Warp personal API key
  - OZ_ENVIRONMENT_ID   (required for cloud runs) — UID of the cloud environment
  - OZ_SKILL_SPEC       (recommended) — repo skill spec for dashboard-assistant
"""
import getpass
import pathlib


def _upsert_env(env_path: pathlib.Path, key: str, value: str) -> None:
    """Set a key in .env, replacing if it already exists."""
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [line for line in lines if not line.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    env_path = pathlib.Path(".env")
    print("\n=== OZ (Warp Cloud Agent) Setup ===")
    print("Docs: https://docs.warp.dev/reference/api-and-sdk")
    print("IMPORTANT: Each agent run is credit-billed.\n")

    # ── API Key ────────────────────────────────────────────────────────
    print("1. API Key")
    print("   Get yours at: https://app.warp.dev/settings (Personal API Keys)")
    key = getpass.getpass("   Paste your OZ API key (input is hidden): ").strip()
    if not key:
        print("   No key entered. Aborted.")
        return
    _upsert_env(env_path, "OZ_API_KEY", key)
    print(f"   ✓ OZ_API_KEY written to {env_path}\n")

    # ── Environment ID ─────────────────────────────────────────────────
    print("2. Environment ID")
    print("   Cloud agent runs need an Environment (Docker image + GitHub repos).")
    print("   Create one at: https://app.warp.dev → Environments")
    env_id = input("   Paste your Environment UID (or press Enter to skip): ").strip()
    if env_id:
        _upsert_env(env_path, "OZ_ENVIRONMENT_ID", env_id)
        print(f"   ✓ OZ_ENVIRONMENT_ID written to {env_path}\n")
    else:
        print("   ⚠ Skipped — set OZ_ENVIRONMENT_ID later before running cloud agents.\n")

    # ── Skill Spec ─────────────────────────────────────────────────────
    print("3. Skill Spec")
    print("   Tells Oz to use .agents/skills/dashboard-assistant/SKILL.md as instructions.")
    print('   Format: "owner/repo:dashboard-assistant"')
    print('   Example: "emanchez/my-repo:dashboard-assistant"')
    skill = input("   Paste your skill spec (or press Enter to skip): ").strip()
    if skill:
        _upsert_env(env_path, "OZ_SKILL_SPEC", skill)
        print(f"   ✓ OZ_SKILL_SPEC written to {env_path}\n")
    else:
        print("   ⚠ Skipped — prompts will be sent without skill instructions.\n")

    # ── Summary ────────────────────────────────────────────────────────
    print("✓ .env is in .gitignore — secrets will NOT be committed.")
    print("\nCost tips:")
    print("  - Default model is claude-haiku-4 (cheapest capable model)")
    print("  - Rate limits: 3 synthesis/week, 5 suggestions/day, 3 co-plans/day")
    print("  - Set AI_ENABLED=false in .env to disable all AI endpoints")
    print("\nDocs:")
    print("  - API reference: https://docs.warp.dev/reference/api-and-sdk/agent")
    print("  - Skills guide:  https://docs.warp.dev/agent-platform/capabilities/skills")
    print("  - Python SDK:    https://github.com/warpdotdev/oz-sdk-python\n")


if __name__ == "__main__":
    main()
