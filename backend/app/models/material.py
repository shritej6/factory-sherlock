from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MaterialLotStatus

if TYPE_CHECKING:
    from app.models.production import ProductionBatch


class MaterialLot(Base):
    __tablename__ = "material_lots"
    __table_args__ = (
        CheckConstraint("quantity_received >= 0", name="ck_material_lot_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lot_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    material_name: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[MaterialLotStatus] = mapped_column(
        Enum(MaterialLotStatus, name="material_lot_status"),
        nullable=False,
        default=MaterialLotStatus.AVAILABLE,
    )
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    batch_links: Mapped[list["BatchMaterial"]] = relationship(back_populates="material_lot")


class BatchMaterial(Base):
    """Junction table: which material lots went into which production batch.

    This is the many-to-many relationship that makes traceability possible.
    A batch may consume several lots and a lot may feed several batches.
    """

    __tablename__ = "batch_materials"
    __table_args__ = (
        CheckConstraint("quantity_used > 0", name="ck_batch_material_quantity_positive"),
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("production_batches.id", ondelete="RESTRICT"), primary_key=True
    )
    material_lot_id: Mapped[int] = mapped_column(
        ForeignKey("material_lots.id", ondelete="RESTRICT"), primary_key=True
    )
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    material_lot: Mapped[MaterialLot] = relationship(back_populates="batch_links")
    batch: Mapped["ProductionBatch"] = relationship(back_populates="material_links")
