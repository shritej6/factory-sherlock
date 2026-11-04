from fastapi import APIRouter, status

from app.api.deps import DbSession, Engineer
from app.schemas.simulation import SimulationRequest, SimulationResult
from app.services import simulation_service

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/runs", response_model=SimulationResult, status_code=status.HTTP_201_CREATED)
def run_simulation(session: DbSession, _: Engineer, body: SimulationRequest) -> SimulationResult:
    """Generate a deterministic factory history and persist it in one transaction."""
    return simulation_service.run_simulation(session, body)
