"""
Company CRUD API routes for Sales Outreach Prep.

Handles:
- GET /api/list - List companies (for Tabulator)
- GET /api/search - Search companies by name (for autocomplete)
- GET /{company_id} - Get company details
- DELETE /{company_id} - Delete company
"""

from app.features.core.route_imports import *
from app.features.business_automations.sales_outreach_prep.dependencies import get_company_service
from app.features.business_automations.sales_outreach_prep.services.companies import CompanyCrudService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/list")
async def list_companies_api(
    request: Request,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    List companies for Tabulator table.

    Args:
        request: FastAPI request
        search: Search term
        industry: Filter by industry
        page: Page number
        size: Page size
        service: Company service
        current_user: Current user

    Returns:
        JSON response with companies and pagination
    """
    try:
        offset = (page - 1) * size
        companies, total = await service.list_companies(
            search=search,
            industry=industry,
            limit=size,
            offset=offset
        )

        return {
            "data": [company.to_dict() for company in companies],
            "last_page": (total + size - 1) // size if total > 0 else 1,
            "total": total
        }

    except Exception as e:
        handle_route_error("list_companies_api", e)
        raise HTTPException(status_code=500, detail="Failed to list companies")


@router.get("/api/search")
async def search_companies_api(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Search companies by name (for autocomplete/typeahead).

    Args:
        query: Search query
        limit: Max results
        service: Company service
        current_user: Current user

    Returns:
        JSON list of companies
    """
    try:
        companies = await service.search_companies_by_name(query, limit)
        return [company.to_dict() for company in companies]

    except Exception as e:
        handle_route_error("search_companies_api", e)
        raise HTTPException(status_code=500, detail="Failed to search companies")


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get company by ID.

    Args:
        company_id: Company ID
        service: Company service
        current_user: Current user

    Returns:
        Company JSON
    """
    try:
        company = await service.get_company_by_id(company_id)

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        return company.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_company", e)
        raise HTTPException(status_code=500, detail="Failed to get company")


@router.delete("/{company_id}")
async def delete_company(
    company_id: str,
    db: AsyncSession = Depends(get_db),
    service: CompanyCrudService = Depends(get_company_service),
    current_user: User = Depends(get_current_user)
):
    """
    Delete company.

    Args:
        company_id: Company ID
        db: Database session
        service: Company service
        current_user: Current user

    Returns:
        Success response
    """
    try:
        deleted = await service.delete_company(company_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Company not found")

        await commit_transaction(db, "delete_company")

        logger.info(
            "Company deleted via API",
            company_id=company_id,
            user_id=current_user.id
        )

        return {"success": True, "message": "Company deleted"}

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("delete_company", e)
        raise HTTPException(status_code=500, detail="Failed to delete company")
