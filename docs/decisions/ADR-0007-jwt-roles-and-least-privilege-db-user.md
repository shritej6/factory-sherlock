# ADR-0007: JWT authentication with four roles and a least-privilege database user

## Status

Accepted. Recorded 2026-11-03. Implemented in `backend/app/core/security.py`, `backend/app/api/deps.py`, `backend/app/services/auth_service.py`, and `scripts/setup/init_databases.sh`.

## Context

The API changes manufacturing state (orders, batches, quarantines, investigations) and must distinguish who may read from who may write. The frontend is a single-page application served separately from the API, so a stateless token scheme fits better than server-side sessions. At the database level, the application should not be able to damage anything outside its own schemas, and secrets must not be committed.

## Decision

Application layer:

- Users are rows in `users` with a bcrypt `password_hash`, an `is_active` flag, and a `role` ENUM of `ADMIN`, `ENGINEER`, `OPERATOR`, `VIEWER`. bcrypt is called directly (not through passlib) because passlib has not kept up with bcrypt 4.x.
- `POST /api/v1/auth/login` verifies the password and returns an HS256 JWT with `sub` (user id), `role`, `iat`, and `exp` (`JWT_ACCESS_TOKEN_MINUTES`, default 120). The same error message is returned for unknown users and wrong passwords.
- `get_current_user` decodes the bearer token, then loads the user row. The role claim is informational; the row decides whether the account is active and which role applies, so deactivating a user takes effect on the next request without token revocation lists.
- Authorisation is declarative per route through `Annotated` dependencies: `CurrentUser` (any role) for reads, `Operator` (admin, engineer, operator) for shop-floor writes such as batch creation, inspections, and status changes, `Engineer` (admin, engineer) for catalog creation, order creation, quarantines, investigations, and simulation runs. ADMIN is a member of every write set; no route is admin-only, so no separate admin dependency exists.
- `JWT_SECRET_KEY` comes from the environment; `create_access_token` raises if it is missing. Secrets are declared with `repr=False` in `Settings`.
- Demo accounts (`admin`, `engineer`, `operator`, `viewer`) are created by the seed command with `SEED_DEMO_PASSWORD`, which must be set; nothing is hard-coded.

Database layer:

- `scripts/setup/init_databases.sh` creates `${MYSQL_DATABASE}` and `${MYSQL_DATABASE}_test` and a user `${MYSQL_USER}` (`sherlock_app` by default) with `SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES` on those two schemas only. The user cannot create users, grant privileges, or touch other schemas.
- The application and Alembic connect as this user. Root is used only by setup scripts (and, in the unexecuted docker-compose path, the container entrypoint) to create the databases, and the local `mysqld` binds to loopback.
- `.env` is ignored by Git; `.env.example` ships placeholders only.

## Consequences

Positive:

- Stateless authentication suits the SPA and `curl`; no session store is needed.
- Role checks are visible in route signatures and in the OpenAPI document, and 403 responses list the required roles in `details`.
- Database compromise through the application is bounded to the two project schemas; migrations still work because DDL on those schemas is granted.
- The test database is created and granted by the same script, so tests run with the same privileges as the application.

Negative or accepted costs:

- Tokens cannot be revoked before expiry; deactivating the user row is the mitigation, and the default lifetime is two hours.
- There is no refresh token or password change endpoint; re-login is required after expiry. User management is done through the seed command, not the API.
- The application user holds DDL rights (`CREATE, ALTER, DROP`) so Alembic can run; a stricter split (migration user versus runtime user) is possible but was not needed for a single-developer deployment.
- `POST /api/v1/analytics/alerts/{id}/acknowledge` requires the `Operator` dependency (OPERATOR, ENGINEER, ADMIN); a `VIEWER` receives 403. `tests/api/test_analytics_api.py::test_alerts_can_be_acknowledged_once_by_operators` covers this.
- No route is admin-only, so ADMIN currently has the same permissions as ENGINEER.

## Alternatives considered

- Server-side sessions with cookies. Rejected: cross-origin SPA setup with cookies needs CSRF handling and a session store; bearer tokens are simpler here.
- OAuth2 password flow with FastAPI's `OAuth2PasswordBearer`. Functionally similar; a plain JSON login body with `HTTPBearer` was chosen so the frontend can send JSON rather than form encoding.
- A single application role or no authorisation. Rejected: a viewer must not be able to quarantine batches or run simulations.
- Connecting as root locally for convenience. Rejected: the point of the least-privilege user is that development and demonstration run the same way the application would in any other environment.
