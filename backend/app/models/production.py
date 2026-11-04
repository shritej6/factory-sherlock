from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_mixins import TimestampMixin
from app.models.enums import BatchStatus, OrderStatus
from app.models.machine import Machine
from app.models.product import Product

if TYPE_CHECKING:
    from app.models.material import BatchMaterial
    from app.models.quality import Inspection


class ProductionOrder(TimestampMixin, Base):
    """A request to manufacture a quantity of one product.

    Database-level rules: quantities are non-negative, completed never exceeds
    planned, and an order always references a real product. Which transitions
    are legal between statuses is enforced in ``app.domain.state_machines``.
    """

    __tablename__ = "production_orders"
    __table_args__ = (
        CheckConstraint("quantity_planned > 0", name="ck_order_quantity_planned_positive"),
        CheckConstraint("quantity_completed >= 0", name="ck_order_quantity_completed_non_negative"),
        CheckConstraint(
            "quantity_completed <= quantity_planned", name="ck_order_completed_within_planned"
        ),
        Index("ix_production_orders_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    machine_id: Mapped[int | None] = mapped_column(ForeignKey("machines.id", ondelete="SET NULL"))
    quantity_planned: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.PLANNED
    )
    due_date: Mapped[date | None] = mapped_column(Date)

    product: Mapped[Product] = relationship()
    machine: Mapped[Machine | None] = relationship()
    batches: Mapped[list["ProductionBatch"]] = relationship(
        back_populates="order", order_by="ProductionBatch.started_at"
    )


class ProductionBatch(Base):
    """A run of units produced for one order on one machine.

    The batch is the unit of traceability: materials attach to batches and
    quarantine decisions are made per batch. Units, material links, and
    investigation links reference the batch with ON DELETE RESTRICT, so a batch
    with history cannot be deleted by accident.
    """

    __tablename__ = "production_batches"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_batch_quantity_positive"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_batch_completed_after_start",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_batch_completed_has_time",
        ),
        CheckConstraint(
            "(status = 'QUARANTINED') = (quarantine_reason IS NOT NULL)",
            name="ck_batch_quarantine_reason",
        ),
        Index("ix_production_batches_machine_time", "machine_id", "started_at"),
        Index("ix_production_batches_order", "production_order_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    production_order_id: Mapped[int] = mapped_column(
        ForeignKey("production_orders.id", ondelete="RESTRICT"), nullable=False
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batch_status"), nullable=False, default=BatchStatus.IN_PROGRESS
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    quarantine_reason: Mapped[str | None] = mapped_column(String(255))

    order: Mapped[ProductionOrder] = relationship(back_populates="batches")
    machine: Mapped[Machine] = relationship()
    units: Mapped[list["ProductionUnit"]] = relationship(
        back_populates="batch", order_by="ProductionUnit.sequence_in_batch"
    )
    material_links: Mapped[list["BatchMaterial"]] = relationship(back_populates="batch")


class ProductionUnit(Base):
    """One manufactured component with a serial number.

    Units exist as rows so that backward traceability can start from a single
    serial number and so each unit can carry one inspection per specification.
    """

    __tablename__ = "production_units"
    __table_args__ = (
        UniqueConstraint("batch_id", "sequence_in_batch", name="uq_unit_batch_sequence"),
        CheckConstraint("sequence_in_batch > 0", name="ck_unit_sequence_positive"),
        Index("ix_production_units_produced_at", "produced_at", "batch_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("production_batches.id", ondelete="RESTRICT"), nullable=False
    )
    serial_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    sequence_in_batch: Mapped[int] = mapped_column(Integer, nullable=False)
    produced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    batch: Mapped[ProductionBatch] = relationship(back_populates="units")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="unit")
