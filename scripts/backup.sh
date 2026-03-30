#!/usr/bin/env bash
# backup.sh - encrypted PostgreSQL backup (MoE section 3.3)
#
# Required env vars:
#   DATABASE_URL          - PostgreSQL connection string
#   BACKUP_ENCRYPTION_KEY - AES-256 passphrase for encrypting the dump
#
# Optional:
#   BACKUP_DIR            - destination directory (default: ./backups)
#
# Usage:
#   ./scripts/backup.sh
#
# The backup is written to: $BACKUP_DIR/YYYY-MM-DD_HH-MM-SS.dump.enc

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${BACKUP_ENCRYPTION_KEY:?BACKUP_ENCRYPTION_KEY is required}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/${TIMESTAMP}.dump.enc"

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

echo "[backup] Starting backup at ${TIMESTAMP}"

# pg_dump → AES-256-CBC → encrypted file
pg_dump --format=custom --no-password "${DATABASE_URL}" \
  | openssl enc -aes-256-cbc -pbkdf2 -iter 310000 \
      -pass "env:BACKUP_ENCRYPTION_KEY" \
      -out "${BACKUP_FILE}"

chmod 600 "${BACKUP_FILE}"

SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
echo "[backup] Done: ${BACKUP_FILE} (${SIZE})"

# Retention: delete backups older than 30 days
find "${BACKUP_DIR}" -name "*.dump.enc" -mtime +30 -delete
echo "[backup] Cleaned up backups older than 30 days"
