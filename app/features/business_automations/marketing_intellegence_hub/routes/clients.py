"""Client routes for Marketing Intelligence GA4."""

from app.features.core.route_imports import APIRouter, Depends, HTTPException
from app.features.auth.dependencies import get_current_user

from ..schemas_clients import Ga4ClientCreate, Ga4ClientUpdate, Ga4ClientResponse
from ..services import Ga4ClientCrudService
from ..dependencies import get_client_service

router = APIRouter(prefix="/ga4/clients", tags=["ga4-clients"])


@router.get("/", response_model=list[Ga4ClientResponse])
async def list_clients(service: Ga4ClientCrudService = Depends(get_client_service)):
    return [Ga4ClientResponse.model_validate(item, from_attributes=True) for item in await service.list_clients()]


@router.post("/", response_model=Ga4ClientResponse, status_code=201)
async def create_client(
    payload: Ga4ClientCreate,
    service: Ga4ClientCrudService = Depends(get_client_service),
    current_user=Depends(get_current_user),
):
    client = await service.create_client(payload)
    await service.db.commit()
    return Ga4ClientResponse.model_validate(client, from_attributes=True)


@router.put("/{client_id}", response_model=Ga4ClientResponse)
async def update_client(
    client_id: str,
    payload: Ga4ClientUpdate,
    service: Ga4ClientCrudService = Depends(get_client_service),
    current_user=Depends(get_current_user),
):
    updated = await service.update_client(client_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found")
    await service.db.commit()
    return Ga4ClientResponse.model_validate(updated, from_attributes=True)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: str,
    service: Ga4ClientCrudService = Depends(get_client_service),
    current_user=Depends(get_current_user),
):
    deleted = await service.delete_client(client_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Client not found")
    await service.db.commit()
    return {}
