"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.models.enums import (
    AlertType,
    BatchStatus,
    InspectionResult,
    InvestigationStatus,
    MachineEventType,
    MachineStatus,
    MaterialLotStatus,
    OrderStatus,
    Severity,
    UserRole,
)
from app.models.investigation import Alert, Investigation, InvestigationBatch, InvestigationEvidence
from app.models.machine import Machine, MachineEvent
from app.models.material import BatchMaterial, MaterialLot
from app.models.product import Product, ProductSpecification
from app.models.production import ProductionBatch, ProductionOrder, ProductionUnit
from app.models.quality import DefectType, Inspection, InspectionDefect
from app.models.user import User

__all__ = [
    "Alert",
    "AlertType",
    "BatchMaterial",
    "BatchStatus",
    "DefectType",
    "Inspection",
    "InspectionDefect",
    "InspectionResult",
    "Investigation",
    "InvestigationBatch",
    "InvestigationEvidence",
    "InvestigationStatus",
    "Machine",
    "MachineEvent",
    "MachineEventType",
    "MachineStatus",
    "MaterialLot",
    "MaterialLotStatus",
    "OrderStatus",
    "Product",
    "ProductSpecification",
    "ProductionBatch",
    "ProductionOrder",
    "ProductionUnit",
    "Severity",
    "User",
    "UserRole",
]
