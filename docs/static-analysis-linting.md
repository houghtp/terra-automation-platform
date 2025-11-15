# Static Analysis & Linting Checklist

Tracking platform-wide linting and static analysis rules to prevent recurring issues.

1. **HTMX Response Contracts**  
   - **Rule**: HTMX endpoints must return explicit `HX-Trigger` / `HX-Redirect` headers or an HTML fragment (never a full page shell).  
   - **Reason**: Avoids responses defaulting to an entire layout which surface as unreadable toasts and break client flows.  
   - **Lint idea**: Scan FastAPI route handlers invoked by HTMX (e.g., paths under `/partials/` or handlers returning `Response(status_code=204)`) to ensure they set `HX-Trigger` or explicitly render a partial template.

2. **Dedicated HTMX vs API Routes**  
   - **Rule**: Do not reuse the same HTTP verb/path for both HTMX form submissions and JSON APIs. HTMX should post to HTML-friendly handlers; JSON APIs belong under `/api/**` or another clear namespace.  
   - **Reason**: Prevents form-encoded payloads from hitting JSON-only endpoints (422 errors) and keeps the request/response contracts predictable.  
   - **Lint idea**: Flag routes without an `/api/` prefix that depend on Pydantic models (e.g., `SecretUpdate`) or expect JSON bodies, and ensure HTMX forms target non-API paths.

3. **Avoid Custom Modal Lifecycle Hooks** _(Medium Priority)_  
   - **Rule**: Front-end code must not register bespoke handlers for the `closeModal` event or reimplement modal lifecycle logic; rely on the shared modal utilities in `site.js` / `table-base.js`.  
   - **Reason**: Ad-hoc listeners leave stale backdrops or duplicate focus logic, causing blocked UI after form submissions.  
   - **Lint idea**: Add an ESLint rule (`no-custom-modal-handlers`) that warns when code listens for `closeModal` (or similar modal closure events) outside the core utilities.

4. **Use Shared Theme Stylesheet**  
   - **Rule**: Global styling tweaks belong in `app/static/css/app-theme.css`; avoid creating new slice-level CSS for patterns that can live in the shared theme.  
   - **Reason**: Keeps Tabler extensions consistent and prevents divergent badge/loader/table styles across slices.  
   - **Lint idea**: CI check that flags new CSS files outside approved directories (`app/static/css`) or direct `<link>` tags to retired files (e.g., `tabulator-unified.css`, `modal.css`, etc.).  
   - **Shared utilities**: `.status-badge` (+ state modifiers), `.card-hover-lift`, `.icon-xl` / `.icon-lg`, `.tab-content-min-400`, table action button classes.
