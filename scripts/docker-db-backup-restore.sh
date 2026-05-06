#!/usr/bin/env bash
# ChatBI — Docker MySQL 备份 / 恢复 / 重建常用命令封装
# 在仓库根目录执行：  ./scripts/docker-db-backup-restore.sh <命令>
# 或在 backend 目录： ../scripts/docker-db-backup-restore.sh <命令>
#
# 说明：
# - 重建镜像（docker compose build）不会删除 mysql_data 卷，数据一般仍在。
# - 只有执行 `docker compose down -v` 或未挂载卷的空目录启动 MySQL 才会丢库。
# - 后端容器启动时会自动执行 `alembic upgrade head`（见 backend/docker-entrypoint.sh）。
# - Compose 内访问数据库时，backend/.env 中 DB_HOST 应为 mysql（不要用 127.0.0.1）。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
# 可用环境变量 COMPOSE_FILE 指向仓库根目录的 docker-compose.yml（含 Mock_data 初始化）或默认 backend 内 compose
COMPOSE_FILE="${COMPOSE_FILE:-${BACKEND_DIR}/docker-compose.yml}"
DUMP_DIR="${BACKEND_DIR}/database/backups"

# 与 compose 中 MYSQL_DATABASE / 凭据默认值对齐；实际以运行时容器内为准
DB_NAME="${DB_NAME:-chatbi}"
# 业务 Mock 库名（与 database/mock_data_docker_init.sql 中一致）
MOCK_DB_NAME="${MOCK_DB_NAME:-Mock_data}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-12345678}"
# 本机直连 MySQL（非 Docker）时用；可与 backend/.env 中 DB_HOST / DB_PORT 对齐
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
# 默认同 PATH 中的 mysql / mysqldump；若新版客户端连旧服务器报 LIBRARIES 错，可改为 8.0 客户端，例如:
#   export MYSQLDUMP=/opt/homebrew/opt/mysql-client@8.0/bin/mysqldump
#   export MYSQL=/opt/homebrew/opt/mysql-client@8.0/bin/mysql
MYSQL="${MYSQL:-mysql}"
MYSQLDUMP="${MYSQLDUMP:-mysqldump}"
# 追加给 mysqldump 的参数（空格分隔）；连 MariaDB 或极旧 MySQL 时可试: --column-statistics=0
MYSQLDUMP_EXTRA_ARGS="${MYSQLDUMP_EXTRA_ARGS:-}"
# 用临时容器跑 mysqldump（与「compose 里备份」同理，客户端为镜像内 8.0，避免本机 9.x 查 LIBRARIES）
DOCKER_MYSQL_DUMP_IMAGE="${DOCKER_MYSQL_DUMP_IMAGE:-mysql:8.0}"
# 显式指定容器内连到的主机；不设则：DB_HOST 为 127.0.0.1/localhost 时用 host.docker.internal 指向宿主机
DOCKER_DB_HOST="${DOCKER_DB_HOST:-}"

_require_docker() {
  command -v docker >/dev/null 2>&1 || {
    echo "未找到 docker。请安装 Docker Desktop 或使用 backup-local + mysql-client@8.0" >&2
    exit 1
  }
}

# 从一次性 mysql 容器里访问「跑在宿主机上的」MySQL 时应使用的主机名
_resolve_docker_db_host() {
  if [[ -n "${DOCKER_DB_HOST}" ]]; then
    echo "${DOCKER_DB_HOST}"
    return
  fi
  local h="${DB_HOST}"
  if [[ "${h}" == "127.0.0.1" || "${h}" == "localhost" ]]; then
    echo "host.docker.internal"
  else
    echo "${h}"
  fi
}

# Linux 上让 host.docker.internal 指向宿主机（Docker 20.10+）
_docker_add_host_arg() {
  if [[ "$(uname -s)" == "Linux" ]] && [[ "$(_resolve_docker_db_host)" == "host.docker.internal" ]]; then
    echo "--add-host=host.docker.internal:host-gateway"
  fi
}

_require_client_tools() {
  _require_one_bin() {
    local bin="$1" what="$2"
    if [[ "${bin}" == */* ]]; then
      [[ -x "${bin}" ]] || {
        echo "不可执行 ${what}: ${bin}" >&2
        exit 1
      }
    else
      command -v "${bin}" >/dev/null 2>&1 || {
        echo "未找到 ${what}（${bin}）。macOS 可: brew install mysql-client 并把其 bin 加入 PATH" >&2
        exit 1
      }
    fi
  }
  _require_one_bin "${MYSQL}" "mysql"
  _require_one_bin "${MYSQLDUMP}" "mysqldump"
}

_mysql_local() {
  "${MYSQL}" -h"${DB_HOST}" -P"${DB_PORT}" -u"${DB_USER}" -p"${DB_PASSWORD}" "$@"
}

# shellcheck disable=SC2086
_mysqldump_local() {
  "${MYSQLDUMP}" -h"${DB_HOST}" -P"${DB_PORT}" -u"${DB_USER}" -p"${DB_PASSWORD}" ${MYSQLDUMP_EXTRA_ARGS} "$@"
}

_ensure_compose() {
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    echo "未找到 ${COMPOSE_FILE}" >&2
    exit 1
  fi
}

_compose_dir() {
  _ensure_compose
  cd "$(dirname "${COMPOSE_FILE}")"
}

_dump_filename() {
  echo "chatbi-${DB_NAME}-$(date +%Y%m%d-%H%M%S).sql.gz"
}

cmd_backup() {
  _compose_dir
  mkdir -p "${DUMP_DIR}"
  local out="${DUMP_DIR}/$(_dump_filename)"
  echo "备份 ${DB_NAME} → ${out}"
  docker compose -f "${COMPOSE_FILE##*/}" exec -T mysql \
    mysqldump -u"${DB_USER}" -p"${DB_PASSWORD}" --single-transaction --routines --triggers "${DB_NAME}" \
    | gzip > "${out}"
  echo "完成: ${out}"
}

# 同时导出 chatbi 与 Mock_data（若实例中存在该库）；单库失败则跳过并提示
cmd_backup_all() {
  _compose_dir
  mkdir -p "${DUMP_DIR}"
  local ts
  ts="$(date +%Y%m%d-%H%M%S)"
  local compose_rel
  compose_rel="${COMPOSE_FILE##*/}"
  for db in "${DB_NAME}" "${MOCK_DB_NAME}"; do
    if ! docker compose -f "${compose_rel}" exec -T mysql \
      mysql -u"${DB_USER}" -p"${DB_PASSWORD}" -N -e "SHOW DATABASES LIKE '${db}'" | grep -qx "${db}"; then
      echo "跳过（实例中无库）: ${db}"
      continue
    fi
    local out="${DUMP_DIR}/${db}-${ts}.sql.gz"
    echo "备份 ${db} → ${out}"
    docker compose -f "${compose_rel}" exec -T mysql \
      mysqldump -u"${DB_USER}" -p"${DB_PASSWORD}" --single-transaction --routines --triggers --databases "${db}" \
      | gzip > "${out}"
    echo "完成: ${out}"
  done
}

cmd_restore() {
  local file="${1:-}"
  if [[ -z "${file}" || ! -f "${file}" ]]; then
    echo "用法: $0 restore <备份文件.sql 或 .sql.gz>" >&2
    exit 1
  fi
  _compose_dir
  local compose_rel="${COMPOSE_FILE##*/}"
  echo "恢复 ${file}（使用 --databases 的 dump 可省略目标库名；否则导入到 ${DB_NAME}）"
  if [[ "${file}" == *.gz ]]; then
    gunzip -c "${file}" | docker compose -f "${compose_rel}" exec -T mysql \
      mysql -u"${DB_USER}" -p"${DB_PASSWORD}"
  else
    docker compose -f "${compose_rel}" exec -T mysql \
      mysql -u"${DB_USER}" -p"${DB_PASSWORD}" < "${file}"
  fi
  echo "恢复完成。如需对齐迁移版本，可执行: $0 migrate"
}

# ---------- 本机 MySQL（未使用 docker-compose 时）----------

cmd_backup_local() {
  _require_client_tools
  mkdir -p "${DUMP_DIR}"
  local out="${DUMP_DIR}/$(_dump_filename)"
  echo "本机备份 ${DB_HOST}:${DB_PORT} / ${DB_NAME} → ${out}"
  _mysqldump_local --single-transaction --routines --triggers "${DB_NAME}" | gzip > "${out}"
  echo "完成: ${out}"
}

cmd_backup_all_local() {
  _require_client_tools
  mkdir -p "${DUMP_DIR}"
  local ts
  ts="$(date +%Y%m%d-%H%M%S)"
  for db in "${DB_NAME}" "${MOCK_DB_NAME}"; do
    if ! _mysql_local -N -e "SHOW DATABASES LIKE '${db}'" | grep -qx "${db}"; then
      echo "跳过（实例中无库）: ${db}"
      continue
    fi
    local out="${DUMP_DIR}/${db}-${ts}.sql.gz"
    echo "本机备份 ${db} → ${out}"
    _mysqldump_local --single-transaction --routines --triggers --databases "${db}" | gzip > "${out}"
    echo "完成: ${out}"
  done
}

cmd_restore_local() {
  local file="${1:-}"
  if [[ -z "${file}" || ! -f "${file}" ]]; then
    echo "用法: $0 restore-local <备份文件.sql 或 .sql.gz>" >&2
    exit 1
  fi
  _require_client_tools
  echo "本机恢复 ${DB_HOST}:${DB_PORT} ← ${file}"
  if [[ "${file}" == *.gz ]]; then
    gunzip -c "${file}" | _mysql_local
  else
    _mysql_local < "${file}"
  fi
  echo "恢复完成。迁移请在项目 venv 中执行: cd backend && alembic upgrade head"
}

# ---------- 宿主机上的 MySQL：用 Docker 内 mysqldump（与 compose 内备份同理，避免本机客户端过新）----------

cmd_backup_docker_host() {
  _require_docker
  mkdir -p "${DUMP_DIR}"
  local out="${DUMP_DIR}/$(_dump_filename)"
  local dhost
  dhost="$(_resolve_docker_db_host)"
  local add_host
  add_host="$(_docker_add_host_arg)"
  echo "Docker 客户端备份 ${dhost}:${DB_PORT} / ${DB_NAME}（镜像 ${DOCKER_MYSQL_DUMP_IMAGE}）→ ${out}"
  # shellcheck disable=SC2086
  docker run --rm ${add_host} -e MYSQL_PWD="${DB_PASSWORD}" "${DOCKER_MYSQL_DUMP_IMAGE}" \
    mysqldump -h"${dhost}" -P"${DB_PORT}" -u"${DB_USER}" --single-transaction --routines --triggers "${DB_NAME}" \
    | gzip > "${out}"
  echo "完成: ${out}"
}

cmd_backup_all_docker_host() {
  _require_docker
  mkdir -p "${DUMP_DIR}"
  local ts dhost add_host
  ts="$(date +%Y%m%d-%H%M%S)"
  dhost="$(_resolve_docker_db_host)"
  add_host="$(_docker_add_host_arg)"
  echo "Docker 客户端备份（镜像 ${DOCKER_MYSQL_DUMP_IMAGE}）→ ${dhost}:${DB_PORT}"
  for db in "${DB_NAME}" "${MOCK_DB_NAME}"; do
    # shellcheck disable=SC2086
    if ! docker run --rm ${add_host} -e MYSQL_PWD="${DB_PASSWORD}" "${DOCKER_MYSQL_DUMP_IMAGE}" \
      mysql -h"${dhost}" -P"${DB_PORT}" -u"${DB_USER}" -N -e "SHOW DATABASES LIKE '${db}'" | grep -qx "${db}"; then
      echo "跳过（实例中无库）: ${db}"
      continue
    fi
    local out="${DUMP_DIR}/${db}-${ts}.sql.gz"
    echo "备份 ${db} → ${out}"
    # shellcheck disable=SC2086
    docker run --rm ${add_host} -e MYSQL_PWD="${DB_PASSWORD}" "${DOCKER_MYSQL_DUMP_IMAGE}" \
      mysqldump -h"${dhost}" -P"${DB_PORT}" -u"${DB_USER}" --single-transaction --routines --triggers --databases "${db}" \
      | gzip > "${out}"
    echo "完成: ${out}"
  done
}

cmd_migrate() {
  _compose_dir
  local compose_rel="${COMPOSE_FILE##*/}"
  docker compose -f "${compose_rel}" run --rm alembic-migrate
}

cmd_rebuild() {
  _compose_dir
  local compose_rel="${COMPOSE_FILE##*/}"
  echo "重建镜像并启动（保留匿名卷 mysql_data，除非你先 down -v）…"
  docker compose -f "${compose_rel}" build "$@"
  docker compose -f "${compose_rel}" up -d
  echo "已启动。后端日志中会看到 alembic upgrade；也可手动: $0 migrate"
}

cmd_rebuild_clean_volumes() {
  _compose_dir
  local compose_rel="${COMPOSE_FILE##*/}"
  echo "警告: 将执行 down -v，删除 MySQL/Redis 数据卷。建议先 $0 backup"
  read -r -p "确认继续? [y/N] " ok
  [[ "${ok}" == [yY] ]] || exit 1
  docker compose -f "${compose_rel}" down -v
  docker compose -f "${compose_rel}" build --no-cache
  docker compose -f "${compose_rel}" up -d
  echo "空卷已启动，迁移将由 entrypoint 执行。若有备份请: $0 restore <file>"
}

cmd_logs() {
  _compose_dir
  local compose_rel="${COMPOSE_FILE##*/}"
  docker compose -f "${compose_rel}" logs -f --tail=200 chatbi-backend
}

usage() {
  cat <<EOF
用法: $0 <命令>

  【Docker Compose 内 MySQL】
  backup              从 MySQL 容器导出 ${DB_NAME} 到 backend/database/backups/（gzip）
  backup-all          依次导出 ${DB_NAME} 与 ${MOCK_DB_NAME}（若库存在；含 CREATE DATABASE，便于远程还原）
  restore <文件>      将 .sql / .sql.gz 导入当前 compose 中的 MySQL（建议 dump 使用 mysqldump --databases）

  【本机安装的 MySQL，未用 compose】需 mysql、mysqldump（可用 MYSQL / MYSQLDUMP 指定路径）
  backup-local        仅导出单个库 ${DB_NAME}（默认 chatbi；要 Mock 请用下一行）
  backup-all-local    依次导出 ${DB_NAME} 与 ${MOCK_DB_NAME}（实例里存在的才导出，含 --databases）
  restore-local <文件>  导入 .sql / .sql.gz 到本机实例

  【本机 MySQL + 仅需 Docker（不要本机 mysqldump 9.x）】镜像内为 8.0 客户端，行为接近 compose 内 backup
  backup-docker-host     导出单个库 ${DB_NAME}（连 DB_HOST，127.0.0.1 时经 host.docker.internal）
  backup-all-docker-host 同上，双库（存在的才导出）

  migrate             仅执行 alembic upgrade head（alembic-migrate 服务；需 compose 内含该服务）
  rebuild [args...]   docker compose build [args] && up -d
  rebuild-clean       down -v 后 no-cache 重建并启动（删库，慎用）
  logs                跟随 chatbi-backend 日志

环境变量（可选）：
  COMPOSE_FILE                默认 ${BACKEND_DIR}/docker-compose.yml；若用仓库根目录全栈（含 Mock 初始化），设为:
                              export COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
  DB_NAME DB_USER DB_PASSWORD 与 .env 中实际值一致
  MOCK_DB_NAME                默认 Mock_data
  DB_HOST DB_PORT             仅 backup-local / restore-local 等；默认 127.0.0.1:3306
  MYSQL MYSQLDUMP           本机子命令使用的客户端路径（默认 PATH 中的 mysql / mysqldump）
  MYSQLDUMP_EXTRA_ARGS      传给 mysqldump 的额外参数（空格分隔，可选）
  DOCKER_MYSQL_DUMP_IMAGE   backup-*-docker-host 使用的镜像，默认 mysql:8.0
  DOCKER_DB_HOST            容器内连接地址；不设且 DB_HOST 为本机时自动用 host.docker.internal

  若 mysqldump 报错 Unknown table 'LIBRARIES' in information_schema：
  多为本机客户端过新（如 9.x）、服务器为 8.0.x。请改用与服务器主版本一致的 mysqldump，例如:
    brew install mysql-client@8.0
    export PATH="/opt/homebrew/opt/mysql-client@8.0/bin:\$PATH"
  Intel Mac 常见路径: /usr/local/opt/mysql-client@8.0/bin
  或改用: backup-all-docker-host（不必改 PATH，需本机已装 Docker）

  （Compose 中 MySQL 服务名为 mysql，脚本已写死该服务名。）

远程还原（示例）：
  scp backend/database/backups/*.sql.gz user@remote:/tmp/
  ssh user@remote 'gunzip -c /tmp/chatbi-*.sql.gz | mysql -h127.0.0.1 -uroot -p你的密码'
  ssh user@remote 'gunzip -c /tmp/Mock_data-*.sql.gz | mysql -h127.0.0.1 -uroot -p你的密码'

提示：
  - 仅 \`docker compose build\` / 重启容器：数据在卷里，通常无需恢复。
  - 根目录 docker-compose 首次启动会执行 database/chatbi_docker_init.sql 与 mock_data_docker_init.sql；仅 backend compose 时可能只有 chatbi，无 Mock_data 则 backup-all 会跳过 Mock。
EOF
}

main() {
  local sub="${1:-}"
  shift || true
  case "${sub}" in
    backup)          cmd_backup ;;
    backup-all)      cmd_backup_all ;;
    backup-local)    cmd_backup_local ;;
    backup-all-local) cmd_backup_all_local ;;
    backup-docker-host) cmd_backup_docker_host ;;
    backup-all-docker-host) cmd_backup_all_docker_host ;;
    restore)         cmd_restore "$@" ;;
    restore-local)   cmd_restore_local "$@" ;;
    migrate)    cmd_migrate ;;
    rebuild)    cmd_rebuild "$@" ;;
    rebuild-clean) cmd_rebuild_clean_volumes ;;
    logs)       cmd_logs ;;
    ""|help|-h) usage ;;
    *)          echo "未知命令: ${sub}" >&2; usage; exit 1 ;;
  esac
}

main "$@"
