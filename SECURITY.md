# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| Latest (`main` branch) | Yes |
| Older releases | No — update to latest |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities by emailing the system maintainer directly. Include:

1. A clear description of the vulnerability
2. Steps to reproduce (proof-of-concept if possible)
3. The potential impact (data affected, attack surface)
4. Your suggested fix (optional but welcome)

You will receive an acknowledgement within **48 hours** and a status update within **7 days**.

If the vulnerability involves student personal data, also notify the school's Data Protection Officer per the Privacy Protection Law 5741-1981.

## Security Controls Summary

This system implements the following controls in compliance with the Israeli Ministry of Education security requirements:

| Control | Implementation |
|---|---|
| Authentication | JWT (access 15 min / refresh 8 h), Argon2id password hashing |
| Authorization | Role-based (admin / teacher / viewer), enforced on every endpoint |
| Account lockout | 5 failed attempts → 15-minute lockout |
| Session management | Inactivity timeout (30 min), token rotation on refresh |
| Password policy | 10+ chars, uppercase, lowercase, digit, special char; last-5 history |
| PII encryption | AES-256-GCM field-level encryption for student names and open-day contact data |
| Transport security | TLS 1.2+ (nginx), HSTS enabled |
| Security headers | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `CSP`, `Permissions-Policy` |
| Audit trail | Immutable `AuditLog` table records all auth events and data mutations |
| Rate limiting | Login: 5/min per IP; Refresh: 10/min per IP; API: 200/min per IP |
| File upload safety | Magic-byte validation, filename sanitization, 50 MB size limit |
| ML privacy | Explicit feature allowlist — PII columns blocked from entering the model |
| Container hardening | Non-root user, `no-new-privileges`, read-only filesystem for client |
| Dependency scanning | `pip-audit` (Python) and `pnpm audit` (Node) in CI |
| SAST | `bandit` static analysis in CI |

## Vulnerability Disclosure Policy

We follow responsible disclosure:

- We will fix critical vulnerabilities within **14 days** of confirmation.
- We will fix high-severity vulnerabilities within **30 days**.
- We will publicly acknowledge reporters who responsibly disclose vulnerabilities (unless they request anonymity).
- We will not take legal action against researchers who follow this policy and do not exfiltrate, modify, or destroy data.

## Third-Party Dependencies

Dependencies are scanned on every CI run with `pip-audit` and `pnpm audit`. Critical or high CVEs block the build. Review the CI workflow (`.github/workflows/ci.yml`) for details.
