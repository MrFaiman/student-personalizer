# Incident Response Plan

Covers detection, classification, escalation, and reporting for security incidents involving the Student Personalizer system and the student data it processes.

## Severity Classification

| Level | Description | Examples |
|---|---|---|
| **P1 — Critical** | Active breach, data exfiltration, or system compromise | Unauthorized database access, stolen credentials with evidence of use, ransomware |
| **P2 — High** | Confirmed vulnerability or failed attack with high impact potential | SQL injection attempt that reached the DB, brute-force attack succeeding lockout threshold, exposed secret key |
| **P3 — Medium** | Suspicious activity or potential misconfiguration | Repeated login failures from unusual IPs, unexpected admin account creation |
| **P4 — Low** | Informational / policy violations | Weak password used before policy enforcement, non-critical dep vulnerability found in audit |

## Response Timeline (MoE Requirements)

| Event | Required Action | Deadline |
|---|---|---|
| P1 incident detected | Notify system owner + school IT manager | Within **1 hour** |
| P1 incident confirmed | Report to Israeli MoE CERT (cert@education.gov.il) | Within **8 hours** |
| P1 incident resolved | Submit full incident report | Within **72 hours** |
| P2 incident confirmed | Notify school IT manager | Within **4 hours** |
| Any personal data breach | Notify Privacy Protection Authority (PPA) if >100 records affected | Within **72 hours** (Privacy Protection Law 5741-1981) |

## Response Steps

### Step 1 — Detect

Detection sources:
- Audit log alerts (`AuditLog` table — monitor for `success=false` spikes, unusual `action` patterns)
- Application logs (JSON structured logs, forward to SIEM)
- Infrastructure alerts (failed container health checks, disk full, unusual network traffic)
- User reports

### Step 2 — Contain

For a confirmed P1 breach:

1. **Isolate** the affected service:
   ```bash
   docker compose -f docker-compose.prod.yml stop server
   ```

2. **Revoke all active sessions** (connect directly to DB):
   ```sql
   UPDATE usersession SET is_revoked = true WHERE is_revoked = false;
   ```

3. **Rotate all secrets** — generate new values for `JWT_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `HASH_PEPPER` and redeploy.

4. **Preserve evidence** — copy logs and DB state before any cleanup:
   ```bash
   docker logs student-personalizer-server-1 > /tmp/incident-$(date +%Y%m%d-%H%M%S).log
   ./scripts/backup.sh
   ```

### Step 3 — Investigate

1. Review audit logs for the incident window:
   ```sql
   SELECT * FROM auditlog
   WHERE timestamp >= '<incident_start>'
   ORDER BY timestamp;
   ```

2. Identify affected records (students, users) by cross-referencing `user_id` and `resource` fields.

3. Determine root cause: misconfiguration, compromised credential, vulnerability, or insider threat.

### Step 4 — Notify

Contacts:

| Role | Contact |
|---|---|
| System owner | Per school's internal directory |
| School IT manager | Per school's internal directory |
| Israeli MoE CERT | cert@education.gov.il |
| Privacy Protection Authority | gov.il/ppa (for data breaches) |

Notification must include:
- Nature of the incident (what happened, when discovered, when it started)
- Data affected (number of students, type of data)
- Actions taken to contain
- Planned remediation

### Step 5 — Remediate

1. Apply patches or configuration fixes.
2. Run full test suite: `cd server && uv run pytest`.
3. Redeploy: `docker compose -f docker-compose.prod.yml up -d --build`.
4. Verify all health checks pass.
5. Re-enable service for users.

### Step 6 — Post-Incident Review

Within 2 weeks of resolution:
- Document timeline, root cause, and lessons learned
- Update runbooks or security controls as needed
- Re-evaluate risk register

## Common Scenarios

### Compromised Admin Account

1. Disable the account immediately:
   ```sql
   UPDATE user SET is_active = false WHERE email = '<compromised@email>';
   ```
2. Revoke all sessions for that user:
   ```sql
   UPDATE usersession SET is_revoked = true WHERE user_id = '<uuid>';
   ```
3. Force password reset via admin panel for all other users if credential stuffing is suspected.
4. Escalate per P1/P2 timeline above.

### Suspected Data Exfiltration

1. Capture current audit log to evidence file.
2. Identify the `user_id` responsible for unusual read volume.
3. Disable account and revoke sessions.
4. Enumerate affected `student_tz` values from audit log `resource` field.
5. Notify affected students' families per school policy.

### Ransomware / Storage Encryption

1. Immediately isolate all containers.
2. Restore from the most recent verified backup: `./scripts/restore.sh --file <backup.dump.enc> --confirm`.
3. Report as P1 and notify MoE CERT within 8 hours.
