from types import SimpleNamespace
from typing import Any

from pydantic import SecretStr

from changeops.ai import model_factory


def test_interpretation_model_uses_responses_api(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        return object()

    settings = SimpleNamespace(
        interpretation_model_provider="openai",
        interpretation_model="gpt-5.6-luna",
        interpretation_model_timeout_seconds=120.0,
        interpretation_model_max_retries=0,
        openai_api_key=SecretStr("test-key"),
    )
    monkeypatch.setattr(model_factory, "ChatOpenAI", fake_chat_openai)
    monkeypatch.setattr(model_factory, "get_settings", lambda: settings)

    configured = model_factory.get_configured_interpretation_model()

    assert configured.identifier == "gpt-5.6-luna"
    assert captured["use_responses_api"] is True
