from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.tracker import MetricDefinition


class MetricObservation(BaseModel):
    """A value observed for a metric already known or proposed by an extraction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    value: float | str | bool
    unit: str | None = Field(default=None, min_length=1, max_length=40)


class NewMetricProposal(MetricDefinition):
    """A metric that the extractor proposes because the tracker does not know it."""


class LifeEvent(BaseModel):
    """A personal event that happened on a concrete date."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    activity: str = Field(min_length=1, max_length=100)
    date: date
    observations: list[MetricObservation] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_unique_observation_keys(self) -> "LifeEvent":
        metric_keys = [observation.metric_key for observation in self.observations]
        if len(metric_keys) != len(set(metric_keys)):
            raise ValueError("An event cannot contain the same metric twice.")
        return self
