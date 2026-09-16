"""Safe, explicit DSPy configuration for optional discovery calls."""

import os
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

import dspy
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from game_accountability.ai.errors import AIConfigurationError


class DSPySettings(BaseModel):
    """Runtime settings loaded without persisting or logging credentials."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str | None = Field(default=None, min_length=1)
    api_key: SecretStr | None = None
    api_base: str | None = None
    allow_remote: bool = False
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1200, ge=1, le=16_384)

    @property
    def is_local(self) -> bool:
        """Return whether the configured provider is clearly local."""

        if self.api_base:
            hostname = (urlparse(self.api_base).hostname or "").lower()
            if hostname in {"127.0.0.1", "localhost", "::1"}:
                return True
        model = (self.model or "").lower()
        return model.startswith(("ollama/", "ollama_chat/", "local/", "lm_studio/"))


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise AIConfigurationError(f"invalid boolean value: {value!r}")


def load_dspy_settings(
    env_file: str | Path | None = ".env",
    *,
    environ: Mapping[str, str] | None = None,
) -> DSPySettings:
    """Load optional `.env` values, overridden by the process environment."""

    values: dict[str, str] = {}
    if env_file is not None:
        values.update(
            {key: value for key, value in dotenv_values(env_file).items() if value is not None}
        )
    values.update(dict(os.environ if environ is None else environ))

    api_key = values.get("GAME_ACCOUNTABILITY_AI_API_KEY") or values.get("OPENAI_API_KEY")

    return DSPySettings(
        model=values.get("GAME_ACCOUNTABILITY_AI_MODEL") or None,
        api_key=SecretStr(api_key) if api_key else None,
        api_base=values.get("GAME_ACCOUNTABILITY_AI_BASE_URL") or None,
        allow_remote=_parse_bool(values.get("GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE")),
        temperature=float(values.get("GAME_ACCOUNTABILITY_AI_TEMPERATURE", "0.0")),
        max_tokens=int(values.get("GAME_ACCOUNTABILITY_AI_MAX_TOKENS", "1200")),
    )


def configure_dspy(settings: DSPySettings) -> dspy.LM:
    """Configure DSPy once at application startup and return the active LM.

    Remote calls require an explicit opt-in. DSPy's persistent LM cache and
    history are disabled so structured gameplay observations are not retained
    outside the application's provenance-aware observation store.
    """

    if not settings.model:
        raise AIConfigurationError("GAME_ACCOUNTABILITY_AI_MODEL is required")
    if not settings.is_local and not settings.allow_remote:
        raise AIConfigurationError(
            "remote AI is disabled; set GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE=true explicitly"
        )

    lm_options: dict[str, object] = {
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "cache": False,
    }
    if settings.api_key:
        lm_options["api_key"] = settings.api_key.get_secret_value()
    if settings.api_base:
        lm_options["api_base"] = settings.api_base

    lm = dspy.LM(settings.model, **lm_options)
    dspy.configure_cache(enable_disk_cache=False, enable_memory_cache=False)
    dspy.configure(
        lm=lm,
        adapter=dspy.JSONAdapter(),
        track_usage=True,
        disable_history=True,
    )
    return lm
