# PROJECT_PLAN: Connectors Slice (Service Catalog + Installed)

Status legend: ☐ Not Started · ⏳ In Progress · ✅ Done

## Phase 0 — Prep
- ✅ Create vertical slice scaffold at `app/features/connectors/`
- ✅ Add slice README with overview and endpoints
- ✅ Register routers under `/features/connectors` and aggregate into `api/v1/router.py`

## Phase 1 — Database & Seeding
- ✅ Create models and Alembic migration for `connector_catalog` (GLOBAL)
- ✅ Create models and Alembic migration for `connectors` (TENANT-scoped, includes `tenant_id`)
- ✅ Ensure both models inherit `AuditMixin`
- ✅ Add indexes per PRP
- ✅ Implement `app/seed_connectors.py` with `twitter`, `wordpress`, `linkedin`, `medium` seeds
- ✅ Add Make target `seed-connectors` and document in README

## Phase 2 — Services
- ✅ Implement `ConnectorService(BaseService[Connector])`
- ✅ Implement `list_catalog()` (global, read-only)
- ✅ Implement `list_installed(tenant_id)`
- ✅ Implement `install_connector(...)` with JSON schema validation + encryption
- ✅ Implement `update_connector(...)` with partial updates, re-validation, re-encryption
- ✅ Implement `delete_connector(...)` (hard delete acceptable for V1)
- ✅ Implement `validate_config(catalog_key, config)`
- ✅ Implement `get_publish_targets(tenant_id)`

## Phase 3 — Routes (API + HTMX)
- ✅ `GET /catalog` (HTMX) – card grid
- ✅ `GET /api/catalog` (JSON)
- ✅ `GET /installed` (HTMX) – card grid
- ✅ `GET /api/installed` (JSON)
- ✅ `POST /api/connectors` – create; validate config; encrypt auth; default `inactive`
- ✅ `PUT /api/connectors/{id}` – update; validate; encrypt; allow status toggle
- ✅ `DELETE /api/connectors/{id}` – delete; tenant-scope enforced
- ✅ `POST /api/validate-config` – validation helper

## Phase 4 — Templates (HTMX + Jinja + Tabler)
- ✅ `catalog.html` – service catalog cards with Add action
- ✅ `installed.html` – installed cards with Configure/Activate/Delete
- ✅ `partials/form_create.html` – server-side generated from JSON schema
- ✅ `partials/form_edit.html` – as above, prefilled
- ✅ `partials/toast.html` – success/error snackbars
- ✅ Wire HTMX flows: picker → create → update card; edit modal → save → swap

## Phase 5 — Security & RBAC
- ✅ Apply `get_current_user`, `tenant_dependency` to all installed endpoints
- ✅ Enforce tenant admin/owner role for mutating ops
- ✅ Ensure secrets never returned in responses (mask when needed)
- ✅ Encrypt `auth` at rest via Fernet symmetric encryption

## Phase 6 — Testing
- ⏳ Unit tests: validation, encryption, CRUD
- ⏳ Integration tests: full flow from catalog to installed
- ⏳ UI tests (Playwright): add connector flow and validation messages
- ⏳ Add tests to CI via Make targets

## Phase 7 — Documentation & DX
- ✅ Slice README with usage examples
- ⏳ Update `docs/architecture.md` with connectors slice
- ⏳ Add troubleshooting tips (validation errors, auth encryption)
- ✅ Demo script or seeds to showcase in dev

## Exit Criteria
- ⏳ All phases complete with ✅ (Phases 0-5 done, 6-7 pending tests & docs)
- ⏳ Manual smoke test passes: add → configure → activate → list publish targets (requires authentication)
- ☐ Code review via `.claude/commands/review.md` shows no 🚨 issues

## Implementation Notes

### Completed (2025-10-10)
- **Database Migration**: Successfully migrated from old connector tables to new PRP-compliant schema
- **Catalog Seeding**: 4 connectors seeded (Twitter, WordPress, LinkedIn, Medium)
- **Service Layer**: Full implementation with Fernet encryption for auth credentials
- **Routes**: Split into api_routes, dashboard_routes, form_routes
- **Templates**: Card-based UI with HTMX dynamic updates
- **Server**: Running successfully on http://0.0.0.0:8000

### Pending
- Unit and integration tests (Phase 6)
- Architecture documentation update (Phase 7)
- Manual end-to-end testing with authenticated user
