from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.persistence import ActivityDefinitionRead, MetricDefinitionRead, TrackerCreate, TrackerRead
from app.schemas.tracker import ActivityDefinition, MetricDefinition
from app.services.persistence import (
    PersistenceError,
    TrackerNotFoundError,
    add_activity_definition,
    add_metric_definition,
    create_tracker,
    get_tracker_for_development_user,
)


router = APIRouter(prefix="/v1/trackers", tags=["trackers"])


@router.post("", response_model=TrackerRead, status_code=status.HTTP_201_CREATED)
def create_development_tracker(
    payload: TrackerCreate, session: Annotated[Session, Depends(get_session)]
) -> TrackerRead:
    try:
        tracker = create_tracker(session, payload)
    except PersistenceError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tracker key already exists.") from error
    return TrackerRead.model_validate(tracker, from_attributes=True)


@router.post("/{tracker_key}/metrics", response_model=MetricDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_metric(
    tracker_key: str,
    payload: MetricDefinition,
    session: Annotated[Session, Depends(get_session)],
) -> MetricDefinitionRead:
    try:
        tracker = get_tracker_for_development_user(session, tracker_key)
        metric = add_metric_definition(session, tracker, payload)
    except TrackerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The requested tracker does not exist.") from error
    except PersistenceError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Metric key already exists in this tracker.") from error
    return MetricDefinitionRead.model_validate(metric, from_attributes=True)


@router.post("/{tracker_key}/activities", response_model=ActivityDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_activity(
    tracker_key: str,
    payload: ActivityDefinition,
    session: Annotated[Session, Depends(get_session)],
) -> ActivityDefinitionRead:
    try:
        tracker = get_tracker_for_development_user(session, tracker_key)
        activity = add_activity_definition(session, tracker, payload)
    except TrackerNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The requested tracker does not exist.") from error
    except PersistenceError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Activity key or parent is invalid.") from error
    return ActivityDefinitionRead.model_validate(activity, from_attributes=True)
