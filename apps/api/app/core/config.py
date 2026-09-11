import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def load_project_environment() -> None:
    """Load Liflow's root .env without replacing real environment variables."""

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)


class ConfigurationError(ValueError):
    """Raised when the configured extraction provider cannot be initialized."""


@dataclass(frozen=True)
class Settings:
    extraction_provider: str
    openai_api_key: str | None
    openai_model: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        load_project_environment()
        provider = os.getenv("EXTRACTION_PROVIDER", "demo").casefold().strip()
        if provider not in {"demo", "openai"}:
            raise ConfigurationError("EXTRACTION_PROVIDER must be 'demo' or 'openai'.")

        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL")
        if provider == "openai" and not api_key:
            raise ConfigurationError("OPENAI_API_KEY is required for the OpenAI provider.")
        if provider == "openai" and not model:
            raise ConfigurationError("OPENAI_MODEL is required for the OpenAI provider.")

        return cls(provider, api_key, model)
