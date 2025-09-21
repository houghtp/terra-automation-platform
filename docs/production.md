# Production checklist and multi-tenant guidance

This document summarizes the production readiness features and recommended steps for operating a multi-tenant automation platform built from this template.

## Overview

This template provides:

- Tenant middleware and dependency (`app/middleware/tenant.py`, `app/deps/tenant.py`).
- Structured JSON logging with `request_id` and `tenant_id` fields (`app/core/logging.py`).
- Demo slice updated to be tenant-aware (models, services, routes).
- Example Alembic migration adding `tenant_id` to `demo_items`.

Treat this repo as a starting point. Before deploying, review the checklist below.

## Tenant onboarding

- Create a canonical `Tenant` record for each customer.
- For each external provider (M365, Google, Slack, etc.), store provider credentials scoped to the tenant.
- Use provider-specific onboarding (OAuth/admin-consent/service accounts) and persist tokens securely.

## Data model

- All tenant-scoped tables must include a `tenant_id` column (indexed).
- Persist provider resources (mailboxes, drives, calendars) with `tenant_id`.
- Job runs, audit logs, and metrics must be tagged with `tenant_id`.

## Authentication and tenant trust

- Resolve tenant identity from authenticated tokens (JWT claims) where possible.
- Treat headers like `X-Tenant-ID` as untrusted unless validated against auth claims.
- Provide an admin reconsent flow for provider connections.

## Secrets and token lifecycle

- Use a secrets manager (Vault, Azure Key Vault) or DB encryption with KMS for storing provider credentials.
- Implement refresh, rotation, revocation handling, and alerting for expired/invalid tokens.

## Runtime isolation

- Workers must accept `tenant_id` in job payloads and load tenant credentials at runtime.
- Apply per-tenant rate-limiting and throttling to protect provider quotas.
- Consider tenant-based queues or partitioning for high-scale tenants.

## Auditing and observability

- Logs must include `request_id` and `tenant_id` fields.
- Export metrics per tenant (or aggregate with tenant labels) and implement tracing.
- Store immutable audit events for all actions performed on external systems.

## Migrations and upgrades

- For live production systems, use a two-step migration when introducing `tenant_id`:
  1. Add nullable `tenant_id` column.
  2. Backfill tenant values via a controlled script.
  3. Alter column to NOT NULL and add index.

- The template includes a convenience migration that sets a default value for demo usage; modify it for production upgrades.

## Recommended next repo steps

1. Add `Tenant` and `ProviderCredentials` models + migrations.
2. Implement provider adapters and onboarding endpoints (OAuth) with secure token storage.
3. Add mailbox/resource discovery jobs and persistence.
4. Implement worker skeleton and job runner that handles tenant-scoped executions.
5. Add integration tests with mocked provider APIs.

## Security checklist

- Audit all logs for PII and filter/redact sensitive fields.
- Confirm CSP is hardened (avoid `unsafe-inline`) before enabling public-facing UI.
- Use HTTPS for all external callbacks and endpoints.

## Operational notes

- Document tenant onboarding and reconsent procedures for customer support.
- Implement tenant deletion workflows that remove tenant data and credentials upon request.

---

This document is a living guide — update it as your product decisions evolve.
