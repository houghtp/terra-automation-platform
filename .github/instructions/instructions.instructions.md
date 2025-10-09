---
applyTo: "**"
---

# 🧠 Project: TerraAutomationPlatform — Copilot Coding Instructions

This is a lightweight FastAPI vertical-slice templat---

## 🔄 Critical Standardization Patterns (MANDATORY)

> **CRITICAL**: These patterns ensure consistency across all slices and prevent common integration issues.

### 📊 API Response Standardization

**✅ CORRECT API Format (follow users pattern):**
```python
# In crud_routes.py - return simple array
@router.get("/list")
async def get_items_list():
    items = await service.get_items()
    result = [item.to_dict() for item in items]
    return result  # Direct array, not wrapped
```

**❌ WRONG API Format:**
```python
# Don't wrap in pagination objects that break Tabulator
return {"data": result, "pagination": {...}}
```

**Root Cause**: Tabulator expects simple arrays when using `ajaxResponse: standardAjaxResponse`. Complex pagination wrappers cause empty tables and require custom handling.

### 🏗️ Route Organization Pattern

**✅ CORRECT Route Separation:**
```
routes/
├── form_routes.py      # UI forms, validations, dashboard pages
├── crud_routes.py      # Database operations, API endpoints
└── dashboard_routes.py # Stats, analytics (if needed)
```

**Route Responsibilities:**
- **form_routes.py**: HTMX partials, modal forms, UI validation, dashboard rendering
- **crud_routes.py**: GET/POST/PUT/DELETE operations, list APIs, field updates
- **dashboard_routes.py**: Statistics endpoints, chart data, analytics

**Anti-Pattern**: ❌ Mixing CRUD operations in form routes or validation logic in CRUD routes.

### 🎯 JavaScript Table Standardization

**✅ REQUIRED Table Structure:**
```javascript
window.initializeEntityTable = function () {
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#entity-table", {
        ...advancedTableConfig,  // MANDATORY: Use centralized config
        ajaxURL: "/features/module/entity/api/list",
        columns: [
            // Column definitions with proper width handling
        ]
    });

    // MANDATORY: Register in global registry
    window.entityTable = table;
    window.appTables["entity-table"] = table;

    return table;
};

// MANDATORY: Standard export function
window.exportTable = function (format) {
    return exportTabulatorTable('entity-table', format, 'entity_name');
};

// Standard initialization pattern
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("entity-table");
    if (tableElement && !window.entityTableInitialized) {
        window.entityTableInitialized = true;
        initializeEntityTable();

        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'entity-table');
        }, 100);
    }
});
```

**❌ Anti-Patterns to AVOID:**
- Custom `showToast()` functions (use `table-base.js` version)
- Manual select-all checkbox handling (handled by `advancedTableConfig`)
- Custom HTMX listeners (use standard patterns)
- Fixed `width` on all columns (causes horizontal overflow)

### 📏 Table Column Width Standards

**✅ CORRECT Width Strategy:**
```javascript
columns: [
    {
        title: "Name",
        field: "name",
        // No width = auto-sizing via fitColumns
        headerFilter: "input"
    },
    {
        title: "Status",
        field: "status",
        width: 80,  // Fixed width only for predictable content
        headerFilter: "list"
    },
    {
        title: "Description",
        field: "description",
        minWidth: 150,  // Minimum width, can expand
        headerFilter: "input"
    },
    {
        title: "Actions",
        field: "actions",
        width: 100,  // Fixed width for action buttons
        headerSort: false
    }
]
```

**Width Guidelines:**
- **No `width`**: Auto-sizing for flexible content (names, emails, messages)
- **Fixed `width`**: Small predictable columns (status badges, toggles, actions)
- **`minWidth`**: Content that needs minimum space but can expand

### 🔗 Service Method Naming Standards

**✅ MANDATORY Naming Convention:**

**Management Service Pattern:**
```python
class EntityManagementService:
    # Primary method: get_entity_by_id (matches CRUD service)
    async def get_entity_by_id(self, entity_id):
        return await self._crud_service.get_entity_by_id(entity_id)

    # Standardized method for forms: get_[full_entity_name]_by_id
    async def get_full_entity_name_by_id(self, entity_id):
        """Standardized method name for form routes consistency."""
        return await self.get_entity_by_id(entity_id)
```

**Examples from codebase:**
- **Audit**: `get_audit_log_by_id()` (form routes use this)
- **Logs**: `get_application_log_by_id()` (delegates to `get_log_by_id()`)
- **Users**: `get_user_by_id()` (standard pattern)

**Critical**: Form routes must call standardized method names. CRUD services use shorter names internally.

### 🎨 Icon & Action Standardization

**✅ MANDATORY Action Icon Pattern:**
```javascript
// All view actions use same formatter
{
    title: "Actions",
    field: "id",
    formatter: (cell) => formatViewAction(cell, 'viewEntityDetails')
}

// Standard view function pattern
window.viewEntityDetails = function (entityId) {
    htmx.ajax('GET', `/module/entity/partials/entity_details?entity_id=${entityId}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        const modal = new bootstrap.Modal(document.getElementById('modal'));
        modal.show();
    });
};
```

**Result**: All tables use identical `ti ti-eye` icons with consistent styling and behavior.

### 🗂️ Template Structure Standards

**✅ REQUIRED Template Pattern:**
```html
<!-- Main dashboard template -->
{% extends "base.html" %}
{% block content %}
<div id="entity-area">
  <div id="entity-table-container">
    {% include "module/entity/partials/list_content.html" %}
  </div>
</div>
{% endblock %}

<!-- list_content.html partial -->
<div class="card">
  <div class="card-header">
    {% include "components/ui/table_actions.html" %}
  </div>
  <div class="card-body p-0">
    <div id="entity-table"></div>
  </div>
</div>
```

**MANDATORY**: Always use `table_actions.html` partial for consistent header with search, export, and action buttons.

### 🔍 Modal Detail Standards

**✅ REQUIRED Modal Route Pattern:**
```python
@router.get("/partials/entity_details")
async def get_entity_details_partial(
    request: Request,
    entity_id: int,
    service: EntityManagementService = Depends(get_entity_service)
):
    entity = await service.get_full_entity_name_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return templates.TemplateResponse(
        "module/entity/partials/entity_details.html",
        {"request": request, "entity": entity}
    )
```

**MANDATORY**: Use standardized service method names, proper 404 handling, and consistent parameter patterns.

---

## 🚨 Common Integration Failures & Fixes

### **Empty Tables (Most Common)**
**Symptoms**: Table loads but shows "No Data Available"
**Root Cause**: API returns complex objects instead of simple arrays
**Fix**: Ensure CRUD routes return `return result` not `return {"data": result}`

### **Horizontal Scroll Issues**
**Symptoms**: Table extends beyond screen width, no scroll bars
**Root Cause**: Fixed `width` on too many columns
**Fix**: Use `minWidth` for flexible columns, `width` only for small predictable columns

### **Modal Details Not Loading**
**Symptoms**: Eye icon works but modal shows error
**Root Cause**: Missing standardized service method names
**Fix**: Add `get_[full_entity_name]_by_id()` method to management service

### **Inconsistent JavaScript Functions**
**Symptoms**: Different tables have different behaviors/styling
**Root Cause**: Custom implementations instead of using `table-base.js` utilities
**Fix**: Remove custom functions, use centralized `advancedTableConfig` and utilities

### **Route Organization Confusion**
**Symptoms**: CRUD mixed with forms, validation in wrong files
**Root Cause**: Not following crud_routes vs form_routes separation
**Fix**: Move database operations to `crud_routes.py`, UI logic to `form_routes.py`

---

## ✅ Prompt Examples (Copilot Reference)

- "Create `roles/` slice with model, routes, Tabulator table, HTMX modals."
- "Use `get_async_session()` with `async_sessionmaker` and dependency injection."
- "Add `try/except` with `logger.exception()` and return 500 HTTP error."
- "Avoid fallback logic — just log and fail if needed."
- "Convert SQLAlchemy model to dict using `.to_dict()`, not `__dict__`."
- "Use `table-action-btn table-action-add` for action buttons, not `btn btn-primary`."
- "Use `showConfirmModal()` for delete confirmations, not `hx-confirm`."
- "Apply `row-action-icon` class to edit/delete icons without inline styles."
- "Follow API standardization: return simple arrays, not pagination wrappers."
- "Use `minWidth` for flexible columns, `width` only for predictable content."
- "Add standardized service methods matching form route expectations."
- "Use centralized `advancedTableConfig` and `table-base.js` utilities."g:

- **Backend**: FastAPI (Python 3.12+), async SQLAlchemy
- **Frontend**: HTMX, Alpine.js, Tabulator.js, Apache ECharts (via CDN)
- **Database**: PostgreSQL (supports JSONB, temporal tables)
- **Architecture**: Vertical slice — each module owns its own models, routes, services, templates, and tests
- **Infra**: Ubuntu-based, dockerized, runs locally in WSL2

---

## 🧱 Architectural Principles

- Follow **vertical slice architecture**: each feature module  contains its own complete stack.
- Avoid central/shared `models/`, `services/`, or `controllers/` unless truly generic (e.g. pagination, logging).
- Use **async SQLAlchemy** with `async_sessionmaker` and dependency injection.
- Maintain a **clear separation of concerns**:
  - Routes = request/response logic
  - Services = business/domain logic
  - Models = persistence/data layer
  - Templates = UI rendering
- Include **type hints** and **docstrings** in all functions and classes.
- Apply **SOLID** principles:
  - **S**ingle Responsibility — each module does one thing
  - **O**pen/Closed — extend behavior, don’t rewrite
  - **L**iskov Substitution — avoid tight coupling
  - **I**nterface Segregation — keep code minimal and focused
  - **D**ependency Inversion — inject services/configs
- All Routes should follow the same pattern as the demo route for basic crud operations.

## 🚫 Anti-Patterns (Copilot: avoid these)

> These rules are for Copilot and LLM-based autocompletion.

- ❌ **Do NOT** create fallback methods unless explicitly instructed
  - e.g. avoid patterns like `safe_get_x()` or `try_alternate_y()` unless needed.
- ❌ **Do NOT** introduce retries, alternate flows, or verbose error handling boilerplate.
- ✅ **Do** use simple `try/except` blocks with structured logging:
  ```python
  try:
      result = await my_service.load_data()
  except SomeError as e:
      logger.exception("Failed to load data")
      raise HTTPException(status_code=500, detail="Internal error")
  ```
- ❌ **Do NOT** swallow or silently ignore exceptions.
- ✅ Let errors fail fast and log them cleanly — business logic should handle errors, not suppress them.

---

## 🔒 Security & CSP Compliance

- Never use inline `<script>` or `<style>` tags.
- Load JS/CSS from CDNs or static files only.
- Use Bootstrap utility classes instead of inline `style="..."` attributes.
- Use `.to_dict()` or Pydantic schemas to control JSON output explicitly.
- HTMX interactions must follow **CSP-safe patterns**.

---

## 🎨 Frontend Rules (HTMX + Bootstrap + Tabulator.js)

- Use **HTMX** for dynamic behavior (modals, partial loads, table updates).
- Use **Bootstrap CSS** framework. Avoid global or inline CSS.
- Use **Tabulator.js** for tables. Configure per-slice — do not over-abstract.
- Templates must extend `base.html`; inject custom CSS/JS using `{% block head %}`.
- Prefer HTMX-driven composition with small partials over nested components.

### 🔘 UI Consistency & Button Styling

**Action Buttons (Create/Add/Export):**
- Use `table-action-btn table-action-add` classes for primary actions
- Pattern: `<a class="table-action-btn table-action-add"><i class="ti ti-plus"></i><span>Add Item</span></a>`
- ❌ **Do NOT** use `btn btn-primary` for action buttons above content areas

**Row Action Icons (Edit/Delete/View):**
- Use `row-action-icon` class for in-row actions
- Pattern: `<i class="ti ti-edit row-action-icon" title="Edit" onclick="editItem(id)"></i>`
- ❌ **Do NOT** use inline `style` attributes on action icons

**Confirmation Modals:**
- Use `showConfirmModal()` function instead of browser `confirm()`
- Use `showToast()` for success/error feedback
- ❌ **Do NOT** use `hx-confirm` or `alert()` for user confirmations

**Template Structure:**
- For table-based slices: Use `partials/table_actions.html`
- For card-based slices: Use `table-action-btn` classes directly
- Always include proper HTMX modal integration

---

## 🧪 Development Conventions

- All code must use **type hints** and **docstrings**.
- Follow **DRY** principles:
  - Reuse utility functions
  - Extract shared logic to services
  - Reuse template fragments for UI patterns
- Slice layout:
  - `models/`: SQLAlchemy models (`.to_dict()` enabled)
  - `services/`: async business logic with DI
  - `routes/`: FastAPI endpoints (API + HTMX)
  - `templates/`: Jinja2 views
  - `tests/`: model/service/route tests

---

## 🔧 Common Issues & Solutions

**Issue**: Route returns 404 after creating new slice
- **Cause**: Missing main page route (`@router.get("/")`) in the router file
- **Solution**: Always include a main page route that renders the primary template
- **Example**: See `app/auth/routes/user_management.py` for correct pattern

**Issue**: HTMX modals not loading or appearing below table instead of as proper modal
- **Cause**: Incorrect HTMX target, missing modal structure, or wrong template pattern
- **Solution**: Use `hx-target="#modal-body"` and follow exact demo pattern with proper modal structure
- **Example**: Use `{% include 'components/ui/table_actions.html' %}` and proper modal container

**Issue**: Table styling doesn't match other tables
- **Cause**: Not using the standard table pattern and missing action buttons
- **Solution**: Follow demo pattern exactly - use `list_content.html` partial with `table_actions.html` include
- **Example**: See `app/demo/templates/demo/partials/list_content.html` for reference

**Issue**: Missing action buttons (Edit, Delete, Export, Group By)
- **Cause**: Not using the `partials/table_actions.html` template
- **Solution**: Always include table_actions partial with proper parameters (title, description, icon, add_url, entity_name)
- **Anti-Pattern**: ❌ Creating custom header with only Add button - use the standard partial

**Issue**: Table data not loading in Tabulator
- **Cause**: Missing API list endpoint or incorrect AJAX URL
- **Solution**: Ensure API routes exist (e.g., `/list`) and return proper JSON format

**Issue**: Adding dashboard elements when not requested
- **Cause**: Not following exact documentation requirements
- **Solution**: Follow vertical slice pattern exactly - no extra dashboard/stats unless specifically requested
- **Anti-Pattern**: ❌ Adding stats cards, user overviews, or custom styling not in demo pattern

---

## ✅ Prompt Examples (Copilot Reference)

- "Create `roles/` slice with model, routes, Tabulator table, HTMX modals."
- "Use `get_async_session()` with async SQLAlchemy."
- "Add `try/except` with `logger.exception()` and return 500 HTTP error."
- "Avoid fallback logic — just log and fail if needed."
- "Convert SQLAlchemy model to dict using `.to_dict()`, not `__dict__`."
- "Use `table-action-btn table-action-add` for action buttons, not `btn btn-primary`."
- "Use `showConfirmModal()` for delete confirmations, not `hx-confirm`."
- "Apply `row-action-icon` class to edit/delete icons without inline styles."
