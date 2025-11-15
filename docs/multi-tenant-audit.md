# Multi-Tenant Implementation Audit (Nov 05 2025)

The table below summarises how each administration slice handles tenant ownership when creating and reading data. ✅ indicates the implementation follows the platform contract; ⚠️ highlights areas to revisit.

| Slice | Create Flow (Tenant Assignment) | Read Flow (Tenant Filtering) | Notes |
| --- | --- | --- | --- |
| **Users** (`app/features/administration/users`) | ✅ `UserManagementService.create_user(...)` now passes both `target_tenant_id` and `created_by_user` to `UserCrudService.create_user`, which persists `tenant_id` and audit fields. | ✅ All listing/query helpers use `BaseService.create_base_query`. Global admins call `create_tenant_join_query` to surface tenant names safely. | Ensure JWT/context provides the correct tenant when acting as non-global users. |
| **Secrets** (`app/features/administration/secrets`) | ✅ `SecretCrudService.create_secret` accepts `target_tenant_id` (or current tenant) and writes it alongside encrypted values. | ✅ CRUD/list endpoints instantiate the service with tenant context; `create_base_query` scopes rows per tenant. | Tenant override forms surface only active tenants via `get_available_tenants_for_user_forms`. |
| **SMTP Configurations** (`app/features/administration/smtp`) | ✅ `create_smtp_configuration` computes `effective_tenant_id = target_tenant_id or self.tenant_id` and stores it before hashing credentials. | ✅ Queries use `BaseService` helpers; global admins may view all while standard tenants see isolated records. | Password validation enforces complexity; errors appear if the new value fails checks. |
| **API Keys** (`app/features/administration/api_keys`) | ✅ Creation routes specify the tenant from dependency or override. | ✅ Listing uses tenant-scoped service queries. | Aligned with the same patterns as secrets. |
| **Audit Logs** (`app/features/administration/audit`) | ✅ Middleware order updated so `TenantMiddleware` runs before `AuthContextMiddleware` and `AuditLoggingMiddleware`, ensuring the correct tenant is stamped on new entries. | ✅ Table endpoints call `AuditCrudService`, which filters by `tenant_id` except for global admins. | Legacy rows created before the fix retain `tenant_id='unknown'`; no automated backfill applied. |
| **Tasks / Scheduled Jobs** (`app/features/administration/tasks`) | ✅ Job creation helpers include tenant in payload. | ✅ Data access uses tenant-aware queries. | Review before enabling background worker to confirm the Celery producer respects tenant scope. |
| **Tenants** (`app/features/administration/tenants`) | N/A (tenants are global records). | N/A | UI is restricted to global admins. |
| **Logs (Admin Activity)** (`app/features/administration/logs`) | ✅ Log entries are tied to the originating tenant via middleware context. | ✅ Fetching logs uses tenant-aware services so tenants see only their history. | Requires audit middleware fix (already applied). |

## Recent fixes

- `TenantMiddleware` now defaults to `"global"` (instead of `"unknown"`), preventing accidental loss of tenant context on admin operations.
- `AuthContextMiddleware` and `AuditLoggingMiddleware` normalise `tenant_id` so any missing/unknown values fall back to `"global"` for authenticated flows.
- User creation now honours the selected tenant; SMTP configuration creation already followed that contract.
- Modal focus restoration has been hardened so HTMX form submissions return focus to the originating control even after DOM updates.

Keep this report up to date whenever a slice adopts new multi-tenant behaviour or a regression is detected.
