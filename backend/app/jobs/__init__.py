"""Commands meant to be run on a schedule (cron, a task runner) rather than per request.

Each module opens its own session, calls one service function, commits, and
logs a JSON line. The services themselves never commit, so the same functions
are shared with the HTTP endpoints.
"""
