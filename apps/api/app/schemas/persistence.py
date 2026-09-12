from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tracker import ActivityDefinition, MetricDefinition


class TrackerCreate(BaseModel):
    """Payload for creating a tracker for the temporary development user."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tracker_key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)


class TrackerRead(TrackerCreate):
    id: int


class MetricDefinitionRead(MetricDefinition):
    id: int


class ActivityDefinitionRead(ActivityDefinition):
    id: int
