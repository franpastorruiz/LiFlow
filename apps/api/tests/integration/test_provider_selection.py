import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_extractor
from app.db.base import Base
from app.db.session import get_session
from app.extraction.errors import ExtractionProviderError
from app.main import app
from app.schemas.extraction import ExtractionResult
from app.schemas.persistence import TrackerCreate
from app.services.persistence import create_tracker


def valid_request_payload() -> dict:
    return {
        "text": "Texto de prueba.",
        "reference_date": "2026-09-11",
        "timezone": "Europe/Madrid",
        "tracker_key": "university",
    }


class ConfiguredExtractor:
    def extract(self, request: object) -> ExtractionResult:
        return ExtractionResult(warnings=["Extracted by the configured provider."])


class FailingExtractor:
    def extract(self, request: object) -> ExtractionResult:
        raise ExtractionProviderError("Provider unavailable")


@pytest.fixture(autouse=True)
def database_override() -> object:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    create_tracker(session, TrackerCreate(tracker_key="university", display_name="Universidad"))
    app.dependency_overrides[get_session] = lambda: session
    yield
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)


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
