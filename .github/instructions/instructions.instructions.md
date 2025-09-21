---
applyTo: "**"
---

# 🧠 Project: TerraAutomationPlatform — Copilot Coding Instructions

This is a lightweight FastAPI vertical-slice template built using:

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
