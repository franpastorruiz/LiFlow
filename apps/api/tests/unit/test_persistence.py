from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import LifeEvent as LifeEventModel
from app.db.models import ActivityDefinition as ActivityDefinitionModel
from app.db.models import MetricDefault as MetricDefaultModel
from app.db.models import MetricDefinition as MetricDefinitionModel
from app.db.models import MetricObservation as MetricObservationModel
from app.schemas.event import LifeEvent, NewActivityProposal, NewMetricProposal
from app.schemas.extraction import DefaultUpdate, ExtractionResult
from app.schemas.persistence import TrackerCreate
from app.schemas.tracker import ActivityDefinition, MetricDefinition
from app.services.persistence import (
    PersistenceError,
    add_activity_definition,
    add_metric_definition,
    create_tracker,
    get_tracker_for_development_user,
    persist_extraction,
    tracker_to_context,
)


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db_session = factory()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(engine)


def study_metric() -> MetricDefinition:
    return MetricDefinition(
        key="study_duration",
        display_name="Tiempo de estudio",
        description="Tiempo dedicado a estudiar.",
        data_type="number",
        preferred_unit="hours",
        aggregation="sum",
    )


def add_activity(session: Session, tracker: object, key: str, display_name: str | None = None, parent_key: str | None = None) -> None:
    add_activity_definition(
        session,
        tracker,  # type: ignore[arg-type]
        ActivityDefinition(
            key=key,
            display_name=display_name or key.replace("_", " ").title(),
            description=f"Actividad {key}.",
            parent_key=parent_key,
        ),
    )


def test_creates_tracker_and_metric_definition(session: Session) -> None:
    tracker = create_tracker(
        session, TrackerCreate(tracker_key="university", display_name="Universidad")
    )
    metric = add_metric_definition(session, tracker, study_metric())

    assert tracker.id is not None
    assert metric.key == "study_duration"


def test_does_not_duplicate_metric_key_within_tracker(session: Session) -> None:
    tracker = create_tracker(
        session, TrackerCreate(tracker_key="university", display_name="Universidad")
    )
    add_metric_definition(session, tracker, study_metric())
    add_activity(session, tracker, "study")

    with pytest.raises(PersistenceError, match="already exists"):
        add_metric_definition(session, tracker, study_metric())


def test_persists_event_observation_and_proposed_metric(session: Session) -> None:
    tracker = create_tracker(
        session, TrackerCreate(tracker_key="university", display_name="Universidad")
    )
    add_activity(session, tracker, "study")
    add_metric_definition(session, tracker, study_metric())
    result = ExtractionResult(
        new_metrics=[
            NewMetricProposal(
                key="exercises_completed",
                display_name="Ejercicios realizados",
                description="Número de ejercicios completados.",
                data_type="number",
                preferred_unit="count",
                aggregation="sum",
            )
        ],
        events=[
            LifeEvent(
                activity_key="study",
                activity="study",
                date=date(2026, 9, 12),
                observations=[
                    {"metric_key": "study_duration", "value": 3, "unit": "hours"},
                    {"metric_key": "exercises_completed", "value": 25, "unit": "count"},
                ],
            )
        ],
    )
    persist_extraction(session, tracker, result, "Hoy he estudiado 3 horas y he hecho 25 ejercicios.")

    event = session.scalar(select(LifeEventModel))
    observations = session.scalars(select(MetricObservationModel)).all()
    created_metric = session.scalar(
        select(MetricDefinitionModel).where(MetricDefinitionModel.key == "exercises_completed")
    )
    assert event is not None
    assert event.source_text.startswith("Hoy he estudiado")
    assert created_metric is not None
    assert len(observations) == 2
    assert {observation.value_number for observation in observations} == {3, 25}


def test_rolls_back_all_changes_when_observation_cannot_be_saved(session: Session) -> None:
    tracker = create_tracker(
        session, TrackerCreate(tracker_key="university", display_name="Universidad")
    )
    add_activity(session, tracker, "test")
    result = ExtractionResult(
        new_metrics=[
            NewMetricProposal(
                key="new_metric",
                display_name="Nueva métrica",
                description="Métrica de prueba.",
                data_type="number",
                preferred_unit="points",
                aggregation="sum",
            )
        ],
        events=[
            LifeEvent(
                activity_key="test",
                activity="test",
                date=date(2026, 9, 12),
                observations=[{"metric_key": "missing_metric", "value": 1, "unit": "points"}],
            )
        ],
    )

    with pytest.raises(PersistenceError, match="unknown metric"):
        persist_extraction(session, tracker, result, "Texto de prueba")

    assert session.scalars(select(LifeEventModel)).all() == []
    assert session.scalars(select(MetricDefinitionModel)).all() == []


def test_stores_text_and_boolean_in_their_typed_columns(session: Session) -> None:
    tracker = create_tracker(
        session, TrackerCreate(tracker_key="habits", display_name="Hábitos")
    )
    add_activity(session, tracker, "daily_checkin")
    result = ExtractionResult(
        new_metrics=[
            NewMetricProposal(
                key="mood_note",
                display_name="Nota de ánimo",
                description="Descripción breve del estado de ánimo.",
                data_type="string",
                preferred_unit=None,
                aggregation="latest",
            ),
            NewMetricProposal(
                key="meditated",
                display_name="Meditó",
                description="Indica si se realizó una meditación.",
                data_type="boolean",
                preferred_unit=None,
                aggregation="count",
            ),
        ],
        events=[
            LifeEvent(
                activity_key="daily_checkin",
                activity="daily_checkin",
                date=date(2026, 9, 12),
                observations=[
                    {"metric_key": "mood_note", "value": "tranquilo"},
                    {"metric_key": "meditated", "value": True},
                ],
            )
        ],
    )

    persist_extraction(session, tracker, result, "Me siento tranquilo y he meditado.")

    observations = session.scalars(select(MetricObservationModel)).all()
    assert {observation.value_text for observation in observations if observation.value_text} == {"tranquilo"}
    assert {observation.value_boolean for observation in observations if observation.value_boolean is not None} == {True}


def duration_metric() -> MetricDefinition:
    return MetricDefinition(
        key="duration",
        display_name="Duración",
        description="Tiempo dedicado a una actividad.",
        data_type="number",
        preferred_unit="hours",
        aggregation="sum",
    )


def test_persists_personal_default_without_creating_an_event(session: Session) -> None:
    tracker = create_tracker(session, TrackerCreate(tracker_key="sport", display_name="Deporte"))
    add_metric_definition(session, tracker, duration_metric())
    add_activity(session, tracker, "bjj", "BJJ")
    result = ExtractionResult(
        default_updates=[
            DefaultUpdate(metric_key="duration", scope_key="bjj", value=1.5, unit="hours")
        ]
    )

    persist_extraction(session, tracker, result, "Normalmente mis clases de BJJ duran una hora y media.")

    default = session.scalar(select(MetricDefaultModel))
    assert default is not None
    assert default.scope_key == "bjj"
    assert default.value_number == 1.5
    assert default.source_kind == "user_statement"
    assert session.scalars(select(LifeEventModel)).all() == []


def test_applies_default_to_a_plain_activity_when_no_explicit_value_exists(session: Session) -> None:
    tracker = create_tracker(session, TrackerCreate(tracker_key="sport", display_name="Deporte"))
    add_metric_definition(session, tracker, duration_metric())
    add_activity(session, tracker, "bjj", "BJJ")
    add_activity(session, tracker, "gym", "Gimnasio")
    persist_extraction(
        session,
        tracker,
        ExtractionResult(
            default_updates=[
                DefaultUpdate(metric_key="duration", scope_key="bjj", value=1.5, unit="hours")
            ]
        ),
        "Normalmente mis clases de BJJ duran una hora y media.",
    )
    result = ExtractionResult(
        events=[
            LifeEvent(
                activity_key="bjj",
                activity="BJJ",
                date=date(2026, 9, 12),
                default_requests=[{"metric_key": "duration", "scope_key": "bjj"}],
            ),
            LifeEvent(
                activity_key="bjj",
                activity="Jiu-jitsu",
                date=date(2026, 9, 12),
                observations=[{"metric_key": "duration", "value": 2, "unit": "hours"}],
                default_requests=[{"metric_key": "duration", "scope_key": "bjj"}],
            ),
            LifeEvent(activity_key="gym", activity="Gym — pierna", date=date(2026, 9, 12)),
        ]
    )

    persist_extraction(session, tracker, result, "Hoy he ido a BJJ.")

    observations = session.scalars(select(MetricObservationModel).order_by(MetricObservationModel.id)).all()
    assert [(observation.value_number, observation.value_origin) for observation in observations] == [
        (1.5, "default"),
        (2, "explicit"),
    ]
    events = session.scalars(select(LifeEventModel).order_by(LifeEventModel.id)).all()
    assert [event.activity_key for event in events] == ["bjj", "bjj", "gym"]


def test_context_includes_scoped_defaults(session: Session) -> None:
    tracker = create_tracker(session, TrackerCreate(tracker_key="sport", display_name="Deporte"))
    add_metric_definition(session, tracker, duration_metric())
    add_activity(session, tracker, "bjj", "BJJ")
    persist_extraction(
        session,
        tracker,
        ExtractionResult(
            default_updates=[
                DefaultUpdate(metric_key="duration", scope_key="bjj", value=1.5, unit="hours")
            ]
        ),
        "Normalmente mis clases de BJJ duran una hora y media.",
    )

    reloaded_tracker = get_tracker_for_development_user(session, "sport")
    context = tracker_to_context(reloaded_tracker)
    assert context.known_defaults[0].model_dump() == {
        "metric_key": "duration",
        "scope_key": "bjj",
        "value": 1.5,
        "unit": "hours",
    }


def test_persists_new_activity_with_parent_and_links_event(session: Session) -> None:
    tracker = create_tracker(session, TrackerCreate(tracker_key="sport", display_name="Deporte"))
    add_activity(session, tracker, "running", "Running")
    result = ExtractionResult(
        new_activities=[
            NewActivityProposal(
                key="trail_running",
                display_name="Trail running",
                description="Carrera por montaña o senderos.",
                parent_key="running",
            )
        ],
        events=[
            LifeEvent(
                activity_key="trail_running",
                activity="Correr por montaña",
                date=date(2026, 9, 12),
            )
        ],
    )

    persist_extraction(session, tracker, result, "Hoy he corrido por montaña.")

    trail = session.scalar(select(ActivityDefinitionModel).where(ActivityDefinitionModel.key == "trail_running"))
    running = session.scalar(select(ActivityDefinitionModel).where(ActivityDefinitionModel.key == "running"))
    event = session.scalar(select(LifeEventModel))
    assert trail is not None and running is not None and event is not None
    assert trail.parent_activity_definition_id == running.id
    assert event.activity_definition_id == trail.id
    assert event.activity_key == "trail_running"


def test_reuses_known_activity_without_creating_a_linguistic_variant(session: Session) -> None:
    tracker = create_tracker(session, TrackerCreate(tracker_key="sport", display_name="Deporte"))
    add_activity(session, tracker, "bjj", "BJJ")
    result = ExtractionResult(
        events=[
            LifeEvent(
                activity_key="bjj",
                activity="Jiu-jitsu",
                date=date(2026, 9, 12),
            )
        ]
    )

    persist_extraction(session, tracker, result, "Hoy he ido a jiujitsu.")

    assert session.scalars(select(ActivityDefinitionModel)).all()[0].key == "bjj"
    assert session.scalar(select(LifeEventModel)).activity_key == "bjj"
    assert result.events[0].activity == "BJJ"
