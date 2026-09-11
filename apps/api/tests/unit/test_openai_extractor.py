from types import SimpleNamespace
from pathlib import Path

import pytest

import app.core.config as config
from app.core.config import ConfigurationError, Settings
from app.extraction.openai_extractor import OpenAIExtractor
from app.schemas.extraction import ExtractionRequest, ExtractionResult


def university_request() -> ExtractionRequest:
    return ExtractionRequest(
        text="Hoy he estudiado 3 horas y he hecho 25 ejercicios.",
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
                }
            ],
        },
    )


class StubResponses:
    def __init__(self, result: ExtractionResult) -> None:
        self.result = result
        self.call_kwargs: dict = {}

    def parse(self, **kwargs: object) -> SimpleNamespace:
        self.call_kwargs = kwargs
        return SimpleNamespace(output_parsed=self.result)


class StubClient:
    def __init__(self, result: ExtractionResult) -> None:
        self.responses = StubResponses(result)


def test_openai_extractor_uses_structured_output_and_returns_multiple_events() -> None:
    result = ExtractionResult(
        events=[
            {
                "activity": "study",
                "date": "2026-09-11",
                "observations": [
                    {"metric_key": "study_duration", "value": 3, "unit": "hours"}
                ],
            },
            {
                "activity": "exercise",
                "date": "2026-09-11",
                "observations": [
                    {"metric_key": "exercises_completed", "value": 25, "unit": "count"}
                ],
            },
        ],
        new_metrics=[
            {
                "key": "exercises_completed",
                "display_name": "Ejercicios realizados",
                "description": "Número de ejercicios completados.",
                "data_type": "number",
                "preferred_unit": "count",
                "aggregation": "sum",
            }
        ],
        unparsed_text=["No se indicó la asignatura de los ejercicios."],
    )
    client = StubClient(result)
    extractor = OpenAIExtractor(api_key="test", model="test-model", client=client)

    extracted = extractor.extract(university_request())

    assert len(extracted.events) == 2
    assert extracted.new_metrics[0].key == "exercises_completed"
    assert extracted.unparsed_text == ["No se indicó la asignatura de los ejercicios."]
    assert client.responses.call_kwargs["store"] is False
    assert client.responses.call_kwargs["text_format"] is ExtractionResult


def test_openai_configuration_requires_a_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("EXTRACTION_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        Settings.from_environment()


def test_configuration_loads_root_dotenv_without_overriding_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "EXTRACTION_PROVIDER=openai\n"
        "OPENAI_API_KEY=file-key\n"
        "OPENAI_MODEL=file-model\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("EXTRACTION_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    settings = Settings.from_environment()

    assert settings.extraction_provider == "openai"
    assert settings.openai_api_key == "environment-key"
    assert settings.openai_model == "file-model"

    monkeypatch.delenv("EXTRACTION_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
