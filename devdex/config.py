from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


CONFIG_DIR = Path.home() / ".devdex"
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDERS = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_var": "NVIDIA_API_KEY",
        "models": {
            "devstral": "mistralai/devstral-2-123b-instruct-2512",
            "ministral": "mistralai/ministral-14b-instruct-2512",
            "mistral_large": "mistralai/mistral-large-3-675b-instruct-2512",
        },
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "env_var": "MISTRAL_API_KEY",
        "models": {
            "devstral": "devstral-small-latest",
            "ministral": "ministral-8b-latest",
            "mistral_large": "mistral-large-latest",
        },
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_var": "OPENAI_API_KEY",
        "models": {
            "devstral": "gpt-4o-mini",
            "ministral": "gpt-4o-mini",
            "mistral_large": "gpt-4o",
        },
    },
}

DEFAULT_PROVIDER = "nvidia"


def get_provider_config(provider: str | None = None) -> dict:
    name = provider or os.environ.get("DEVDEX_PROVIDER", DEFAULT_PROVIDER)
    if name in PROVIDERS:
        return PROVIDERS[name]
    return {
        "base_url": os.environ.get("DEVDEX_BASE_URL", PROVIDERS[DEFAULT_PROVIDER]["base_url"]),
        "env_var": "DEVDEX_API_KEY",
        "models": PROVIDERS[DEFAULT_PROVIDER]["models"],
    }


NVIDIA_BASE_URL = PROVIDERS["nvidia"]["base_url"]
MODELS = PROVIDERS["nvidia"]["models"]


class DevDexConfig(BaseModel):

    api_key: str = ""
    base_url: str = ""
    provider: str = ""
    wandb_api_key: str = ""

    supabase_url: str = ""
    supabase_key: str = ""
    mistral_embed_api_key: str = ""
    finetuned_model_id: str = ""

    telemetry_enabled: bool = True
    telemetry_url: str = "https://jskgxjarandblbkpssso.supabase.co/functions/v1/feedback-ingest"

    nvidia_api_key: str = ""

    @classmethod
    def load(cls) -> DevDexConfig:
        config = cls()

        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                config = cls.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                pass

        provider_name = config.provider or os.environ.get("DEVDEX_PROVIDER", DEFAULT_PROVIDER)
        provider_cfg = get_provider_config(provider_name)
        config.provider = provider_name

        if not config.base_url:
            config.base_url = os.environ.get("DEVDEX_BASE_URL", provider_cfg["base_url"])

        if not config.api_key:
            config.api_key = (
                os.environ.get(provider_cfg["env_var"], "")
                or os.environ.get("DEVDEX_API_KEY", "")
                or os.environ.get("NVIDIA_API_KEY", "")
            )

        if not config.api_key and config.nvidia_api_key:
            config.api_key = config.nvidia_api_key

        if not config.wandb_api_key:
            config.wandb_api_key = os.environ.get("WANDB_API_KEY", "")

        if not config.supabase_url:
            config.supabase_url = os.environ.get("DEVDEX_SUPABASE_URL", "")
        if not config.supabase_key:
            config.supabase_key = os.environ.get("DEVDEX_SUPABASE_KEY", "")
        if not config.mistral_embed_api_key:
            config.mistral_embed_api_key = (
                os.environ.get("MISTRAL_API_KEY", "")
                or config.api_key
            )

        telemetry_env = os.environ.get("DEVDEX_TELEMETRY", "").lower()
        if telemetry_env in ("false", "0", "no", "off"):
            config.telemetry_enabled = False
        override_url = os.environ.get("DEVDEX_TELEMETRY_URL", "")
        if override_url:
            config.telemetry_url = override_url

        return config

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(self.model_dump_json(indent=2))

    @property
    def models(self) -> dict[str, str]:
        provider_cfg = get_provider_config(self.provider)
        return provider_cfg["models"]

    def ensure_api_key(self) -> None:
        if not self.api_key:
            provider_cfg = get_provider_config(self.provider)
            print(
                f"Error: API key not found.\n"
                f"Set it via: export {provider_cfg['env_var']}=your-key\n"
                f"Or set DEVDEX_API_KEY for any provider.\n"
                f"Or run: devdex config set api_key your-key",
                file=sys.stderr,
            )
            raise SystemExit(1)
