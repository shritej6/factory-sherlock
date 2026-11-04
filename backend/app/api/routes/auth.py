from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(session: DbSession, body: LoginRequest) -> TokenResponse:
    _, token = auth_service.authenticate(session, username=body.username, password=body.password)
    return TokenResponse(
        access_token=token, expires_in_minutes=get_settings().jwt_access_token_minutes
    )


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
