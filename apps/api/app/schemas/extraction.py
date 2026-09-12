from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.event import LifeEvent, NewActivityProposal, NewMetricProposal
from app.schemas.tracker import TrackerContext


class ExtractionRequest(BaseModel):
    """Text and temporal context used to interpret a personal record."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2_000)
    reference_date: date
    timezone: str = Field(min_length=1, max_length=64)
    tracker: TrackerContext


class StoredExtractionRequest(BaseModel):
    """Public request: the tracker context is loaded from the database."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2_000)
    reference_date: date
    timezone: str = Field(min_length=1, max_length=64)
    tracker_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)


class DefaultUpdate(BaseModel):
    """An explicit user statement that creates or replaces a personal default."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    scope_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    value: float | str | bool
    unit: str | None = Field(default=None, min_length=1, max_length=40)


class ExtractionResult(BaseModel):
    """Validated events and transparent information about unprocessed text."""

    events: list[LifeEvent] = Field(default_factory=list)
    new_activities: list[NewActivityProposal] = Field(default_factory=list)
    new_metrics: list[NewMetricProposal] = Field(default_factory=list)
    default_updates: list[DefaultUpdate] = Field(default_factory=list)
    unparsed_text: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
