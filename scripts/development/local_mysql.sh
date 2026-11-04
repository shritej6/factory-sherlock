#!/usr/bin/env bash
# Runs a private MySQL 8 server for this project without Docker.
#
#   scripts/development/local_mysql.sh init    # one-time: create data dir, databases, app user
#   scripts/development/local_mysql.sh start
#   scripts/development/local_mysql.sh stop
#   scripts/development/local_mysql.sh status
#   scripts/development/local_mysql.sh shell   # mysql client as the app user
#
# Requires the mysqld binary on PATH (Homebrew "brew install mysql" or the
# Anaconda distribution both provide it). All state lives under .local/mysql,
# which is ignored by Git.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_file="${repo_root}/.env"
if [[ ! -f "${env_file}" ]]; then
  echo "Missing ${env_file}. Copy .env.example to .env first." >&2
  exit 1
fi
set -a; source "${env_file}"; set +a

base_dir="${repo_root}/.local/mysql"
data_dir="${base_dir}/data"
socket="${base_dir}/mysql.sock"
pid_file="${base_dir}/mysqld.pid"
log_file="${base_dir}/mysqld.log"
port="${MYSQL_PORT:-3306}"

require_mysqld() {
  command -v mysqld >/dev/null || { echo "mysqld not found on PATH" >&2; exit 1; }
}

is_running() {
  [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null
}

# Some distributions (Anaconda in particular) do not locate their own plugin
# and message directories unless told explicitly. Derive them from the binary.
layout_args() {
  local prefix
  prefix="$(cd "$(dirname "$(command -v mysqld)")/.." && pwd)"
  [[ -d "${prefix}/lib/plugin" ]] && echo "--plugin-dir=${prefix}/lib/plugin"
  [[ -d "${prefix}/share/mysql" ]] && echo "--lc-messages-dir=${prefix}/share/mysql"
}

# Returns 0 when something already listens on the configured port. Prefers
# lsof, falls back to nc, and skips the check with a warning when neither is
# installed so a missing tool is never mistaken for a free port.
port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "${port}" >/dev/null 2>&1
  else
    echo "warning: neither lsof nor nc is installed; skipping the check that port ${port} is free" >&2
    return 1
  fi
}

start_server() {
  if is_running; then echo "MySQL already running (pid $(cat "${pid_file}"))"; return; fi
  if port_in_use; then
    echo "Port ${port} is already in use by another process. Stop it or change MYSQL_PORT in .env." >&2
    exit 1
  fi
  mkdir -p "${base_dir}"
  mysqld --datadir="${data_dir}" --port="${port}" --socket="${socket}" $(layout_args) \
    --pid-file="${pid_file}" --log-error="${log_file}" --bind-address=127.0.0.1 \
    --character-set-server=utf8mb4 --collation-server=utf8mb4_0900_ai_ci \
    --sql-mode=STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO \
    --mysqlx=OFF --daemonize
  local ready=0
  for _ in $(seq 1 30); do
    if mysqladmin --no-defaults --protocol=socket --socket="${socket}" -uroot ping >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "${ready}" -ne 1 ]]; then
    echo "MySQL did not answer on ${socket} within 30 seconds. Last 20 lines of ${log_file}:" >&2
    tail -n 20 "${log_file}" >&2 2>/dev/null || echo "(log file not readable)" >&2
    exit 1
  fi
  echo "MySQL listening on 127.0.0.1:${port} (socket ${socket})"
}

case "${1:-}" in
  init)
    require_mysqld
    if [[ -d "${data_dir}" ]]; then echo "Data directory exists: ${data_dir}. Remove it to re-initialise." >&2; exit 1; fi
    mkdir -p "${base_dir}"
    # --initialize-insecure creates root with no password; the server only binds
    # to loopback and the application never uses root, so this is acceptable for
    # a local development instance.
    mysqld --initialize-insecure --datadir="${data_dir}" --log-error="${log_file}" $(layout_args)
    start_server
    if ! MYSQL_ROOT_ARGS="-uroot" MYSQL_CLIENT_ARGS="--protocol=socket --socket=${socket}" \
        bash "${repo_root}/scripts/setup/init_databases.sh"; then
      echo "init_databases.sh failed. The server is still running; fix the cause (usually a value in .env)," >&2
      echo "then either rerun the script by hand with the same MYSQL_ROOT_ARGS and MYSQL_CLIENT_ARGS," >&2
      echo "or stop the server and remove ${data_dir} to run 'init' again from scratch." >&2
      exit 1
    fi
    ;;
  start) require_mysqld; start_server ;;
  stop)
    if is_running; then mysqladmin --no-defaults --protocol=socket --socket="${socket}" -uroot shutdown; echo "MySQL stopped"; else echo "MySQL is not running"; fi
    ;;
  status)
    if is_running; then echo "running (pid $(cat "${pid_file}"), port ${port})"; else echo "stopped"; exit 1; fi
    ;;
  shell)
    mysql --no-defaults --protocol=socket --socket="${socket}" -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}"
    ;;
  *)
    echo "usage: $0 {init|start|stop|status|shell}" >&2; exit 1 ;;
esac
