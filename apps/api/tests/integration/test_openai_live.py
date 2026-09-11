import os

import pytest
from dotenv import load_dotenv

from app.core.config import Settings
from app.extraction.openai_extractor import OpenAIExtractor
from app.schemas.extraction import ExtractionRequest


pytestmark = pytest.mark.openai_live


@pytest.mark.skipif(
    os.getenv("RUN_OPENAI_LIVE_TESTS") != "1",
    reason="Set RUN_OPENAI_LIVE_TESTS=1 to make a billable OpenAI request.",
)
def test_openai_extracts_the_university_example() -> None:
    load_dotenv()
    settings = Settings.from_environment()
    assert settings.extraction_provider == "openai"

    result = OpenAIExtractor(
        api_key=settings.openai_api_key or "",
        model=settings.openai_model or "",
    ).extract(
        ExtractionRequest(
            text="Hoy he estudiado 3 horas, he estado concentrado un 8/10 y he hecho 25 ejercicios de álgebra.",
            reference_date="2026-09-11",
            timezone="Europe/Madrid",
            tracker={
                "tracker_key": "university",
                "display_name": "Universidad",
                "known_metrics": [
                    {
                        "key": "study_duration",
                        "display_name": "Tiempo de estudio",
                        "description": "Tiempo dedicado a estudiar.",
                        "data_type": "number",
                        "preferred_unit": "hours",
                        "aggregation": "sum",
                    },
                    {
                        "key": "concentration",
                        "display_name": "Concentración",
                        "description": "Nivel subjetivo de concentración.",
                        "data_type": "number",
                        "preferred_unit": "score_1_10",
                        "aggregation": "average",
                    },
                ],
            },
        )
    )

    assert result.events
