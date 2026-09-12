from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.tracker import ActivityDefinition, MetricDefinition


MetricValue = float | Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | bool


class MetricObservation(BaseModel):
    """A value observed for a metric already known or proposed by an extraction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    value: MetricValue
    unit: str | None = Field(default=None, min_length=1, max_length=40)


class DefaultRequest(BaseModel):
    """Request to apply a stored personal default to this event."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    scope_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)


class NewMetricProposal(MetricDefinition):
    """A metric that the extractor proposes because the tracker does not know it."""


class NewActivityProposal(ActivityDefinition):
    """A canonical activity proposed only when no known activity is equivalent."""


class LifeEvent(BaseModel):
    """A personal event that happened on a concrete date."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    activity_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    activity: str = Field(min_length=1, max_length=100)
    date: date
    observations: list[MetricObservation] = Field(default_factory=list, max_length=30)
    default_requests: list[DefaultRequest] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_unique_observation_keys(self) -> "LifeEvent":
        metric_keys = [observation.metric_key for observation in self.observations]
        if len(metric_keys) != len(set(metric_keys)):
            raise ValueError("An event cannot contain the same metric twice.")
        default_metric_keys = [request.metric_key for request in self.default_requests]
        if len(default_metric_keys) != len(set(default_metric_keys)):
            raise ValueError("An event cannot request the same default twice.")
        return self
