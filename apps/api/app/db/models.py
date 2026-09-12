from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trackers: Mapped[list["Tracker"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Tracker(Base):
    __tablename__ = "trackers"
    __table_args__ = (UniqueConstraint("user_id", "tracker_key", name="uq_tracker_user_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tracker_key: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="trackers")
    metric_definitions: Mapped[list["MetricDefinition"]] = relationship(back_populates="tracker", cascade="all, delete-orphan")
    activity_definitions: Mapped[list["ActivityDefinition"]] = relationship(back_populates="tracker", cascade="all, delete-orphan")
    life_events: Mapped[list["LifeEvent"]] = relationship(back_populates="tracker", cascade="all, delete-orphan")


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (UniqueConstraint("tracker_id", "key", name="uq_metric_tracker_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(16))
    preferred_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    aggregation: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tracker: Mapped[Tracker] = relationship(back_populates="metric_definitions")
    observations: Mapped[list["MetricObservation"]] = relationship(back_populates="metric_definition")
    defaults: Mapped[list["MetricDefault"]] = relationship(back_populates="metric_definition", cascade="all, delete-orphan")


class ActivityDefinition(Base):
    __tablename__ = "activity_definitions"
    __table_args__ = (UniqueConstraint("tracker_id", "key", name="uq_activity_tracker_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    parent_activity_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_definitions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tracker: Mapped[Tracker] = relationship(back_populates="activity_definitions")
    parent: Mapped["ActivityDefinition | None"] = relationship(
        back_populates="children", remote_side="ActivityDefinition.id"
    )
    children: Mapped[list["ActivityDefinition"]] = relationship(back_populates="parent")
    life_events: Mapped[list["LifeEvent"]] = relationship(back_populates="activity_definition")


class MetricDefault(Base):
    __tablename__ = "metric_defaults"
    __table_args__ = (
        UniqueConstraint("metric_definition_id", "scope_key", name="uq_metric_default_scope"),
        CheckConstraint(
            "(CASE WHEN value_number IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_boolean IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_default_one_value",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    metric_definition_id: Mapped[int] = mapped_column(ForeignKey("metric_definitions.id", ondelete="CASCADE"))
    scope_key: Mapped[str] = mapped_column(String(64))
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_text: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(32), default="user_statement")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metric_definition: Mapped[MetricDefinition] = relationship(back_populates="defaults")


class LifeEvent(Base):
    __tablename__ = "life_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id", ondelete="CASCADE"))
    activity_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_definitions.id", ondelete="RESTRICT"), nullable=True
    )
    activity_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    activity: Mapped[str] = mapped_column(String(100))
    occurred_on: Mapped[date] = mapped_column(Date)
    source_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tracker: Mapped[Tracker] = relationship(back_populates="life_events")
    activity_definition: Mapped[ActivityDefinition | None] = relationship(back_populates="life_events")
    observations: Mapped[list["MetricObservation"]] = relationship(back_populates="life_event", cascade="all, delete-orphan")


class MetricObservation(Base):
    __tablename__ = "metric_observations"
    __table_args__ = (CheckConstraint("(CASE WHEN value_number IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN value_boolean IS NOT NULL THEN 1 ELSE 0 END) = 1", name="ck_observation_one_value"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    life_event_id: Mapped[int] = mapped_column(ForeignKey("life_events.id", ondelete="CASCADE"))
    metric_definition_id: Mapped[int] = mapped_column(ForeignKey("metric_definitions.id", ondelete="RESTRICT"))
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    value_origin: Mapped[str] = mapped_column(String(16), server_default="explicit")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    life_event: Mapped[LifeEvent] = relationship(back_populates="observations")
    metric_definition: Mapped[MetricDefinition] = relationship(back_populates="observations")
