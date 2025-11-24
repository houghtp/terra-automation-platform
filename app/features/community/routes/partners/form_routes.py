"""Form routes for community partners (modal GET only)."""

from app.features.core.route_imports import (
    APIRouter,
    Depends,
    HTMLResponse,
    Request,
    templates,
)

from ...dependencies import get_partner_service
from ...schemas import PartnerResponse
from ...services import PartnerCrudService

router = APIRouter()


@router.get("/partials/form", response_class=HTMLResponse)
async def partner_form_partial(
    request: Request,
    partner_id: str | None = None,
    partner_service: PartnerCrudService = Depends(get_partner_service),
):
    partner = None
    if partner_id:
        partner = await partner_service.get_by_id(partner_id)
        if not partner:
            return HTMLResponse(
                "<div class='alert alert-danger mb-0'>Partner not found.</div>",
                status_code=404,
            )
        partner = PartnerResponse.model_validate(partner, from_attributes=True)

    context = {
        "request": request,
        "partner": partner,
        "form_data": None,
        "errors": {},
    }
    return templates.TemplateResponse("community/partners/partials/form.html", context)


__all__ = ["router"]
