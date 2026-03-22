#!/usr/bin/env python
"""One-time LLM provider setup. Run from code/backend/:
    python scripts/setup_llm.py

Configures:
  - LLM_PROVIDER   (default: anthropic) — "anthropic" or "groq"
  - LLM_API_KEY    (required for real inference)
  - LLM_MODEL_ID   (optional — overrides per-provider default)

Provider API key sources:
  - Anthropic: https://console.anthropic.com/settings/keys
  - Groq:      https://console.groq.com/keys  (free tier available)
"""
import getpass
import pathlib


_PROVIDER_DEFAULTS: dict[str, str] = {
    "anthropic": "claude-3-5-haiku-latest",
    "groq": "llama-3.1-8b-instant",
}


def _upsert_env(env_path: pathlib.Path, key: str, value: str) -> None:
    """Set a key in .env, replacing an existing value if present."""
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [line for line in lines if not line.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    env_path = pathlib.Path(".env")
    print("\n=== LLM Provider Setup ===")
    print("Supported providers: anthropic (Claude), groq (Llama — free tier)\n")

    # ── Provider ────────────────────────────────────────────────────────
    print("1. Provider")
    print("   Options: anthropic | groq")
    provider = input("   Enter LLM_PROVIDER [anthropic]: ").strip().lower() or "anthropic"
    if provider not in ("anthropic", "groq"):
        print(f"   Unknown provider '{provider}'. Use 'anthropic' or 'groq'. Aborted.")
        return
    _upsert_env(env_path, "LLM_PROVIDER", provider)
    print(f"   ✓ LLM_PROVIDER={provider} written to {env_path}\n")

    # ── API Key ─────────────────────────────────────────────────────────
    print("2. API Key")
    if provider == "anthropic":
        print("   Get yours at: https://console.anthropic.com/settings/keys")
    else:
        print("   Get yours at: https://console.groq.com/keys (free tier available)")
    key = getpass.getpass("   Paste your API key (input is hidden): ").strip()
    if not key:
        print("   No key entered — running in mock mode (no real API calls).")
        print("   ✓ LLM_API_KEY left empty (mock mode)\n")
    else:
        _upsert_env(env_path, "LLM_API_KEY", key)
        print(f"   ✓ LLM_API_KEY written to {env_path}\n")

    # ── Model override (optional) ───────────────────────────────────────
    default_model = _PROVIDER_DEFAULTS[provider]
    print("3. Model ID (optional)")
    print(f"   Default for {provider}: {default_model}")
    model = input(f"   Enter LLM_MODEL_ID [leave blank for default '{default_model}']: ").strip()
    if model:
        _upsert_env(env_path, "LLM_MODEL_ID", model)
        print(f"   ✓ LLM_MODEL_ID={model} written to {env_path}\n")
    else:
        print(f"   ✓ Using default model: {default_model}\n")

    print("Setup complete.")
    print(f"Test with: cd code/backend && pytest tests/test_llm_client.py -v")


if __name__ == "__main__":
    main()
