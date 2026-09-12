from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.models import ActivityDefinition as ActivityDefinitionModel
from app.db.models import LifeEvent as LifeEventModel
from app.db.models import MetricDefault as MetricDefaultModel
from app.db.models import MetricDefinition as MetricDefinitionModel
from app.db.models import MetricObservation as MetricObservationModel
from app.db.models import Tracker, User
from app.schemas.event import MetricObservation
from app.schemas.extraction import DefaultUpdate, ExtractionResult
from app.schemas.persistence import TrackerCreate
from app.schemas.tracker import ActivityDefinition, MetricDefaultContext, MetricDefinition, TrackerContext


DEVELOPMENT_USER_IDENTIFIER = "development-user"


class PersistenceError(ValueError):
    """Raised when an extraction cannot safely be persisted."""


class TrackerNotFoundError(PersistenceError):
    """Raised when a tracker is not owned by the development user."""


def get_or_create_development_user(session: Session) -> User:
    user = session.scalar(select(User).where(User.identifier == DEVELOPMENT_USER_IDENTIFIER))
    if user is None:
        user = User(identifier=DEVELOPMENT_USER_IDENTIFIER)
        session.add(user)
        session.flush()
    return user


def create_tracker(session: Session, payload: TrackerCreate) -> Tracker:
    user = get_or_create_development_user(session)
    tracker = Tracker(
        user_id=user.id,
        tracker_key=payload.tracker_key,
        display_name=payload.display_name,
        description=payload.description,
    )
    session.add(tracker)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersistenceError("A tracker with this key already exists.") from error
    session.refresh(tracker)
    return tracker


def add_metric_definition(
    session: Session, tracker: Tracker, definition: MetricDefinition
) -> MetricDefinitionModel:
    metric = MetricDefinitionModel(
        tracker_id=tracker.id,
        key=definition.key,
        display_name=definition.display_name,
        description=definition.description,
        data_type=definition.data_type,
        preferred_unit=definition.preferred_unit,
        aggregation=definition.aggregation,
    )
    session.add(metric)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersistenceError("A metric with this key already exists in the tracker.") from error
    session.refresh(metric)
    return metric


def add_activity_definition(
    session: Session, tracker: Tracker, definition: ActivityDefinition
) -> ActivityDefinitionModel:
    parent = None
    if definition.parent_key:
        parent = session.scalar(
            select(ActivityDefinitionModel).where(
                ActivityDefinitionModel.tracker_id == tracker.id,
                ActivityDefinitionModel.key == definition.parent_key,
            )
        )
        if parent is None:
            raise PersistenceError("The parent activity does not exist in this tracker.")
    activity = ActivityDefinitionModel(
        tracker_id=tracker.id,
        key=definition.key,
        display_name=definition.display_name,
        description=definition.description,
        parent_activity_definition_id=parent.id if parent else None,
    )
    session.add(activity)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersistenceError("An activity with this key already exists in the tracker.") from error
    session.refresh(activity)
    return activity


def get_tracker_for_development_user(session: Session, tracker_key: str) -> Tracker:
    statement = (
        select(Tracker)
        .join(Tracker.user)
        .options(
            selectinload(Tracker.metric_definitions).selectinload(MetricDefinitionModel.defaults),
            selectinload(Tracker.activity_definitions),
        )
        .where(User.identifier == DEVELOPMENT_USER_IDENTIFIER, Tracker.tracker_key == tracker_key)
    )
    tracker = session.scalar(statement)
    if tracker is None:
        raise TrackerNotFoundError("Tracker not found.")
    return tracker


def tracker_to_context(tracker: Tracker) -> TrackerContext:
    activities_by_id = {activity.id: activity for activity in tracker.activity_definitions}
    return TrackerContext(
        tracker_key=tracker.tracker_key,
        display_name=tracker.display_name,
        description=tracker.description,
        known_metrics=[
            MetricDefinition(
                key=metric.key,
                display_name=metric.display_name,
                description=metric.description,
                data_type=metric.data_type,
                preferred_unit=metric.preferred_unit,
                aggregation=metric.aggregation,
            )
            for metric in tracker.metric_definitions
        ],
        known_activities=[
            ActivityDefinition(
                key=activity.key,
                display_name=activity.display_name,
                description=activity.description,
                parent_key=(
                    activities_by_id[activity.parent_activity_definition_id].key
                    if activity.parent_activity_definition_id else None
                ),
            )
            for activity in tracker.activity_definitions
        ],
        known_defaults=[
            MetricDefaultContext(
                metric_key=metric.key,
                scope_key=default.scope_key,
                value=_default_value(default),
                unit=default.unit,
            )
            for metric in tracker.metric_definitions
            for default in metric.defaults
        ],
    )


def _observation_values(
    observation: MetricObservation, metric: MetricDefinitionModel
) -> dict[str, Decimal | str | bool | None]:
    if metric.data_type == "number":
        if isinstance(observation.value, bool) or not isinstance(observation.value, (int, float)):
            raise PersistenceError(f"Metric '{metric.key}' requires a numeric value.")
        return {"value_number": Decimal(str(observation.value)), "value_text": None, "value_boolean": None}
    if metric.data_type == "string":
        if not isinstance(observation.value, str):
            raise PersistenceError(f"Metric '{metric.key}' requires a text value.")
        return {"value_number": None, "value_text": observation.value, "value_boolean": None}
    if metric.data_type == "boolean":
        if not isinstance(observation.value, bool):
            raise PersistenceError(f"Metric '{metric.key}' requires a boolean value.")
        return {"value_number": None, "value_text": None, "value_boolean": observation.value}
    raise PersistenceError(f"Metric '{metric.key}' has an unsupported data type.")


def _default_value(default: MetricDefaultModel) -> float | str | bool:
    if default.value_number is not None:
        return float(default.value_number)
    if default.value_text is not None:
        return default.value_text
    if default.value_boolean is not None:
        return default.value_boolean
    raise PersistenceError("A stored default has no value.")


def _upsert_default(
    session: Session,
    metric: MetricDefinitionModel,
    update: DefaultUpdate,
    source_text: str,
) -> MetricDefaultModel:
    values = _observation_values(
        MetricObservation(metric_key=update.metric_key, value=update.value, unit=update.unit),
        metric,
    )
    statement = select(MetricDefaultModel).where(
        MetricDefaultModel.metric_definition_id == metric.id,
        MetricDefaultModel.scope_key == update.scope_key,
    )
    default = session.scalar(statement)
    if default is None:
        default = MetricDefaultModel(
            metric_definition_id=metric.id,
            scope_key=update.scope_key,
            unit=update.unit,
            source_text=source_text,
            source_kind="user_statement",
            **values,
        )
        session.add(default)
    else:
        default.unit = update.unit
        default.source_text = source_text
        default.source_kind = "user_statement"
        default.value_number = values["value_number"]  # type: ignore[assignment]
        default.value_text = values["value_text"]  # type: ignore[assignment]
        default.value_boolean = values["value_boolean"]  # type: ignore[assignment]
    session.flush()
    return default


def persist_extraction(
    session: Session, tracker: Tracker, result: ExtractionResult, source_text: str
) -> None:
    """Atomically create proposed metrics, events and observations for one extraction."""

    try:
        metrics_by_key = {metric.key: metric for metric in tracker.metric_definitions}
        activities_by_key = {activity.key: activity for activity in tracker.activity_definitions}
        new_activities_by_key: dict[str, ActivityDefinitionModel] = {}
        for proposal in result.new_activities:
            if proposal.key in activities_by_key:
                continue
            activity = ActivityDefinitionModel(
                tracker_id=tracker.id,
                key=proposal.key,
                display_name=proposal.display_name,
                description=proposal.description,
            )
            session.add(activity)
            session.flush()
            activities_by_key[activity.key] = activity
            new_activities_by_key[activity.key] = activity
        for proposal in result.new_activities:
            activity = new_activities_by_key.get(proposal.key)
            if activity is None or proposal.parent_key is None:
                continue
            parent = activities_by_key.get(proposal.parent_key)
            if parent is None or parent.id == activity.id:
                raise PersistenceError(
                    f"New activity '{proposal.key}' references an unknown or invalid parent."
                )
            activity.parent_activity_definition_id = parent.id
        for proposal in result.new_metrics:
            if proposal.key not in metrics_by_key:
                metric = MetricDefinitionModel(
                    tracker_id=tracker.id,
                    key=proposal.key,
                    display_name=proposal.display_name,
                    description=proposal.description,
                    data_type=proposal.data_type,
                    preferred_unit=proposal.preferred_unit,
                    aggregation=proposal.aggregation,
                )
                session.add(metric)
                session.flush()
                metrics_by_key[metric.key] = metric

        for update in result.default_updates:
            if update.scope_key not in activities_by_key:
                raise PersistenceError(
                    f"Default update references unknown activity '{update.scope_key}'."
                )
            metric = metrics_by_key.get(update.metric_key)
            if metric is None:
                raise PersistenceError(
                    f"Default update references unknown metric '{update.metric_key}'."
                )
            _upsert_default(session, metric, update, source_text)

        for extracted_event in result.events:
            activity = activities_by_key.get(extracted_event.activity_key)
            if activity is None:
                raise PersistenceError(
                    f"Event references unknown activity '{extracted_event.activity_key}'."
                )
            extracted_event.activity = activity.display_name
            event = LifeEventModel(
                tracker_id=tracker.id,
                activity_definition_id=activity.id,
                activity_key=activity.key,
                activity=activity.display_name,
                occurred_on=extracted_event.date,
                source_text=source_text,
            )
            session.add(event)
            session.flush()
            for observation in extracted_event.observations:
                metric = metrics_by_key.get(observation.metric_key)
                if metric is None:
                    raise PersistenceError(
                        f"Observation references unknown metric '{observation.metric_key}'."
                    )
                session.add(
                    MetricObservationModel(
                        life_event_id=event.id,
                        metric_definition_id=metric.id,
                        unit=observation.unit,
                        value_origin="explicit",
                        **_observation_values(observation, metric),
                    )
                )
            explicit_metric_keys = {observation.metric_key for observation in extracted_event.observations}
            for default_request in extracted_event.default_requests:
                if default_request.metric_key in explicit_metric_keys:
                    continue
                metric = metrics_by_key.get(default_request.metric_key)
                if metric is None:
                    raise PersistenceError(
                        f"Default request references unknown metric '{default_request.metric_key}'."
                    )
                default = session.scalar(
                    select(MetricDefaultModel).where(
                        MetricDefaultModel.metric_definition_id == metric.id,
                        MetricDefaultModel.scope_key == default_request.scope_key,
                    )
                )
                if default is None:
                    continue
                session.add(
                    MetricObservationModel(
                        life_event_id=event.id,
                        metric_definition_id=metric.id,
                        unit=default.unit,
                        value_origin="default",
                        **_observation_values(
                            MetricObservation(
                                metric_key=metric.key,
                                value=_default_value(default),
                                unit=default.unit,
                            ),
                            metric,
                        ),
                    )
                )
        session.commit()
        # A following extraction in the same session must see newly created defaults.
        session.expire_all()
    except (IntegrityError, PersistenceError):
        session.rollback()
        raise
    except Exception:
        # Preserve the original error for internal logs while never leaving a partial transaction.
        session.rollback()
        raise
