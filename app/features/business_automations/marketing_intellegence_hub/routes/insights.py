"""GA4 insights routes."""

from typing import List

from app.features.core.route_imports import APIRouter, Depends, HTTPException
from app.features.auth.dependencies import get_current_user

from ..schemas import Ga4InsightCreate, Ga4InsightResponse
from ..services import Ga4InsightCrudService
from ..dependencies import get_insight_service

router = APIRouter(prefix="/ga4/insights", tags=["ga4-insights"])


@router.get("/{connection_id}", response_model=List[Ga4InsightResponse])
async def list_insights(
    connection_id: str,
    service: Ga4InsightCrudService = Depends(get_insight_service),
):
    insights = await service.list_insights(connection_id)
    return [Ga4InsightResponse.model_validate(item, from_attributes=True) for item in insights]


@router.post("/{connection_id}", response_model=Ga4InsightResponse, status_code=201)
async def create_insight(
    connection_id: str,
    payload: Ga4InsightCreate,
    service: Ga4InsightCrudService = Depends(get_insight_service),
    current_user = Depends(get_current_user),
):
    insight = await service.create_insight(connection_id, payload, current_user)
    return Ga4InsightResponse.model_validate(insight, from_attributes=True)
