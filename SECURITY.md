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
| Safe error responses                      | `backend/app/api/errors.py` maps exceptions to JSON without SQL text, stack traces, or driver messages; database and unexpected errors carry a `request_id` in `details`            |
| Structured logs without secrets           | `backend/app/core/logging.py` emits JSON lines; secret settings are declared with `repr=False`; request bodies are not logged                   |
| Secrets kept out of Git                   | `.env` and `.env.*` are ignored in `.gitignore`; only `.env.example` with placeholder values is committed                                       |
| Seed command refuses to run without a password | `backend/app/seed.py` requires `SEED_DEMO_PASSWORD` to be set                                                                             |

## Known limitations

These are accepted for the course deliverable and are documented so nobody mistakes the project for a production system.

- No rate limiting on any endpoint, including login. Credential guessing is not slowed down by the server.
- No refresh tokens. An access token is valid until it expires; there is no revocation list, so a leaked token cannot be invalidated before expiry except by rotating `JWT_SECRET_KEY`, which logs out every user.
- No account lockout after repeated failed logins.
- No HTTPS termination in development. The API and the Vite dev server speak plain HTTP on localhost. Any deployment must put a TLS-terminating proxy in front of the API.
- Demo accounts (`admin`, `engineer`, `operator`, `viewer`) share the single password from `SEED_DEMO_PASSWORD`. They exist for demonstrations and grading only.
- The frontend stores the JWT in `localStorage` (`frontend/src/services/http.ts`). Any script running on the page can read it, so a cross-site scripting flaw would expose the token. No decision record covers this choice.
- The root MySQL password and the application password live in a local `.env` file in plain text.
- CORS is restricted to the origins in `CORS_ORIGINS`, but there is no CSRF protection beyond the bearer token model.
- Dependencies are not yet scanned automatically for known vulnerabilities in CI.

## Statement on hardening

This system has not been penetration tested. No security audit has been performed by a third party. The controls listed above have been verified by reading the code at the referenced paths, not by adversarial testing. Treat the project as a reference implementation of good practices for a course, not as production hardened software.
