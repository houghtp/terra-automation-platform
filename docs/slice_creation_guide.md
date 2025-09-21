# 🔧 Complete Slice Creation Guide

## Overview
This guide provides exact steps to create a fully functional vertical slice with a table that follows the standard FastAPI template patterns. Follow these steps precisely to avoid common issues.

## ⚠️ Critical Requirements

### 1. Authentication Pattern
- **ALWAYS** use `get_current_user` dependency (never `get_optional_current_user`)
- **ALWAYS** include `tenant_dependency` in all routes
- **NEVER** mix authentication patterns within a slice

### 2. Response Format Standardization
- **ALWAYS** use `{"items": [], "total": x, "page": y, "size": z}` for list endpoints
- **NEVER** use `{"data": [], "total": x, "offset": y, "limit": z}` format
- **ALWAYS** ensure Tabulator templates handle both `response.items` and `response.data`

### 3. Tenant Data Alignment
- **ALWAYS** create test data for the `global` tenant (default for logged-in users)
- **ALWAYS** test with actual tenant filtering
- **NEVER** assume tenant filtering will work without proper test data

## 📋 Step-by-Step Implementation

### Step 1: Create Slice Directory Structure
```bash
mkdir -p app/features/[domain]/[slice_name]/{models,services,routes,templates,tests,static}
mkdir -p app/features/[domain]/[slice_name]/templates/[domain]/[slice_name]/{partials}
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

### Step 4: Create Routes
**File:** `app/features/[domain]/[slice_name]/routes.py`

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
from app.features.auth.dependencies import get_current_user  # CRITICAL: Use get_current_user
from app.deps.tenant import tenant_dependency
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/[slice_name]", tags=["[slice_name]"])

async def get_service(db: AsyncSession = Depends(get_db)) -> [ServiceName]:
    """Dependency to get service."""
    return [ServiceName](db)

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user)  # CRITICAL: Required auth
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

@router.get("/api/list", response_class=JSONResponse)
async def get_list(
    request: Request,
    search: Optional[str] = Query(None, description="Search term"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(25, ge=1, le=200, description="Page size"),
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),  # CRITICAL: Required auth
    service: [ServiceName] = Depends(get_service)
):
    """Get paginated list - CRITICAL: Must return 'items' format."""
    try:
        offset = (page - 1) * size

        result = await service.get_list(
            tenant_id=tenant_id,
            limit=size,
            offset=offset,
            search=search,
            is_active=is_active
        )

        # CRITICAL: Return in standard format with 'items'
        return JSONResponse(content={
            "items": result["data"],  # CRITICAL: Use 'items', not 'data'
            "total": result["total"],
            "page": page,
            "size": size
        })

    except Exception as e:
        logger.exception("Failed to get [slice_name] list via API")
        raise HTTPException(status_code=500, detail="Failed to retrieve items")

@router.get("/api/{item_id}", response_class=JSONResponse)
async def get_item(
    item_id: int,
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    service: [ServiceName] = Depends(get_service)
):
    """Get item by ID."""
    try:
        item = await service.get_by_id(tenant_id, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get [slice_name] {item_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve item")

@router.post("/api", response_class=JSONResponse)
async def create_item(
    request: Request,
    data: dict,  # Use proper Pydantic schema in production
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    service: [ServiceName] = Depends(get_service)
):
    """Create new item."""
    try:
        item = await service.create(tenant_id, data)
        return item.to_dict()
    except Exception as e:
        logger.exception("Failed to create [slice_name]")
        raise HTTPException(status_code=500, detail="Failed to create item")

@router.put("/api/{item_id}", response_class=JSONResponse)
async def update_item(
    item_id: int,
    request: Request,
    data: dict,  # Use proper Pydantic schema in production
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
    service: [ServiceName] = Depends(get_service)
):
    """Update existing item."""
    try:
        item = await service.update(tenant_id, item_id, data)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update [slice_name] {item_id}")
        raise HTTPException(status_code=500, detail="Failed to update item")

@router.delete("/api/{item_id}", response_class=JSONResponse)
async def delete_item(
    item_id: int,
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    current_user = Depends(get_current_user),
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

### Step 5: Create Dashboard Template
**File:** `app/features/[domain]/[slice_name]/templates/[domain]/[slice_name]/dashboard.html`

```html
{% extends "base.html" %}

{% block head %}
<link rel="stylesheet" href="{{ url_for('static', path='css/tabulator-unified.css') }}">
<script src="https://unpkg.com/tabulator-tables@6.2.1/dist/js/tabulator.min.js"></script>
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

    <!-- Filters -->
    <div class="filter-card">
        <div class="row">
            <div class="col-md-4">
                <label for="search-filter" class="form-label">Search</label>
                <input type="text" id="search-filter" class="form-control" placeholder="Search items...">
            </div>
            <div class="col-md-3">
                <label for="status-filter" class="form-label">Status</label>
                <select id="status-filter" class="form-select">
                    <option value="">All Statuses</option>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                </select>
            </div>
            <div class="col-md-2">
                <label class="form-label">&nbsp;</label>
                <button type="button" class="btn btn-outline-secondary d-block" onclick="clearFilters()">
                    <i class="ti ti-filter-off"></i> Clear
                </button>
            </div>
        </div>
    </div>

    <!-- Table Container -->
    <div class="card border-0 shadow">
        <div class="card-body p-0">
            <div id="[slice_name]-table"></div>
        </div>
    </div>
</div>

<!-- Modals -->
<div class="modal fade" id="item-modal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="modal-title">Item Details</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="modal-body">
                <!-- Content loaded dynamically -->
            </div>
        </div>
    </div>
</div>

<script>
let table;

document.addEventListener('DOMContentLoaded', function() {
    initializeTable();
    setupEventListeners();
});

function initializeTable() {
    // CRITICAL: Use advancedTableConfig for consistency
    const config = window.advancedTableConfig || {};

    table = new Tabulator("#[slice_name]-table", {
        ...config,
        ajaxURL: "/features/[domain]/[slice_name]/api/list",  // CRITICAL: Correct endpoint
        columns: [
            {title: "ID", field: "id", width: 80, sorter: "number"},
            {title: "Name", field: "name", sorter: "string", headerFilter: "input"},
            {title: "Description", field: "description", sorter: "string"},
            {title: "Status", field: "is_active", width: 100, formatter: function(cell) {
                return cell.getValue() ?
                    '<span class="badge bg-success">Active</span>' :
                    '<span class="badge bg-secondary">Inactive</span>';
            }},
            {title: "Created", field: "created_at", width: 150, sorter: "datetime", formatter: "datetime", formatterParams: {
                outputFormat: "MM/DD/YYYY HH:mm"
            }},
            {
                title: "Actions",
                field: "id",
                width: 120,
                headerSort: false,
                formatter: function(cell) {
                    return `<i class="ti ti-eye row-action-icon" title="View Details" onclick="viewItem(${cell.getValue()})"></i>
                            <i class="ti ti-edit row-action-icon" title="Edit" onclick="editItem(${cell.getValue()})"></i>
                            <i class="ti ti-trash row-action-icon" title="Delete" onclick="deleteItem(${cell.getValue()})"></i>`;
                }
            }
        ],
        // CRITICAL: Handle both response formats
        ajaxResponse: function(url, params, response) {
            return {
                data: response.data || response.items || [],  // CRITICAL: Support both formats
                last_page: Math.ceil((response.total || 0) / (params.size || 25))
            };
        },
        rowClick: function(e, row) {
            viewItem(row.getData().id);
        }
    });
}

function setupEventListeners() {
    // Search filter
    document.getElementById('search-filter').addEventListener('input', function() {
        updateFilters();
    });

    // Status filter
    document.getElementById('status-filter').addEventListener('change', function() {
        updateFilters();
    });
}

function updateFilters() {
    const filters = {};

    const search = document.getElementById('search-filter').value;
    if (search) filters.search = search;

    const status = document.getElementById('status-filter').value;
    if (status) filters.is_active = status;

    table.setData(table.options.ajaxURL, filters);
}

function clearFilters() {
    document.getElementById('search-filter').value = '';
    document.getElementById('status-filter').value = '';
    table.setData(table.options.ajaxURL);
}

function viewItem(id) {
    fetch(`/features/[domain]/[slice_name]/api/${id}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('modal-title').textContent = 'View Item: ' + data.name;
            document.getElementById('modal-body').innerHTML = `
                <div class="row">
                    <div class="col-md-6"><strong>Name:</strong> ${data.name}</div>
                    <div class="col-md-6"><strong>Status:</strong> ${data.is_active ? 'Active' : 'Inactive'}</div>
                    <div class="col-12 mt-2"><strong>Description:</strong> ${data.description || 'N/A'}</div>
                    <div class="col-md-6 mt-2"><strong>Created:</strong> ${new Date(data.created_at).toLocaleString()}</div>
                    <div class="col-md-6 mt-2"><strong>Updated:</strong> ${data.updated_at ? new Date(data.updated_at).toLocaleString() : 'Never'}</div>
                </div>
            `;
            new bootstrap.Modal(document.getElementById('item-modal')).show();
        })
        .catch(error => {
            console.error('Error loading item:', error);
            showToast('Error loading item details', 'error');
        });
}

function editItem(id) {
    // Implement edit functionality
    console.log('Edit item:', id);
}

function deleteItem(id) {
    showConfirmModal('Delete Item', 'Are you sure you want to delete this item?', function() {
        fetch(`/features/[domain]/[slice_name]/api/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Item deleted successfully', 'success');
                table.replaceData();
            } else {
                showToast('Failed to delete item', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting item:', error);
            showToast('Error deleting item', 'error');
        });
    });
}

// Export functions for table actions
window.viewItem = viewItem;
window.editItem = editItem;
window.deleteItem = deleteItem;
</script>
{% endblock %}
```

### Step 6: Create __init__.py Files
**Critical:** Ensure Python can import your modules.

**File:** `app/features/[domain]/[slice_name]/__init__.py`
```python
# Empty file - required for Python package
```

**File:** `app/features/[domain]/__init__.py` (if doesn't exist)
```python
# Empty file - required for Python package
```

### Step 7: Register Routes in Main App
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

### Step 8: Update Database Configuration
**File:** `app/features/core/database.py`

Add to model imports (critical for table creation):
```python
import app.features.[domain].[slice_name].models
```

### Step 9: Create Database Migration (if using Alembic)
```bash
# Generate migration for new models
cd /path/to/project
alembic revision --autogenerate -m "Add [slice_name] table"
alembic upgrade head
```

### Step 10: Template Path Verification
**Critical:** Ensure template paths match exactly.

1. **Template file location:** `app/features/[domain]/[slice_name]/templates/[domain]/[slice_name]/dashboard.html`
2. **Template reference in routes:** `"[domain]/[slice_name]/dashboard.html"`
3. **Static files:** Place in `app/features/[domain]/[slice_name]/static/` if needed
4. **Shared components:** Reference as `'components/ui/table_actions.html'`

### Step 11: Authentication & Multi-Tenant Setup

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

### Step 12: Template Dependencies & Includes

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

### Step 13: Create Test Data with GLOBAL Tenant
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

## 🎯 Verification Checklist

Before considering the slice complete:

### Core Functionality
- [ ] Routes return 302 redirect when not authenticated
- [ ] Routes return data when properly authenticated
- [ ] Table displays data without empty results
- [ ] All CRUD operations work through the UI
- [ ] Tenant filtering works correctly
- [ ] Response format matches standard pattern
- [ ] Authentication dependencies are consistent
- [ ] Test data exists for the correct tenant

### File Structure & Imports
- [ ] All `__init__.py` files created in package directories
- [ ] Model imported in `app/features/core/database.py`
- [ ] Router registered in `app/main.py` with correct prefix
- [ ] Template path matches: `[domain]/[slice_name]/dashboard.html`
- [ ] JavaScript API endpoints match router definitions exactly

### Authentication & Multi-Tenant
- [ ] All routes use `get_current_user` (not optional)
- [ ] All routes include `tenant_dependency`
- [ ] All service methods filter by `tenant_id`
- [ ] Test data created with `tenant_id="global"`
- [ ] Models have `tenant_id` column with index
- [ ] Cross-tenant data access properly blocked

### Template & UI Integration
- [ ] Template extends `base.html`
- [ ] Uses `components/ui/table_actions.html` for header
- [ ] JavaScript accesses `window.advancedTableConfig`
- [ ] Tabulator handles both `response.items` and `response.data`
- [ ] Action icons use `row-action-icon` class
- [ ] Modals use `showConfirmModal()` for deletions
- [ ] Success/error messages use `showToast()`

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
- Test with different user contexts if available

Follow this guide exactly and your slice will work on the first try! 🎯
