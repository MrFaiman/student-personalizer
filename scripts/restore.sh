#!/usr/bin/env bash
# restore.sh - decrypt and restore a PostgreSQL backup (MoE section 3.3)
#
# Required env vars:
#   DATABASE_URL          - PostgreSQL connection string (target DB)
#   BACKUP_ENCRYPTION_KEY - AES-256 passphrase used during backup
#
# Required flags:
#   --confirm             - explicit confirmation to prevent accidental restore
#   --file <path>         - path to the .dump.enc backup file
#
# Usage:
#   ./scripts/restore.sh --file ./backups/2026-03-30_12-00-00.dump.enc --confirm

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_ENCRYPTION_KEY:?BACKUP_ENCRYPTION_KEY is required}"

CONFIRM=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm) CONFIRM=true; shift ;;
    --file)    BACKUP_FILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "${BACKUP_FILE}" ]]; then
  echo "Error: --file <path> is required" >&2
  exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Error: backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

if [[ "${CONFIRM}" != "true" ]]; then
  echo "Error: --confirm flag is required to prevent accidental restore" >&2
  echo "       This will OVERWRITE the target database: ${DATABASE_URL}" >&2
  exit 1
fi

echo "[restore] Decrypting and restoring: ${BACKUP_FILE}"
echo "[restore] Target: ${DATABASE_URL}"

# Decrypt → pg_restore
openssl enc -d -aes-256-cbc -pbkdf2 -iter 310000 \
    -pass "env:BACKUP_ENCRYPTION_KEY" \
    -in "${BACKUP_FILE}" \
  | pg_restore --no-password --clean --if-exists --dbname "${DATABASE_URL}"

echo "[restore] Restore complete."
