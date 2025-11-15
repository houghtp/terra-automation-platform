# TerraAutomationPlatform - Claude Code Reference

> **Comprehensive codebase reference for AI-assisted development**

This document captures the complete technical architecture, patterns, and conventions used in this FastAPI codebase to ensure consistent AI-assisted development.

---

## 📋 Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Architecture Patterns](#architecture-patterns)
4. [Code Style & Conventions](#code-style--conventions)
5. [Database Patterns](#database-patterns)
6. [Authentication & Authorization](#authentication--authorization)
7. [Testing Approach](#testing-approach)
8. [Development Commands](#development-commands)
9. [Key Design Decisions](#key-design-decisions)

---

## 🛠 Tech Stack

### Core Framework
- **Python**: 3.10.12
- **FastAPI**: 0.104.x (Modern async web framework)
- **Uvicorn**: 0.23.x (ASGI server)
- **Pydantic**: 2.x (Data validation with Settings)

### Database
- **PostgreSQL**: Primary database (async)
- **SQLAlchemy**: 2.0.23+ (Async ORM)
- **AsyncPG**: 0.28+ (PostgreSQL async driver)
- **Psycopg2-binary**: 2.9.9+ (Sync driver for migrations)
- **Alembic**: 1.16.5+ (Database migrations)

### Frontend
- **Jinja2**: 3.1.2+ (Server-side templating)
- **HTMX**: Dynamic interactions without heavy JavaScript
- **Tabler**: Admin dashboard UI components
- **Tabulator**: Advanced data tables

### Authentication & Security
- **python-jose[cryptography]**: 3.3.0+ (JWT handling)
- **passlib[bcrypt]**: 1.7.4+ (Password hashing)
- **bcrypt**: 3.2.x (Password hashing backend)
- **cryptography**: 41.0+ (Encryption for sensitive data)
- **pyotp**: 2.9+ (TOTP for MFA)
- **qrcode**: 7.4.2+ (QR code generation for MFA)
- **email-validator**: 2.0+ (Email validation)

### Background Processing
- **Celery**: 5.3+ (Distributed task queue)
- **Redis**: 4.5+ (Message broker and result backend)
- **Kombu**: 5.3+ (Celery messaging)

### Monitoring & Logging
- **structlog**: 23.1+ (Structured logging)
- **prometheus-client**: 0.17+ (Metrics collection)

### AI & Integration
- **openai**: 1.1+ (OpenAI API SDK)
- **anthropic**: 0.8+ (Claude API SDK)
- **beautifulsoup4**: 4.12+ (Web scraping)
- **firecrawl-py**: 0.1+ (Web crawling)
- **youtube-transcript-api**: 0.6+ (YouTube transcripts)
- **aiohttp**: 3.8+ (Async HTTP client)

### Data Processing
- **pandas**: 2.0+ (Data analysis)
- **plotly**: 5.14+ (Visualizations)
- **openpyxl**: 3.1+ (Excel file handling)

### Testing
- **pytest**: 8.0+
- **pytest-asyncio**: 0.24+ (Async test support)
- **pytest-httpx**: 0.30+ (HTTP mocking)
- **pytest-playwright**: 0.4+ (Browser automation)
- **playwright**: 1.40+ (UI testing)
- **factory-boy**: 3.3+ (Test data factories)
- **faker**: 25.0+ (Fake data generation)

### HTTP Clients
- **httpx**: 0.24+ (Modern async HTTP client)
- **requests**: 2.28+ (Sync HTTP client)

### Utilities
- **python-dotenv**: 1.0+ (Environment variables)
- **python-multipart**: 0.0.6+ (Form data handling)

---

## 📁 Project Structure

### High-Level Organization

```
terra-automation-platform/
├── app/                           # Main application code
│   ├── api/                      # Versioned API aggregation
│   │   ├── v1/                  # API version 1
│   │   │   └── router.py       # V1 router aggregation
│   │   └── webhooks/           # Webhook system routes
│   ├── deps/                     # Shared dependencies
│   │   └── tenant.py           # Tenant dependency injection
│   ├── features/                 # Vertical slices (features)
│   │   ├── core/               # Shared infrastructure
│   │   ├── auth/               # Authentication slice
│   │   ├── administration/     # Admin features
│   │   │   ├── audit/         # Audit logging
│   │   │   ├── logs/          # Application logs viewer
│   │   │   ├── secrets/       # Secrets management
│   │   │   ├── smtp/          # Email configuration (standardized to tenant_id)
│   │   │   ├── tenants/       # Tenant management
│   │   │   ├── users/         # User management (GOLD STANDARD - standardized to tenant_id)
│   │   │   ├── tasks/         # Background tasks
│   │   │   └── api_keys/      # API key management (standardized to tenant_id)
│   │   ├── dashboard/          # Main dashboard
│   │   ├── monitoring/         # System monitoring
│   │   ├── tasks/              # Task management
│   │   ├── business_automations/  # Business automation features
│   │   │   └── content_broadcaster/  # Content broadcasting
│   │   └── connectors/         # External integrations
│   ├── integrations/            # Integration base classes
│   ├── middleware/              # Custom middleware
│   ├── static/                  # Global static files (CSS, JS)
│   ├── templates/               # Shared Jinja2 templates
│   ├── main.py                  # Application entry point
│   ├── seed_data.py            # Database seeding
│   └── seed_connectors.py      # Connector seeding
├── tests/                        # All test files
│   ├── compliance/             # Compliance validation tests
│   ├── integration/            # Integration tests
│   ├── performance/            # Performance tests
│   ├── ui/                     # Playwright UI tests
│   ├── conftest.py            # Global test fixtures
│   └── utils.py               # Test utilities
├── docs/                         # Documentation
├── scripts/                      # Utility scripts
├── migrations/                   # Alembic database migrations
│   └── versions/              # Migration version files
├── monitoring/                   # Prometheus/Grafana configs
├── logs/                        # Application log files
├── .claude/                     # Claude Code configuration
├── .github/                     # GitHub workflows
├── .vscode/                     # VSCode settings
├── docker-compose.yml          # Development docker setup
├── docker-compose.production.yml  # Production docker setup
├── docker-compose.monitoring.yml  # Monitoring stack
├── Dockerfile                   # Development container
├── Dockerfile.production       # Production container
├── Makefile                    # Development commands
├── manage_db.py               # Database management CLI
├── alembic.ini                # Alembic configuration
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python dependencies
└── .env.example              # Environment variables template
```

### Vertical Slice Structure

Each feature follows **Vertical Slice Architecture**:

```
app/features/{feature_name}/
├── models.py           # Pydantic models AND SQLAlchemy models
├── db_models.py       # Alternative: Separate DB models
├── services/          # Business logic layer
│   ├── crud_services.py     # CRUD operations
│   ├── dashboard_services.py # Dashboard-specific logic
│   └── form_services.py     # Form handling logic
├── routes/            # FastAPI endpoints
│   ├── __init__.py          # Router aggregation
│   ├── crud_routes.py       # CRUD endpoints
│   ├── form_routes.py       # Form/HTMX endpoints
│   ├── dashboard_routes.py  # Dashboard views
│   └── api_routes.py        # Pure API endpoints
├── templates/{feature}/     # Feature-specific templates
│   └── partials/           # HTMX partial templates
├── static/{feature}/        # Feature-specific assets
└── tests/                  # Feature-specific tests
```

### Core Infrastructure (`app/features/core/`)

```
app/features/core/
├── config.py              # Pydantic Settings configuration
├── database.py            # SQLAlchemy setup with auto-discovery
├── templates.py           # Jinja2 template configuration
├── logging.py            # Structlog configuration
├── security.py           # Security utilities, password hashing
├── secrets_manager.py    # Secrets management abstraction
├── bootstrap.py          # Application bootstrap logic
├── validation.py         # Form validation utilities
├── rate_limiter.py       # Rate limiting implementation
├── versioning.py         # API versioning middleware
├── api_security.py       # API security middleware
├── enhanced_base_service.py   # Base service class (GOLD STANDARD)
├── sqlalchemy_imports.py      # Centralized SQLAlchemy imports
├── route_imports.py           # Centralized route imports
├── audit_mixin.py            # Audit fields mixin for models
├── log_viewer.py             # Log viewing routes
├── static/                   # Core static assets
└── templates/                # Core templates
```

---

## 🏗 Architecture Patterns

### 1. Vertical Slice Architecture

**Philosophy**: Each feature owns its complete vertical stack from UI to database.

**Benefits**:
- **High cohesion**: Related code stays together
- **Low coupling**: Features are independent
- **Easy to understand**: Follow one feature from top to bottom
- **Parallel development**: Teams can work on different slices

**Rules**:
- ✅ Each slice has its own models, services, routes, templates
- ✅ Slices communicate through well-defined interfaces
- ✅ Shared code goes in `core/`
- ❌ Don't access other slices' models directly
- ❌ Don't share services between slices

### 2. Dependency Injection Pattern

**FastAPI's built-in DI system** is used extensively:

```python
# Database session injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# Usage in routes
@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    # tenant_id, db, and current_user are automatically injected
    pass
```

**Common Dependencies**:
- `get_db`: Database session
- `tenant_dependency`: Tenant ID extraction and validation
- `get_current_user`: Current authenticated user
- `get_admin_user`: Admin role validation
- `get_global_admin_user`: Global admin validation
- `rate_limit_api`: Rate limiting

**CRITICAL: tenant_id Parameter Naming Convention**:

⚠️ **ALWAYS use `tenant_id` as the parameter name, NOT `tenant`**:

```python
# ✅ CORRECT - Use tenant_id
@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),  # ✅ Parameter named tenant_id
    current_user: User = Depends(get_current_user)
):
    service = UserService(db, tenant_id)  # ✅ Pass tenant_id to service
    return await service.list_users()

# ❌ WRONG - Do NOT use tenant
@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),  # ❌ Wrong parameter name
    current_user: User = Depends(get_current_user)
):
    service = UserService(db, tenant)  # ❌ Inconsistent with codebase
    return await service.list_users()
```

**Why this matters**:
- Consistency across the entire codebase
- `tenant_id` is more explicit than `tenant` (indicates it's an ID string, not an object)
- Service layer and BaseService expect `tenant_id` as the parameter name
- Prevents confusion between tenant objects and tenant ID strings

**CRITICAL: Do NOT check `if not self.tenant_id` in services**:

```python
# ❌ WRONG - This breaks global admin access
class MyService(BaseService[MyModel]):
    async def list_items(self):
        if not self.tenant_id:  # ❌ Global admins have tenant_id=None by design!
            raise ValueError("Tenant ID required")
        # ...

# ✅ CORRECT - Let BaseService handle tenant filtering
class MyService(BaseService[MyModel]):
    async def list_items(self):
        stmt = self.create_base_query(MyModel)  # ✅ Automatically handles tenant filtering
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

**Remember**: BaseService converts `tenant_id="global"` to `None` for global admins. This is intentional! When `tenant_id is None`, queries return ALL records across all tenants. See "Multi-Tenancy Pattern" section for details.

**How to verify**: Search the codebase for examples:
```bash
grep -r "tenant_id: str = Depends(tenant_dependency)" app/features
```

### 3. Service Layer Pattern

**All business logic goes in service classes**, not in routes.

**Gold Standard**: `app/features/administration/users/services/crud_services.py`

```python
from app.features.core.enhanced_base_service import BaseService

class UserCrudService(BaseService[User]):
    """Service inheriting from BaseService for consistency."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Business logic for user creation with validation."""
        # Validation
        await self._validate_user_creation(user_data, self.tenant_id)

        # Create entity
        user = User(...)
        self.db.add(user)
        await self.db.flush()

        # Logging
        self.log_operation("user_creation", {...})

        return self._to_response(user)
```

**Service Responsibilities**:
- Business logic and validation
- Database operations
- Error handling
- Logging
- Domain-specific transformations

**Routes Responsibilities**:
- HTTP request/response handling
- Dependency injection
- Calling services
- Template rendering

### 4. Repository/Query Builder Pattern

**BaseService provides common query patterns**:

```python
# Tenant-scoped query
stmt = self.create_base_query(User)

# Global query with tenant join
stmt = self.create_tenant_join_query(User)

# Search across multiple fields
stmt = self.apply_search_filters(stmt, User, search_term, ['name', 'email'])

# Get by ID with tenant scope
user = await self.get_by_id(User, user_id)

# Check existence
exists = await self.exists_by_field(User, 'email', email)
```

### 5. Multi-Tenancy Pattern

**Three-layer tenant isolation**:

1. **Middleware Layer** (`app/middleware/tenant.py`):
   - Extracts tenant from headers/JWT/subdomain
   - Stores in ContextVar for logging

2. **Dependency Layer** (`app/deps/tenant.py`):
   - Validates tenant_id from JWT
   - Checks header/token consistency
   - Returns validated tenant_id (or `"global"` for global admins)

3. **Service Layer** (`BaseService`):
   - **CRITICAL**: Converts `tenant_id="global"` to `None` automatically
   - Automatically adds `WHERE tenant_id = ?` to queries when `tenant_id is not None`
   - When `tenant_id is None` (global admin), queries return ALL records across all tenants

**Global Admin Pattern**:

Global admins have `tenant_id = "global"` in their JWT token and `role = "global_admin"` in the database.

**✅ CORRECT Service Implementation** (Standard Pattern):

```python
from app.features.core.enhanced_base_service import BaseService

class MyService(BaseService[MyModel]):
    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)
        # BaseService automatically converts tenant_id="global" to None
        # self.tenant_id will be None for global admins

    async def list_items(self) -> List[MyModel]:
        """List items for current tenant (or all items for global admin)."""
        # ✅ CORRECT: Use create_base_query() - it handles tenant filtering automatically
        stmt = self.create_base_query(MyModel)
        result = await self.db.execute(stmt)
        return result.scalars().all()
        # For regular users: SELECT * FROM my_model WHERE tenant_id = ?
        # For global admins: SELECT * FROM my_model (no tenant filter)
```

**❌ WRONG Service Implementation** (Anti-Pattern):

```python
class MyService(BaseService[MyModel]):
    async def list_items(self) -> List[MyModel]:
        # ❌ WRONG: Do NOT check if tenant_id is None
        if not self.tenant_id:
            raise ValueError("Tenant ID required")  # This breaks global admin access!

        stmt = self.create_base_query(MyModel)
        # ...
```

**Why This Matters**:

1. **Route receives**: `tenant_id="global"` from `tenant_dependency` for global admins
2. **BaseService converts**: `"global"` → `None` in `__init__`
3. **create_base_query() checks**: `if self.tenant_id is not None` to add `WHERE tenant_id = ?`
4. **Result**: Global admins see ALL records, regular users see only their tenant's records

**Service Layer Rules**:

- ✅ **DO**: Use `create_base_query()` for automatic tenant filtering
- ✅ **DO**: Use `get_by_id()` for tenant-scoped lookups
- ✅ **DO**: Let BaseService handle tenant isolation
- ❌ **DON'T**: Check `if not self.tenant_id:` and raise errors
- ❌ **DON'T**: Manually add `WHERE tenant_id = ?` filters
- ❌ **DON'T**: Create separate methods for global admin access (unless explicitly needed)

**Cross-Tenant Operations** (Optional):

For explicit cross-tenant operations (like global admin creating a resource for a different tenant):

```python
async def create_item_global(
    self,
    data: ItemCreate,
    target_tenant_id: str  # Explicit tenant override
) -> Item:
    """Global admin method to create item for any tenant."""
    item = Item(
        tenant_id=target_tenant_id,  # Use target_tenant_id, not self.tenant_id
        **data.dict()
    )
    self.db.add(item)
    await self.db.flush()
    return item
```

**Route Layer Pattern**:

```python
@router.get("/items")
async def list_items(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),  # Will be "global" for global admins
    current_user: User = Depends(get_current_user)
):
    """List items. Regular users see their tenant's items, global admins see all."""
    service = MyService(db, tenant_id)  # Pass tenant_id as-is
    items = await service.list_items()  # Automatically tenant-scoped (or not, for global admins)
    return items
```

**Tenant Filter Validation (Security Best Practice)**:

For enhanced security, use `self.execute()` instead of `self.db.execute()` to get **automatic tenant filter validation**:

```python
from app.features.core.enhanced_base_service import BaseService, TenantFilterError

class MyService(BaseService[MyModel]):
    async def list_items_with_validation(self) -> List[MyModel]:
        """List items with automatic tenant filter validation."""
        # ✅ RECOMMENDED: Use self.execute() for validation
        stmt = self.create_base_query(MyModel)
        result = await self.execute(stmt, MyModel)  # Validates tenant filter!
        return result.scalars().all()

    async def custom_query_with_validation(self, status: str) -> List[MyModel]:
        """Custom query with manual filter and validation."""
        # Build query with manual tenant filter
        stmt = select(MyModel).where(
            MyModel.status == status,
            MyModel.tenant_id == self.tenant_id  # Manual filter
        )

        # ✅ execute() validates the filter is present
        result = await self.execute(stmt, MyModel)
        return result.scalars().all()
```

**Cross-Tenant Query Pattern** (with audit trail):

For legitimate cross-tenant operations (admin dashboards, aggregations, etc.):

```python
async def get_tenant_statistics(self) -> Dict[str, Any]:
    """Admin dashboard - aggregate stats across all tenants."""
    # Cross-tenant aggregation with explicit reason
    stmt = select(
        MyModel.tenant_id,
        func.count(MyModel.id).label('count')
    ).group_by(MyModel.tenant_id)

    # ✅ allow_cross_tenant=True with reason (logged for audit)
    result = await self.execute(
        stmt,
        MyModel,
        allow_cross_tenant=True,
        reason="Admin dashboard - tenant statistics report"
    )

    return dict(result.all())
```

**How Tenant Filter Validation Works**:

1. **Regular Users** (tenant_id set):
   - `execute()` checks if query contains `WHERE tenant_id = ?`
   - Raises `TenantFilterError` if missing
   - Prevents accidental data leaks

2. **Global Admins** (tenant_id is None):
   - Validation automatically **SKIPPED**
   - Can query across all tenants without restrictions
   - No `reason` parameter needed

3. **Explicit Cross-Tenant Queries**:
   - Set `allow_cross_tenant=True` to bypass validation
   - **MUST** provide `reason` parameter (for audit trail)
   - All bypasses logged with reason

**Error Handling**:

```python
from app.features.core.enhanced_base_service import TenantFilterError

try:
    stmt = select(MyModel)  # Missing tenant filter!
    result = await self.execute(stmt, MyModel)
except TenantFilterError as e:
    # Clear error message with solutions:
    # "Query for MyModel is missing tenant filter! Current tenant: tenant-123.
    #  Solutions: 1) Use create_base_query(), 2) Add .where(tenant_id == ...),
    #  3) Set allow_cross_tenant=True with reason"
    pass
```

**Legacy Pattern** (still works, but discouraged):

```python
# ⚠️ DEPRECATED but still functional
stmt = self.create_base_query(MyModel)
result = await self.db.execute(stmt)  # Logs deprecation warning
# Warning: "DEPRECATED: Direct self.db.execute() usage detected.
#           Consider using self.execute() for tenant filter validation."
```

### 6. Centralized Import Pattern

**Problem**: Import inconsistency across files
**Solution**: Centralized import modules

```python
# In services - use centralized SQLAlchemy imports
from app.features.core.sqlalchemy_imports import *

# In routes - use centralized route imports
from app.features.core.route_imports import *
```

**Benefits**:
- Consistent imports across codebase
- Single source of truth
- Easier to update/refactor
- Includes utility functions

### 7. API Versioning Pattern

**Versioned API structure**:

```python
# app/api/v1/router.py
v1_router = APIRouter(prefix="/api/v1", tags=["API v1"])
v1_router.include_router(auth_router, prefix="/auth")
v1_router.include_router(users_router)

# In main.py
app.include_router(v1_router)
```

**URL Structure**:
- `/api/v1/auth/login` - Versioned API endpoint
- `/auth/login` - Legacy endpoint (backward compatibility)
- `/features/administration/users/` - HTMX/UI endpoints

### 8. Middleware Stack (Order Matters!)

```python
# From first to last in request processing:
1. VersioningMiddleware        # API version detection
2. APISecurityMiddleware        # API security headers
3. AuthContextMiddleware        # Auth context extraction
4. AuditLoggingMiddleware       # Audit logging (async background)
5. RequestIDMiddleware          # Request ID generation
6. TenantMiddleware            # Tenant extraction
7. RateLimitMiddleware         # Rate limiting
8. MetricsMiddleware           # Prometheus metrics
9. RequestLoggingMiddleware    # Request/response logging
10. CORSMiddleware             # CORS headers
11. SecureHeadersMiddleware    # Security headers
```

### 9. Background Task Pattern (Celery)

```python
# Celery task definition
@celery_app.task(name="process_data")
def process_data_task(data: dict):
    """Background task for data processing."""
    return result

# Task invocation
task = process_data_task.delay(data_dict)
task_id = task.id
```

**Task Organization**:
- Tasks defined in `app/features/{feature}/tasks.py`
- Celery app configured in `app/features/core/celery_app.py`
- Redis as broker and result backend

### 10. Modal Close & Focus Restoration Pattern

**CRITICAL**: All modal close operations are handled **globally**. Never add custom modal close handlers in table JavaScript files.

#### Global Handler Architecture

**Location**: `app/features/core/static/js/table-base.js` (lines 1269-1348)

**How It Works**:
```javascript
// Global HTMX form submission handler
document.body.addEventListener("htmx:afterRequest", (e) => {
    if (e.target.id && e.target.id.endsWith('-form')) {
        if (e.detail.xhr.status >= 200 && e.detail.xhr.status < 300) {
            // 1. Show success toast
            // 2. Close modal with window.closeModal()
            // 3. Wait 1200ms for focus restoration to complete
            // 4. Refresh table automatically
        }
    }
});
```

#### Focus Restoration

**Location**: `app/static/js/site.js` (lines 217-260, 538-626)

**Features**:
- Automatic focus restoration to trigger button (Edit/Create button)
- Works with both Bootstrap Modal and fallback modal system
- Retry logic: 10 attempts with 100ms delays (max ~1150ms)
- Complete backdrop cleanup (prevents locked page)
- Table refresh delayed to 1200ms (after focus restoration completes)

**Flow**:
```
User submits form
  ↓
Global handler detects `-form` ID
  ↓
Calls window.closeModal()
  ↓
Modal closes (Bootstrap or fallback)
  ↓
Removes ALL backdrop elements
  ↓
Restores focus (up to 10 retries)
  ↓
Waits 1200ms
  ↓
Table refreshes automatically
  ↓
User can continue working ✅
```

#### Standard Pattern (DO THIS)

✅ **DO**: Let the global handler manage modal lifecycle automatically

```javascript
// In your table JavaScript file - NO MODAL CODE NEEDED!

// Your table initialization
window.myTable = new Tabulator("#my-table", {
    // ... table config
});

// Edit function
window.editItem = function(id) {
    editTabulatorRow(`/features/my-slice/${id}/edit`);
};

// ✅ That's it! Modal close is automatic
```

✅ **DO**: Use form IDs ending with `-form`

```html
<form id="user-form" hx-post="/features/administration/users/">
    <!-- Global handler detects this automatically -->
</form>
```

✅ **DO**: Add `data-default-focus` to Create/Add buttons

```html
<a id="add-record-btn"
   data-default-focus
   hx-get="/features/my-slice/partials/form"
   hx-target="#modal-body">
    Add Item
</a>
```

#### Anti-Patterns (DON'T DO THIS)

❌ **DON'T**: Add custom `closeModal` event listeners

```javascript
// ❌ WRONG - Redundant and creates race conditions
document.body.addEventListener('closeModal', function () {
    const modal = bootstrap.Modal.getInstance(document.getElementById('modal'));
    if (modal) {
        modal.hide();  // ❌ Don't do this!
    }
});
```

❌ **DON'T**: Call `modal.hide()` directly in table JavaScript

```javascript
// ❌ WRONG - Bypasses global handler and breaks focus restoration
function customCloseModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('modal'));
    modal.hide();  // ❌ Don't do this!
}
```

❌ **DON'T**: Add `location.reload()` after form submission

```javascript
// ❌ WRONG - Heavy-handed, breaks UX
document.getElementById('my-form').addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.xhr.status === 204) {
        closeModal();
        setTimeout(() => location.reload(), 300);  // ❌ Don't do this!
    }
});
```

❌ **DON'T**: Implement custom HX-Trigger closeModal logic

```javascript
// ❌ WRONG - Global handler already does this
document.body.addEventListener("htmx:afterRequest", function (event) {
    const triggerHeader = xhr.getResponseHeader("HX-Trigger") || "";
    if (triggerHeader.includes("closeModal")) {
        window.closeModal();  // ❌ Redundant!
    }
});
```

#### Why This Matters

**Before (Custom Handlers)**:
- Modal backdrop stayed on page (locked UI)
- Focus didn't return to trigger button
- Race conditions between modal close and table refresh
- Inconsistent behavior across tables
- 50+ lines of redundant code

**After (Global Handler)**:
- Backdrop removed completely ✅
- Focus restored automatically ✅
- Proper timing (focus → then table refresh) ✅
- Consistent across all 20+ tables ✅
- Zero custom modal code needed ✅

#### Debugging Modal Issues

If modal doesn't close or page is locked:

```javascript
// Add temporary debug logging
console.log('Modal debug:', {
    hasBootstrap: !!window.bootstrap,
    hasModal: !!bootstrap?.Modal,
    instance: bootstrap?.Modal?.getInstance(document.getElementById('modal')),
    backdrops: document.querySelectorAll('.modal-backdrop').length
});
```

**Common issues**:
1. Form ID doesn't end with `-form` → handler won't trigger
2. Bootstrap not loaded → using fallback mode
3. Backdrop elements not cleaned up → check `cleanupFallbackModal()`
4. Focus not returning → check `data-default-focus` attribute

#### Files Modified (2025-11-05)

**Cleaned up custom handlers in**:
- `app/features/business_automations/content_broadcaster/static/js/content-table.js`
- `app/features/business_automations/content_broadcaster/static/js/planning-table.js`
- `app/features/community/static/js/members-table.js`
- `app/features/community/static/js/partners-table.js`
- `app/features/msp/cspm/static/js/m365-tenants-table.js`
- `app/features/msp/cspm/static/js/tenant-benchmarks-table.js`

**Key commits**: Modal focus restoration fix (2025-11-05)

---

## 💻 Code Style & Conventions

### Naming Conventions

**Files & Directories**:
- `snake_case` for Python files: `crud_services.py`, `dashboard_routes.py`
- `lowercase` for directories: `administration/`, `users/`
- Descriptive suffixes: `_service`, `_routes`, `_models`

**Python Identifiers**:
- `snake_case` for functions and variables: `get_user_by_id`, `user_data`
- `PascalCase` for classes: `UserCrudService`, `UserResponse`
- `UPPER_SNAKE_CASE` for constants: `DATABASE_URL`, `MAX_RETRIES`

**Models**:
- Pydantic models: `UserCreate`, `UserUpdate`, `UserResponse`, `UserSearchFilter`
- SQLAlchemy models: `User`, `Tenant`, `AuditLog`
- Database tables: `snake_case` plural: `users`, `audit_logs`, `password_reset_tokens`

**Routes**:
- HTTP methods as prefixes: `get_users_api`, `create_user_form`, `update_user_field_api`
- Clear action names: `list_users`, `delete_tenant`, `refresh_token`

### Import Organization

**Standard order** (enforced by centralized imports):

```python
"""Module docstring describing purpose."""

# 1. Centralized imports (PREFERRED)
from app.features.core.sqlalchemy_imports import *  # For services - includes get_logger
from app.features.core.route_imports import *       # For routes - includes get_logger

# 2. Standard library
import os
import uuid
from datetime import datetime, timezone

# 3. Third-party packages
from fastapi import APIRouter, Depends
from sqlalchemy import select

# 4. Local application imports
from app.features.auth.models import User
from app.features.core.database import get_db

# 5. Setup logger (ALWAYS use centralized imports)
logger = get_logger(__name__)
```

**❌ WRONG - Logger Import Anti-Patterns:**
```python
# DON'T import from app.features.core.logging - it doesn't export get_logger
from app.features.core.logging import get_logger  # ❌ ImportError

# DON'T import structlog directly - bypasses centralization
import structlog
logger = structlog.get_logger(__name__)  # ❌ Not standardized

# DON'T import from structured_logging directly
from app.features.core.structured_logging import get_logger  # ❌ Not centralized
```

**✅ CORRECT - Use Centralized Imports:**
```python
# Services: Use sqlalchemy_imports (includes get_logger)
from app.features.core.sqlalchemy_imports import *
logger = get_logger(__name__)

# Routes: Use route_imports (includes get_logger)
from app.features.core.route_imports import *
logger = get_logger(__name__)
```

**Why?**
- `get_logger` is exported by both `sqlalchemy_imports.py` and `route_imports.py`
- Ensures consistent logging configuration across all modules
- Single source of truth for logger setup
- Already configured with structlog and proper formatting

### Type Hints

**Always use type hints** on:
- Function parameters
- Return types
- Class attributes
- Complex variables

```python
# ✅ Good - Full type hints
async def get_user_by_id(
    self,
    user_id: str
) -> Optional[UserResponse]:
    """Get user by ID."""
    user: User = await self.db.get(User, user_id)
    return self._to_response(user) if user else None

# ❌ Bad - No type hints
async def get_user_by_id(self, user_id):
    user = await self.db.get(User, user_id)
    return self._to_response(user) if user else None
```

### Docstrings

**Format**: Google-style docstrings

```python
async def create_user(
    self,
    user_data: UserCreate,
    target_tenant_id: Optional[str] = None
) -> UserResponse:
    """
    Create new user with validation and proper error handling.

    Args:
        user_data: User creation data with validation
        target_tenant_id: Optional tenant ID for global admin cross-tenant creation

    Returns:
        UserResponse: Created user information

    Raises:
        ValueError: If validation fails or user already exists
    """
```

**Required for**:
- All public methods
- Complex functions
- Service classes
- Model classes

### Error Handling

**Service Layer** - Raise exceptions:

```python
async def create_user(self, user_data: UserCreate) -> UserResponse:
    try:
        await self._validate_user_creation(user_data, self.tenant_id)
        # ... creation logic
        return self._to_response(user)
    except Exception as e:
        await self.handle_error("create_user", e, email=user_data.email)
```

**Route Layer** - Catch and return HTTP errors:

```python
@router.post("/users")
async def create_user_route(...):
    try:
        user = await service.create_user(user_data)
        await commit_transaction(db, "create_user")
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("create_user_route", e)
        raise HTTPException(status_code=500, detail="Failed to create user")
```

### Logging

**Use structured logging** (structlog):

```python
logger = get_logger(__name__)

# ✅ Good - Structured logging
logger.info("User created",
    user_id=user.id,
    email=user.email,
    tenant_id=tenant_id
)

logger.error("Failed to create user",
    email=user_data.email,
    error=str(e),
    tenant_id=tenant_id
)

# ❌ Bad - String formatting
logger.info(f"User {user.id} created with email {user.email}")
```

**BaseService provides** `log_operation()` and `handle_error()`:

```python
self.log_operation("user_creation", {
    "user_id": user.id,
    "target_tenant": tenant_id
})
```

### Async/Await

**Always use async** for:
- Database operations
- HTTP requests
- File I/O
- Any potentially blocking operation

```python
# ✅ Good
async def get_users(self) -> List[User]:
    result = await self.db.execute(select(User))
    return result.scalars().all()

# ❌ Bad - Blocking in async context
def get_users_sync(self) -> List[User]:
    # This blocks the event loop!
    return session.execute(select(User)).scalars().all()
```

### Validation

**Use Pydantic models** for validation:

```python
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    """User creation with validation."""
    name: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator('name')
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!"
            }
        }
    }
```

### Comments

**Use comments for**:
- Complex business logic explanation
- Non-obvious decisions
- TODO items
- Important warnings

```python
# ✅ Good - Explains WHY
# Cast tenant.id (Integer) to String for join with tenant_id (String)
stmt = stmt.outerjoin(Tenant, model.tenant_id == cast(Tenant.id, String))

# ✅ Good - Important warning
# WARNING: This operation is expensive - use sparingly
await self.rebuild_full_search_index()

# ❌ Bad - States the obvious
# Increment counter by 1
counter += 1
```

---

## 🗄 Database Patterns

### Model Definition

**SQLAlchemy 2.0 declarative style with AuditMixin**:

```python
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin
from sqlalchemy import Column, String, Boolean, Text, JSON, Index
import uuid

class User(Base, AuditMixin):
    """User model with tenant isolation and audit fields."""

    __tablename__ = "users"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Core fields
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Tenant isolation
    tenant_id = Column(String(64), nullable=False, index=True)

    # Role-based access
    role = Column(String(50), nullable=False, default="user")

    # Status fields
    status = Column(String(50), default="active")
    enabled = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)

    # AuditMixin provides:
    # - created_at: DateTime(timezone=False)  # IMPORTANT: Use timezone-naive!
    # - updated_at: DateTime(timezone=False)
    # - created_by: String(36)
    # - updated_by: String(36)
    # - created_by_name: String(255)
    # - updated_by_name: String(255)

    # Composite indexes
    __table_args__ = (
        Index('idx_users_email_tenant', 'email', 'tenant_id', unique=True),
    )
```

### DateTime and Timezone Handling ⚠️ CRITICAL

**PostgreSQL Standard**: This project uses `TIMESTAMP WITHOUT TIME ZONE` for all datetime columns.

**❌ WRONG - Timezone-Aware Datetimes:**
```python
# DON'T use timezone-aware datetimes
from datetime import datetime, timezone

# ❌ This will cause errors with PostgreSQL
content.updated_at = datetime.now(timezone.utc)
job.run_at = datetime.now(timezone.utc) + timedelta(hours=1)

# Column definition
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # ❌ ERROR
```

**✅ CORRECT - Timezone-Naive Datetimes:**
```python
# Always use timezone-naive datetimes
from datetime import datetime, timedelta

# ✅ Correct for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
content.updated_at = datetime.now()
job.run_at = datetime.now() + timedelta(hours=1)

# Column definition
created_at = Column(DateTime, default=datetime.now, nullable=False)  # ✅ CORRECT
updated_at = Column(DateTime, onupdate=datetime.now)  # ✅ CORRECT

# In queries
stmt = select(Job).where(Job.run_at > datetime.now())  # ✅ CORRECT
```

**Why?**
- PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` expects timezone-naive Python datetimes
- Mixing timezone-aware and timezone-naive causes: `TypeError: can't subtract offset-naive and offset-aware datetimes`
- All other slices in the project use timezone-naive datetimes
- Server time is assumed to be UTC in production (Docker containers run in UTC)

**Error Example:**
```
asyncpg.exceptions.DataError: invalid input for query argument $2:
datetime.datetime(2025, 10, 11, 9, 33, 25, 572867, tzinfo=datetime.timezone.utc)
(can't subtract offset-naive and offset-aware datetimes)
```

**Column Definition Standard:**
```python
from sqlalchemy import Column, DateTime
from datetime import datetime

# ✅ CORRECT
created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)
scheduled_at = Column(DateTime, nullable=True)
run_at = Column(DateTime, nullable=False, index=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON responses."""
        base_dict = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "tenant_id": self.tenant_id,
            # ... other fields
        }
        base_dict.update(self.get_audit_info())  # From AuditMixin
        return base_dict
```

### AuditMixin Pattern

**All models SHOULD inherit from AuditMixin** for audit trails:

```python
from app.features.core.audit_mixin import AuditMixin

class MyModel(Base, AuditMixin):
    """Model with automatic audit fields."""
    __tablename__ = "my_table"

    # Your fields here

# Automatically includes:
# - created_at, updated_at (timestamps)
# - created_by, updated_by (user IDs)
# - created_by_name, updated_by_name (user names)
# - get_audit_info() method
```

### Query Patterns

**Use BaseService query builders**:

```python
# Tenant-scoped SELECT
stmt = self.create_base_query(User)
# Generates: SELECT * FROM users WHERE tenant_id = ?

# Global query with tenant information
stmt = self.create_tenant_join_query(User)
# Joins with tenants table for tenant_name

# Apply search
stmt = self.apply_search_filters(stmt, User, "john", ['name', 'email'])
# Adds: WHERE name ILIKE '%john%' OR email ILIKE '%john%'

# Complex query
stmt = (
    self.create_base_query(User)
    .where(User.status == "active")
    .where(User.enabled == True)
    .order_by(desc(User.created_at))
)
```

### Migrations (Alembic)

**Creating migrations**:

```bash
# Auto-generate migration
python manage_db.py revision --autogenerate -m "Add user status field"

# Apply migrations
python manage_db.py upgrade head

# Rollback
python manage_db.py downgrade -1
```

**Migration file structure**:

```python
"""Add user status field

Revision ID: abc123
Revises: def456
Create Date: 2024-01-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Apply changes."""
    op.add_column('users', sa.Column('status', sa.String(50), default='active'))

def downgrade():
    """Revert changes."""
    op.drop_column('users', 'status')
```

### Database Configuration

**Settings** (app/features/core/config.py):

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5434/db"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }
```

**Engine setup** (app/features/core/database.py):

```python
# Async engine for application
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Async session maker
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

---

## 🔐 Authentication & Authorization

### JWT Token Structure

**Token payload**:

```python
{
    "user_id": "uuid-string",
    "email": "user@example.com",
    "tenant_id": "tenant-id",
    "role": "admin",
    "exp": 1234567890,  # Expiration timestamp
    "iat": 1234567890   # Issued at timestamp
}
```

**Token generation** (app/features/auth/jwt_utils.py):

```python
from app.features.auth.jwt_utils import JWTUtils

# Create token
token = JWTUtils.create_access_token(
    user_id=user.id,
    email=user.email,
    tenant_id=user.tenant_id,
    role=user.role
)

# Verify token
token_data = JWTUtils.verify_token(token)
```

### Authentication Flow

1. **Login** (`POST /auth/login`):
   - Validate credentials
   - Generate JWT token
   - Set cookie or return token

2. **Request** with authentication:
   - Extract token from header or cookie
   - Validate JWT signature and expiration
   - Extract user info from token
   - Load full user from database

3. **Authorization**:
   - Check user role
   - Validate tenant access
   - Enforce permissions

### Dependency-Based Auth

```python
from app.features.auth.dependencies import (
    get_current_user,
    get_admin_user,
    get_global_admin_user,
    get_optional_current_user
)

# Require any authenticated user
@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return user.to_dict()

# Require admin (tenant or global)
@router.get("/admin")
async def admin_panel(user: User = Depends(get_admin_user)):
    return {"message": "Admin access granted"}

# Require global admin only
@router.get("/global-admin")
async def global_admin_panel(user: User = Depends(get_global_admin_user)):
    return {"message": "Global admin access"}

# Optional authentication (no error if not authenticated)
@router.get("/public")
async def public_page(user: Optional[User] = Depends(get_optional_current_user)):
    if user:
        return {"message": f"Welcome {user.name}"}
    return {"message": "Welcome guest"}
```

### Role Hierarchy

```
global_admin  (tenant_id = "global")
    ↓
admin  (tenant-scoped admin)
    ↓
user   (regular user)
```

**Permission checks**:

```python
def is_global_admin(user: User) -> bool:
    return user.role == "global_admin" and user.tenant_id == "global"

def can_manage_users(user: User) -> bool:
    return user.role in ["admin", "global_admin"]
```

### Password Security

**Hashing** (using passlib + bcrypt):

```python
from app.features.core.security import hash_password, verify_password

# Hash password
hashed = hash_password("user_password")

# Verify password
is_valid = verify_password("user_password", hashed)
```

**Complexity validation**:

```python
from app.features.core.security import validate_password_complexity

errors = validate_password_complexity("weak")
# Returns list of error messages if invalid
# ["Password must be at least 8 characters", "Must contain uppercase", ...]
```

### Multi-Factor Authentication (MFA)

**TOTP-based MFA** using pyotp:

```python
# Generate MFA secret
import pyotp
secret = pyotp.random_base32()

# Generate QR code
import qrcode
qr = qrcode.make(pyotp.totp.TOTP(secret).provisioning_uri(
    name=user.email,
    issuer_name="TerraAutomationPlatform"
))

# Verify TOTP code
totp = pyotp.TOTP(secret)
is_valid = totp.verify(user_code, valid_window=1)
```

### API Key Authentication

**API keys for programmatic access**:

```python
# Create API key
from app.features.administration.api_keys.models import APIKey

api_key = APIKey(
    name="Integration Key",
    key_hash=hash_api_key(raw_key),
    user_id=user.id,
    tenant_id=user.tenant_id,
    scopes=["read:users", "write:users"]
)

# Validate API key
from app.features.administration.api_keys.dependencies import get_api_key

@router.get("/api/users")
async def list_users(api_key: APIKey = Depends(get_api_key)):
    # API key validated
    return {"users": [...]}
```

---

## 🧪 Testing Approach

### Test Structure

```
tests/
├── conftest.py              # Global fixtures and configuration
├── conftest_playwright.py   # Playwright-specific fixtures
├── database.py             # Database test helpers
├── utils.py                # Test utilities
├── compliance/             # Compliance validation tests
│   ├── test_tenant_crud_compliance.py
│   ├── test_logging_compliance.py
│   └── test_service_imports_compliance.py
├── integration/            # Integration tests
│   ├── test_auth_endpoints.py
│   ├── test_tenant_isolation.py
│   ├── test_monitoring.py
│   └── test_webhooks.py
├── performance/            # Performance tests
└── ui/                     # Playwright UI tests
    └── test_navigation.py
```

### Test Markers

**Defined in pytest.ini**:

```ini
[pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    ui: UI tests (Playwright)
    e2e: End-to-end tests
    slow: Slow running tests
    auth: Authentication tests
    mfa: Multi-factor authentication tests
    webhooks: Webhook system tests
    api: API endpoint tests
    performance: Performance tests
    tenant_isolation: Tenant isolation tests
```

**Usage**:

```python
@pytest.mark.integration
@pytest.mark.auth
async def test_login_flow(client):
    """Test authentication login flow."""
    pass
```

**Run specific markers**:

```bash
pytest -m "integration"
pytest -m "auth and not slow"
pytest -m "unit or integration"
```

### Fixtures (tests/conftest.py)

**Database fixtures**:

```python
@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create test database engine."""
    # Creates tables, yields engine, drops tables

@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine):
    """Create test database session."""
    # Yields session for tests

@pytest_asyncio.fixture(scope="function")
async def test_client(test_db_session):
    """Create test client with DB override."""
    # Overrides get_db dependency
```

**Auth fixtures**:

```python
@pytest_asyncio.fixture
async def auth_service():
    """Create auth service instance."""
    return AuthService()
```

**Data fixtures**:

```python
@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "tenant_a": {"id": "tenant-a", "name": "Tenant A"},
        "tenant_b": {"id": "tenant-b", "name": "Tenant B"}
    }

@pytest_asyncio.fixture
async def sample_test_users(test_db_session):
    """Create sample users in database."""
    # Creates users using DatabaseTestHelper
```

**Request fixtures**:

```python
@pytest.fixture
def mock_request_factory():
    """Factory for creating mock Request objects."""
    class MockRequest:
        def __init__(self, headers=None, path="/"):
            self.headers = headers or {}
            self.path = path
    return MockRequest

@pytest.fixture
def tenant_headers():
    """Factory for tenant-specific headers."""
    def _make_headers(tenant_id: str, **extras):
        return {"X-Tenant-ID": tenant_id, **extras}
    return _make_headers
```

### Test Patterns

**Integration test example**:

```python
@pytest.mark.integration
@pytest.mark.auth
async def test_user_creation(test_client, test_db_session):
    """Test user creation endpoint."""

    # Setup
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }

    # Execute
    response = await test_client.post(
        "/api/v1/administration/users",
        json=user_data,
        headers={"X-Tenant-ID": "test-tenant"}
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
```

**Tenant isolation test example**:

```python
@pytest.mark.integration
@pytest.mark.tenant_isolation
async def test_tenant_data_isolation(test_client, multi_tenant_test_users):
    """Ensure users cannot access other tenants' data."""

    # Create users in tenant A and B
    tenant_a_user = multi_tenant_test_users["tenant-alpha"][0]

    # Login as tenant A user
    response = await test_client.post("/auth/login", json={
        "email": tenant_a_user["email"],
        "password": "password"
    })
    token = response.json()["access_token"]

    # Try to access tenant B data
    response = await test_client.get(
        "/api/v1/administration/users",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-beta"  # Different tenant!
        }
    )

    # Should be forbidden or return no data
    assert response.status_code in [403, 200]
    if response.status_code == 200:
        assert len(response.json()) == 0
```

**UI test example** (Playwright):

```python
@pytest.mark.ui
async def test_login_ui(page):
    """Test login page UI flow."""

    await page.goto("http://localhost:8000/auth/login")

    # Fill login form
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password"]', 'password')

    # Submit
    await page.click('button[type="submit"]')

    # Verify redirect to dashboard
    await page.wait_for_url("**/dashboard")
    assert "Dashboard" in await page.title()
```

### Test Utilities (tests/utils.py)

```python
class DatabaseTestHelper:
    """Helper for creating test data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_test_users(self, tenant_id: str, count: int):
        """Create test users for a tenant."""
        users = []
        for i in range(count):
            user = User(
                email=f"user{i}@{tenant_id}.com",
                tenant_id=tenant_id,
                # ... other fields
            )
            self.session.add(user)
            users.append(user)

        await self.session.commit()
        return users
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/integration/test_auth_endpoints.py

# Run with markers
pytest -m integration
pytest -m "auth and not slow"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/integration/test_auth_endpoints.py::test_login_success

# Run tests in parallel
pytest -n auto
```

### Compliance Tests

**Automated compliance validation**:

```bash
# Run all compliance checks
make all-compliance-checks

# Tenant CRUD compliance
make compliance-check

# Logging compliance
make logging-compliance-check

# Generate compliance report
make compliance-report
```

**Compliance test structure**:

```python
class TestTenantCRUDCompliance:
    """Validate all slices follow tenant CRUD standards."""

    def test_all_services_use_base_service(self):
        """Ensure all CRUD services inherit from BaseService."""
        # Scans codebase for compliance
        pass

    def test_all_services_use_centralized_imports(self):
        """Ensure services use centralized import pattern."""
        pass
```

---

## ⚙️ Development Commands

### Makefile Commands

```bash
# Help
make help                    # Show all available commands

# Setup
make install                # Install dependencies
make dev-setup             # Complete dev environment setup

# Testing
make test                   # Run all tests
make test-unit             # Run unit tests only
make test-integration      # Run integration tests only
make test-ui               # Run UI tests (Playwright)
make test-performance      # Run performance tests

# Compliance
make compliance-check       # Run tenant CRUD compliance
make logging-compliance-check  # Run logging compliance
make all-compliance-checks # Run all compliance checks
make compliance-report     # Generate compliance report

# Code Quality
make lint                  # Run linting (flake8, mypy)
make format                # Format code (black, isort)
make pre-commit           # Run pre-commit hooks

# Database
make db-migrate           # Run migrations
make db-reset            # Reset database (DESTRUCTIVE)

# Server
make dev-server          # Start development server
make prod-server         # Start production server

# Docker
make docker-build        # Build Docker image
make docker-run          # Run Docker container
make docker-compose-up   # Start docker-compose
make docker-compose-down # Stop docker-compose

# Security
make security-check      # Run security checks (bandit, safety)
make audit              # Full audit (compliance + security)

# CI/CD
make ci-test            # Simulate CI/CD pipeline
make quick-check        # Quick dev check (fast tests + compliance)
```

### Database Management (manage_db.py)

```bash
# Create migration
python manage_db.py revision --autogenerate -m "Description"

# Apply migrations
python manage_db.py upgrade head

# Rollback one migration
python manage_db.py downgrade -1

# Show current revision
python manage_db.py current

# Show migration history
python manage_db.py history
```

### Application Scripts (scripts/)

```bash
# Create new vertical slice
python scripts/create_slice.py feature_name

# Manage global admin
python scripts/manage_global_admin.py create admin@example.com
python scripts/manage_global_admin.py list

# Reset admin password
python scripts/reset_admin_password.py admin@example.com

# Manage secrets
python scripts/manage_secrets.py set KEY value
python scripts/manage_secrets.py get KEY
python scripts/manage_secrets.py list

# Manage rate limits
python scripts/manage_rate_limits.py set /api/users 100
python scripts/manage_rate_limits.py list

# Check compliance
python scripts/check_compliance.py
python scripts/check_logging_compliance.py

# Start Celery workers
python scripts/start_celery_worker.py
python scripts/start_celery_beat.py
python scripts/start_celery_flower.py

# Fix code issues
python scripts/fix_logging_imports.py
python scripts/fix_remaining_logging.py
```

### Development Server

```bash
# Development (with auto-reload)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Using make
make dev-server
make prod-server

# Using main.py directly
python -m app.main
```

### Docker Commands

```bash
# Development
docker-compose up -d
docker-compose down
docker-compose logs -f app

# Production
docker-compose -f docker-compose.production.yml up -d

# Monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Build image
docker build -t terra-automation-platform .
docker build -f Dockerfile.production -t terra-automation-platform:prod .
```

### Testing Commands

```bash
# All tests
pytest

# Specific markers
pytest -m integration
pytest -m "auth and not slow"

# Specific file
pytest tests/integration/test_auth_endpoints.py

# Specific test
pytest tests/integration/test_auth_endpoints.py::test_login

# With coverage
pytest --cov=app --cov-report=html
pytest --cov=app --cov-report=term-missing

# Parallel execution
pytest -n auto

# Verbose
pytest -v -s

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l
```

---

## 🎯 Key Design Decisions

### 1. Why Vertical Slice Architecture?

**Decision**: Organize by feature, not by technical layer

**Rationale**:
- **Easier to understand**: Follow one feature from UI to database
- **Better for teams**: Different teams can work on different features
- **Faster development**: All related code in one place
- **Reduced coupling**: Features are independent
- **Easier to test**: Test entire feature in isolation

**Alternative considered**: Layered architecture (models/, services/, controllers/)
**Rejected because**: Requires jumping between many directories for one feature

### 2. Why PostgreSQL Only?

**Decision**: PostgreSQL as the only supported database

**Rationale**:
- **Production-grade**: Industry standard for reliability
- **Rich features**: JSONB, full-text search, arrays
- **Strong typing**: Better data integrity
- **Performance**: Excellent for complex queries
- **Async support**: Full async/await compatibility

**Alternative considered**: SQLite for development
**Rejected because**: Production/dev parity is crucial for multi-tenancy

### 3. Why Centralized Imports?

**Decision**: `sqlalchemy_imports.py` and `route_imports.py` modules

**Rationale**:
- **Consistency**: Everyone imports the same way
- **Maintainability**: Change imports in one place
- **Less boilerplate**: One import instead of 20
- **Best practices**: Centralized utilities and patterns

**Alternative considered**: Each file imports what it needs
**Rejected because**: Led to inconsistent patterns across codebase

### 4. Why BaseService Pattern?

**Decision**: All services inherit from `BaseService`

**Rationale**:
- **DRY principle**: Common operations defined once
- **Tenant isolation**: Automatic tenant filtering
- **Type safety**: Generic type support
- **Consistent patterns**: Same query builders everywhere
- **Easier testing**: Mock BaseService for all services

**Alternative considered**: Utility functions
**Rejected because**: Less encapsulation, harder to override

### 5. Why AuditMixin?

**Decision**: All models inherit `AuditMixin` for audit fields

**Rationale**:
- **Compliance**: Track who created/updated records
- **Debugging**: Know when changes occurred
- **Security**: Audit trail for investigations
- **Consistency**: Same fields across all tables

**Alternative considered**: Manual audit fields
**Rejected because**: Easy to forget, inconsistent implementation

### 6. Why HTMX + Jinja2 Instead of React/Vue?

**Decision**: Server-side rendering with HTMX for interactivity

**Rationale**:
- **Simplicity**: Less JavaScript complexity
- **Performance**: Faster initial page load
- **SEO-friendly**: Server-rendered content
- **Developer velocity**: One language (Python) for most logic
- **Small bundle size**: Minimal JavaScript

**Alternative considered**: React SPA
**Rejected because**: Unnecessary complexity for admin interface

### 7. Why Pydantic v2?

**Decision**: Use Pydantic v2 for validation and settings

**Rationale**:
- **Performance**: 5-50x faster than v1
- **Better validation**: More robust validation
- **Settings management**: Built-in config system
- **Type safety**: Better IDE support

**Alternative considered**: Pydantic v1
**Rejected because**: v2 is the future, v1 is legacy

### 8. Why Structlog?

**Decision**: Use structlog for structured logging

**Rationale**:
- **Machine-readable**: JSON logs for parsing
- **Context-aware**: Automatically includes request_id, tenant_id
- **Performance**: Fast structured logging
- **Observability**: Better integration with log aggregators

**Alternative considered**: Standard logging
**Rejected because**: String formatting is hard to parse

### 9. Why Multi-Tenant from Day One?

**Decision**: Build multi-tenancy into core architecture

**Rationale**:
- **Hard to retrofit**: Much easier to build in from start
- **Data isolation**: Critical for security
- **Scalability**: Easier to scale per-tenant
- **Business model**: Supports SaaS model

**Alternative considered**: Add multi-tenancy later
**Rejected because**: Requires rewriting most of the app

### 10. Why API Versioning?

**Decision**: Support versioned API structure (`/api/v1/...`)

**Rationale**:
- **Backward compatibility**: Don't break existing integrations
- **Gradual migration**: Deprecate old versions slowly
- **Clear contracts**: Explicit version in URL
- **Professional**: Expected in B2B SaaS

**Alternative considered**: No versioning
**Rejected because**: Breaking changes would affect all users

### 11. Why Hybrid Tenant Filter Validation?

**Decision**: Optional `execute()` method with mandatory validation + deprecation warnings for direct `db.execute()`

**Rationale**:
- **Catches 99% of mistakes**: Validation prevents accidental cross-tenant queries
- **Maintains compatibility**: Existing code continues to work (no breaking changes)
- **Explicit bypasses**: `allow_cross_tenant=True` with required `reason` for audit trail
- **Global admin support**: Auto-bypasses validation when `tenant_id is None`
- **Developer choice**: Use `execute()` for new code, migrate old code gradually
- **Audit trail**: All cross-tenant queries logged with justification

**Alternatives considered**:
1. **Soft enforcement (linting only)**: Can still be bypassed by developers
2. **Hard enforcement (no bypass)**: Blocks legitimate cross-tenant queries (aggregations, admin dashboards)

**Why hybrid won**:
- Balances security with flexibility
- Encourages best practices without forcing migration
- Provides clear error messages with actionable solutions
- Logs all bypasses for security audits

**Implementation**:
- `self.execute()`: Validates tenant filters, raises `TenantFilterError` if missing
- `self.db`: Returns session with deprecation warning (once per instance)
- `allow_cross_tenant=True`: Requires `reason` parameter, logs to audit trail
- Global admins: Validation automatically skipped

---

## 📝 Quick Reference

### Common Patterns

**Create a new vertical slice**:
```bash
python scripts/create_slice.py my_feature
```

**Add a new service method**:
```python
from app.features.core.enhanced_base_service import BaseService

class MyService(BaseService[MyModel]):
    async def my_operation(self, data: MyInput) -> MyOutput:
        try:
            # Validate
            await self._validate(data)

            # Execute
            result = await self._execute(data)

            # Log
            self.log_operation("my_operation", {"result_id": result.id})

            return result
        except Exception as e:
            await self.handle_error("my_operation", e)
```

**Add a new route**:
```python
from app.features.core.route_imports import *

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("/items")
async def list_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    service = MyService(db, tenant_id)
    items = await service.list_items()

    return templates.TemplateResponse(
        "my_feature/list.html",
        {"request": request, "items": items}
    )
```

**Implement tenant isolation (Standard Pattern)**:
```python
# ✅ CORRECT: Let BaseService handle tenant filtering automatically
class MyService(BaseService[MyModel]):
    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)
        # BaseService converts tenant_id="global" → None for global admins

    async def list_items(self) -> List[MyModel]:
        # ✅ Use create_base_query() - automatically tenant-scoped
        stmt = self.create_base_query(MyModel)
        result = await self.db.execute(stmt)
        return result.scalars().all()
        # Regular users: WHERE tenant_id = ?
        # Global admins: No tenant filter (sees all records)

# ❌ WRONG: Do NOT check if tenant_id and raise errors
class MyService(BaseService[MyModel]):
    async def list_items(self) -> List[MyModel]:
        if not self.tenant_id:  # ❌ This breaks global admin access!
            raise ValueError("Tenant ID required")
        # Don't do this!
```

**Implement tenant isolation with validation (Enhanced Security)**:
```python
from app.features.core.enhanced_base_service import BaseService, TenantFilterError

# ✅ RECOMMENDED: Use self.execute() for automatic validation
class MyService(BaseService[MyModel]):
    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def list_items_safe(self) -> List[MyModel]:
        """List items with tenant filter validation."""
        stmt = self.create_base_query(MyModel)
        result = await self.execute(stmt, MyModel)  # Validates filter!
        return result.scalars().all()

    async def custom_query_safe(self, status: str) -> List[MyModel]:
        """Custom query with manual filter and validation."""
        stmt = select(MyModel).where(
            MyModel.status == status,
            MyModel.tenant_id == self.tenant_id
        )
        result = await self.execute(stmt, MyModel)  # Validates filter!
        return result.scalars().all()

    async def cross_tenant_stats(self) -> Dict[str, int]:
        """Admin method - cross-tenant aggregation with audit trail."""
        stmt = select(
            MyModel.tenant_id,
            func.count(MyModel.id)
        ).group_by(MyModel.tenant_id)

        # Explicit bypass with reason (logged)
        result = await self.execute(
            stmt,
            MyModel,
            allow_cross_tenant=True,
            reason="Admin dashboard - tenant statistics"
        )
        return dict(result.all())
```

**Page Layout Pattern (Standard)**:
```html
<!-- ✅ CORRECT: Direct content without excessive containers -->
{% extends "base.html" %}
{% block content %}
<!-- Page header -->
<div class="page-header d-print-none">
    <div class="row align-items-center">
        <div class="col">
            <div class="page-pretitle">Section Name</div>
            <h2 class="page-title">
                <i class="ti ti-icon me-2"></i>Page Title
            </h2>
        </div>
    </div>
</div>

<!-- Main content -->
<div class="row">
    <div class="col-12">
        <!-- Content here -->
    </div>
</div>
{% endblock %}

<!-- ❌ WRONG: Don't use page-wrapper or double container-xl nesting -->
{% block content %}
<div class="page-wrapper">
    <div class="container-xl">
        <div class="page-header">...</div>
    </div>
    <div class="page-body">
        <div class="container-xl">
            <!-- Too much nesting, excessive padding -->
```

**Modal Button Styling (Standard)**:
```html
<!-- ✅ CORRECT: Outline buttons with icons -->
<div class="modal-footer">
    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
        <i class="ti ti-x icon"></i>
        Cancel
    </button>
    <button type="submit" class="btn btn-outline-primary">
        <i class="ti ti-check icon"></i>
        Submit
    </button>
</div>

<!-- ❌ WRONG: Link buttons or solid buttons -->
<div class="modal-footer">
    <button class="btn btn-link link-secondary">Cancel</button>
    <button class="btn btn-primary">
        <i class="ti ti-check me-1"></i>Submit
    </button>
</div>
```

**Key Points:**
- Page layout: Remove `page-wrapper` and nested `container-xl` for consistent spacing
- Modal buttons: Use `btn-outline-secondary` and `btn-outline-primary` classes
- Icon spacing: Use `icon` class, not `me-1` or `me-2` for button icons
- Cancel icons: Use `ti-x` for cancel/close actions
- Submit icons: Use `ti-check` for submit/save, `ti-plus` for add/create

**Add a new model**:
```python
from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin
from sqlalchemy import Column, String, Text, JSON

class MyModel(Base, AuditMixin):
    __tablename__ = "my_table"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    metadata = Column(JSON, default=dict)
```

### Standardization History

**2025-10-10: tenant_id Parameter Standardization**

The codebase was fully standardized to use `tenant_id: str = Depends(tenant_dependency)` across ALL slices.

**Before standardization:**
- 92 uses of `tenant_id:` (majority)
- 32 uses of `tenant:` (minority in older slices)

**Slices updated to tenant_id:**
- ✅ `administration/users` (10 occurrences) - GOLD STANDARD slice
- ✅ `administration/smtp` (17 occurrences)
- ✅ `dashboard` (4 occurrences)
- ✅ `administration/api_keys` (1 occurrence)

**After standardization:**
- ✅ **124 uses of `tenant_id:`** (100%)
- ✅ **0 uses of `tenant:`** (0%)

**Why tenant_id is the standard:**
- More explicit (indicates it's an ID string, not an object)
- Prevents confusion between tenant objects and tenant ID strings
- Majority of codebase already used it
- Newer slices (content_broadcaster, connectors) use it
- Better consistency with BaseService parameter naming

**Reference documentation:** `.claude/CLAUDE_MD_UPDATE_tenant_id.md`

### File Locations

- **Core infrastructure**: `app/features/core/`
- **Feature slices**: `app/features/{feature_name}/`
- **API aggregation**: `app/api/v1/router.py`
- **Shared dependencies**: `app/deps/`
- **Middleware**: `app/middleware/`
- **Tests**: `tests/`
- **Migrations**: `migrations/versions/`
- **Scripts**: `scripts/`
- **Docs**: `docs/`

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5434/db

# Security
SECRET_KEY=your-secret-key-here

# Environment
ENVIRONMENT=development  # or production
DEBUG=true

# CORS
CORS_ORIGINS=*  # or comma-separated URLs

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log
```

---

**Last Updated**: 2025-10-27
**Codebase Version**: Based on commit bd115db + tenant filter validation enhancement
**Recent Changes**:
- Added hybrid tenant filter validation (Option 3) with `BaseService.execute()` method
- Documented `allow_cross_tenant` pattern with required `reason` parameter
- Added comprehensive tenant filter validation tests
- Updated security best practices for multi-tenant queries
