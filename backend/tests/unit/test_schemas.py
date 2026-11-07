"""Pydantic input schemas: the first enforcement layer for the numeric and text rules.

Each case pairs a value just inside the limit (accepted) with one just outside
(rejected), so the boundary of every rule in business-rules.md that names a
schema is pinned.
"""

from datetime import datetime
from typing import Any

import pytest
from app.schemas.catalog import (
    MachineCreate,
    MachineStatusChange,
    MaterialLotCreate,
    ProductCreate,
    SpecificationCreate,
)
from app.schemas.investigation import InvestigationCreate, InvestigationStatusChange
from app.schemas.production import (
    BatchMaterialInput,
    ProductionBatchCreate,
    ProductionOrderCreate,
    QuarantineRequest,
)
from app.schemas.quality import InspectionCreate
from app.schemas.simulation import FaultScenario, SimulationRequest
from pydantic import BaseModel, ValidationError

START = datetime(2026, 11, 2, 6, 0)
LOT = {"material_name": "Steel", "supplier": "Northline", "received_at": START}
ORDER = {"product_id": 1, "quantity_planned": 10}
BATCH = {"production_order_id": 1, "materials": [{"material_lot_id": 1, "quantity_used": "1.00"}]}
INSPECTION = {"unit_id": 1, "specification_id": 1}
WINDOW = {"window_start": START, "window_end": datetime(2026, 11, 3)}


def accepts(model: type[BaseModel], **fields: Any) -> None:
    model.model_validate(fields)


def rejects(model: type[BaseModel], **fields: Any) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(fields)


@pytest.mark.parametrize("code", ["AB", "A1", "0-ABC_DEF", "X" * 30])
def test_codes_matching_the_pattern_are_accepted(code: str) -> None:
    accepts(ProductCreate, code=code, name="n")
    accepts(MachineCreate, code=code, name="n")
    accepts(MaterialLotCreate, lot_number=code, quantity_received="1.00", **LOT)
    accepts(ProductionOrderCreate, order_number=code, **ORDER)


@pytest.mark.parametrize("code", ["A", "ab", "-AB", "X" * 31, "A B", "A.B", ""])
def test_codes_outside_the_pattern_are_rejected(code: str) -> None:
    rejects(ProductCreate, code=code, name="n")
    rejects(MachineCreate, code=code, name="n")
    rejects(MaterialLotCreate, lot_number=code, quantity_received="1.00", **LOT)
    rejects(ProductionOrderCreate, order_number=code, **ORDER)


def test_specification_target_and_tolerance_are_positive_with_three_decimals() -> None:
    accepts(SpecificationCreate, characteristic="d", target_value="0.001", tolerance="0.001")
    rejects(SpecificationCreate, characteristic="d", target_value="1", tolerance="0")
    rejects(SpecificationCreate, characteristic="d", target_value="0", tolerance="0.1")
    rejects(SpecificationCreate, characteristic="d", target_value="1", tolerance="0.0001")
    rejects(SpecificationCreate, characteristic="d", target_value="1.0001", tolerance="0.1")


def test_material_lot_quantity_is_non_negative_with_two_decimals() -> None:
    accepts(MaterialLotCreate, lot_number="L1", quantity_received="0", **LOT)
    accepts(MaterialLotCreate, lot_number="L1", quantity_received="0.01", **LOT)
    rejects(MaterialLotCreate, lot_number="L1", quantity_received="-0.01", **LOT)
    rejects(MaterialLotCreate, lot_number="L1", quantity_received="1.001", **LOT)


def test_machine_status_change_reason_is_one_to_255_characters() -> None:
    accepts(MachineStatusChange, status="RUNNING", reason="x")
    accepts(MachineStatusChange, status="RUNNING", reason="x" * 255)
    rejects(MachineStatusChange, status="RUNNING", reason="")
    rejects(MachineStatusChange, status="RUNNING", reason="x" * 256)
    rejects(MachineStatusChange, status="EXPLODED", reason="x")


def test_order_quantity_is_between_one_and_one_hundred_thousand() -> None:
    accepts(ProductionOrderCreate, order_number="PO-1", product_id=1, quantity_planned=1)
    accepts(ProductionOrderCreate, order_number="PO-1", product_id=1, quantity_planned=100_000)
    rejects(ProductionOrderCreate, order_number="PO-1", product_id=1, quantity_planned=0)
    rejects(ProductionOrderCreate, order_number="PO-1", product_id=1, quantity_planned=100_001)
    rejects(ProductionOrderCreate, order_number="PO-1", product_id=0, quantity_planned=1)
    rejects(ProductionOrderCreate, order_number="PO-1", priority=1, **ORDER)


def test_batch_quantity_is_between_one_and_ten_thousand() -> None:
    accepts(ProductionBatchCreate, quantity=1, **BATCH)
    accepts(ProductionBatchCreate, quantity=10_000, **BATCH)
    rejects(ProductionBatchCreate, quantity=0, **BATCH)
    rejects(ProductionBatchCreate, quantity=10_001, **BATCH)


def test_batch_materials_need_one_entry_with_positive_two_decimal_quantities() -> None:
    rejects(ProductionBatchCreate, production_order_id=1, quantity=1, materials=[])
    too_many = [{"material_lot_id": i, "quantity_used": "1"} for i in range(1, 52)]
    rejects(ProductionBatchCreate, production_order_id=1, quantity=1, materials=too_many)
    accepts(BatchMaterialInput, material_lot_id=1, quantity_used="0.01")
    rejects(BatchMaterialInput, material_lot_id=1, quantity_used="0")
    rejects(BatchMaterialInput, material_lot_id=1, quantity_used="0.001")


def test_measured_values_have_at_most_three_decimals() -> None:
    accepts(InspectionCreate, measured_value="20.001", **INSPECTION)
    rejects(InspectionCreate, measured_value="20.0001", **INSPECTION)
    rejects(InspectionCreate, measured_value="20", result="PASS", **INSPECTION)
    codes = [f"C{i}" for i in range(11)]
    rejects(InspectionCreate, measured_value="20", defect_type_codes=codes, **INSPECTION)


def test_quarantine_reason_is_five_to_255_characters() -> None:
    accepts(QuarantineRequest, reason="x" * 5)
    accepts(QuarantineRequest, reason="x" * 255)
    rejects(QuarantineRequest, reason="x" * 4)
    rejects(QuarantineRequest, reason="x" * 256)


def test_investigation_title_and_window_boundaries() -> None:
    accepts(InvestigationCreate, title="abc", **WINDOW)
    accepts(InvestigationCreate, title="x" * 150, **WINDOW)
    rejects(InvestigationCreate, title="ab", **WINDOW)
    rejects(InvestigationCreate, title="x" * 151, **WINDOW)
    rejects(InvestigationCreate, title="abc", window_start=START, window_end=START)
    accepts(
        InvestigationCreate,
        title="abc",
        window_start=START,
        window_end=datetime(2026, 11, 2, 6, 0, 1),
    )
    with pytest.raises(ValidationError, match="window_end must be after window_start"):
        InvestigationCreate(title="abc", window_start=WINDOW["window_end"], window_end=START)


def test_investigation_conclusion_is_at_most_4000_characters() -> None:
    accepts(InvestigationStatusChange, status="CLOSED", conclusion="x" * 4000)
    rejects(InvestigationStatusChange, status="CLOSED", conclusion="x" * 4001)
    rejects(InvestigationStatusChange, status="ARCHIVED")


def test_simulation_request_ranges() -> None:
    accepts(SimulationRequest, seed=0, start_time=START)
    rejects(SimulationRequest, seed=-1, start_time=START)
    accepts(SimulationRequest, start_time=START, batches_per_machine=200)
    rejects(SimulationRequest, start_time=START, batches_per_machine=201)
    accepts(SimulationRequest, start_time=START, units_per_batch=500)
    rejects(SimulationRequest, start_time=START, units_per_batch=501)
    accepts(SimulationRequest, start_time=START, minutes_per_batch=600)
    rejects(SimulationRequest, start_time=START, minutes_per_batch=601)
    rejects(SimulationRequest, start_time=START, speed=2)


def test_fault_scenarios_need_a_known_kind_and_a_non_negative_index() -> None:
    accepts(FaultScenario, machine_code="CNC-01", fault="TOOL_WEAR", start_batch_index=0)
    rejects(FaultScenario, machine_code="CNC-01", fault="TOOL_WEAR", start_batch_index=-1)
    rejects(FaultScenario, machine_code="CNC-01", fault="GREMLINS", start_batch_index=0)
    rejects(FaultScenario, machine_code="cnc-01", fault="TOOL_WEAR", start_batch_index=0)
    last = {"machine_code": "CNC-01", "fault": "TOOL_WEAR", "start_batch_index": 3}
    accepts(SimulationRequest, start_time=START, batches_per_machine=4, faults=[last])
    rejects(SimulationRequest, start_time=START, batches_per_machine=3, faults=[last])
