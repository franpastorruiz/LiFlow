from fastapi import HTTPException, status

from app.core.config import ConfigurationError, Settings
from app.extraction.base import Extractor
from app.extraction.demo_extractor import DemoExtractor
from app.extraction.openai_extractor import OpenAIExtractor


def get_extractor() -> Extractor:
    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The extraction provider is not configured.",
        ) from error
    if settings.extraction_provider == "demo":
        return DemoExtractor()
    return OpenAIExtractor(
        api_key=settings.openai_api_key or "",
        model=settings.openai_model or "",
    )
