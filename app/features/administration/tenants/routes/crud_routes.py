# Gold Standard Route Imports - Tenants CRUD
from app.features.core.route_imports import (
    APIRouter, Depends, Request, HTTPException, Body,
    HTMLResponse, JSONResponse, AsyncSession, get_db, templates,
    get_logger
)
from app.features.core.rate_limiter import rate_limit_api
from app.features.administration.tenants.services import TenantManagementService
from app.features.auth.dependencies import get_global_admin_user
from app.features.auth.models import User
from app.features.administration.tenants.schemas import TenantSearchFilter, TenantUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["tenants-crud"])

# --- TABULATOR CRUD ROUTES ---

@router.patch("/{tenant_id}/field")
async def update_tenant_field_api(tenant_id: int, field_update: dict = Body(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    field = field_update.get("field")
    value = field_update.get("value")

    service = TenantManagementService(db)

    # Create update data with just the field being updated
    update_data = TenantUpdate()
    setattr(update_data, field, value)

    try:
        result = await service.update_tenant(tenant_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Tenant not found")

        await db.commit()  # Route handles transaction commit
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update tenant: {str(e)}")

# List content partial (for HTMX table refresh)
@router.get("/partials/list_content", response_class=HTMLResponse)
async def tenant_list_partial(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    service = TenantManagementService(db)
    filters = TenantSearchFilter()
    tenants = await service.list_tenants(filters)
    return templates.TemplateResponse("administration/tenants/partials/list_content.html", {"request": request, "tenants": tenants})

# API endpoint for Tabulator
@router.get("/api/list", response_class=JSONResponse)
async def get_tenants_api(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_global_admin_user),
    _rate_limit: dict = Depends(rate_limit_api)
):
    service = TenantManagementService(db)
    filters = TenantSearchFilter()
    tenants = await service.list_tenants(filters)
    # Return array directly for Tabulator compatibility
    return [tenant.model_dump() for tenant in tenants]

# Delete tenant (accept both DELETE and POST for compatibility)
@router.delete("/{tenant_id}/delete")
@router.post("/{tenant_id}/delete")
async def tenant_delete_api(tenant_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_global_admin_user)):
    """Delete a tenant by ID. Accepts both DELETE and POST for frontend compatibility."""
    service = TenantManagementService(db)
    success = await service.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.commit()  # Route handles transaction commit
    return {"status": "ok"}
