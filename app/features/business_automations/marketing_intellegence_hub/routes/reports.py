"""GA4 reports routes."""

from typing import List

from app.features.core.route_imports import APIRouter, Depends, HTTPException
from app.features.auth.dependencies import get_current_user

from ..schemas import Ga4ReportCreate, Ga4ReportResponse
from ..services import Ga4ReportCrudService
from ..dependencies import get_report_service

router = APIRouter(prefix="/ga4/reports", tags=["ga4-reports"])


@router.get("/{connection_id}", response_model=List[Ga4ReportResponse])
async def list_reports(connection_id: str, service: Ga4ReportCrudService = Depends(get_report_service)):
    reports = await service.list_reports(connection_id)
    return [Ga4ReportResponse.model_validate(item, from_attributes=True) for item in reports]


@router.post("/{connection_id}", response_model=Ga4ReportResponse, status_code=201)
async def create_report(
    connection_id: str,
    payload: Ga4ReportCreate,
    service: Ga4ReportCrudService = Depends(get_report_service),
    current_user = Depends(get_current_user),
):
    report = await service.create_report(connection_id, payload, current_user)
    return Ga4ReportResponse.model_validate(report, from_attributes=True)


@router.post("/mark-sent/{report_id}", response_model=Ga4ReportResponse)
async def mark_report_sent(
    report_id: str,
    service: Ga4ReportCrudService = Depends(get_report_service),
):
    updated = await service.mark_sent(report_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Report not found")
    return Ga4ReportResponse.model_validate(updated, from_attributes=True)
