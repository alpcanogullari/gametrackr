from unittest.mock import Mock

import pytest

from game_accountability.ai.config import DSPySettings, configure_dspy, load_dspy_settings
from game_accountability.ai.errors import AIConfigurationError


def test_environment_overrides_dotenv_values(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GAME_ACCOUNTABILITY_AI_MODEL=openai/from-file\n"
        "GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE=false\n",
        encoding="utf-8",
    )

    settings = load_dspy_settings(
        env_file,
        environ={
            "GAME_ACCOUNTABILITY_AI_MODEL": "ollama_chat/qwen3",
            "GAME_ACCOUNTABILITY_AI_MAX_TOKENS": "900",
        },
    )

    assert settings.model == "ollama_chat/qwen3"
    assert settings.max_tokens == 900
    assert settings.is_local


def test_openai_api_key_uses_standard_environment_variable() -> None:
    settings = load_dspy_settings(
        env_file=None,
        environ={
            "GAME_ACCOUNTABILITY_AI_MODEL": "openai/example",
            "GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE": "true",
            "OPENAI_API_KEY": "test-key-not-real",
        },
    )

    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "test-key-not-real"
    assert "test-key-not-real" not in repr(settings)


def test_project_specific_api_key_remains_an_override() -> None:
    settings = load_dspy_settings(
        env_file=None,
        environ={
            "OPENAI_API_KEY": "standard-test-key",
            "GAME_ACCOUNTABILITY_AI_API_KEY": "override-test-key",
        },
    )

    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "override-test-key"


def test_remote_provider_requires_explicit_opt_in() -> None:
    with pytest.raises(AIConfigurationError, match="remote AI is disabled"):
        configure_dspy(DSPySettings(model="openai/example"))


def test_missing_model_is_rejected() -> None:
    with pytest.raises(AIConfigurationError, match="MODEL is required"):
        configure_dspy(DSPySettings())


def test_local_provider_configures_json_adapter_without_cache(monkeypatch) -> None:
    lm = Mock()
    lm_factory = Mock(return_value=lm)
    configure_cache = Mock()
    configure = Mock()
    monkeypatch.setattr("game_accountability.ai.config.dspy.LM", lm_factory)
    monkeypatch.setattr("game_accountability.ai.config.dspy.configure_cache", configure_cache)
    monkeypatch.setattr("game_accountability.ai.config.dspy.configure", configure)

    result = configure_dspy(DSPySettings(model="ollama_chat/qwen3"))

    assert result is lm
    lm_factory.assert_called_once_with(
        "ollama_chat/qwen3",
        temperature=0.0,
        max_tokens=1200,
        cache=False,
    )
    configure_cache.assert_called_once_with(enable_disk_cache=False, enable_memory_cache=False)
    configured = configure.call_args.kwargs
    assert configured["lm"] is lm
    assert configured["track_usage"] is True
    assert configured["disable_history"] is True
