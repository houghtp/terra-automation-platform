"""
CSPM Form Routes

HTMX-based form endpoints for M365 tenant management and scan execution.
"""

import json
from typing import Optional
from types import SimpleNamespace
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.core.route_imports import *
from app.features.core.config import get_settings
from app.features.msp.cspm.services import (
    CSPMScanService,
    M365TenantService,
    TenantBenchmarkService,
)
from app.features.msp.cspm.tasks import run_cspm_compliance_scan
from app.features.msp.cspm.schemas import (
    ComplianceScanRequest,
    CSPMBenchmarkResponse,
    CSPMTenantBenchmarkCreate,
    CSPMTenantBenchmarkUpdate,
    M365TenantCreate,
    M365TenantUpdate,
)
from app.features.core.audit_mixin import AuditContext

logger = get_logger(__name__)

router = APIRouter(tags=["cspm-forms"])

settings = get_settings()

# ============================================================================
# M365 Tenant Management Forms
# ============================================================================

@router.get("/partials/m365-tenant-form", response_class=HTMLResponse)
async def get_m365_tenant_form(
    request: Request,
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get M365 tenant form (for add or edit).

    Args:
        tenant_id: M365 tenant ID for editing (optional)

    Returns:
        HTML form partial
    """
    service = M365TenantService(db, current_tenant_id)
    tenant = None
    credentials = None

    if tenant_id:
        tenant = await service.get_m365_tenant(tenant_id)
        if tenant:
            try:
                credentials = await service.get_tenant_credentials_info(tenant_id)
            except Exception as e:
                logger.warning(f"Failed to get credentials info: {e}")

    global_admin = is_global_admin(current_user)
    available_tenants: list[dict[str, str]] = []
    if global_admin:
        available_tenants = await service.get_available_tenants_for_forms()

    return templates.TemplateResponse(
        "cspm/partials/m365_tenant_form.html",
        {
            "request": request,
            "tenant": tenant,
            "credentials": credentials,
            "form_data": None,
            "form_error": None,
            "is_global_admin": global_admin,
            "available_tenants": available_tenants,
            "current_tenant_id": current_tenant_id
        }
    )


# ============================================================================
# Tenant Benchmark Management Forms
# ============================================================================


@router.get("/partials/tenant-benchmark-form", response_class=HTMLResponse)
async def get_tenant_benchmark_form(
    request: Request,
    assignment_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get tenant benchmark form for create or edit.
    """
    service = TenantBenchmarkService(db, current_tenant_id)
    assignment = None
    config_text = ""

    if assignment_id:
        assignment = await service.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Benchmark assignment not found")
        config_text = json.dumps(assignment.config or {}, indent=2)
    else:
        config_text = json.dumps({}, indent=2)

    benchmarks = await service.list_available_benchmarks()
    benchmark_options = [
        CSPMBenchmarkResponse.model_validate(row) for row in benchmarks
    ]

    global_admin = is_global_admin(current_user)
    available_tenants: list[dict[str, str]] = []
    if global_admin:
        available_tenants = await service.get_available_tenants_for_forms()

    return templates.TemplateResponse(
        "cspm/partials/tenant_benchmark_form.html",
        {
            "request": request,
            "assignment": assignment,
            "form_data": None,
            "form_error": None,
            "available_benchmarks": benchmark_options,
            "config_text": config_text,
            "is_global_admin": global_admin,
            "available_tenants": available_tenants,
            "current_tenant_id": current_tenant_id,
        }
    )


@router.post("/tenant-benchmarks", response_class=HTMLResponse)
async def create_tenant_benchmark_form(
    request: Request,
    benchmark_id: str = Form(...),
    display_name: Optional[str] = Form(None),
    status: Optional[str] = Form("active"),
    config_json: Optional[str] = Form(None),
    target_tenant_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Create a tenant benchmark via HTMX form submission.
    """
    service = TenantBenchmarkService(db, current_tenant_id)
    global_admin = is_global_admin(current_user)

    if target_tenant_id and not global_admin:
        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": None,
                "form_data": SimpleNamespace(
                    benchmark_id=benchmark_id,
                    display_name=display_name,
                    status=status,
                    config_json=config_json,
                    target_tenant_id=None,
                ),
                "form_error": "You do not have permission to assign benchmarks to another tenant.",
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row)
                    for row in await service.list_available_benchmarks()
                ],
                "config_text": config_json or json.dumps({}, indent=2),
                "is_global_admin": global_admin,
                "available_tenants": [],
                "current_tenant_id": current_tenant_id,
            },
            status_code=403,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    try:
        parsed_config = {}
        if config_json:
            parsed_config = json.loads(config_json)

        assignment = await service.create_assignment(
            CSPMTenantBenchmarkCreate(
                benchmark_id=benchmark_id,
                display_name=display_name,
                status=status or "active",
                config=parsed_config,
                target_tenant_id=target_tenant_id if global_admin else None,
            ),
            created_by_user=current_user,
            target_tenant_id=target_tenant_id if global_admin else None,
        )

        await db.commit()

        response = Response(status_code=204)
        response.headers["HX-Trigger"] = "closeModal, refreshTenantBenchmarks, showSuccess"
        return response

    except json.JSONDecodeError:
        await db.rollback()
        form_data = SimpleNamespace(
            benchmark_id=benchmark_id,
            display_name=display_name,
            status=status,
            config_json=config_json,
            target_tenant_id=target_tenant_id,
        )
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": None,
                "form_data": form_data,
                "form_error": "Configuration must be valid JSON.",
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row)
                    for row in await service.list_available_benchmarks()
                ],
                "config_text": config_json or "",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": current_tenant_id,
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    except ValueError as exc:
        await db.rollback()
        form_data = SimpleNamespace(
            benchmark_id=benchmark_id,
            display_name=display_name,
            status=status,
            config_json=config_json,
            target_tenant_id=target_tenant_id,
        )
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": None,
                "form_data": form_data,
                "form_error": str(exc),
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row)
                    for row in await service.list_available_benchmarks()
                ],
                "config_text": config_json or "",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": current_tenant_id,
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    except Exception as exc:
        await db.rollback()
        logger.error("Failed to create tenant benchmark", error=str(exc), exc_info=True)
        form_data = SimpleNamespace(
            benchmark_id=benchmark_id,
            display_name=display_name,
            status=status,
            config_json=config_json,
            target_tenant_id=target_tenant_id,
        )
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": None,
                "form_data": form_data,
                "form_error": "Failed to create benchmark assignment.",
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row)
                    for row in await service.list_available_benchmarks()
                ],
                "config_text": config_json or "",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": current_tenant_id,
            },
            status_code=500,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )


@router.post("/tenant-benchmarks/{assignment_id}", response_class=HTMLResponse)
async def update_tenant_benchmark_form(
    request: Request,
    assignment_id: str,
    display_name: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    config_json: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Update a tenant benchmark via HTMX form submission.
    """
    service = TenantBenchmarkService(db, current_tenant_id)
    global_admin = is_global_admin(current_user)

    try:
        parsed_config = None
        if config_json is not None and config_json.strip():
            parsed_config = json.loads(config_json)

        update_payload = CSPMTenantBenchmarkUpdate(
            display_name=display_name,
            status=status,
            config=parsed_config,
        )

        await service.update_assignment(
            assignment_id,
            update_payload,
            updated_by_user=current_user,
        )

        await db.commit()

        response = Response(status_code=204)
        response.headers["HX-Trigger"] = "closeModal, refreshTenantBenchmarks, showSuccess"
        return response

    except json.JSONDecodeError:
        await db.rollback()
        assignment = await service.get_assignment(assignment_id)
        benchmarks = await service.list_available_benchmarks()
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": assignment,
                "form_data": SimpleNamespace(
                    display_name=display_name,
                    status=status,
                    config_json=config_json,
                ),
                "form_error": "Configuration must be valid JSON.",
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row) for row in benchmarks
                ],
                "config_text": config_json or "",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": current_tenant_id,
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    except ValueError as exc:
        await db.rollback()
        assignment = await service.get_assignment(assignment_id)
        benchmarks = await service.list_available_benchmarks()
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": assignment,
                "form_data": SimpleNamespace(
                    display_name=display_name,
                    status=status,
                    config_json=config_json,
                ),
                "form_error": str(exc),
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row) for row in benchmarks
                ],
                "config_text": config_json or "",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": current_tenant_id,
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    except Exception as exc:
        await db.rollback()
        logger.error("Failed to update tenant benchmark", error=str(exc), exc_info=True)
        assignment = await service.get_assignment(assignment_id)
        benchmarks = await service.list_available_benchmarks()
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/tenant_benchmark_form.html",
            {
                "request": request,
                "assignment": assignment,
                "form_data": SimpleNamespace(
                    display_name=display_name,
                    status=status,
                    config_json=config_json,
                ),
                "form_error": "Failed to update benchmark assignment.",
                "available_benchmarks": [
                    CSPMBenchmarkResponse.model_validate(row) for row in benchmarks
                ],
                "config_text": config_json or "",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": current_tenant_id,
            },
            status_code=500,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )
@router.post("/m365-tenants", response_class=HTMLResponse)
async def create_m365_tenant_form(
    request: Request,
    m365_tenant_id: str = Form(...),
    m365_domain: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    certificate_thumbprint: Optional[str] = Form(None),
    certificate_pfx: Optional[str] = Form(None),
    certificate_password: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    target_tenant_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Create M365 tenant via HTMX form submission.

    Returns:
        Updated list content HTML
    """
    try:
        service = M365TenantService(db, tenant_id)
        global_admin = is_global_admin(current_user)
        effective_target = target_tenant_id if global_admin else None
        if global_admin and not effective_target:
            raise ValueError("Target tenant is required for global admin operations.")

        tenant_data = M365TenantCreate(
            m365_tenant_id=m365_tenant_id,
            m365_domain=m365_domain,
            description=description,
            client_id=client_id if client_id else None,
            client_secret=client_secret if client_secret else None,
            certificate_thumbprint=certificate_thumbprint if certificate_thumbprint else None,
            certificate_pfx=certificate_pfx if certificate_pfx else None,
            certificate_password=certificate_password if certificate_password else None,
            username=username if username else None,
            password=password if password else None
        )

        await service.create_m365_tenant(
            tenant_data,
            created_by_user=current_user,
            target_tenant_id=effective_target
        )

        await db.commit()

        logger.info(
            "M365 tenant created via form",
            m365_tenant_id=m365_tenant_id,
            user=current_user.name
        )

        response = Response(status_code=204)
        response.headers["HX-Trigger"] = "closeModal, refreshTable, showSuccess"
        return response

    except ValueError as e:
        await db.rollback()
        logger.warning(f"Tenant creation failed: {e}")

        form_data = SimpleNamespace(
            m365_tenant_id=m365_tenant_id,
            m365_domain=m365_domain,
            description=description,
            client_id=client_id,
            certificate_thumbprint=certificate_thumbprint,
            username=username,
            target_tenant_id=target_tenant_id
        )

        service = M365TenantService(db, tenant_id)
        available_tenants = []
        global_admin = is_global_admin(current_user)
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/m365_tenant_form.html",
            {
                "request": request,
                "tenant": None,
                "credentials": None,
                "form_data": form_data,
                "form_error": str(e),
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": tenant_id
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create tenant: {e}", exc_info=True)

        form_data = SimpleNamespace(
            m365_tenant_id=m365_tenant_id,
            m365_domain=m365_domain,
            description=description,
            client_id=client_id,
            certificate_thumbprint=certificate_thumbprint,
            username=username,
            target_tenant_id=target_tenant_id
        )

        service = M365TenantService(db, tenant_id)
        available_tenants = []
        global_admin = is_global_admin(current_user)
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/m365_tenant_form.html",
            {
                "request": request,
                "tenant": None,
                "credentials": None,
                "form_data": form_data,
                "form_error": "Failed to create M365 tenant",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": tenant_id
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )


@router.post("/m365-tenants/{m365_tenant_id}", response_class=HTMLResponse)
async def update_m365_tenant_form(
    request: Request,
    m365_tenant_id: str,
    m365_domain: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    certificate_thumbprint: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    target_tenant_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Update M365 tenant via HTMX form submission.

    Returns:
        Updated list content HTML
    """
    try:
        service = M365TenantService(db, tenant_id)

        tenant_data = M365TenantUpdate(
            m365_domain=m365_domain,
            description=description,
            client_id=client_id if client_id else None,
            client_secret=client_secret if client_secret else None,
            certificate_thumbprint=certificate_thumbprint if certificate_thumbprint else None,
            username=username if username else None,
            password=password if password else None
        )

        await service.update_m365_tenant(
            m365_tenant_id,
            tenant_data,
            updated_by_user=current_user
        )

        await db.commit()

        logger.info(
            "M365 tenant updated via form",
            m365_tenant_id=m365_tenant_id,
            user=current_user.name
        )

        response = Response(status_code=204)
        response.headers["HX-Trigger"] = "closeModal, refreshTable, showSuccess"
        return response

    except ValueError as e:
        await db.rollback()
        logger.warning(f"Tenant update failed: {e}")
        service = M365TenantService(db, tenant_id)
        tenant_obj = await service.get_m365_tenant(m365_tenant_id)
        credentials = None
        if tenant_obj:
            try:
                credentials = await service.get_tenant_credentials_info(m365_tenant_id)
            except Exception:
                credentials = None

        form_data = SimpleNamespace(
            m365_domain=m365_domain,
            description=description,
            client_id=client_id,
            certificate_thumbprint=certificate_thumbprint,
            username=username,
            target_tenant_id=target_tenant_id
        )

        global_admin = is_global_admin(current_user)
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/m365_tenant_form.html",
            {
                "request": request,
                "tenant": tenant_obj,
                "credentials": credentials,
                "form_data": form_data,
                "form_error": str(e),
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": tenant_id
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update tenant: {e}", exc_info=True)
        service = M365TenantService(db, tenant_id)
        tenant_obj = await service.get_m365_tenant(m365_tenant_id)
        credentials = None
        if tenant_obj:
            try:
                credentials = await service.get_tenant_credentials_info(m365_tenant_id)
            except Exception:
                credentials = None

        form_data = SimpleNamespace(
            m365_domain=m365_domain,
            description=description,
            client_id=client_id,
            certificate_thumbprint=certificate_thumbprint,
            username=username,
            target_tenant_id=target_tenant_id
        )

        global_admin = is_global_admin(current_user)
        available_tenants = []
        if global_admin:
            available_tenants = await service.get_available_tenants_for_forms()

        return templates.TemplateResponse(
            "cspm/partials/m365_tenant_form.html",
            {
                "request": request,
                "tenant": tenant_obj,
                "credentials": credentials,
                "form_data": form_data,
                "form_error": "Failed to update tenant",
                "is_global_admin": global_admin,
                "available_tenants": available_tenants,
                "current_tenant_id": tenant_id
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )


@router.delete("/m365-tenants/{m365_tenant_id}")
async def delete_m365_tenant_form(
    request: Request,
    m365_tenant_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Delete M365 tenant via HTMX.

    Returns:
        Updated list content HTML
    """
    try:
        service = M365TenantService(db, tenant_id)
        await service.delete_m365_tenant(m365_tenant_id)
        await db.commit()

        logger.info(
            "M365 tenant deleted via form",
            m365_tenant_id=m365_tenant_id,
            user=current_user.name
        )

        response = Response(status_code=204)
        response.headers["HX-Trigger"] = "refreshTable, showSuccess"
        return response

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete tenant: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to delete tenant: {str(e)}"}
        )


@router.post("/m365-tenants/{m365_tenant_id}/test-connection")
async def test_connection_form(
    request: Request,
    m365_tenant_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Test M365 connection via HTMX.

    Returns:
        Updated list content HTML with test results
    """
    try:
        service = M365TenantService(db, tenant_id)
        test_result = await service.test_connection(m365_tenant_id)
        await db.commit()

        logger.info(
            "Connection test completed via form",
            m365_tenant_id=m365_tenant_id,
            success=test_result["success"],
            user=current_user.name
        )

        message = (
            "Connection test successful! Credentials are valid."
            if test_result["success"]
            else f"Connection test failed: {test_result.get('message', 'Unknown error')}"
        )

        return JSONResponse(
            {"success": test_result["success"], "message": message}
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Connection test failed: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "message": f"Connection test failed: {str(e)}"},
            status_code=500
        )


# ============================================================================
# Scan Execution Forms
# ============================================================================

@router.get("/partials/scan-form", response_class=HTMLResponse)
async def get_scan_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get scan execution form.

    Returns:
        HTML form partial with M365 tenant dropdown
    """
    service = M365TenantService(db, tenant_id)
    tenants = await service.list_m365_tenants()

    return templates.TemplateResponse(
        "cspm/partials/scan_form.html",
        {
            "request": request,
            "m365_tenants": tenants,
            "form_data": None
        }
    )


@router.post("/scans/start-form", response_class=HTMLResponse)
async def start_scan_form(
    request: Request,
    m365_tenant_id: str = Form(...),
    tenant_benchmark_id: Optional[str] = Form(None),
    scan_level: str = Form("all"),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Start compliance scan via HTMX form.

    Returns:
        Scan progress partial
    """
    try:
        m365_service = M365TenantService(db, tenant_id)

        # Validate M365 tenant
        m365_tenant = await m365_service.get_m365_tenant(m365_tenant_id)
        if not m365_tenant:
            raise ValueError("M365 tenant not found")

        if not tenant_benchmark_id:
            tenant_benchmark_id = m365_tenant.tenant_benchmark_id

        target_tenant_id = m365_tenant.tenant_id or (None if tenant_id == "global" else tenant_id)
        if not target_tenant_id:
            raise ValueError("Unable to resolve tenant for scan")

        scan_service = CSPMScanService(db, target_tenant_id)

        l1_only = scan_level.lower() == "l1"

        # Build scan options
        scan_options = {
            "l1_only": l1_only,
            "check_ids": [],
            "output_format": "json"
        }

        scan_request = ComplianceScanRequest(
            m365_tenant_id=m365_tenant_id,
            tenant_benchmark_id=tenant_benchmark_id,
            l1_only=l1_only,
            output_format="json"
        )

        # Create scan record with pending status (Celery task ID will be populated after enqueue)
        scan = await scan_service.create_scan(
            scan_request,
            celery_task_id="pending",
            created_by_user=current_user
        )

        await db.commit()

        # Build progress callback URL
        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")
        progress_callback_url = f"{base_url}/msp/cspm/webhook/progress/{scan.scan_id}"

        try:
            # Enqueue Celery task for background execution
            real_task = run_cspm_compliance_scan.apply_async(
                args=[
                    scan.scan_id,
                    target_tenant_id,
                    m365_tenant_id,
                    scan_options,
                    progress_callback_url
                ]
            )

            # Update scan with real task ID
            scan_update = await scan_service._get_scan_by_scan_id(scan.scan_id)
            scan_update.celery_task_id = real_task.id
            audit_ctx = AuditContext.from_user(current_user)
            scan_update.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            scan_update.updated_at = datetime.now()
            await db.commit()

            logger.info(
                "Compliance scan started via form (Celery)",
                scan_id=scan.scan_id,
                celery_task_id=real_task.id,
                m365_tenant_id=m365_tenant_id,
                user=current_user.name
            )

            response = Response(status_code=204)
            response.headers["HX-Trigger"] = "closeModal, refreshTable, showSuccess"
            # Trigger WebSocket connection for real-time progress updates
            response.headers["HX-Trigger-After-Settle"] = f"scanStarted:{{\"scan_id\":\"{scan.scan_id}\"}}"
            return response

        except Exception as runtime_exc:  # pylint: disable=broad-except
            message = "Unable to start compliance scan (Celery task queue unavailable). Check server logs."
            logger.error(
                "Celery task enqueue failed (form submission)",
                error=str(runtime_exc),
                scan_id=scan.scan_id,
                tenant_id=target_tenant_id,
                exc_info=True
            )

            await scan_service.update_scan_status(
                scan.scan_id,
                "failed",
                error_message=message
            )
            await db.commit()

            tenants = await m365_service.list_m365_tenants()
            form_data = SimpleNamespace(
                m365_tenant_id=m365_tenant_id,
                tenant_benchmark_id=tenant_benchmark_id,
                scan_level=scan_level
            )

            return templates.TemplateResponse(
                "cspm/partials/scan_form.html",
                {
                    "request": request,
                    "m365_tenants": tenants,
                    "error_message": message,
                    "form_data": form_data
                },
                status_code=503,
                headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
            )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to start scan: {e}", exc_info=True)

        # Return error in form
        service = M365TenantService(db, tenant_id)
        tenants = await service.list_m365_tenants()

        form_data = SimpleNamespace(
            m365_tenant_id=m365_tenant_id,
            tenant_benchmark_id=tenant_benchmark_id,
            scan_level=scan_level
        )

        return templates.TemplateResponse(
            "cspm/partials/scan_form.html",
            {
                "request": request,
                "m365_tenants": tenants,
                "error_message": f"Failed to start scan: {str(e)}",
                "form_data": form_data
            },
            status_code=400,
            headers={"HX-Retarget": "#modal-body", "HX-Reswap": "innerHTML"}
        )
