"""API routes for partner operations (aligned with platform CRUD patterns)."""

from app.features.core.route_imports import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    JSONResponse,
    Query,
    Response,
    AsyncSession,
    commit_transaction,
    create_error_response,
    create_success_response,
    get_current_user,
    get_db,
    handle_route_error,
    User,
    Optional,
)

from ..dependencies import get_partner_service
from ..schemas import PartnerCreate, PartnerResponse, PartnerUpdate
from ..services import PartnerService

router = APIRouter(prefix="/partners", tags=["community-partners"])


@router.get("/api", response_class=JSONResponse)
async def list_partners_api(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    partner_service: PartnerService = Depends(get_partner_service),
):
    """Return paginated partner directory entries."""
    try:
        items, total = await partner_service.list_partners(
            search=search,
            category=category,
            limit=limit,
            offset=offset,
        )
        return {
            "data": [partner.to_dict() for partner in items],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        handle_route_error("list_partners_api", exc)
        raise HTTPException(status_code=500, detail="Failed to list partners")


@router.get("/api/{partner_id}", response_model=PartnerResponse)
async def get_partner_api(
    partner_id: str,
    partner_service: PartnerService = Depends(get_partner_service),
):
    """Fetch a single partner entry."""
    partner = await partner_service.get_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found.")
    return PartnerResponse.model_validate(partner, from_attributes=True)


@router.post("/api", response_model=PartnerResponse, status_code=201)
async def create_partner_api(
    payload: PartnerCreate,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Create a new partner directory entry."""
    try:
        partner = await partner_service.create_partner(payload.model_dump(), current_user)
        await commit_transaction(db, "create_partner")
        return PartnerResponse.model_validate(partner, from_attributes=True)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        handle_route_error("create_partner_api", exc)
        raise HTTPException(status_code=500, detail="Failed to create partner")


@router.put("/api/{partner_id}", response_model=PartnerResponse)
async def update_partner_api(
    partner_id: str,
    payload: PartnerUpdate,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Update a partner entry."""
    try:
        partner = await partner_service.update_partner(
            partner_id,
            payload.model_dump(exclude_unset=True),
            current_user,
        )
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found.")
        await commit_transaction(db, "update_partner")
        return PartnerResponse.model_validate(partner, from_attributes=True)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_partner_api", exc, partner_id=partner_id)
        raise HTTPException(status_code=500, detail="Failed to update partner")


@router.patch("/api/{partner_id}/field")
async def update_partner_field_api(
    partner_id: str,
    field_update: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    partner_service: PartnerService = Depends(get_partner_service),
):
    """Update a single partner field (inline editing support)."""
    field = field_update.get("field")
    value = field_update.get("value")

    if not field:
        return create_error_response("Field name is required", status_code=400)

    try:
        updated = await partner_service.update_partner_field(partner_id, field, value, current_user)
        if not updated:
            raise HTTPException(status_code=404, detail="Partner not found.")
        await commit_transaction(db, "update_partner_field")
        return {"success": True}
    except ValueError as exc:
        await db.rollback()
        return create_error_response(str(exc), status_code=400)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        handle_route_error("update_partner_field_api", exc, partner_id=partner_id, field=field)
        raise HTTPException(status_code=500, detail="Failed to update partner field")


@router.delete("/api/{partner_id}", status_code=204)
async def delete_partner_api(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Delete a partner entry."""
    success = await partner_service.delete_partner(partner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Partner not found.")

    await commit_transaction(db, "delete_partner")
    return Response(status_code=204)


@router.delete("/{partner_id}/delete")
@router.post("/{partner_id}/delete")
async def delete_partner_ui(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    partner_service: PartnerService = Depends(get_partner_service),
    current_user: User = Depends(get_current_user),
):
    """Delete partner endpoint compatible with table helpers."""
    success = await partner_service.delete_partner(partner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Partner not found.")

    await commit_transaction(db, "delete_partner")
    return create_success_response()


__all__ = ["router"]
