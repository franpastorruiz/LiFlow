from fastapi.testclient import TestClient

from app.api.dependencies import get_extractor
from app.extraction.errors import ExtractionProviderError
from app.main import app
from app.schemas.extraction import ExtractionResult


def valid_request_payload() -> dict:
    return {
        "text": "Texto de prueba.",
        "reference_date": "2026-09-11",
        "timezone": "Europe/Madrid",
        "tracker": {
            "tracker_key": "university",
            "display_name": "Universidad",
            "known_metrics": [],
        },
    }


class ConfiguredExtractor:
    def extract(self, request: object) -> ExtractionResult:
        return ExtractionResult(warnings=["Extracted by the configured provider."])


class FailingExtractor:
    def extract(self, request: object) -> ExtractionResult:
        raise ExtractionProviderError("Provider unavailable")


def test_endpoint_uses_the_injected_extractor() -> None:
    app.dependency_overrides[get_extractor] = lambda: ConfiguredExtractor()
    try:
        response = TestClient(app).post("/v1/extractions", json=valid_request_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["warnings"] == ["Extracted by the configured provider."]


def test_endpoint_returns_a_safe_provider_error() -> None:
    app.dependency_overrides[get_extractor] = lambda: FailingExtractor()
    try:
        response = TestClient(app).post("/v1/extractions", json=valid_request_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "The extraction provider is unavailable."
