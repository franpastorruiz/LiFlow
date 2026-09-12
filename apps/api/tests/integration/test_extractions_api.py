import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_extractor
from app.db.base import Base
from app.db.session import get_session
from app.extraction.demo_extractor import DemoExtractor
from app.main import app
from app.schemas.persistence import TrackerCreate
from app.schemas.tracker import ActivityDefinition, MetricDefinition
from app.services.persistence import add_activity_definition, add_metric_definition, create_tracker


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_demo_extractor() -> object:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    tracker = create_tracker(
        session,
        TrackerCreate(tracker_key="university", display_name="Universidad"),
    )
    add_activity_definition(
        session,
        tracker,
        ActivityDefinition(key="study", display_name="Estudio", description="Actividad académica."),
    )
    for metric in university_tracker_context()["known_metrics"]:
        add_metric_definition(session, tracker, MetricDefinition.model_validate(metric))

    app.dependency_overrides[get_extractor] = lambda: DemoExtractor()
    app.dependency_overrides[get_session] = lambda: session
    yield
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)


def university_tracker_context() -> dict:
    return {
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
    }


def test_extraction_reuses_known_metrics_and_proposes_a_new_one() -> None:
    response = client.post(
        "/v1/extractions",
        json={
            "text": "Hoy he estudiado 3 horas, he estado concentrado un 8/10 y he hecho 25 ejercicios de álgebra.",
            "reference_date": "2026-09-11",
            "timezone": "Europe/Madrid",
            "tracker_key": "university",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"][0]["activity"] == "Estudio"
    assert payload["events"][0]["activity_key"] == "study"
    assert {observation["metric_key"] for observation in payload["events"][0]["observations"]} == {
        "study_duration",
        "concentration",
        "exercises_completed",
    }
    assert [metric["key"] for metric in payload["new_metrics"]] == [
        "exercises_completed"
    ]


def test_extraction_returns_a_warning_for_unknown_text() -> None:
    response = client.post(
        "/v1/extractions",
        json={
            "text": "Hoy he practicado yoga.",
            "reference_date": "2026-09-11",
            "timezone": "Europe/Madrid",
            "tracker_key": "university",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"] == []
    assert payload["unparsed_text"] == ["Hoy he practicado yoga."]
    assert len(payload["warnings"]) == 1
