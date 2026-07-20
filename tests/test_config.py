import pytest

from app.config import Config, _load_config, config


def test_configuration():
    assert config.llm_model
    assert config.embedding_model
    assert config.storage_dir
    assert config.data_dir
    assert config.max_tool_calls > 0


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(Config, "model_config", {**Config.model_config, "env_file": None})

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        _load_config()


def test_unsupported_model_provider_rejected(monkeypatch):
    from app.services.llm import configure_models

    monkeypatch.setattr(config, "model_provider", "some-unsupported-provider")

    with pytest.raises(ValueError, match="Unsupported MODEL_PROVIDER"):
        configure_models()

    monkeypatch.setattr(config, "model_provider", "openai")
