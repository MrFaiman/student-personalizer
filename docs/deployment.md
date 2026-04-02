# Deployment Guide

## Requirements

- **Cloud region**: Must deploy within Israel or an EU region that satisfies Israeli data-residency requirements (MoE directive). Recommended: Microsoft Azure Israel Central or AWS eu-central-1 with data-residency guarantees.
- **OS**: Linux (Ubuntu 22.04 LTS or RHEL 8+), 64-bit
- **Docker**: 24.0+, Docker Compose 2.20+
- **PostgreSQL**: 15+ (managed service recommended — RDS/Azure Database for PostgreSQL)
- **TLS**: Certificate from a trusted CA (Let's Encrypt acceptable); TLS 1.2 minimum, TLS 1.3 preferred

## Environment Variables

### Required in Production

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql://user:pass@host:5432/db`) |
| `JWT_SECRET_KEY` | 32+ byte random string for JWT signing — **never reuse across environments** |
| `FIELD_ENCRYPTION_KEY` | Base64-encoded 32-byte AES key for PII field encryption |
| `HASH_PEPPER` | 32+ byte random string for HMAC student-ID hashing |
| `FIELD_ENCRYPTION_REQUIRED` | Set to `true` |
| `DB_SSL_REQUIRED` | Set to `true` |
| `ORIGIN_URL` | Production frontend URL (e.g. `https://students.school.il`) |

### Optional

| Variable | Description | Default |
|---|---|---|
| `PORT` | Server listen port | `3000` |
| `ENABLE_DEBUG` | Enable OpenAPI docs (`/docs`) | `false` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token TTL | `15` |
| `REFRESH_TOKEN_EXPIRE_HOURS` | JWT refresh token TTL | `8` |
| `INACTIVITY_TIMEOUT_MINUTES` | Session inactivity cutoff | `30` |
| `MAX_UPLOAD_SIZE_MB` | Max Excel upload size | `50` |
| `UPLOAD_DIR` | Directory for uploaded files | `uploads/` |
| `DEFAULT_ADMIN_PASSWORD` | Initial admin password (change immediately) | `Admin@1234!` |

### Generating Secrets

```bash
# JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# FIELD_ENCRYPTION_KEY (base64-encoded 32 bytes)
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# HASH_PEPPER
python -c "import secrets; print(secrets.token_hex(32))"
```

## Production Deployment

### 1. Clone and Configure

```bash
git clone <repo-url> student-personalizer
cd student-personalizer
cp server/.env.example server/.env   # fill in required vars
```

### 2. TLS Certificate

Place your certificate and key in `certs/`:

```
certs/
  server.crt
  server.key
```

Or use the Certbot integration:

```bash
certbot certonly --standalone -d students.school.il
ln -s /etc/letsencrypt/live/students.school.il/fullchain.pem certs/server.crt
ln -s /etc/letsencrypt/live/students.school.il/privkey.pem certs/server.key
```

### 3. Initialize Database Schema

The server manages schema at runtime using `SQLModel.metadata.create_all()` on startup (no Alembic).

### 4. Start Services

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 5. First Login

Connect to `https://<your-domain>` and log in with:
- Email: `admin@school.local`
- Password: the value of `DEFAULT_ADMIN_PASSWORD` (default: `Admin@1234!`)

**Change the password immediately after first login.**

## Network Architecture

```
Internet
  │
  ▼
[nginx:443] ── TLS termination, security headers
  │
  ├── /api/* ──▶ [FastAPI:3000]
  │                    │
  │               [PostgreSQL:5432]
  │
  └── /* ──▶ [React SPA static files]
```

All inter-service communication is over the internal Docker network. The database port (5432) must NOT be exposed externally.

## Backup & Restore

See `scripts/backup.sh` and `scripts/restore.sh`. Schedule daily backups:

```bash
# Add to crontab (runs at 2:00 AM)
0 2 * * * /path/to/student-personalizer/scripts/backup.sh >> /var/log/student-personalizer-backup.log 2>&1
```

Required env vars: `DATABASE_URL`, `BACKUP_ENCRYPTION_KEY`.

Backups are retained for 30 days (configurable via `BACKUP_RETENTION_DAYS`).

## Health Check

```bash
curl https://<your-domain>/health
# Expected: {"status": "ok"}
```

## Monitoring

The `/health` endpoint is suitable for load-balancer and uptime-monitor probes.

Application logs are written to stdout in JSON format (structured logging). Forward to your SIEM or log aggregation system (ELK, Splunk, Azure Monitor) via Docker log driver.

## Updates

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
