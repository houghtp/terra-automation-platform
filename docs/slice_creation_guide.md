# 🔧 Complete Slice Creation Guide

## ⚠️ STOP! SECURITY REQUIREMENTS - READ FIRST ⚠️

### 🚨 ZERO-TOLERANCE SECURITY POLICY 🚨

**EVERY ROUTE MUST HAVE BOTH:**
1. `tenant_id: str = Depends(tenant_dependency)`
2. `current_user: User = Depends(get_current_user)`

**NO EXCEPTIONS. NO ROUTES WITHOUT THESE DEPENDENCIES.**

**If you create ANY route without both dependencies, you create a CRITICAL SECURITY VULNERABILITY that allows:**
- ❌ Cross-tenant data access
- ❌ Unauthenticated access to sensitive data
- ❌ Complete bypass of security architecture

### 🔒 FAIL-SAFE VERIFICATION

Before writing ANY code, verify you understand:

1. **What is tenant isolation?** _Users can only access their own tenant's data_
2. **What happens without `tenant_dependency`?** _Users can access ANY tenant's data_
3. **What happens without `get_current_user`?** _Anyone can access data without login_
4. **Are there exceptions?** _NO. Every route needs both dependencies._

**✅ If you understand these concepts, proceed. ❌ If not, ask for clarification.**

---

## Overview
This guide provides exact steps to create a fully functional vertical slice with a table that follows the standard FastAPI template patterns. Follow these steps precisely to avoid common issues.

## ⚠️ Critical Requirements

### 1. 🔒 MANDATORY AUTHENTICATION PATTERN (SECURITY CRITICAL)
- **🚨 SECURITY VULNERABILITY:** Routes without authentication allow cross-tenant data access
- **ALWAYS** use `get_current_user` dependency (never `get_optional_current_user`)
- **ALWAYS** include `tenant_dependency` in all routes
- **NEVER** mix authentication patterns within a slice

**✅ REQUIRED Authentication Pattern for ALL routes:**
```python
@router.get("/api/list")
async def list_items(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user),
    service: MyService = Depends(get_my_service)
):
```

**❌ FORBIDDEN - Missing authentication = critical security hole:**
```python
@router.get("/api/list")
async def list_items(
    service: MyService = Depends(get_my_service)  # ❌ ALLOWS CROSS-TENANT ACCESS
):
```

**Required Security Imports:**
```python
from app.features.auth.dependencies import get_current_user
from app.deps.tenant import tenant_dependency
from app.features.auth.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import get_db
```

### 2. Response Format Standardization
- **ALWAYS** use `{"items": [], "total": x, "page": y, "size": z}` for list endpoints
- **NEVER** use `{"data": [], "total": x, "offset": y, "limit": z}` format
- **ALWAYS** ensure Tabulator templates handle both `response.items` and `response.data`

### 3. Tenant Data Alignment
- **ALWAYS** create test data for the `global` tenant (default for logged-in users)
- **ALWAYS** test with actual tenant filtering
- **NEVER** assume tenant filtering will work without proper test data

## � Automatic Template Discovery System

The platform now features **automatic template discovery**, eliminating the need for manual template configuration when creating new slices.

### How It Works:
- **Automatic Scanning**: The system scans `app/features/` for all `templates/` directories
- **Zero Configuration**: Just create your slice structure with a `templates/` directory
- **Instant Recognition**: New slices are automatically included without server restart
- **Multi-Level Support**: Works with any nesting: `app/features/domain/slice/templates`

### Benefits:
✅ **No Manual Updates**: Never update `TEMPLATE_DIRS` again
✅ **Reduced Errors**: Eliminates template path configuration mistakes
✅ **Developer Friendly**: Focus on building features, not configuration
✅ **Maintenance Free**: Scales automatically as you add more slices

### Usage in Routes:
```python
# ✅ Always use the global template system
from app.features.core.templates import templates

@router.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("slice_name/dashboard.html", {
        "request": request,
        "title": "My Slice"
    })
```

---

## � Critical Routing Pattern Updates (September 2025)

**All slices must follow these exact routing patterns to avoid double prefix issues:**

### ❌ **WRONG Patterns (old way - causes double prefixes):**
```python
# routes.py - DON'T DO THIS
router = APIRouter(prefix="/domain/slice", tags=["slice"])

# main.py - DON'T DO THIS
app.include_router(router, prefix="/features", tags=["domain"])
# Results in: /features/domain/slice/domain/slice/ (BROKEN!)
```

### ✅ **CORRECT Patterns (new way):**
```python
# routes.py - NO PREFIX
router = APIRouter(tags=["slice"])

# main.py - FULL PREFIX
app.include_router(router, prefix="/features/domain/slice", tags=["domain"])
# Results in: /features/domain/slice/ (CORRECT!)
```

### **API Endpoints Must Use `/api/list`:**
```python
# ✅ CORRECT
@router.get("/api/list", response_class=JSONResponse)
async def list_items_api():
    pass

# ❌ WRONG
@router.get("/api", response_class=JSONResponse)  # Missing /list
```

### **JavaScript AJAX URLs:**
```javascript
// ✅ CORRECT
ajaxURL: "/features/domain/slice/api/list",

// ❌ WRONG
ajaxURL: "/features/domain/slice/api",  // Missing /list
```

---

## �📋 Slice Creation Checklist

### Step 1: Create Slice Directory Structure
```bash
mkdir -p app/features/[domain]/[slice_name]/{models,services,routes,templates,tests,static}
mkdir -p app/features/[domain]/[slice_name]/templates/[domain]/[slice_name]/{partials}
mkdir -p app/features/[domain]/[slice_name]/static/js
```

### Step 2: Create SQLAlchemy Model
**File:** `app/features/[domain]/[slice_name]/models.py`

```python
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from app.features.core.database import Base

class [ModelName](Base):
    """[Description of the model]"""
    __tablename__ = "[table_name]"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True, default="global")

    # Your business fields here
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Optional: structured data
    metadata = Column(JSONB, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, tenant_id='{self.tenant_id}', name='{self.name}')>"
```

### Step 3: Create Service Layer
**File:** `app/features/[domain]/[slice_name]/services.py`

```python
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import desc, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import [ModelName]
import structlog

logger = structlog.get_logger(__name__)

class [ServiceName]:
    """Service for managing [slice_name] with tenant isolation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_list(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Get paginated list with filtering."""
        try:
            # Build base query
            query = select([ModelName]).filter([ModelName].tenant_id == tenant_id)

            # Apply filters
            if search:
                query = query.filter([ModelName].name.ilike(f"%{search}%"))

            if is_active is not None:
                query = query.filter([ModelName].is_active == is_active)

            # Get total count
            count_query = select(func.count([ModelName].id)).filter([ModelName].tenant_id == tenant_id)
            if search:
                count_query = count_query.filter([ModelName].name.ilike(f"%{search}%"))
            if is_active is not None:
                count_query = count_query.filter([ModelName].is_active == is_active)

            total_result = await self.session.execute(count_query)
            total = total_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc([ModelName].created_at))
            query = query.offset(offset).limit(limit)

            result = await self.session.execute(query)
            items = result.scalars().all()

            return {
                "data": [item.to_dict() for item in items],
                "total": total,
                "offset": offset,
                "limit": limit
            }

        except Exception as e:
            logger.exception(f"Failed to get [slice_name] list for tenant {tenant_id}")
            raise

    async def get_by_id(self, tenant_id: str, item_id: int) -> Optional[[ModelName]]:
        """Get item by ID with tenant isolation."""
        try:
            query = select([ModelName]).filter(
                and_([ModelName].id == item_id, [ModelName].tenant_id == tenant_id)
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Failed to get [slice_name] {item_id} for tenant {tenant_id}")
            raise

    async def create(self, tenant_id: str, data: Dict[str, Any]) -> [ModelName]:
        """Create new item."""
        try:
            item = [ModelName](tenant_id=tenant_id, **data)
            self.session.add(item)
            await self.session.commit()
            await self.session.refresh(item)
            return item
        except Exception as e:
            await self.session.rollback()
            logger.exception(f"Failed to create [slice_name] for tenant {tenant_id}")
            raise

    async def update(self, tenant_id: str, item_id: int, data: Dict[str, Any]) -> Optional[[ModelName]]:
        """Update existing item."""
        try:
            item = await self.get_by_id(tenant_id, item_id)
            if not item:
                return None

            for key, value in data.items():
                if hasattr(item, key):
                    setattr(item, key, value)

            item.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(item)
            return item
        except Exception as e:
            await self.session.rollback()
            logger.exception(f"Failed to update [slice_name] {item_id} for tenant {tenant_id}")
            raise

    async def delete(self, tenant_id: str, item_id: int) -> bool:
        """Delete item by ID."""
        try:
            item = await self.get_by_id(tenant_id, item_id)
            if not item:
                return False

            await self.session.delete(item)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.exception(f"Failed to delete [slice_name] {item_id} for tenant {tenant_id}")
            raise
```

## 🚨 Service Layer Security Requirements

**ALL service methods MUST:**
1. **Accept `tenant_id` parameter** - Required for all database operations
2. **Filter by tenant_id** - ALL database queries MUST include tenant_id in WHERE clause
3. **Never trust request data for tenant_id** - Always use authenticated tenant context
4. **Use compound WHERE clauses** - `and_(Model.id == item_id, Model.tenant_id == tenant_id)`
5. **Verify ownership before modification** - Call get_by_id with tenant_id before update/delete

**FORBIDDEN patterns in services:**
- ❌ Database queries without tenant_id filtering: `select(Model).filter(Model.id == item_id)`
- ❌ Using request data for tenant_id parameter: `tenant_id = data.get('tenant_id')`
- ❌ Direct ID-only lookups: `session.get(Model, item_id)`
- ❌ Bulk operations without tenant filtering: `session.query(Model).delete()`

**✅ CORRECT tenant isolation patterns:**
```python
# ✅ Proper tenant filtering in queries
query = select(Model).filter(
    and_(Model.id == item_id, Model.tenant_id == tenant_id)
)

# ✅ Always verify ownership before operations
item = await self.get_by_id(tenant_id, item_id)
if not item:
    return None  # Item doesn't exist or doesn't belong to tenant
```

### Step 4: Create Routes
**File:** `app/features/[domain]/[slice_name]/routes.py`

## 🚨 MANDATORY SECURITY PATTERN - NO EXCEPTIONS 🚨

**Every single route MUST include ALL of these dependencies in this EXACT order:**

```python
# ✅ REQUIRED PATTERN FOR ALL ROUTES - COPY THIS EXACTLY:
@router.get("/example")
async def example_route(
    # ... other parameters first ...
    db: AsyncSession = Depends(get_db),           # 1. Database session
    tenant_id: str = Depends(tenant_dependency),  # 2. Tenant isolation (CRITICAL)
    current_user: User = Depends(get_current_user), # 3. Authentication (CRITICAL)
    service: ServiceName = Depends(get_service)   # 4. Service dependency
):
```

**❌ NEVER CREATE ROUTES WITHOUT THESE DEPENDENCIES - CREATES SECURITY VULNERABILITY**

## Required Imports (Copy Exactly):

```python
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.database import get_db
from app.features.core.templates import templates
from .models import [ModelName]
from .services import [ServiceName]
from app.features.auth.dependencies import get_current_user  # 🚨 CRITICAL
from app.features.auth.models import User                    # 🚨 CRITICAL
from app.deps.tenant import tenant_dependency               # 🚨 CRITICAL
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/features/[domain]/[slice_name]", tags=["[slice_name]"])

async def get_service(db: AsyncSession = Depends(get_db)) -> [ServiceName]:
    """Dependency to get service."""
    return [ServiceName](db)
```

## Mandatory Route Templates:

### 1. Main Dashboard Route (REQUIRED)
```python
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),        # 🚨 REQUIRED
    current_user: User = Depends(get_current_user),     # 🚨 REQUIRED
):
    """Display dashboard."""
    try:
        return templates.TemplateResponse(
            "[domain]/[slice_name]/dashboard.html",
            {
                "request": request,
                "user": current_user,
                "page_title": "[Slice Display Name]",
                "page_description": "Manage [slice_name] items"
            }
        )
    except Exception as e:
        logger.exception("Failed to render [slice_name] dashboard")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")
```

### 2. API List Route (REQUIRED)
```python
@router.get("/api/list", response_class=JSONResponse)
async def get_list(
    search: Optional[str] = Query(None, description="Search term"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(25, ge=1, le=200, description="Page size"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),        # 🚨 REQUIRED
    current_user: User = Depends(get_current_user),     # 🚨 REQUIRED
    service: [ServiceName] = Depends(get_service)
):
    """Get paginated list - CRITICAL: Must return 'items' format."""
    try:
        offset = (page - 1) * size

        result = await service.get_list(
            tenant_id=tenant_id,  # 🚨 CRITICAL: Pass tenant_id to service
            limit=size,
            offset=offset,
            search=search,
            is_active=is_active
        )

        # 🚨 CRITICAL: Return in standard format with 'items'
        return JSONResponse(content={
            "items": result["data"],  # CRITICAL: Use 'items', not 'data'
            "total": result["total"],
            "page": page,
            "size": size
        })

    except Exception as e:
        logger.exception("Failed to get [slice_name] list via API")
        raise HTTPException(status_code=500, detail="Failed to retrieve items")
```

### 3. Get Item Route (REQUIRED)
```python
@router.get("/api/{item_id}", response_class=JSONResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),        # 🚨 REQUIRED
    current_user: User = Depends(get_current_user),     # 🚨 REQUIRED
    service: [ServiceName] = Depends(get_service)
):
    """Get item by ID."""
    try:
        item = await service.get_by_id(tenant_id, item_id)  # 🚨 Pass tenant_id
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get [slice_name] {item_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve item")
```

### 4. Create Route (REQUIRED)
```python
@router.post("/api", response_class=JSONResponse)
async def create_item(
    data: dict,  # Use proper Pydantic schema in production
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),        # 🚨 REQUIRED
    current_user: User = Depends(get_current_user),     # 🚨 REQUIRED
    service: [ServiceName] = Depends(get_service)
):
    """Create new item."""
    try:
        item = await service.create(tenant_id, data)    # 🚨 Pass tenant_id
        return item.to_dict()
    except Exception as e:
        logger.exception("Failed to create [slice_name]")
        raise HTTPException(status_code=500, detail="Failed to create item")
```

### 5. Update Route (REQUIRED)
```python
@router.put("/api/{item_id}", response_class=JSONResponse)
async def update_item(
    item_id: int,
    data: dict,  # Use proper Pydantic schema in production
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),        # 🚨 REQUIRED
    current_user: User = Depends(get_current_user),     # 🚨 REQUIRED
    service: [ServiceName] = Depends(get_service)
):
    """Update existing item."""
    try:
        item = await service.update(tenant_id, item_id, data)  # 🚨 Pass tenant_id
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update [slice_name] {item_id}")
        raise HTTPException(status_code=500, detail="Failed to update item")
```

### 6. Delete Route (REQUIRED)
```python
@router.delete("/api/{item_id}", response_class=JSONResponse)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),        # 🚨 REQUIRED
    current_user: User = Depends(get_current_user),     # 🚨 REQUIRED
    service: [ServiceName] = Depends(get_service)
):
    """Delete item."""
    try:
        success = await service.delete(tenant_id, item_id)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete [slice_name] {item_id}")
        raise HTTPException(status_code=500, detail="Failed to delete item")
```

### Step 5: Create Tabulator Configuration File
**File:** `app/features/[domain]/[slice_name]/static/js/[slice_name]-table.js`

```javascript
window.initialize[SliceName]Table = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#[slice_name]-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/[domain]/[slice_name]/api/list",
        columns: [
            {
                title: "ID",
                field: "id",
                width: 80,
                sorter: "number",
                headerFilter: "number",
                headerFilterPlaceholder: "Filter by ID..."
            },
            {
                title: "Name",
                field: "name",
                editor: "input",
                headerFilter: "input",
                headerFilterPlaceholder: "Filter names...",
                sorter: "string",
                width: 200
            },
            {
                title: "Description",
                field: "description",
                sorter: "string",
                width: 250
            },
            {
                title: "Status",
                field: "is_active",
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Statuses",
                        "true": "Active",
                        "false": "Inactive"
                    }
                },
                sorter: "boolean",
                formatter: function(cell) {
                    return cell.getValue() ?
                        '<span class="badge bg-success">Active</span>' :
                        '<span class="badge bg-secondary">Inactive</span>';
                },
                width: 100
            },
            {
                title: "Created",
                field: "created_at",
                sorter: "datetime",
                formatter: function(cell) {
                    const value = cell.getValue();
                    return value ? new Date(value).toLocaleDateString() : '';
                },
                width: 120
            },
            {
                title: "Actions",
                field: "actions",
                formatter: function (cell) {
                    const rowData = cell.getRow().getData();
                    return `
                        <i class="ti ti-eye row-action-icon" title="View Details" onclick="view[SliceName](${rowData.id})"></i>
                        <i class="ti ti-edit row-action-icon" title="Edit" onclick="edit[SliceName](${rowData.id})"></i>
                        <i class="ti ti-trash row-action-icon text-danger" title="Delete" onclick="delete[SliceName](${rowData.id})"></i>
                    `;
                },
                headerSort: false,
                width: 120
            }
        ]
    });

    // Store in global registry
    window.[sliceName]Table = table;
    window.appTables["[slice_name]-table"] = table;

    // Add cellEdited event listener
    addCellEditedHandler(table, '/features/[domain]/[slice_name]', '[SliceName]');

    // Bulk Edit Selected
    addBulkEditHandler(table, '/features/[domain]/[slice_name]');

    // Bulk Delete Selected
    addBulkDeleteHandler(table, '/features/[domain]/[slice_name]', '[SliceName]');

    // Row action handlers
    bindRowActionHandlers("#[slice_name]-table", {
        onEdit: "edit[SliceName]",
        onDelete: "delete[SliceName]"
    });

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('[slice_name]-table', format, '[slice_name]s');
};

// Action handlers
window.view[SliceName] = function (id) {
    fetch(`/features/[domain]/[slice_name]/api/${id}`)
        .then(response => response.json())
        .then(data => {
            const modalBody = document.getElementById('modal-body');
            modalBody.innerHTML = `
                <div class="modal-header">
                    <h5 class="modal-title">View [SliceName]: ${data.name}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6"><strong>Name:</strong> ${data.name}</div>
                        <div class="col-md-6"><strong>Status:</strong> ${data.is_active ? 'Active' : 'Inactive'}</div>
                        <div class="col-12 mt-2"><strong>Description:</strong> ${data.description || 'No description provided'}</div>
                        <div class="col-md-6 mt-2"><strong>Created:</strong> ${new Date(data.created_at).toLocaleString()}</div>
                        <div class="col-md-6 mt-2"><strong>Updated:</strong> ${data.updated_at ? new Date(data.updated_at).toLocaleString() : 'Never'}</div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            `;
            new bootstrap.Modal(document.getElementById('modal')).show();
        })
        .catch(error => {
            console.error('Error loading [slice_name]:', error);
            showToast('Error loading [slice_name] details', 'error');
        });
};

window.edit[SliceName] = function (id) {
    editTabulatorRow(`/features/[domain]/[slice_name]/${id}/edit`);
};

window.delete[SliceName] = function (id) {
    deleteTabulatorRow(`/features/[domain]/[slice_name]/${id}/delete`, '#[slice_name]-table', {
        title: 'Delete [SliceName]',
        message: 'Are you sure you want to delete this [slice_name]? This action cannot be undone.',
        confirmText: 'Delete [SliceName]',
        cancelText: 'Cancel'
    });
};

// Initialize table when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("[slice_name]-table");

    if (tableElement && !window.[sliceName]TableInitialized) {
        window.[sliceName]TableInitialized = true;
        initialize[SliceName]Table();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', '[slice_name]-table');
        }, 100);
    }
});
```

### Step 6: Create Dashboard Template
**File:** `app/features/[domain]/[slice_name]/templates/[domain]/[slice_name]/dashboard.html`

```html
{% extends "base.html" %}

{% block head %}
<script src="/features/core/static/js/table-base.js"></script>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <!-- Page Header with Actions -->
    {% set table_actions = {
        'title': '[Slice Display Name]',
        'description': 'Manage [slice_name] items with filtering and actions',
        'icon': 'ti-list',
        'add_url': '#',
        'entity_name': '[slice_name]'
    } %}
    {% include 'components/ui/table_actions.html' %}

    <!-- Table Container -->
    <div class="card border-0 shadow">
        <div class="card-body p-0">
            <div id="[slice_name]-table"></div>
        </div>
    </div>
</div>

<!-- HTMX Modal Container -->
<div class="modal fade" id="modal" tabindex="-1" aria-labelledby="modalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div id="modal-body">
                <!-- HTMX content will be loaded here -->
            </div>
        </div>
    </div>
</div>

{% endblock %}

{% block scripts %}
<!-- [SliceName] table configuration (Tabulator operations) -->
<script src="/features/[slice_name]/static/js/[slice_name]-table.js"></script>
{% endblock %}
```

**🚨 CRITICAL URL PATTERNS:**
- ✅ **Static files**: `/features/[slice_name]/static/...` (simplified URL)
- ✅ **API endpoints**: `/features/[slice_name]/api/...` (matches router prefix)
- ✅ **HTMX endpoints**: `/features/[slice_name]/...` (matches router prefix)
- ❌ **WRONG**: `/features/[domain]/[slice_name]/...` (too verbose for static files)
```

### Step 7: Create __init__.py Files
**Critical:** Ensure Python can import your modules.

**File:** `app/features/[domain]/[slice_name]/__init__.py`
```python
# Empty file - required for Python package
```

**File:** `app/features/[domain]/__init__.py` (if doesn't exist)
```python
# Empty file - required for Python package
```

### Step 8: Register Routes in Main App
**File:** `app/main.py`

Add to imports:
```python
from .features.[domain].[slice_name].routes import router as [slice_name]_router
```

Add to router registration (follow existing patterns):
```python
# Add after existing router registrations
app.include_router([slice_name]_router, prefix="/features/[domain]", tags=["[domain]"])
```

### Step 8.5: Mount Static Files (If You Have Static Assets)
**🚨 CRITICAL:** If your slice has static files (JS, CSS), you MUST mount them.

**File:** `app/main.py`

Add after existing static mounts:
```python
# Mount [slice_name] static files
app.mount("/features/[slice_name]/static", StaticFiles(directory="app/features/[domain]/[slice_name]/static"), name="[slice_name]_static")
```

**Common Issues:**
- ❌ **Wrong URL pattern**: Use `/features/[slice_name]/static` (NOT `/features/[domain]/[slice_name]/static`)
- ❌ **Wrong directory**: Use full path `app/features/[domain]/[slice_name]/static`
- ✅ **Correct example**: `app.mount("/features/content-broadcaster/static", StaticFiles(directory="app/features/business_automations/content_broadcaster/static"), name="content_broadcaster_static")`

### Step 9: Update Database Configuration
**File:** `app/features/core/database.py`

Add to model imports (critical for table creation):
```python
import app.features.[domain].[slice_name].models
```

### Step 10: Create Database Migration (if using Alembic)
```bash
# Generate migration for new models
cd /path/to/project
alembic revision --autogenerate -m "Add [slice_name] table"
alembic upgrade head
```

### Step 11: Template Configuration ✨ AUTOMATIC
**✅ GOOD NEWS:** Template configuration is now automatic! No manual setup required.

#### A. Template Configuration in Routes (UPDATED)
**File:** `app/features/[domain]/[slice_name]/routes.py`

```python
# ✅ CORRECT: Use the global auto-discovery template system
from app.features.core.templates import templates

# ❌ WRONG: Don't create local template instances anymore
# from fastapi.templating import Jinja2Templates
# templates = Jinja2Templates(directory=["app/templates", "app/features/[domain]/[slice_name]/templates"])
```

**🚀 How Auto-Discovery Works:**
- The system automatically scans `app/features/` for all `templates/` directories
- No need to manually add your slice to any configuration
- Just create your templates directory and it's automatically included
- Supports any nesting level: `app/features/[domain]/[slice]/templates`

#### B. Template File Structure
**Required structure:**
```
app/features/[domain]/[slice_name]/
├── templates/
│   └── [slice_name]/
│       ├── [slice_name].html        # Main page template
│       └── partials/
│           ├── create_modal.html
│           ├── edit_modal.html
│           └── table_content.html
├── static/                          # Optional: slice-specific CSS/JS
│   ├── css/
│   └── js/
└── routes.py
```

#### C. Template Reference Verification
1. **Template file location:** `app/features/[domain]/[slice_name]/templates/[slice_name]/[slice_name].html`
2. **Template reference in routes:** `"[slice_name]/[slice_name].html"`
3. **Static files:** Place in `app/features/[domain]/[slice_name]/static/` if needed
4. **Shared components:** Reference as `'components/ui/table_actions.html'`

#### D. Template Syntax Validation
**🚨 MANDATORY CHECKS:**
1. **Block matching:** Every `{% block name %}` must have `{% endblock %}`
2. **Script placement:** JavaScript must be inside `{% block scripts %}...{% endblock %}`
3. **CSS placement:** Styles must be inside `{% block head %}...{% endblock %}`
4. **Content structure:** Main content inside `{% block content %}...{% endblock %}`

**Common template errors to avoid:**
- ❌ Orphaned `{% endblock %}` without opening `{% block %}`
- ❌ JavaScript outside of script blocks
- ❌ Missing base template extension: `{% extends "base.html" %}`

#### E. Verification Commands
```bash
# Test template loading (should return 302 redirect, not 500 error)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/features/[slice_name]/

# Check template file exists
ls -la app/features/[domain]/[slice_name]/templates/[slice_name]/[slice_name].html
```

### Step 12: Authentication & Multi-Tenant Setup

#### A. Verify Authentication Dependencies are Available
**Check file:** `app/features/auth/dependencies.py` contains:
```python
from fastapi.security import HTTPBearer
from fastapi import Depends, HTTPException, Request

async def get_current_user(request: Request):
    """Get current authenticated user - CRITICAL: Must exist."""
    # Implementation should validate JWT/session and return user info
    pass
```

#### B. Verify Tenant Dependencies are Available
**Check file:** `app/deps/tenant.py` contains:
```python
from fastapi import Request, Depends
from typing import Optional

async def tenant_dependency(request: Request) -> str:
    """Extract tenant from request context."""
    # Should return 'global' for logged-in users by default
    pass
```

#### C. Multi-Tenant Model Requirements
**Every model MUST have:**
```python
# Required for all models
tenant_id = Column(String(50), nullable=False, index=True, default="global")

# Required in service layer - ALL queries must filter by tenant
query = select(Model).filter(Model.tenant_id == tenant_id)
```

#### D. Authentication Flow Verification
1. **Unauthenticated requests** → 302 redirect to `/auth/login`
2. **Authenticated requests** → Extract `tenant_id` from token/session
3. **Service calls** → Always pass `tenant_id` to isolate data
4. **Default tenant** → `"global"` for regular logged-in users

### Step 13: Template Dependencies & Includes

#### A. Required Template Structure
```html
<!-- MUST extend base.html -->
{% extends "base.html" %}

<!-- MUST include CSS/JS in head block -->
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', path='css/tabulator-unified.css') }}">
<script src="https://unpkg.com/tabulator-tables@6.2.1/dist/js/tabulator.min.js"></script>
{% endblock %}

<!-- MUST use components/ui/table_actions.html for header -->
{% set table_actions = {
    'title': '[Title]',
    'description': '[Description]',
    'icon': 'ti-[icon]',
    'add_url': '#',
    'entity_name': '[entity]'
} %}
{% include 'components/ui/table_actions.html' %}
```

#### B. Required JavaScript Dependencies
**Templates MUST access these globals:**
```javascript
// CRITICAL: Must be available from base.html or table-base.js
window.advancedTableConfig  // Table configuration
window.showToast()          // Success/error messages
window.showConfirmModal()   // Delete confirmations
```

#### C. Template Path Resolution
**FastAPI template resolution order:**
1. `app/features/[domain]/[slice_name]/templates/` (slice-specific)
2. `app/templates/` (global templates)
3. Components: `app/templates/components/ui/`

### Step 14: Create Test Data with GLOBAL Tenant
**Critical:** Always create test data for the `global` tenant.

```python
# Create test data script
import asyncio
from app.features.core.database import get_db
from app.features.[domain].[slice_name].models import [ModelName]
from datetime import datetime

async def create_test_data():
    async for session in get_db():
        items = [
            [ModelName](
                tenant_id="global",  # CRITICAL: Use global tenant
                name="Test Item 1",
                description="First test item",
                is_active=True
            ),
            [ModelName](
                tenant_id="global",  # CRITICAL: Use global tenant
                name="Test Item 2",
                description="Second test item",
                is_active=False
            ),
            [ModelName](
                tenant_id="global",  # CRITICAL: Use global tenant
                name="Test Item 3",
                description="Third test item",
                is_active=True
            )
        ]

        for item in items:
            session.add(item)
        await session.commit()
        break

asyncio.run(create_test_data())
```

## 🚨 Common Pitfalls to Avoid

### ❌ Don't Do This:
1. Using `get_optional_current_user` in routes
2. Returning `{"data": []}` instead of `{"items": []}`
3. Creating test data with wrong tenant_id
4. Forgetting tenant_dependency in routes
5. Not handling both `response.data` and `response.items` in templates
6. Missing authentication requirements
7. Inconsistent response formats between endpoints
8. **Wrong template paths** - `dashboard.html` instead of `[domain]/[slice_name]/dashboard.html`
9. **Missing model imports** in `database.py` - causes table creation failures
10. **Forgetting __init__.py files** - causes import errors
11. **Wrong API endpoints** in JavaScript - must match router prefix exactly
12. **Missing tenant filtering** in all service methods
13. **Missing dedicated table JS file** - causes table functionality to break
14. **Using inline JavaScript** instead of dedicated `*-table.js` files
15. **Wrong table ID references** - JavaScript and HTML must match exactly

### ✅ Always Do This:
1. Use `get_current_user` for all authenticated routes
2. Return `{"items": [], "total": x, "page": y, "size": z}` format
3. Create test data with `tenant_id="global"`
4. Include `tenant_dependency` in all routes
5. Use `advancedTableConfig` for table initialization
6. Test with actual authentication (not API-only tests)
7. Follow exact template patterns from working slices
8. **Use correct template paths**: `"[domain]/[slice_name]/dashboard.html"`
9. **Import models in database.py** for table creation
10. **Create __init__.py files** in all package directories
11. **Match JavaScript endpoints** to router definitions exactly
12. **Filter ALL queries by tenant_id** in service layer
13. **Create dedicated `[slice_name]-table.js`** file in `static/js/` directory
14. **Include table JS file** in template `{% block scripts %}` section
15. **Use consistent table IDs** between HTML template and JavaScript configuration

## 🔧 Advanced Multi-Tenant Patterns

### Tenant Isolation Levels

#### Level 1: Row-Level Isolation (Standard)
```python
# Every query MUST include tenant filter
query = select(Model).filter(Model.tenant_id == tenant_id)

# Count queries MUST also filter
count_query = select(func.count(Model.id)).filter(Model.tenant_id == tenant_id)
```

#### Level 2: Cross-Tenant Operations (Admin Only)
```python
# Only for global admins - check user permissions first
if user.is_global_admin:
    query = select(Model)  # No tenant filter
else:
    query = select(Model).filter(Model.tenant_id == tenant_id)
```

### Authentication Integration Patterns

#### Pattern 1: Standard Route Authentication
```python
@router.get("/api/list")
async def get_list(
    tenant_id: str = Depends(tenant_dependency),    # Extract from token/session
    current_user = Depends(get_current_user),       # Validate authentication
    service: Service = Depends(get_service)
):
    # tenant_id automatically extracted from authenticated user context
    return await service.get_list(tenant_id=tenant_id)
```

#### Pattern 2: Optional Authentication (Rare)
```python
# Only use for public endpoints or health checks
@router.get("/public/status")
async def public_status(
    current_user = Depends(get_optional_current_user)  # May be None
):
    # Handle both authenticated and anonymous access
    pass
```

### Template Integration Patterns

#### Pattern 1: Standard Table Template
```html
<!-- Exact path resolution -->
{% extends "base.html" %}

<!-- Required for all table pages -->
{% set table_actions = {
    'title': 'Items',
    'description': 'Manage your items',
    'icon': 'ti-list',
    'add_url': '/features/domain/slice/create',
    'entity_name': 'item'
} %}
{% include 'components/ui/table_actions.html' %}

<!-- JavaScript MUST use exact API path -->
<script>
table = new Tabulator("#table", {
    ajaxURL: "/features/[domain]/[slice_name]/api/list"  // CRITICAL: Match router
});
</script>
```

## 🎯 MANDATORY VERIFICATION CHECKLIST

**❌ DO NOT PROCEED WITHOUT 100% COMPLETION OF ALL ITEMS**

### 🔒 SECURITY-CRITICAL CHECKS (AUDIT EVERY SINGLE ROUTE)

#### Route Security Verification - ZERO TOLERANCE FOR MISSING DEPENDENCIES
- [ ] **🚨 COUNT ALL ROUTES: Every `@router.` decorator MUST have both dependencies**
- [ ] **🚨 VERIFY: `tenant_id: str = Depends(tenant_dependency)` in EVERY route**
- [ ] **🚨 VERIFY: `current_user: User = Depends(get_current_user)` in EVERY route**
- [ ] **🚨 VERIFY: All routes pass `tenant_id` to service methods**
- [ ] **🚨 VERIFY: No route can access data without authentication**
- [ ] **🚨 VERIFY: No route can access cross-tenant data**

#### Mandatory Security Tests
- [ ] **Test unauthenticated access returns 403/401 (not 500 or data)**
- [ ] **Test authenticated user cannot access other tenant's data**
- [ ] **Verify all service calls include tenant_id parameter**
- [ ] **Verify no routes missing either dependency**

#### Required Imports Verification
- [ ] **`from app.features.auth.dependencies import get_current_user`**
- [ ] **`from app.features.auth.models import User`**
- [ ] **`from app.deps.tenant import tenant_dependency`**
- [ ] **All routes use correct type hints: `current_user: User`**

### 🎨 TEMPLATE VERIFICATION (PREVENTS 500 ERRORS)

#### Template Configuration Verification - CRITICAL FOR FUNCTIONALITY
- [ ] **🚨 VERIFY: `templates = Jinja2Templates(directory=["app/templates", "app/features/[domain]/[slice_name]/templates"])`**
- [ ] **🚨 VERIFY: Template file exists at correct path: `app/features/[domain]/[slice_name]/templates/[slice_name]/[slice_name].html`**
- [ ] **🚨 VERIFY: Base template accessible: `app/templates/base.html`**
- [ ] **🚨 VERIFY: Template extends base: `{% extends "base.html" %}`**
- [ ] **🚨 VERIFY: All `{% block %}` tags have matching `{% endblock %}`**
- [ ] **🚨 VERIFY: JavaScript inside `{% block scripts %}...{% endblock %}`**
- [ ] **🚨 VERIFY: CSS inside `{% block head %}...{% endblock %}`**

#### Template Error Prevention
- [ ] **Test template loading: `curl -w "%{http_code}" http://localhost:8000/features/[slice_name]/` returns 302 (not 500)**
- [ ] **No orphaned `{% endblock %}` without opening `{% block %}`**
- [ ] **No JavaScript or CSS outside proper blocks**
- [ ] **Template directory matches Jinja2Templates configuration**

### Core Functionality
- [ ] Routes return 302 redirect when not authenticated
- [ ] Routes return data when properly authenticated
- [ ] Table displays data without empty results
- [ ] All CRUD operations work through the UI
- [ ] Tenant filtering works correctly
- [ ] Response format matches standard pattern (`items`, not `data`)
- [ ] Test data exists for the correct tenant (`tenant_id="global"`)

### File Structure & Imports
- [ ] All `__init__.py` files created in package directories
- [ ] Model imported in `app/features/core/database.py`
- [ ] Router registered in `app/main.py` with correct prefix
- [ ] Template path matches: `[domain]/[slice_name]/dashboard.html`
- [ ] JavaScript API endpoints match router definitions exactly
- [ ] **Dedicated `[slice_name]-table.js` file created** in `static/js/` directory
- [ ] **Table JS file included** in template `{% block scripts %}` section
- [ ] **Table-base.js included** in template `{% block head %}` section

### Service Layer Security
- [ ] **All service methods require `tenant_id` parameter**
- [ ] **All database queries filter by `tenant_id`**
- [ ] **No service method can return cross-tenant data**
- [ ] **Service methods validate tenant ownership**

### Template & UI Integration
- [ ] Template extends `base.html`
- [ ] Uses `components/ui/table_actions.html` for header
- [ ] **Table ID consistent** between HTML and JavaScript (`#[slice_name]-table`)
- [ ] **Dedicated table initialization function** (`initialize[SliceName]Table`)
- [ ] **Global table registry updated** (`window.appTables["[slice_name]-table"]`)
- [ ] JavaScript accesses `window.advancedTableConfig`
- [ ] Tabulator handles both `response.items` and `response.data`
- [ ] Action icons use `row-action-icon` class
- [ ] Modals use `showConfirmModal()` for deletions
- [ ] Success/error messages use `showToast()`
- [ ] **Action handlers properly bound** (`window.view[SliceName]`, `edit[SliceName]`, `delete[SliceName]`)

### API Compliance
- [ ] List endpoint returns `{"items": [], "total": x, "page": y, "size": z}`
- [ ] Pagination uses `page` and `size` parameters
- [ ] Filtering parameters properly handled
- [ ] Error responses return appropriate HTTP status codes
- [ ] All endpoints require authentication via `get_current_user`

## 📝 Quick Reference

### Standard Response Format:
```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 25
}
```

### Standard Route Dependencies:
```python
tenant_id: str = Depends(tenant_dependency),
current_user = Depends(get_current_user),
service: ServiceName = Depends(get_service)
```

### Standard Tabulator Response Handler:
```javascript
ajaxResponse: function(url, params, response) {
    return {
        data: response.data || response.items || [],
        last_page: Math.ceil((response.total || 0) / (params.size || 25))
    };
}
```

### Template Path Examples:
```
✅ Correct: "[domain]/[slice_name]/dashboard.html"
❌ Wrong:   "dashboard.html"
❌ Wrong:   "[slice_name]/dashboard.html"

✅ Correct: "/features/[domain]/[slice_name]/api/list"
❌ Wrong:   "/api/[slice_name]/list"
❌ Wrong:   "/[slice_name]/api/list"
```

### Model Requirements:
```python
# Required fields for multi-tenant support
tenant_id = Column(String(50), nullable=False, index=True, default="global")

# Required method for API responses
def to_dict(self) -> Dict[str, Any]:
    return {
        "id": self.id,
        "tenant_id": self.tenant_id,
        # ... other fields
    }
```

## 🚀 Testing Your New Slice

### 1. Test Authentication
```bash
# Should return 302 redirect
curl -I http://localhost:8000/features/[domain]/[slice_name]/

# Should return 302 redirect
curl -I http://localhost:8000/features/[domain]/[slice_name]/api/list
```

### 2. Test with Authentication
- Login to the application via browser
- Navigate to `/features/[domain]/[slice_name]/`
- Verify table loads with your test data
- Verify filters work
- Verify view/edit/delete actions work

### 3. Test Data Isolation
- Ensure only `global` tenant data appears
- Verify no cross-tenant data leakage

---

## 🚀 **RECOMMENDED: Use Automated Slice Generator**

**Instead of manual creation, use the automated slice generator to avoid all routing issues:**

```bash
# Generate a new slice automatically
python scripts/create_slice.py business_automations email_campaigns
python scripts/create_slice.py administration user_roles

# The script automatically:
# ✅ Creates correct directory structure
# ✅ Uses proper routing patterns (no double prefixes)
# ✅ Registers routes in main.py correctly
# ✅ Mounts static files properly
# ✅ Uses /api/list endpoints
# ✅ Updates database imports
# ✅ Follows all current best practices
```

**Benefits:**
- **Zero Configuration Errors**: Eliminates manual mistakes
- **Always Current**: Uses latest architectural patterns
- **Saves Time**: Complete slice in seconds vs hours
- **Consistent**: Every slice follows exact same patterns

**Usage:**
```bash
# Basic slice creation
python scripts/create_slice.py <domain> <slice_name>

# Examples
python scripts/create_slice.py business_automations email_campaigns
python scripts/create_slice.py administration user_roles
python scripts/create_slice.py core notifications

# Skip static files if not needed
python scripts/create_slice.py administration simple_slice --no-static
```

**Next Steps After Generation:**
1. `alembic revision --autogenerate -m "Add [slice_name] tables"`
2. `alembic upgrade head`
3. Restart server
4. Access at: `http://localhost:8000/features/[domain]/[slice_name]/`
- Test with different user contexts if available

Follow this guide exactly and your slice will work on the first try! 🎯
