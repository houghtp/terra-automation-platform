"""GA4 client services."""

from __future__ import annotations

from typing import List, Optional

from app.features.core.sqlalchemy_imports import AsyncSession, select
from app.features.core.enhanced_base_service import BaseService

from ...models import Ga4Client
from ...schemas_clients import Ga4ClientCreate, Ga4ClientUpdate


class Ga4ClientCrudService(BaseService[Ga4Client]):
    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def list_clients(self) -> List[Ga4Client]:
        stmt = self.create_base_query(Ga4Client).order_by(Ga4Client.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_client(self, client_id: str) -> Optional[Ga4Client]:
        return await self.get_by_id(Ga4Client, client_id)

    async def create_client(self, payload: Ga4ClientCreate) -> Ga4Client:
        client = Ga4Client(
            tenant_id=self.tenant_id,
            name=payload.name,
            notes=payload.notes,
            status=payload.status or "active",
        )
        self.db.add(client)
        await self.db.flush()
        await self.db.refresh(client)
        return client

    async def update_client(self, client_id: str, payload: Ga4ClientUpdate) -> Optional[Ga4Client]:
        client = await self.get_by_id(Ga4Client, client_id)
        if not client:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(client, key, value)
        await self.db.flush()
        await self.db.refresh(client)
        return client

    async def delete_client(self, client_id: str) -> bool:
        client = await self.get_by_id(Ga4Client, client_id)
        if not client:
            return False
        await self.db.delete(client)
        await self.db.flush()
        return True
