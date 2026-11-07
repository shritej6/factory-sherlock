from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import InspectionResult
from app.models.product import ProductSpecification

if TYPE_CHECKING:
    from app.models.production import ProductionUnit


class DefectType(Base):
    __tablename__ = "defect_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Inspection(Base):
    """A measurement of one unit against one specification.

    The pass/fail result is stored rather than recomputed so historical results
    stay stable even if a specification tolerance is later changed.
    """

    __tablename__ = "inspections"
    __table_args__ = (
        UniqueConstraint("unit_id", "specification_id", name="uq_inspection_unit_spec"),
        Index("ix_inspections_time_result", "inspected_at", "result"),
        Index("ix_inspections_time_id", "inspected_at", "id"),
        Index("ix_inspections_spec_time", "specification_id", "inspected_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("production_units.id", ondelete="RESTRICT"), nullable=False
    )
    specification_id: Mapped[int] = mapped_column(
        ForeignKey("product_specifications.id", ondelete="RESTRICT"), nullable=False
    )
    measured_value: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    result: Mapped[InspectionResult] = mapped_column(
        Enum(InspectionResult, name="inspection_result"), nullable=False
    )
    inspected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    unit: Mapped["ProductionUnit"] = relationship(back_populates="inspections")
    specification: Mapped[ProductSpecification] = relationship()
    defect_links: Mapped[list["InspectionDefect"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )


class InspectionDefect(Base):
    """Junction table: defects found during an inspection (many-to-many).

    A failed inspection can carry more than one defect classification, and a
    defect type appears across many inspections.
    """

    __tablename__ = "inspection_defects"

    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), primary_key=True
    )
    defect_type_id: Mapped[int] = mapped_column(
        ForeignKey("defect_types.id", ondelete="RESTRICT"), primary_key=True
    )

    inspection: Mapped[Inspection] = relationship(back_populates="defect_links")
    defect_type: Mapped[DefectType] = relationship()
