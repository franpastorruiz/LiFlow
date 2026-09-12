from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MetricDataType = Literal["number", "string", "boolean"]
Aggregation = Literal["sum", "average", "latest", "min", "max", "count"]


class ActivityDefinition(BaseModel):
    """A tracker-owned canonical activity, optionally nested below another one."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=300)
    parent_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)


class MetricDefaultContext(BaseModel):
    """A personal default available to the extractor for a scoped activity."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    scope_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    value: float | str | bool
    unit: str | None = Field(default=None, min_length=1, max_length=40)


class MetricDefinition(BaseModel):
    """The semantic definition of one metric within a tracker."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=300)
    data_type: MetricDataType
    preferred_unit: str | None = Field(default=None, min_length=1, max_length=40)
    aggregation: Aggregation


class TrackerContext(BaseModel):
    """Known tracker information sent to the extraction component."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tracker_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    known_metrics: list[MetricDefinition] = Field(default_factory=list, max_length=100)
    known_activities: list[ActivityDefinition] = Field(default_factory=list, max_length=100)
    known_defaults: list[MetricDefaultContext] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_unique_metric_keys(self) -> "TrackerContext":
        metric_keys = [metric.key for metric in self.known_metrics]
        if len(metric_keys) != len(set(metric_keys)):
            raise ValueError("A tracker cannot contain duplicated metric keys.")
        activity_keys = [activity.key for activity in self.known_activities]
        if len(activity_keys) != len(set(activity_keys)):
            raise ValueError("A tracker cannot contain duplicated activity keys.")
        return self
