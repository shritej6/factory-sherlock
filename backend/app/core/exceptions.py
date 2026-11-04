"""Typed application errors.

Services raise these instead of HTTPException so the domain layer stays free
of HTTP concerns. ``app.api.errors`` maps each type to a status code and a safe
response body that never leaks SQL or stack traces to clients.
"""


class AppError(Exception):
    """Base class for errors that are safe to show to API clients."""

    status_code = 400

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    """Duplicate keys and other uniqueness violations."""

    status_code = 409


class ValidationError(AppError):
    """Business rule violations that are not pure schema validation."""

    status_code = 422


class InvalidTransitionError(ValidationError):
    """Raised when a state machine rejects a transition."""


class AuthenticationError(AppError):
    status_code = 401


class AuthorizationError(AppError):
    status_code = 403
