"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.request_id import request_id_middleware
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.common import ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Factory Sherlock API",
        version="0.1.0",
        description=(
            "Smart manufacturing simulation, production intelligence, and quality "
            "investigation platform backed by MySQL."
        ),
        docs_url=None if settings.app_env == "production" else "/api/docs",
        openapi_url=None if settings.app_env == "production" else "/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.middleware("http")(request_id_middleware)
    register_error_handlers(app)
    app.include_router(
        api_router,
        responses={
            422: {"model": ErrorResponse, "description": "Validation failed"},
            500: {"model": ErrorResponse, "description": "Unexpected server error"},
            503: {"model": ErrorResponse, "description": "Database not reachable"},
        },
    )
    return app


app = create_app()
