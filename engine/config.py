"""Runtime settings, read from environment / .env."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name, default=None):
    v = os.getenv(name)
    return v if v not in (None, "") else default


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(ROOT / "data"))))
    provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "openai" if _env("OPENAI_API_KEY") else "mock"))
    openai_key: str | None = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    anthropic_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    model_fast: str = field(default_factory=lambda: _env("MODEL_FAST", "gpt-5-mini"))
    model_standard: str = field(default_factory=lambda: _env("MODEL_STANDARD", "gpt-5"))
    model_premium: str = field(default_factory=lambda: _env("MODEL_PREMIUM", "gpt-5"))
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "text-embedding-3-small"))
    transcribe_model: str = field(default_factory=lambda: _env("TRANSCRIBE_MODEL", "gpt-4o-transcribe"))
    tts_model: str = field(default_factory=lambda: _env("TTS_MODEL", "gpt-4o-mini-tts"))
    image_model: str = field(default_factory=lambda: _env("IMAGE_MODEL", "gpt-image-1-mini"))
    reasoning_effort: str | None = field(default_factory=lambda: _env("REASONING_EFFORT", "low"))
    max_parallel: int = field(default_factory=lambda: int(_env("MAX_PARALLEL", "6")))
    # cost guard: sections processed per course before asking the teacher to narrow scope
    max_sections: int = field(default_factory=lambda: int(_env("MAX_SECTIONS", "60")))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "engine.db"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()

# Approximate list prices, USD per million tokens (input, output). Used only for pre-build estimates;
# check the provider's pricing page — override by editing here.
PRICES = {
    "gpt-5-nano": (0.05, 0.40), "gpt-5-mini": (0.25, 2.00), "gpt-5": (1.25, 10.00),
    "gpt-5.6-luna": (0.20, 1.20), "gpt-5.6-terra": (2.00, 12.00), "gpt-5.6-sol": (4.00, 20.00),
    "gpt-6-astra": (10.00, 50.00), "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00), "claude-sonnet-5": (2.00, 10.00), "claude-opus-5-5": (5.00, 25.00),
    "text-embedding-3-small": (0.02, 0.0),
}
for d in (settings.data_dir, settings.media_dir, settings.upload_dir):
    d.mkdir(parents=True, exist_ok=True)
