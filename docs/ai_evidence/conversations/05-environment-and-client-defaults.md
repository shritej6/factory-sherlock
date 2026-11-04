# Conversation 5: Local MySQL setup and a misleading client default

Project area: environment and reproducible setup. Tool: Claude Code. Date: 2026-11-03.
Outcome: revised twice; the final script is what the README documents.

## Sequence

1. Student prompt (paraphrased): the machine has no Docker; provide a way to run a private MySQL 8 instance for the project.
2. AI proposal: scripts/development/local_mysql.sh wrapping `mysqld --initialize-insecure` and `mysqld --daemonize` with a data directory under .local/.
3. First failure: the Anaconda build of mysqld could not load its component library or find its error message file. The script was revised to pass `--plugin-dir` and `--lc-messages-dir` derived from the binary's install prefix.
4. Second failure: every `mysql --socket=... -uroot` call was denied even though the server had an empty root password. The cause was that `.env` had been sourced into the shell and the mysql client honours the `MYSQL_HOST` environment variable, so the client was silently connecting over TCP to a different, pre-existing MySQL server on port 3306. The scripts now pass `--no-defaults --protocol=socket`, unset the client-affecting variables, and the project instance runs on port 3307.
5. Decision: both revisions kept; the troubleshooting section of docs/development/setup-guide.md records the symptoms so another developer does not repeat the diagnosis.

## Verification

- `scripts/development/local_mysql.sh init` creates the data directory, both databases, and the least-privilege user in one step; `status` reports running; the application user connects over TCP on 3307.
- A later mysqldump as the application user failed on tablespaces and LOCK TABLES, which confirmed the user has no PROCESS or LOCK privilege; the export script uses `--no-tablespaces --skip-lock-tables` instead of widening the grant.

## Student annotation

[Shritej: add what you learned about least privilege from the mysqldump failure and whether you would grant PROCESS to the app user (and why not).]
