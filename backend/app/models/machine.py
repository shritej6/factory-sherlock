from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_mixins import TimestampMixin
from app.models.enums import MachineEventType, MachineStatus, Severity


class Machine(TimestampMixin, Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus, name="machine_status"), nullable=False, default=MachineStatus.IDLE
    )

    events: Mapped[list["MachineEvent"]] = relationship(
        back_populates="machine", order_by="MachineEvent.occurred_at"
    )


class MachineEvent(Base):
    """Append-only log of what happened to a machine and when.

    Both state changes and simulated faults land here so the investigation
    engine can ask "what happened on this machine shortly before quality
    deteriorated" with a single range query on (machine_id, occurred_at).
    """

    __tablename__ = "machine_events"
    __table_args__ = (
        Index("ix_machine_events_machine_time", "machine_id", "occurred_at"),
        CheckConstraint(
            "(event_type = 'STATE_CHANGE') = (new_state IS NOT NULL)", name="ck_event_state_pair"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[MachineEventType] = mapped_column(
        Enum(MachineEventType, name="machine_event_type"), nullable=False
    )
    previous_state: Mapped[MachineStatus | None] = mapped_column(
        Enum(MachineStatus, name="machine_status")
    )
    new_state: Mapped[MachineStatus | None] = mapped_column(
        Enum(MachineStatus, name="machine_status")
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False, default=Severity.INFO
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    machine: Mapped[Machine] = relationship(back_populates="events")
