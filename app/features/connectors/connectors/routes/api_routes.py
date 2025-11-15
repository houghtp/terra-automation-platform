"""
API routes for connectors (pure JSON endpoints).

Provides REST API for catalog browsing and connector CRUD operations.
"""

from typing import List, Optional
from app.features.core.route_imports import *
from app.features.connectors.connectors.services.connector_service import ConnectorService
from app.features.connectors.connectors.schemas import (
    ConfigValidationRequest,
    ConfigValidationResponse,
    ConnectorCatalogResponse,
    ConnectorCreate,
    ConnectorResponse,
    ConnectorSearchFilter,
    ConnectorUpdate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["connectors-api"])


# === CATALOG ENDPOINTS (READ-ONLY) ===

@router.get("/catalog", response_model=List[ConnectorCatalogResponse])
async def list_catalog_api(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all available connectors from the catalog.

    Query Parameters:
        category: Optional category filter (e.g., "Social", "Web")

    Returns:
        List of catalog connectors
    """
    try:
        service = ConnectorService(db)
        connectors = await service.list_catalog(category=category)
        return connectors

    except Exception as e:
        handle_route_error("list_catalog_api", e)
        raise HTTPException(status_code=500, detail="Failed to load connector catalog")


@router.get("/catalog/{catalog_id}", response_model=ConnectorCatalogResponse)
async def get_catalog_item_api(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific catalog connector by ID.

    Path Parameters:
        catalog_id: Catalog connector ID

    Returns:
        Catalog connector details
    """
    try:
        service = ConnectorService(db)
        connector = await service.get_catalog_by_id(catalog_id)

        if not connector:
            raise HTTPException(status_code=404, detail="Catalog connector not found")

        return connector

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_catalog_item_api", e)
        raise HTTPException(status_code=500, detail="Failed to load catalog connector")


# === INSTALLED CONNECTOR ENDPOINTS (TENANT-SCOPED) ===

@router.get("/installed", response_model=List[ConnectorResponse])
async def list_installed_api(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    List installed connectors for the current tenant.

    Query Parameters:
        search: Optional search term
        category: Optional category filter
        status: Optional status filter (inactive, active, error)
        limit: Max results (default: 50, max: 100)
        offset: Pagination offset

    Returns:
        List of installed connectors with catalog info
    """
    try:
        service = ConnectorService(db, tenant_id)

        # Build filters
        from app.features.connectors.connectors.models import ConnectorStatus
        filters = ConnectorSearchFilter(
            search=search,
            category=category,
            status=ConnectorStatus(status) if status else None,
            limit=min(limit, 100),
            offset=offset
        )

        connectors = await service.list_installed(filters)
        return connectors

    except Exception as e:
        handle_route_error("list_installed_api", e)
        raise HTTPException(status_code=500, detail="Failed to load installed connectors")


@router.get("/installed/{connector_id}", response_model=ConnectorResponse)
async def get_installed_connector_api(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific installed connector by ID.

    Path Parameters:
        connector_id: Connector ID

    Returns:
        Installed connector details
    """
    try:
        service = ConnectorService(db, tenant_id)
        connector = await service.get_by_id_with_enrichment(connector_id)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        return connector

    except HTTPException:
        raise
    except Exception as e:
        handle_route_error("get_installed_connector_api", e)
        raise HTTPException(status_code=500, detail="Failed to load connector")


@router.post("/connectors", response_model=ConnectorResponse, status_code=201)
async def create_connector_api(
    connector_data: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Install a new connector instance.

    Request Body:
        ConnectorCreate with catalog_id, name, config, auth, tags

    Returns:
        Created connector with catalog info

    Raises:
        400: Validation failed or connector already exists
        404: Catalog connector not found
    """
    try:
        service = ConnectorService(db, tenant_id)
        connector = await service.install_connector(
            connector_data,
            created_by_id=current_user.id,
            created_by_name=current_user.name
        )

        await commit_transaction(db, "create_connector_api")

        logger.info("Connector created",
                   connector_id=connector.id,
                   name=connector.name,
                   tenant_id=tenant_id)

        return connector

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        handle_route_error("create_connector_api", e)
        raise HTTPException(status_code=500, detail="Failed to create connector")


@router.put("/connectors/{connector_id}", response_model=ConnectorResponse)
async def update_connector_api(
    connector_id: str,
    connector_data: ConnectorUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Update an installed connector.

    Path Parameters:
        connector_id: Connector ID

    Request Body:
        ConnectorUpdate with optional fields

    Returns:
        Updated connector

    Raises:
        400: Validation failed
        404: Connector not found
    """
    try:
        service = ConnectorService(db, tenant_id)
        connector = await service.update_connector(connector_id, connector_data)

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        await commit_transaction(db, "update_connector_api")

        logger.info("Connector updated",
                   connector_id=connector_id,
                   tenant_id=tenant_id)

        return connector

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        handle_route_error("update_connector_api", e)
        raise HTTPException(status_code=500, detail="Failed to update connector")


@router.delete("/connectors/{connector_id}", status_code=204)
async def delete_connector_api(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an installed connector.

    Path Parameters:
        connector_id: Connector ID

    Returns:
        204 No Content on success

    Raises:
        404: Connector not found
    """
    try:
        service = ConnectorService(db, tenant_id)
        deleted = await service.delete_connector(connector_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Connector not found")

        await commit_transaction(db, "delete_connector_api")

        logger.info("Connector deleted",
                   connector_id=connector_id,
                   tenant_id=tenant_id)

        return Response(status_code=204)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        handle_route_error("delete_connector_api", e)
        raise HTTPException(status_code=500, detail="Failed to delete connector")


# === VALIDATION ENDPOINT ===

@router.post("/validate-config", response_model=ConfigValidationResponse)
async def validate_config_api(
    validation_request: ConfigValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate configuration against catalog's JSON Schema.

    Request Body:
        catalog_key: Connector type key (e.g., "twitter")
        config: Configuration object to validate

    Returns:
        Validation result with errors if any
    """
    try:
        service = ConnectorService(db)
        result = await service.validate_config(
            validation_request.catalog_key,
            validation_request.config
        )

        return result

    except Exception as e:
        handle_route_error("validate_config_api", e)
        return ConfigValidationResponse(
            valid=False,
            errors=[f"Validation failed: {str(e)}"]
        )


# === PUBLISH TARGETS (FOR INTEGRATIONS) ===

@router.get("/publish-targets")
async def get_publish_targets_api(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """
    Get active connectors suitable for publishing/scheduling.

    Used by content broadcaster and other integrations.

    Returns:
        List of publish targets with capabilities
    """
    try:
        service = ConnectorService(db, tenant_id)
        targets = await service.get_publish_targets()

        return {"targets": targets, "count": len(targets)}

    except Exception as e:
        handle_route_error("get_publish_targets_api", e)
        raise HTTPException(status_code=500, detail="Failed to load publish targets")
