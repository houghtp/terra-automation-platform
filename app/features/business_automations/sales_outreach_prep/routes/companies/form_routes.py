"""
Company form routes for Sales Outreach Prep.

Handles:
- GET /partials/form - Render company form (create/edit)
- POST / - Create new company
- PUT /{company_id} - Update existing company
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_company_service
from app.features.business_automations.sales_outreach_prep.services.companies import CompanyCrudService
from app.features.business_automations.sales_outreach_prep.schemas import CompanyCreate, CompanyUpdate

logger = get_logger(__name__)
router = APIRouter()


@router.get("/partials/form")
async def get_company_form(
    request: Request,
    company_id: Optional[str] = None,
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Render company create/edit form partial.

    Args:
        request: FastAPI request
        company_id: Company ID for edit, None for create
        service: Company service
        current_user: Current user

    Returns:
        TemplateResponse with form HTML
    """
    try:
        company = None
        if company_id:
            company = await service.get_company_by_id(company_id)
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

        return templates.TemplateResponse(
            "business_automations/sales_outreach_prep/companies/partials/form.html",
            {
                "request": request,
                "company": company,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_company_form", e)
        raise HTTPException(status_code=500, detail="Failed to load form")


@router.post("/")
async def create_company(
    request: Request,
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new company.

    Args:
        request: FastAPI request
        data: Company creation data
        db: Database session
        service: Company service
        current_user: Current user

    Returns:
        Success response or error
    """
    try:
        company = await service.create_company(data.dict(), current_user)
        await commit_transaction(db, "create_company")

        logger.info(
            "Company created via form",
            company_id=company.id,
            name=company.name,
            user_id=current_user.id
        )

        return Response(
            status_code=200,
            headers={"HX-Trigger": "closeModal, refreshTable"}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("create_company", e)
        raise HTTPException(status_code=500, detail="Failed to create company")


@router.put("/{company_id}")
async def update_company(
    request: Request,
    company_id: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing company.

    Args:
        request: FastAPI request
        company_id: Company ID
        data: Company update data
        db: Database session
        service: Company service
        current_user: Current user

    Returns:
        Success response or error
    """
    try:
        company = await service.update_company(
            company_id,
            data.dict(exclude_unset=True),
            current_user
        )

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        await commit_transaction(db, "update_company")

        logger.info(
            "Company updated via form",
            company_id=company.id,
            user_id=current_user.id
        )

        return Response(
            status_code=200,
            headers={"HX-Trigger": "closeModal, refreshTable"}
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        handle_route_error("update_company", e)
        raise HTTPException(status_code=500, detail="Failed to update company")
