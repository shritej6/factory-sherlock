"""FastAPI dependencies: database session, current user, and role guards."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.models import User, UserRole
from app.repositories.pagination import PageParams
from app.services import auth_service

# scope="function" closes the session (and so commits) before the response is
# sent, so a failed commit becomes an error response instead of a silent 200.
DbSession = Annotated[Session, Depends(get_db_session, scope="function")]
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentication required")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Access token is invalid") from exc
    # The role in the token is informational; the database row decides.
    return auth_service.get_active_user(session, user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]

# Role hierarchy used by every mutating endpoint. Reads require any
# authenticated user; writes require the role listed on the route. ADMIN is
# included in every write set; no route is admin-only today.
READ_ROLES = frozenset(UserRole)
OPERATOR_ROLES = frozenset({UserRole.ADMIN, UserRole.ENGINEER, UserRole.OPERATOR})
ENGINEER_ROLES = frozenset({UserRole.ADMIN, UserRole.ENGINEER})


def require_roles(allowed: frozenset[UserRole]) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AuthorizationError(
                f"Role {user.role} is not permitted to perform this action",
                details={"required": sorted(str(r) for r in allowed)},
            )
        return user

    return dependency


Operator = Annotated[User, Depends(require_roles(OPERATOR_ROLES))]
Engineer = Annotated[User, Depends(require_roles(ENGINEER_ROLES))]


def get_page_params(
    limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


Paging = Annotated[PageParams, Depends(get_page_params)]
