"""CSPM Benchmark Routes

Read-only routes for viewing available compliance benchmarks.
"""

from typing import List
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import *
from app.features.msp.cspm.schemas import CSPMBenchmarkResponse
from app.features.msp.cspm.models import CSPMBenchmark

logger = get_logger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["cspm-benchmarks"])


@router.get("", response_class=HTMLResponse)
async def benchmarks_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info("Rendering benchmarks page", user=current_user.name)

    result = await db.execute(select(CSPMBenchmark).order_by(CSPMBenchmark.tech_type, CSPMBenchmark.display_name))
    benchmarks = [CSPMBenchmarkResponse.model_validate(row) for row in result.scalars().all()]

    return templates.TemplateResponse(
        "cspm/benchmarks.html",
        {
            "request": request,
            "user": current_user,
            "benchmarks": benchmarks
        }
    )
