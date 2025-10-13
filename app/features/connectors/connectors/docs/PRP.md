# PRP: Connectors Slice (Service Catalog + Installed Connectors)

**Feature Owner:** Business Automations – Connectors  
**Vertical Slice Path:** `app/features/connectors/`  
**Depends On:** `core/` (DB, settings, security, templates), `administration/secrets/` (optional), auth/tenants from core  
**Goal (V1):** Provide a complete **Connectors** slice that (a) renders a **service-catalog card view** of pre-seeded connector types, (b) lets a user **Add Connector** via a picker, (c) stores per‑instance **config/auth** in JSONB, (d) lists **installed connectors** as cards with **Configure** actions, and (e) exposes installed connectors for use by other slices (e.g., Content Broadcaster scheduling).

---

## 1) Explicit Scope (V1)

- **Catalog:** Read-only library of connector *types* (Twitter, WordPress, LinkedIn, etc.) shown as cards.  
- **Installed Connectors:** User-installed connector *instances* (e.g., “Marketing Twitter”, “Blog WP”).  
- **Add Connector Flow:** Picker from catalog → create instance → set status (inactive by default) → edit config/auth → activate.  
- **Config/Auth Storage:** JSONB columns with per‑connector schema validation at the API boundary; **auth** encrypted at rest.  
- **Cards UI:** Two tabs: **Catalog** and **Installed**. Cards show icon, name, description, status, and actions.  
- **APIs:** CRUD for installed connectors, read-only catalog, JSON-schema validation endpoints.  
- **Tenant Isolation:** All installed connectors tenant-scoped; catalog is global read-only seed.  
- **Compliance With Project Rules:** Vertical slice architecture, BaseService, AuditMixin, centralized imports, async SQLAlchemy, Pydantic v2, HTMX + Jinja, RBAC via dependencies.

**Out of Scope (V1):** OAuth callback implementations, rate-limit dashboards, connector usage analytics, advanced secrets vault UI, connector-level quotas. These can be placeholders or TODOs.

---

## 2) Data Model (PostgreSQL / SQLAlchemy 2.x)

> Follow `AuditMixin` (created_at/updated_at/created_by/updated_by/…); use JSONB for flexible fields; add strict DB indexes. Use async models/patterns per CLAUDE.md. All tenant-scoped tables include `tenant_id` (string, indexed).

### 2.1 connector_catalog (GLOBAL seed data; read-only at runtime)
- `id` (uuid, pk)
- `key` (text, unique, e.g., `twitter`, `wordpress`)
- `name` (text, not null)
- `description` (text, nullable)
- `category` (text, e.g., `Social`, `Web`, `Video`)
- `icon` (text, optional icon name/url)
- `auth_type` (text, enum-like: `oauth`, `api_key`, `basic`, `none`)
- `capabilities` (jsonb, default `{}`) – e.g., `{ "post_text": true, "post_media": true, "max_length": 280 }`
- `default_config_schema` (jsonb, default `{}`) – JSON Schema-like structure for `connectors.config`
- `created_at` (timestamp tz)
- **Indexes:** `idx_connector_catalog_key (key unique)`

> **Seed file:** `app/seed_connectors.py` populates at least Twitter + WordPress with realistic capability & schema examples.

**Example seeds (abbrev.):**
```json
{
  "twitter": {
    "name": "Twitter (X)",
    "description": "Post text and images to X.",
    "category": "Social",
    "icon": "brand-x",
    "auth_type": "oauth",
    "capabilities": {"post_text": true, "post_media": true, "max_length": 280},
    "default_config_schema": {
      "type": "object",
      "required": ["account_label"],
      "properties": {
        "account_label": {"type": "string", "title": "Account Label", "minLength": 2},
        "post_defaults": {
          "type": "object",
          "properties": {
            "append_hashtags": {"type": "array", "items": {"type": "string"}, "maxItems": 5}
          }
        }
      }
    }
  },
  "wordpress": {
    "name": "WordPress",
    "description": "Publish posts and pages via REST.",
    "category": "Web",
    "icon": "brand-wordpress",
    "auth_type": "basic",
    "capabilities": {"post_text": true, "post_media": true, "supports_html": true},
    "default_config_schema": {
      "type": "object",
      "required": ["base_url", "site_label"],
      "properties": {
        "base_url": {"type": "string", "format": "uri"},
        "site_label": {"type": "string", "minLength": 2},
        "default_status": {"type": "string", "enum": ["draft", "publish"], "default": "draft"}
      }
    }
  }
}
```

### 2.2 connectors (TENANT-scoped installed instances)
- `id` (uuid, pk)
- `tenant_id` (string, indexed)  **← add via project’s tenant pattern**
- `catalog_id` (uuid, fk → connector_catalog.id)
- `name` (text, not null) – user label shown on cards (e.g., “Marketing Twitter”)
- `status` (text enum: `inactive`, `active`, `error`; default `inactive`)
- `config` (jsonb, default `{}`) – validated against `default_config_schema`
- `auth` (jsonb, default `{}`) – sensitive tokens/keys; **encrypt at rest**
- `tags` (jsonb array, default `[]`)
- Audit fields via `AuditMixin`
- **Indexes:** `idx_connectors_tenant (tenant_id)`, `idx_connectors_catalog (catalog_id)`

**Constraints/Validation:**
- `name` unique per tenant.
- `auth` must pass minimal presence rules for `auth_type` (e.g., API key present if `api_key`).

---

## 3) Routes & Endpoints (FastAPI, async)

Prefix the slice routes with `/features/connectors`. Provide API and HTMX endpoints split by files (`api_routes.py`, `form_routes.py`, `dashboard_routes.py`). Use dependency injection for `db`, `tenant`, `current_user` per CLAUDE.md.

### 3.1 Catalog (read-only)
- `GET /catalog` (HTMX/Jinja): Render **catalog card grid** from `connector_catalog`.
- `GET /api/catalog` (JSON): Return list with schema & capabilities for client rendering.

### 3.2 Installed Connectors
- `GET /installed` (HTMX/Jinja): Render **installed connectors card grid** (tenant-scoped).
- `GET /api/installed` (JSON): List installed connectors.
- `POST /api/connectors`:
  - **Body:** `{ "catalog_id": "uuid", "name": "string", "config": {...}, "auth": {...} }`
  - **Validate** `config` against catalog’s `default_config_schema` (server-side); **mask**/encrypt `auth`.
  - **Default status:** `inactive`
- `PUT /api/connectors/{id}`:
  - Update `name`, `config`, `auth`, `status`. Re-validate `config`; re-encrypt `auth`.
- `DELETE /api/connectors/{id}`:
  - Soft delete or hard delete (V1: hard delete is acceptable). Ensure tenant ownership.

### 3.3 Validation/Schema Helper
- `POST /api/validate-config`:
  - **Body:** `{ "catalog_key": "twitter"|"wordpress", "config": {...} }`
  - Validate against `default_config_schema`, return structured errors.

---

## 4) Services (Business Logic)

Create `services/connector_service.py` with `ConnectorService(BaseService[Connector])`:

- `list_catalog()` – global query (no tenant filter)
- `list_installed(tenant_id)` – tenant-scoped
- `install_connector(tenant_id, catalog_id, name, config, auth)` – validate config with schema, encrypt auth, create row
- `update_connector(tenant_id, id, patch)` – merge/validate, rotate encryption if needed
- `delete_connector(tenant_id, id)` – delete row
- `validate_config(catalog_key, config)` – JSON schema validation routine
- `get_publish_targets(tenant_id)` – return `id, name, catalog.key, capabilities` for scheduling UIs

> **Encryption:** Use `core/secrets_manager.py` or `cryptography.Fernet` wrapper to encrypt/decrypt `auth` transparently in the service layer. Never return raw secrets from routes.

---

## 5) Templates (HTMX + Jinja + Tabler)

Directory: `app/features/connectors/templates/connectors/`

- `catalog.html` – Grid of catalog cards (icon, name, short description, Add button).  
  - “Add Connector” → opens modal with **picker** (list of catalog items) → proceed to **create form**.
- `installed.html` – Grid of installed connectors (status badge, name, catalog key/icon).  
  - Actions: **Configure** (inline/edit modal), **Activate/Deactivate**, **Delete**.
- `partials/form_create.html` – Form rendered from schema (server-side mapping from JSON Schema types → inputs).  
- `partials/form_edit.html` – Same as create; prefilled values.
- `partials/toast.html` – Reusable success/error htmx swaps.

**HTMX Actions:** Use `hx-get` to load forms, `hx-post` for submit, `hx-swap="outerHTML"` for card updates.

---

## 6) Validation Rules (No Ambiguity)

- **Server-side** JSON schema validation is **mandatory** before insert/update. Reject requests with 400 + error map `{field: [errors...]}`.
- **Name uniqueness** enforced per-tenant.
- **Auth storage** must be encrypted; never render secrets back to the client once saved (show masked values, with “Update Secret” workflow).
- **Status transitions:** `inactive ↔ active`, any → `error` (set by system if health checks fail). V1 does not implement health checks; allow manual status set by user with warning.

---

## 7) Security & RBAC

- All installed connector endpoints require authenticated user and tenant verification (`get_current_user`, `tenant_dependency`).
- **Global catalog read** allowed to all authenticated users; writes disallowed at runtime.
- Only **tenant admins/owners** can add, edit, delete connectors (use role checks from auth slice).

---

## 8) Migrations & Seeding

- Alembic migration for both tables with indexes and JSONB columns.
- Seed script `app/seed_connectors.py` (idempotent) to populate `connector_catalog` with `twitter`, `wordpress` at minimum.
- Add Make target `make seed-connectors` to run seeding.

---

## 9) Testing (must implement)

- **Unit:** Config validation (positive/negative), encryption roundtrip, service CRUD, schema mismatch errors.
- **Integration:** End-to-end: list catalog → create installed connector → edit config → activate → list installed.
- **UI (Playwright):** Catalog cards render; “Add Connector” flow works; form validation shows helpful errors.

---

## 10) Success Criteria

- Catalog cards render with seed data.
- Can install a connector with valid config/auth; appears in Installed list.
- Editing config/auth works; secrets are encrypted; masked in UI.
- Status toggles and delete work tenant-safely.
- JSON schema validation prevents invalid config.
- `get_publish_targets()` returns correct structure for other slices to schedule against.

---

## 11) Deliverables Checklist

- Vertical slice directories and files created
- SQLAlchemy models + Alembic migrations
- Seed script and Make target
- Services with full validation + encryption
- Routes (API + HTMX) with RBAC
- Templates (cards, forms, modals) with HTMX flows
- Tests (unit, integration, basic UI)
- Docs: brief README in slice root explaining usage
