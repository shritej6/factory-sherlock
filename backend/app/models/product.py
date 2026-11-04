from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_mixins import TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    specifications: Mapped[list["ProductSpecification"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductSpecification.id"
    )


class ProductSpecification(Base):
    """One measurable characteristic of a product with its target and tolerance.

    A unit passes a specification when ``abs(measured - target) <= tolerance``.
    Keeping specifications in their own table (rather than columns on products)
    lets a product carry any number of characteristics without schema changes.
    """

    __tablename__ = "product_specifications"
    __table_args__ = (
        UniqueConstraint("product_id", "characteristic", name="uq_spec_product_characteristic"),
        CheckConstraint("tolerance > 0", name="ck_spec_tolerance_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    characteristic: Mapped[str] = mapped_column(String(50), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    tolerance: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="mm")

    product: Mapped[Product] = relationship(back_populates="specifications")
