import pytest
from pydantic import ValidationError

from app.schemas.event import LifeEvent
from app.schemas.tracker import MetricDefinition, TrackerContext


def test_event_accepts_multiple_dynamic_observations() -> None:
    event = LifeEvent(
        activity_key="study",
        activity="study",
        date="2026-09-11",
        observations=[
            {
                "metric_key": "study_duration",
                "value": 3,
                "unit": "hours",
            },
            {
                "metric_key": "topics_completed",
                "value": 2,
                "unit": "topics",
            },
        ],
    )

    assert event.activity == "study"
    assert len(event.observations) == 2


def test_metric_definition_accepts_a_new_unit_without_code_changes() -> None:
    metric = MetricDefinition(
        key="pages_read",
        display_name="Páginas leídas",
        description="Número de páginas leídas durante una sesión.",
        data_type="number",
        preferred_unit="pages",
        aggregation="sum",
    )

    assert metric.preferred_unit == "pages"


def test_event_rejects_repeated_metric_observations() -> None:
    with pytest.raises(ValidationError, match="same metric twice"):
        LifeEvent(
            activity_key="study",
            activity="study",
            date="2026-09-11",
            observations=[
                {
                    "metric_key": "study_duration",
                    "value": 1,
                    "unit": "hours",
                },
                {
                    "metric_key": "study_duration",
                    "value": 30,
                    "unit": "minutes",
                },
            ],
        )


def test_event_rejects_an_empty_string_as_an_observation_value() -> None:
    with pytest.raises(ValidationError):
        LifeEvent(
            activity_key="bjj",
            activity="BJJ",
            date="2026-09-12",
            observations=[
                {"metric_key": "duration", "value": "", "unit": "hours"}
            ],
        )


def test_tracker_rejects_duplicate_metric_definitions() -> None:
    definition = {
        "key": "study_duration",
        "display_name": "Tiempo de estudio",
        "description": "Tiempo dedicado a estudiar.",
        "data_type": "number",
        "preferred_unit": "hours",
        "aggregation": "sum",
    }

    with pytest.raises(ValidationError, match="duplicated metric keys"):
        TrackerContext(
            tracker_key="university",
            display_name="Universidad",
            known_metrics=[definition, definition],
        )
