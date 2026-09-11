from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.event import LifeEvent, NewMetricProposal
from app.schemas.tracker import TrackerContext


class ExtractionRequest(BaseModel):
    """Text and temporal context used to interpret a personal record."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2_000)
    reference_date: date
    timezone: str = Field(min_length=1, max_length=64)
    tracker: TrackerContext


class ExtractionResult(BaseModel):
    """Validated events and transparent information about unprocessed text."""

    events: list[LifeEvent] = Field(default_factory=list)
    new_metrics: list[NewMetricProposal] = Field(default_factory=list)
    unparsed_text: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
