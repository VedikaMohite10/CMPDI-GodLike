# SECURITY.md — CMPDI AI Mining Intelligence Platform

## Overview

This document describes the security architecture, authentication model, role-based access control (RBAC) design, and responsible disclosure process for the CMPDI AI Mining Intelligence Platform (Phase 5+).

---

## Authentication

### JWT (JSON Web Tokens)

All protected API endpoints require a valid **Bearer JWT token** in the `Authorization` header.

```
Authorization: Bearer <token>
```

Tokens are issued by `POST /auth/login` using form-encoded credentials (`username` + `password`).

| Property | Value |
|---|---|
| Algorithm | `HS256` |
| Expiry | Configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 min) |
| Claims | `sub` (user UUID), `username`, `role`, `exp` |
| No refresh tokens | Tokens expire; re-login to obtain a new token |

### Password Hashing

- Passwords are hashed with **bcrypt** via `passlib[bcrypt]`.
- Plain-text passwords are never stored or logged.
- The `BOOTSTRAP_ADMIN_PASSWORD` **must be changed** immediately after first deployment.

### Bootstrap Admin

On first startup, if no users exist, the server creates a default admin account using:

```
BOOTSTRAP_ADMIN_USERNAME=admin  (default)
BOOTSTRAP_ADMIN_PASSWORD=changeme123!  (default — CHANGE THIS)
```

This is controlled by environment variables. See `.env.example`.

---

## Role-Based Access Control (RBAC)

Three roles exist, in ascending order of privilege:

| Role | Allowed Actions |
|---|---|
| `analyst` | Read all data, submit queries, run forecasts, upload documents |
| `reviewer` | All analyst actions + approve/reject review flags, resolve conflicts, approve/reject parliamentary queries |
| `admin` | All reviewer actions + create/manage users, run benchmark harness |

### Enforcement

RBAC is enforced server-side via the `require_role()` FastAPI dependency factory in `app/services/auth/dependencies.py`. Every protected route explicitly declares the minimum required role. There is no front-end-only enforcement.

### Protected Endpoints Summary

| Endpoint | Minimum Role |
|---|---|
| `POST /auth/users` | `admin` |
| `POST /review/flags/{id}/accept` | `reviewer` |
| `POST /review/flags/{id}/correct` | `reviewer` |
| `POST /review/flags/{id}/reject` | `reviewer` |
| `POST /review/conflicts/{id}/resolve` | `reviewer` |
| `GET /review/audit-log` | `reviewer` |
| `POST /parliamentary/{id}/approve` | `reviewer` |
| `POST /parliamentary/{id}/reject` | `reviewer` |
| `POST /benchmark/run` | `admin` |
| All other authenticated endpoints | Any authenticated user (`analyst`+) |

---

## CORS

Cross-Origin Resource Sharing is controlled via the `CORS_ALLOWED_ORIGINS` environment variable:

- **Development default**: `*` (permissive — allows any origin, disables credentials)
- **Production**: Set to a comma-separated list of allowed origins, e.g.:
  ```
  CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
  ```
  When set to a specific origin, `allow_credentials=True` is enabled, permitting cookie-based auth flows.

---

## Audit Logging

Every mutating action in the system writes a row to the `audit_log` table with:

- `reviewer` — username of the actor (or `"system"` for automated actions)
- `action_type` — semantic action name (e.g. `document_uploaded`, `flag_accepted`, `report_generated`, `parliamentary_approved`)
- `target_table` + `target_id` — identifies the affected record
- `before_value` / `after_value` — JSONB snapshots of the state change
- `timestamp` — UTC timestamp

Audit log entries are **immutable** (no `UPDATE` or `DELETE` on `audit_log`). Reviewers can query the log via `GET /review/audit-log`.

### Covered Actions

| Action | action_type |
|---|---|
| Document upload | `document_uploaded` |
| Flag accepted | `accept` |
| Flag corrected | `correct` |
| Flag rejected | `reject` |
| Conflict resolved | `resolve_conflict` |
| Report generated | `report_generated` |
| Parliamentary query submitted | `parliamentary_submitted` |
| Parliamentary query approved | `parliamentary_approved` |
| Parliamentary query rejected | `parliamentary_rejected` |

---

## Parliamentary Query Safeguards

Parliamentary queries run through an additional layer of controls beyond standard auth:

1. **All queries start as `pending_review`** — the LLM draft answer is never surfaced until explicitly approved by a `reviewer`+.
2. **`final_answer` is null** in all API responses until `status == 'approved'`.
3. **Every approval and rejection** writes an audit log entry with the reviewer's identity.
4. **Open conflicts are always disclosed** in the draft — the pipeline never silences conflict signals.
5. **Every factual claim must be cited** — uncited claims are replaced with a sentinel string.

---

## Data Integrity Controls

- **Synthetic documents are labeled**: The `is_synthetic` column on `documents` and `BenchmarkGroundTruth` ensures synthetic stress-test data is never cited as real CMPDI data.
- **Forecast type is always labeled**: Every `ForecastResult` carries `forecast_type = "Model-based forecast"` enforced at both the ORM and DB constraint level.
- **Benchmark real/synthetic separation**: Real and synthetic metrics are **never aggregated**; they are always reported in separate keys.

---

## Secret Management

| Secret | Env Var | Notes |
|---|---|---|
| JWT signing key | `JWT_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_hex(64))"`. Must be ≥32 chars. |
| DB password | `POSTGRES_PASSWORD` / `DATABASE_URL` | Never commit to version control |
| Bootstrap admin password | `BOOTSTRAP_ADMIN_PASSWORD` | Change immediately after first login |

The `.env` file is listed in `.gitignore`. Use `.env.example` (which contains no real secrets) as the template for new deployments.

---

## Responsible Disclosure

If you discover a security vulnerability in this codebase, please follow responsible disclosure:

1. **Do not** open a public GitHub issue.
2. Contact the project maintainer directly (email TBD — contact your project lead).
3. Provide a clear description of the vulnerability, steps to reproduce, and potential impact.
4. Allow reasonable time for a fix before public disclosure.

We take security seriously and will acknowledge your report within 48 hours.

---

## Deployment Checklist

Before deploying to any non-local environment:

- [ ] Set `JWT_SECRET_KEY` to a strong random value (≥64 hex chars)
- [ ] Change `BOOTSTRAP_ADMIN_PASSWORD` before or immediately after first startup
- [ ] Set `CORS_ALLOWED_ORIGINS` to specific frontend origins (not `*`)
- [ ] Ensure `.env` is **not committed** to version control
- [ ] Use HTTPS (TLS) in front of the API — this service does not terminate TLS
- [ ] Rotate JWT secret if it was ever accidentally exposed
- [ ] Run `POST /benchmark/run` after deployment to validate accuracy baselines
