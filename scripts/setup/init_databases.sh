#!/usr/bin/env bash
# Creates the application database, the test database, and a least-privilege
# application user. Idempotent: safe to run more than once.
#
# Used in two places:
#   1. docker-compose mounts it into /docker-entrypoint-initdb.d and passes the
#      values as APP_DB_NAME, APP_DB_USER, and APP_DB_PASSWORD (MYSQL_DATABASE
#      and MYSQL_USER are deliberately not set in the container, because the
#      official image would then create the user with GRANT ALL).
#   2. scripts/development/local_mysql.sh calls it after initialising a local
#      data directory with the MYSQL_* values from .env, passing
#      MYSQL_CLIENT_ARGS (socket) and MYSQL_ROOT_ARGS.
set -euo pipefail

MYSQL_DATABASE="${MYSQL_DATABASE:-${APP_DB_NAME:-}}"
MYSQL_USER="${MYSQL_USER:-${APP_DB_USER:-}}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-${APP_DB_PASSWORD:-}}"

: "${MYSQL_DATABASE:?MYSQL_DATABASE or APP_DB_NAME is required}"
: "${MYSQL_USER:?MYSQL_USER or APP_DB_USER is required}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD or APP_DB_PASSWORD is required}"

# The mysql client reads MYSQL_HOST and MYSQL_TCP_PORT from the environment and
# would silently connect to a different server than the one named by the
# socket or host arguments below, so clear them here.
unset MYSQL_HOST MYSQL_TCP_PORT MYSQL_UNIX_PORT MYSQL_PWD

# The password is interpolated into a single-quoted SQL string literal, so
# double every single quote it contains.
pw_sql=${MYSQL_PASSWORD//\'/\'\'}

read -ra root_args <<< "${MYSQL_ROOT_ARGS:--uroot}"
read -ra client_args <<< "${MYSQL_CLIENT_ARGS:-}"

# The ${arr[@]+"${arr[@]}"} form expands to nothing for an empty array without
# tripping "set -u" on bash 3.2 (macOS).
mysql --no-defaults ${root_args[@]+"${root_args[@]}"} ${client_args[@]+"${client_args[@]}"} <<SQL
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}_test\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${pw_sql}';
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'localhost' IDENTIFIED BY '${pw_sql}';
-- The application user gets DML plus the DDL it needs to run migrations.
-- It cannot create users, grant privileges, or touch other schemas.
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES
  ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%', '${MYSQL_USER}'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES
  ON \`${MYSQL_DATABASE}_test\`.* TO '${MYSQL_USER}'@'%', '${MYSQL_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
echo "Databases ${MYSQL_DATABASE} and ${MYSQL_DATABASE}_test are ready for user ${MYSQL_USER}."
