from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalog import CODE_PATTERN
from app.simulation.config import FaultKind


class FaultScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    machine_code: str = Field(pattern=CODE_PATTERN)
    fault: FaultKind
    start_batch_index: int = Field(
        ge=0, description="Batch index (per machine) at which the fault begins"
    )


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int = Field(default=42, ge=0)
    start_time: datetime
    batches_per_machine: int = Field(default=12, ge=1, le=200)
    units_per_batch: int = Field(default=20, ge=1, le=500)
    minutes_per_batch: int = Field(default=30, ge=1, le=600)
    faults: list[FaultScenario] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def _faults_are_distinct_and_in_range(self) -> "SimulationRequest":
        seen: set[tuple[str, int]] = set()
        for fault in self.faults:
            key = (fault.machine_code, fault.start_batch_index)
            if key in seen:
                raise ValueError(f"Duplicate fault for {key[0]} at batch index {key[1]}")
            seen.add(key)
            if fault.start_batch_index >= self.batches_per_machine:
                raise ValueError(
                    f"start_batch_index {fault.start_batch_index} is beyond the last batch "
                    f"({self.batches_per_machine - 1}) for {fault.machine_code}"
                )
        return self


class SimulationResult(BaseModel):
    seed: int
    orders_created: int
    batches_created: int
    units_created: int
    inspections_created: int
    failed_inspections: int
    events_created: int
    alerts_created: int
