# Tenant Switching Feature for Global Admin

## Overview
Global admins can now switch their session context to view data from specific tenants without logging out and back in. This feature enables global admins to:
- View tenant-specific logs
- Access tenant-specific data
- Troubleshoot tenant issues
- Switch back to global view at any time

## Implementation

### Backend Components

1. **Service Layer** (`app/features/auth/services/tenant_switch_service.py`)
   - `TenantSwitchService`: Manages tenant switching in session
   - Methods: `set_switched_tenant()`, `get_switched_tenant()`, `clear_switched_tenant()`, `is_tenant_switched()`

2. **API Routes** (`app/features/auth/routes/tenant_switch_routes.py`)
   - `GET /auth/tenant-switch/available-tenants`: List all tenants
   - `POST /auth/tenant-switch/switch`: Switch to specific tenant
   - `POST /auth/tenant-switch/clear`: Return to global view
   - `GET /auth/tenant-switch/current`: Get current switched tenant status

3. **Middleware Update** (`app/middleware/auth_context.py`)
   - `AuthContextMiddleware` now checks for switched tenant context
   - Overrides `request.state.tenant_id` for global admin when tenant is switched
   - Logs tenant switching for audit purposes

4. **Session Middleware** (`app/main.py`)
   - Added `SessionMiddleware` to enable session storage
   - Uses secure secret key from environment or generates random key

### Frontend Components

1. **Tenant Selector UI** (`app/templates/base.html`)
   - Dropdown in navigation header (visible only to global admin)
   - Shows current tenant or "Global View"
   - Lists all available tenants with active/inactive badges
   - Highlights currently selected tenant

2. **JavaScript** (`app/templates/base.html`)
   - `initTenantSwitcher()`: Initialize tenant selector on page load
   - `switchTenant(tenantId, tenantName)`: Switch to tenant via API
   - `clearTenantSwitch()`: Return to global view
   - Auto-reload page after switching to apply new tenant context

## Usage

### As Global Admin:

1. **View Tenant Selector**
   - Log in as global admin
   - See tenant dropdown next to user menu in header
   - Button shows "Global View" when not switched

2. **Switch to Tenant**
   - Click tenant dropdown
   - Select tenant from list (active tenants highlighted)
   - Page reloads with tenant context applied
   - Button now shows "Tenant: [Tenant Name]"

3. **View Tenant Data**
   - All logs, users, and data now filtered to selected tenant
   - Audit logs show tenant-specific events
   - Application logs show tenant-specific messages

4. **Return to Global View**
   - Click tenant dropdown
   - Select "Global View" option
   - Page reloads with global context restored

## Security

- Only users with `role = 'global_admin'` can access tenant switching
- All API endpoints validate user role before allowing switch
- Tenant switching stored in server-side session (not in JWT)
- Audit logs track all tenant switch events
- Session expires on logout or session timeout

## Data Isolation

- Users only see their own tenant's logs (strict isolation)
- Global admin sees all logs when in "Global View"
- Global admin sees only switched tenant's logs when switched
- Middleware ensures correct tenant_id is always set for audit logs

## Testing Checklist

- [ ] Global admin can see tenant selector dropdown
- [ ] Non-admin users don't see tenant selector
- [ ] Tenant list loads correctly
- [ ] Switching to tenant applies correct context
- [ ] Logs show only switched tenant's data
- [ ] Audit logs record tenant switches
- [ ] Returning to global view works correctly
- [ ] Page reloads apply new context immediately
- [ ] Session persists across page navigations
- [ ] Logout clears tenant switch session

## Configuration

### Environment Variables

- `SESSION_SECRET_KEY`: Secret key for session encryption (auto-generated if not set)

### Dependencies

- `starlette.middleware.sessions.SessionMiddleware`: Session management
- Bootstrap dropdown: UI component
- HTMX: Not required for this feature (uses fetch API)

## Future Enhancements

- [ ] Add tenant switch history/breadcrumb
- [ ] Show tenant-specific dashboard stats when switched
- [ ] Add "Quick Switch" to recent tenants
- [ ] Persist last switched tenant preference
- [ ] Add tenant switch duration tracking
- [ ] Show tenant color theme when switched
