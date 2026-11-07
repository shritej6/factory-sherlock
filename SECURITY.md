# Security Policy

Factory Sherlock is a university database systems project. It is built with standard security controls for a web application backed by MySQL, but it has not been penetration tested and is not hardened for production use. Do not deploy it with real manufacturing data or expose it to the public internet without the additional work listed under known limitations.

## Supported versions

The project has no tagged releases yet. Only the `main` branch is maintained. Reports against any other branch or against a fork will not be triaged.

| Branch | Supported |
| ------ | --------- |
| `main` | Yes       |
| other  | No        |

## Reporting a vulnerability

Do not open a public GitHub issue for a security problem. Blank issues are disabled and the issue templates are for functional bugs only.

Send a report to the maintainer at: `<security contact email to be filled in by the repository owner>`

If the repository is hosted on GitHub and private vulnerability reporting is enabled in the repository settings, the "Report a vulnerability" button on the Security tab may be used instead.

Include in the report:

- A description of the issue and the component affected (endpoint, query file, migration, script, or frontend module).
- Steps to reproduce, including the request or command used.
- The impact you believe it has (for example, reading another role's data, bypassing a role check, or executing arbitrary SQL).
- The commit or branch you tested against.

You can expect an acknowledgement within 7 days. Because this is a solo project, fix timelines depend on severity and on the maintainer's availability; the acknowledgement will state an estimated timeline.

## Security controls implemented

The following controls exist in the current codebase. File references are given so the claims can be checked.

| Control                                   | Where                                                                                                                                          |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Password hashing with bcrypt              | `backend/app/core/security.py` (`hash_password`, `verify_password`)                                                                            |
| JWT access tokens with expiry             | `backend/app/core/security.py`; lifetime set by `JWT_ACCESS_TOKEN_MINUTES`, default 120 minutes; HS256 signed with `JWT_SECRET_KEY`           |
| Database is the authority on identity     | `backend/app/api/deps.py` reloads the user row on every request; the role in the token is not trusted on its own                              |
| Role checks on every mutating endpoint    | `Operator` and `Engineer` dependencies in `backend/app/api/deps.py` (ADMIN is in both sets); routes in `backend/app/api/routes/` declare the required role. Alert acknowledgement requires `Operator`, so a viewer receives 403 |
| Parameterized SQL                         | SQL files under `database/queries/` are executed through `backend/app/repositories/query_runner.py` with SQLAlchemy `text()` and named binds   |
| Input validation                          | Pydantic request schemas in `backend/app/schemas/` with `extra="forbid"` so unknown fields are rejected                                        |
| Least-privilege MySQL user                | `scripts/setup/init_databases.sh` creates `sherlock_app` with DML and migration DDL on the two project schemas only; the API never runs as root |
| Login throttling                          | `backend/app/core/throttle.py`; after `LOGIN_MAX_FAILURES` (default 5) failed logins for one account within `LOGIN_WINDOW_SECONDS` (default 900) the endpoint returns 429 with a `Retry-After` header; the same count per client address turns further failed attempts from that address into 429. See "Login throttling" below |
| Request body caps before authentication | `backend/app/api/body_limit.py`: a pure ASGI middleware answers 413 `payload_too_large` (with `limit_bytes` and a `request_id`) when `Content-Length` exceeds the cap or a chunked body passes it while streaming, without reading or spooling the body. Caps: 1 MiB + 64 KiB for `POST /api/v1/inspections/import`, 64 KiB for every other route |
| Safe error responses                      | `backend/app/api/errors.py` maps exceptions to JSON without SQL text, stack traces, or driver messages; database and unexpected errors carry a `request_id` in `details`            |
| Structured logs without secrets           | `backend/app/core/logging.py` emits JSON lines; secret settings are declared with `repr=False`; request bodies are not logged                   |
| Secrets kept out of Git                   | `.env` and `.env.*` are ignored in `.gitignore`; only `.env.example` with placeholder values is committed                                       |
| Seed command refuses to run without a password | `backend/app/seed.py` requires `SEED_DEMO_PASSWORD` to be set                                                                             |

## Login throttling

`POST /api/v1/auth/login` is the only endpoint that accepts a password, so it is the only endpoint with a request limit. The implementation is `LoginThrottle` in `backend/app/core/throttle.py`, called from `backend/app/services/auth_service.py::authenticate`. The module docstring describes the design; this section summarises it.

How it works:

- Failures are counted under two kinds of key with different roles: the account key and the client address.
- The account key is the user id when the username matches a row, and otherwise the username normalised with NFKD, combining marks removed, and casefolded. `admin`, `ADMIN`, and `ädmin` therefore count against the same bucket, for real accounts and for unknown names alike, and varying the spelling does not buy extra attempts.
- Before the password is checked, the account bucket is read and a pending slot is reserved under a lock. If the account already holds `LOGIN_MAX_FAILURES` failures or reservations (default 5) inside the last `LOGIN_WINDOW_SECONDS` (default 900, fifteen minutes), the request is rejected with HTTP 429 and no password hash is computed. Reserving the slot before verification means concurrent requests for one account cannot all pass the check at once and exceed the limit. The window slides: the lock ends when the oldest failure is older than the window, not at a fixed time.
- The client address is checked only after a verification has failed. The failure is recorded under the address, and when the address already held `LOGIN_MAX_FAILURES` failures inside the window the attempt is answered with 429 instead of 401. A correct password is never rejected because of the address alone. This matters in development, where the Vite proxy makes every browser arrive from `127.0.0.1`: five wrong passwords from one person cannot lock the other demo accounts out. The address counter still slows a guessing run that walks through many usernames, and each name it tries is subject to the per-account lockout.
- When the server does not know the peer address (`request.client` is `None`), the address dimension is skipped and only the account counter applies.
- The response body has the same shape as every other error: `{"error": "RateLimitedError", "message": "Too many failed login attempts. Try again later.", "details": {"retry_after_seconds": n}, "request_id": "..."}`. The same number of seconds is sent in the `Retry-After` header.
- A successful login clears the failures recorded under that account. It does not clear the address counter, so a guessing run from one machine stays slowed down even when one attempt succeeds.
- Throttled requests return 429 whether or not the username exists, so the throttle does not reveal valid usernames. The 401 message for a rejected password is unchanged.
- Throttle events are logged at `WARNING` with `operation: login`, `status: 429`, `error: RateLimitedError`, and `retry_after_seconds`. Usernames, passwords, and addresses are not written to the log.

Client address and proxy headers:

- The address is `request.client.host`, which is whatever the ASGI server reports. Uvicorn rewrites it from the `X-Forwarded-For` header when the connecting peer is in its trusted proxy list, and that list defaults to loopback. Any process on the same machine, including anything that reaches the API through the Vite dev proxy, could therefore choose its own address by setting the header. Every place the project starts uvicorn itself (`make backend`, the setup guide, and the Playwright `webServer` command that the `End-to-End` workflow uses) passes `--no-proxy-headers`, so the TCP peer is always used.
- A deployment behind a reverse proxy must terminate client connections at a proxy it trusts and start uvicorn with `--proxy-headers` and an explicit `--forwarded-allow-ips` listing only that proxy's addresses. Without those flags the API sees the proxy's address for every request and the address counter applies to all users together; with `--proxy-headers` but a permissive allow list, any client can forge its address and escape the address counter. The per-account lockout does not depend on the address and holds in either case.

Limits of the implementation:

- The counters live in the memory of one API process and are lost on restart. With several worker processes or several hosts each process counts separately, so an attacker who is spread across them gets `LOGIN_MAX_FAILURES` attempts per process. A shared store (a MySQL table or Redis) would be needed to enforce one limit across processes.
- Expired entries and abandoned reservations are pruned on every call, so memory is bounded by the number of distinct accounts and addresses that failed inside the current window.
- Other endpoints have no request limit. They require a valid token, so they cannot be used to guess credentials.

Verification: `backend/tests/unit/test_login_throttle.py` pins the clock and checks the window arithmetic, the reservation, the normalisation, and the address rule; `backend/tests/api/test_login_throttle_api.py` drives the real endpoint with the demo users, including five failures as one user followed by a successful login as another user from the same address.

## Known limitations

These are accepted for the course deliverable and are documented so nobody mistakes the project for a production system.

- Request limiting covers only the login endpoint and is counted per API process (see "Login throttling"). There is no general rate limit on authenticated endpoints. The address counter only changes the status of an already failed attempt from 401 to 429; it does not save the server any password hashing.
- No refresh tokens. An access token is valid until it expires; there is no revocation list, so a leaked token cannot be invalidated before expiry except by rotating `JWT_SECRET_KEY`, which logs out every user.
- No permanent account lockout. A locked username becomes available again once its oldest failure leaves the window; nothing is written to the `users` table and no administrator action is needed or possible.
- No HTTPS termination in development. The API and the Vite dev server speak plain HTTP on localhost. Any deployment must put a TLS-terminating proxy in front of the API.
- Demo accounts (`admin`, `engineer`, `operator`, `viewer`) share the single password from `SEED_DEMO_PASSWORD`. They exist for demonstrations and grading only.
- The frontend stores the JWT in `localStorage` (`frontend/src/services/http.ts`). Any script running on the page can read it, so a cross-site scripting flaw would expose the token. No decision record covers this choice.
- The root MySQL password and the application password live in a local `.env` file in plain text.
- CORS is restricted to the origins in `CORS_ORIGINS`, but there is no CSRF protection beyond the bearer token model.
- Dependencies are not yet scanned automatically for known vulnerabilities in CI.

## Statement on hardening

This system has not been penetration tested. No security audit has been performed by a third party. The controls listed above have been verified by reading the code at the referenced paths, not by adversarial testing. Treat the project as a reference implementation of good practices for a course, not as production hardened software.
