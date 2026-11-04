from typing import Any

from fastapi import APIRouter

from app.api.routes import (
    analytics,
    auth,
    catalog,
    health,
    investigations,
    production,
    quality,
    simulation,
    traceability,
)
from app.schemas.common import ErrorResponse

PROTECTED_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Role not permitted"},
    404: {"model": ErrorResponse, "description": "Entity not found"},
    409: {"model": ErrorResponse, "description": "Conflict with existing data"},
}

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router, responses={401: PROTECTED_RESPONSES[401]})
for module in (
    catalog,
    production,
    quality,
    investigations,
    traceability,
    analytics,
    simulation,
):
    api_router.include_router(module.router, responses=PROTECTED_RESPONSES)
