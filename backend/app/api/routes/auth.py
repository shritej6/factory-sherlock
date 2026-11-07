from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.schemas.common import ErrorResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    # The direct peer address is used as is. X-Forwarded-For is ignored because
    # any client can set it; honouring it would need a trusted proxy list.
    return request.client.host if request.client is not None else "unknown"


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={429: {"model": ErrorResponse, "description": "Too many failed login attempts"}},
)
def login(request: Request, session: DbSession, body: LoginRequest) -> TokenResponse:
    _, token = auth_service.authenticate(
        session, username=body.username, password=body.password, client_ip=_client_ip(request)
    )
    return TokenResponse(
        access_token=token, expires_in_minutes=get_settings().jwt_access_token_minutes
    )


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
