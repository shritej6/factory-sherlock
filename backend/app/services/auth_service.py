import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, hash_password, verify_password
from app.core.throttle import account_key, get_login_throttle
from app.models import User

logger = logging.getLogger(__name__)


# Hash compared against when the username does not exist, so the request takes
# as long as a real password check and timing does not reveal valid usernames.
_UNKNOWN_USER_HASH = hash_password("unknown-user-placeholder")


def authenticate(
    session: Session, *, username: str, password: str, client_ip: str | None
) -> tuple[User, str]:
    user = session.scalar(select(User).where(User.username == username))
    # The throttle runs after the cheap row lookup (so the key is the user id
    # and spelling variants share one bucket) but before the bcrypt check, so a
    # throttled attacker costs the server no hashing work. Known and unknown
    # names are throttled alike, so the 429 does not reveal which exist.
    throttle = get_login_throttle()
    account = account_key(username, user.id if user is not None else None)
    throttle.check(account=account)
    # Same error for unknown user and wrong password so the API does not reveal
    # which usernames exist.
    stored_hash = user.password_hash if user is not None else _UNKNOWN_USER_HASH
    password_ok = verify_password(password, stored_hash)
    if user is None or not user.is_active or not password_ok:
        throttle.record_failure(account=account, client_ip=client_ip)
        logger.info("login rejected", extra={"operation": "login"})
        raise AuthenticationError("Invalid username or password")
    throttle.record_success(account=account)
    token = create_access_token(user_id=user.id, role=str(user.role))
    logger.info("login accepted", extra={"operation": "login", "user_id": user.id})
    return user, token


def get_active_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User account is not active")
    return user
