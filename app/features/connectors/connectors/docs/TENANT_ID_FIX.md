# Fix: Standardized tenant_id Parameter Naming

## Issue
Route parameters were using `tenant: str = Depends(tenant_dependency)` instead of the standardized `tenant_id: str = Depends(tenant_dependency)` pattern used throughout the codebase.

This caused errors when the service layer expected `tenant_id` but received a parameter named `tenant`.

## Root Cause
I missed the project's naming convention standard when implementing the routes. The standard pattern across all features is:

```python
async def some_route(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),  # ✅ Correct - parameter named tenant_id
    current_user: User = Depends(get_current_user)
):
    service = SomeService(db, tenant_id)  # ✅ Pass tenant_id
```

What I incorrectly implemented:

```python
async def some_route(
    db: AsyncSession = Depends(get_db),
    tenant: str = Depends(tenant_dependency),  # ❌ Wrong - parameter named tenant
    current_user: User = Depends(get_current_user)
):
    service = SomeService(db, tenant)  # ❌ Pass tenant
```

## Files Fixed

### 1. `dashboard_routes.py`
**Changes:**
- `connectors_home()`: Changed `tenant` → `tenant_id` (parameter and usage)
- `installed_view()`: Changed `tenant` → `tenant_id` (parameter and usage)
- Template context: Changed `"tenant": tenant` → `"tenant_id": tenant_id`

### 2. `api_routes.py`
**Changes:**
- All tenant-scoped endpoints (7 routes total)
- Changed all instances of `tenant: str = Depends(tenant_dependency)` → `tenant_id: str = Depends(tenant_dependency)`
- Changed all instances of `ConnectorService(db, tenant)` → `ConnectorService(db, tenant_id)`

**Affected routes:**
- `/api/installed`
- `/api/connectors` (POST)
- `/api/connectors/{id}` (GET, PUT, DELETE)
- `/api/publish-targets`

### 3. `form_routes.py`
**Changes:**
- All form handling endpoints (5 routes total)
- Changed all instances of `tenant: str = Depends(tenant_dependency)` → `tenant_id: str = Depends(tenant_dependency)`
- Changed all instances of `ConnectorService(db, tenant)` → `ConnectorService(db, tenant_id)`

**Affected routes:**
- `/forms/create` (GET, POST)
- `/forms/edit/{id}` (GET, POST, DELETE)
- `/forms/validate-name`

## Why This Matters

1. **Consistency**: All features should follow the same naming convention
2. **Clarity**: `tenant_id` is more explicit than just `tenant`
3. **Service Layer**: The `BaseService` class expects `tenant_id` as the parameter name
4. **Error Prevention**: Prevents confusion between the tenant object and tenant ID string

## Reference Implementation

For future slices, always follow this pattern (from `content_broadcaster/routes/dashboard_routes.py`):

```python
@router.get("/api/summary", response_class=JSONResponse)
async def get_summary_stats(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),  # ✅ Standard naming
    current_user = Depends(get_current_user),
    service: ContentBroadcasterService = Depends(get_content_service)
):
    """Get summary statistics for stats cards."""
    try:
        stats = await service.get_dashboard_stats()
        return stats
    except Exception as e:
        logger.exception("Failed to get summary stats")
        raise HTTPException(status_code=500, detail="Failed to get stats")
```

## Verification

After the fix:
✅ Server starts without errors
✅ All routes properly pass `tenant_id` to services
✅ Tenant isolation working correctly
✅ No "Tenant ID required" errors

## Lessons Learned

1. **Always check existing implementations** before writing new code
2. **Follow the project's established patterns** (documented in CLAUDE.md, PRP, and existing slices)
3. **Parameter naming matters** - especially for dependency injection
4. **Use grep to find patterns** across the codebase:
   ```bash
   grep -r "tenant_id: str = Depends(tenant_dependency)" app/features/
   ```

## Related Files
- Standards documentation: Check other feature slices for patterns
- tenant_dependency definition: `app/deps/tenant.py`
- BaseService implementation: `app/features/core/base_service.py`
