from langchain_openai import ChatOpenAI

from changeops.ai.policy_extractor import ConfiguredExtractionModel
from changeops.config import get_settings


class ExtractionProviderConfigurationError(Exception):
    pass


def get_configured_extraction_model() -> ConfiguredExtractionModel:
    settings = get_settings()
    if settings.extraction_model_provider != "openai":
        raise ExtractionProviderConfigurationError(
            f"Unsupported extraction provider: {settings.extraction_model_provider}"
        )
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip():
        raise ExtractionProviderConfigurationError(
            "OPENAI_API_KEY is required to run policy extraction."
        )
    return ConfiguredExtractionModel(
        model=ChatOpenAI(
            model=settings.extraction_model,
            api_key=settings.openai_api_key,
            temperature=0,
        ),
        provider=settings.extraction_model_provider,
        identifier=settings.extraction_model,
    )
