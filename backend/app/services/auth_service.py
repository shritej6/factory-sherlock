import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User

logger = logging.getLogger(__name__)


# Hash compared against when the username does not exist, so the request takes
# as long as a real password check and timing does not reveal valid usernames.
_UNKNOWN_USER_HASH = hash_password("unknown-user-placeholder")


def authenticate(session: Session, *, username: str, password: str) -> tuple[User, str]:
    user = session.scalar(select(User).where(User.username == username))
    # Same error for unknown user and wrong password so the API does not reveal
    # which usernames exist.
    stored_hash = user.password_hash if user is not None else _UNKNOWN_USER_HASH
    password_ok = verify_password(password, stored_hash)
    if user is None or not user.is_active or not password_ok:
        logger.info("login rejected", extra={"operation": "login"})
        raise AuthenticationError("Invalid username or password")
    token = create_access_token(user_id=user.id, role=str(user.role))
    logger.info("login accepted", extra={"operation": "login", "user_id": user.id})
    return user, token


def get_active_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User account is not active")
    return user
