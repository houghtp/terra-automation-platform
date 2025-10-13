# Connectors Slice - Implementation Guide

## Overview

This slice implements a service catalog and installed connectors system per the PRP specification in `INITIAL.md`.

## Architecture

### Two-Tier Model:

1. **Connector Catalog** (`connector_catalog` table)
   - Global read-only catalog of available connector types
   - Seeded via `app/seed_connectors.py`
   - Examples: Twitter, WordPress, LinkedIn, Medium

2. **Installed Connectors** (`connectors` table)
   - Tenant-scoped installed instances
   - Each instance has custom config and encrypted auth
   - Status: inactive (default), active, error

## Current Implementation Status

### ✅ Completed (Phase 1 - Models & Seeding)

1. **Models** (`models.py`)
   - `ConnectorCatalog`: Global catalog model with capabilities and config schema
   - `Connector`: Tenant-scoped installed instances with AuditMixin
   - Pydantic schemas: `ConnectorCatalogResponse`, `ConnectorResponse`, `ConnectorCreate`, `ConnectorUpdate`
   - Enums: `AuthType` (oauth, api_key, basic, none), `ConnectorStatus` (inactive, active, error)

2. **Seeding** (`app/seed_connectors.py`)
   - Idempotent seeding script
   - Seeds 4 connectors: Twitter, WordPress, LinkedIn, Medium
   - Each with complete JSON Schema for validation
   - Run via: `make seed-connectors`

3. **Makefile Target**
   - Added `seed-connectors` target to Makefile

### 🚧 In Progress (Phase 1 - Migration)

**Database Migration**
- Need to create Alembic migration for new tables
- Current blocker: Existing `services.py` and `routes.py` import old model names
- Next step: Clean up or rewrite services.py and routes.py to match new models

### ⏳ Pending

#### Phase 2: Service Layer
- Rewrite `ConnectorService` inheriting from `BaseService[Connector]`
- Methods needed:
  - `list_catalog()` - Global catalog query (no tenant filter)
  - `list_installed(tenant_id)` - Tenant-scoped installed connectors
  - `install_connector(...)` - Create instance with validation & encryption
  - `update_connector(...)` - Update with re-validation & re-encryption
  - `delete_connector(...)` - Hard delete (V1 acceptable)
  - `validate_config(catalog_key, config)` - JSON Schema validation
  - `get_publish_targets(tenant_id)` - For content broadcaster integration

#### Phase 3: Routes (3 files per PRP)
Split routes into:
- `routes/api_routes.py` - Pure JSON API endpoints
- `routes/form_routes.py` - HTMX form handling
- `routes/dashboard_routes.py` - Page rendering

Endpoints needed:
- `GET /catalog` - Render catalog card grid (HTMX)
- `GET /api/catalog` - JSON catalog list
- `GET /installed` - Render installed card grid (HTMX)
- `GET /api/installed` - JSON installed list
- `POST /api/connectors` - Create instance
- `PUT /api/connectors/{id}` - Update instance
- `DELETE /api/connectors/{id}` - Delete instance
- `POST /api/validate-config` - Validate config against schema

#### Phase 4: Templates (Card-Based UI)
Create Jinja2 templates:
- `templates/connectors/catalog.html` - Service catalog with card grid
- `templates/connectors/installed.html` - Installed connectors with card grid
- `templates/connectors/partials/card_catalog.html` - Single catalog card
- `templates/connectors/partials/card_installed.html` - Single installed card
- `templates/connectors/partials/form_create.html` - Create form modal
- `templates/connectors/partials/form_edit.html` - Edit form modal
- `templates/connectors/partials/toast.html` - Success/error messages

**UI Requirements:**
- Two tabs: "Catalog" and "Installed"
- Card view (NOT table view as currently implemented)
- Each catalog card shows: icon, name, description, category, "Add" button
- Each installed card shows: status badge, name, icon, "Configure", "Activate/Deactivate", "Delete"
- Modal forms for add/edit with dynamic field generation from JSON Schema

#### Phase 5: Security & Validation
- JSON Schema validation using catalog's `default_config_schema`
- Encrypt `auth` field at rest using `core/secrets_manager.py` or `cryptography.Fernet`
- Mask secrets in responses (never return raw auth)
- RBAC: Require tenant admin/owner for mutating operations
- Use `get_current_user` and `tenant_dependency` on all endpoints

#### Phase 6: Testing
- Unit tests: Config validation, encryption roundtrip, CRUD operations
- Integration tests: Full flow from catalog → install → configure → activate
- UI tests (Playwright): Catalog render, add flow, validation messages

#### Phase 7: Documentation
- API documentation
- Usage examples
- Troubleshooting guide

## Key Design Decisions

1. **Card View vs Table View**
   - PRP specifies card/service catalog view
   - Current implementation uses table view (needs replacement)

2. **Auth Encryption**
   - `auth` JSONB field encrypted at rest
   - Never exposed in API responses
   - Mask values when needed with "Update Secret" workflow

3. **Config Validation**
   - Server-side JSON Schema validation mandatory
   - Validate against catalog's `default_config_schema` before insert/update
   - Return structured error map: `{field: [errors...]}`

4. **Status Transitions**
   - `inactive` (default) ↔ `active`
   - Any status → `error`
   - Manual status control in V1 (no automatic health checks)

5. **Name Uniqueness**
   - Connector names must be unique per tenant
   - Enforced at database level with composite unique index

## Integration Points

### Content Broadcaster
The `get_publish_targets(tenant_id)` method returns connectors formatted for scheduling:
```python
{
    "id": "uuid",
    "name": "Marketing Twitter",
    "catalog_key": "twitter",
    "capabilities": {...}
}
```

### Secrets Management
Optional integration with `administration/secrets/` slice for credential storage.

## Database Schema

### connector_catalog (GLOBAL)
```sql
id              VARCHAR(36) PK
key             VARCHAR(100) UNIQUE NOT NULL
name            VARCHAR(255) NOT NULL
description     TEXT
category        VARCHAR(50) NOT NULL
icon            VARCHAR(100)
auth_type       VARCHAR(20) NOT NULL
capabilities    JSONB DEFAULT '{}'
default_config_schema JSONB DEFAULT '{}'
created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

### connectors (TENANT-SCOPED)
```sql
id              VARCHAR(36) PK
tenant_id       VARCHAR(64) NOT NULL INDEXED
catalog_id      VARCHAR(36) FK -> connector_catalog.id
name            VARCHAR(255) NOT NULL
status          VARCHAR(20) NOT NULL DEFAULT 'inactive'
config          JSONB DEFAULT '{}'
auth            JSONB DEFAULT '{}' -- ENCRYPTED
tags            JSONB DEFAULT '[]'
-- AuditMixin fields: created_at, updated_at, created_by, updated_by, created_by_name, updated_by_name

UNIQUE(name, tenant_id)
INDEX(tenant_id)
INDEX(catalog_id)
```

## Development Commands

```bash
# Seed connector catalog
make seed-connectors

# Create migration (once services.py is fixed)
python3 manage_db.py migrate -m "Update connector tables"

# Apply migration
python3 manage_db.py upgrade

# Run tests (once implemented)
pytest tests/connectors/ -v
```

## Next Immediate Steps

1. **Fix Import Errors**
   - Update or remove old `services.py` and `routes.py` that reference old models
   - Ensure migration can run without circular import errors

2. **Create Migration**
   - Generate Alembic migration for `connector_catalog` and `connectors` tables
   - Apply migration to create tables

3. **Implement Service Layer**
   - Create new `ConnectorService` inheriting from `BaseService[Connector]`
   - Implement all required methods with encryption

4. **Implement Routes**
   - Split into api_routes, form_routes, dashboard_routes
   - Wire up dependency injection (db, tenant, current_user)

5. **Build Templates**
   - Create card-based UI with tabs
   - Implement HTMX interactions

6. **Add to Main Router**
   - Register connectors router in `app/api/v1/router.py`
   - Ensure routes are accessible at `/features/connectors/`

## Reference Implementation

Gold standard: `app/features/administration/users/`
- Follows vertical slice architecture
- Uses BaseService properly
- Has proper CRUD routes split
- Good template examples

## Questions & Decisions Log

**Q: Should we keep existing `available_connectors` and `tenant_connectors` tables?**
**A:** No. PRP specifies `connector_catalog` and `connectors`. We should migrate/replace the old tables.

**Q: How to handle OAuth callback flows?**
**A:** Out of scope for V1. Store OAuth tokens manually in `auth` field for now.

**Q: Rate limiting per connector?**
**A:** Out of scope for V1. Can be added later.

## Resources

- PRP Specification: [`INITIAL.md`](./INITIAL.md)
- Project Plan: [`PROJECT_PLAN_Connectors_Slice.md`](./PROJECT_PLAN_Connectors_Slice.md)
- Seed Script: [`/app/seed_connectors.py`](/app/seed_connectors.py)
- Models: [`models.py`](./models.py)
