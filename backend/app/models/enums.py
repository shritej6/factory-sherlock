"""Enumerations shared by the ORM models, the schemas, and the state machines.

They are stored in MySQL as ENUM columns so the database rejects unknown
values even when rows are inserted outside the application.
"""

import enum


class UserRole(enum.StrEnum):
    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class MachineStatus(enum.StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WARNING = "WARNING"
    STOPPED = "STOPPED"
    FAULT = "FAULT"


class MachineEventType(enum.StrEnum):
    STATE_CHANGE = "STATE_CHANGE"
    TOOL_WEAR = "TOOL_WEAR"
    CALIBRATION_DRIFT = "CALIBRATION_DRIFT"
    MATERIAL_ISSUE = "MATERIAL_ISSUE"
    DOWNTIME = "DOWNTIME"
    MAINTENANCE = "MAINTENANCE"


class Severity(enum.StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class OrderStatus(enum.StrEnum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BatchStatus(enum.StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    QUARANTINED = "QUARANTINED"


class MaterialLotStatus(enum.StrEnum):
    AVAILABLE = "AVAILABLE"
    QUARANTINED = "QUARANTINED"
    CONSUMED = "CONSUMED"


class InspectionResult(enum.StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class AlertType(enum.StrEnum):
    HIGH_DEFECT_RATE = "HIGH_DEFECT_RATE"
    MACHINE_FAULT = "MACHINE_FAULT"
    MATERIAL_QUARANTINE = "MATERIAL_QUARANTINE"
    ORDER_OVERDUE = "ORDER_OVERDUE"


class InvestigationStatus(enum.StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    CLOSED = "CLOSED"
