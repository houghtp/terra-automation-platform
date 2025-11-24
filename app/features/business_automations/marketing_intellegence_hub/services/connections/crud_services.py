"""GA4 connection services (Phase 1)."""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime

from app.features.core.sqlalchemy_imports import AsyncSession, select
from app.features.core.enhanced_base_service import BaseService
from app.features.core.audit_mixin import AuditContext
from app.features.core.encryption import encrypt_secret, decrypt_secret

from ...models import Ga4Connection, Ga4Token
from ...schemas import Ga4ConnectionCreate, Ga4ConnectionUpdate
from sqlalchemy import select


class Ga4ConnectionCrudService(BaseService[Ga4Connection]):
    """Manage GA4 connections and tokens."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id)

    async def list_connections(self) -> List[Ga4Connection]:
        try:
            stmt = self.create_base_query(Ga4Connection).order_by(Ga4Connection.created_at.desc())
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            await self.handle_error("list_connections", exc)

    async def get_connection(self, connection_id: str) -> Optional[Ga4Connection]:
        return await self.get_by_id(Ga4Connection, connection_id)

    async def create_connection(self, payload: Ga4ConnectionCreate, token_data: Dict[str, str], user=None) -> Ga4Connection:
        try:
            audit = AuditContext.from_user(user) if user else None

            # Upsert by (tenant_id, property_id)
            existing = await self._get_by_property(payload.property_id)
            if existing:
                connection = existing
                connection.property_name = payload.property_name or connection.property_name
                connection.client_name = payload.client_name or connection.client_name
                connection.client_id = payload.client_id or connection.client_id
                connection.status = "active"
                if audit:
                    connection.set_updated_by(audit.user_email, audit.user_name)
            else:
                connection = Ga4Connection(
                    tenant_id=self.tenant_id,
                    property_id=payload.property_id,
                    property_name=payload.property_name,
                    client_name=payload.client_name,
                    client_id=payload.client_id,
                    status="active",
                )
                if audit:
                    connection.set_created_by(audit.user_email, audit.user_name)

            self.db.add(connection)
            await self.db.flush()

            await self._store_tokens(connection.id, token_data)
            await self.db.refresh(connection)
            return connection
        except Exception as exc:
            await self.handle_error("create_connection", exc)

    async def _get_by_property(self, property_id: str) -> Optional[Ga4Connection]:
        try:
            stmt = self.create_base_query(Ga4Connection).where(Ga4Connection.property_id == property_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as exc:
            await self.handle_error("_get_by_property", exc)

    async def update_connection(self, connection_id: str, payload: Ga4ConnectionUpdate, user=None) -> Optional[Ga4Connection]:
        connection = await self.get_by_id(Ga4Connection, connection_id)
        if not connection:
            return None
        try:
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(connection, key, value)

            if user:
                audit = AuditContext.from_user(user)
                connection.set_updated_by(audit.user_email, audit.user_name)

            await self.db.flush()
            await self.db.refresh(connection)
            return connection
        except Exception as exc:
            await self.handle_error("update_connection", exc, connection_id=connection_id)

    async def delete_connection(self, connection_id: str) -> bool:
        connection = await self.get_by_id(Ga4Connection, connection_id)
        if not connection:
            return False
        try:
            await self.db.delete(connection)
            await self.db.flush()
            return True
        except Exception as exc:
            await self.handle_error("delete_connection", exc, connection_id=connection_id)

    async def upsert_tokens(self, connection_id: str, token_data: Dict[str, str]) -> Ga4Token:
        connection = await self.get_by_id(Ga4Connection, connection_id)
        if not connection:
            raise ValueError("Connection not found")
        try:
            expires_at = token_data.get("access_token_expires_at")
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at)
                except ValueError:
                    expires_at = None

            encrypted_refresh = encrypt_secret(token_data.get("refresh_token", ""), connection.tenant_id)
            encrypted_access = None
            if token_data.get("access_token"):
                encrypted_access = encrypt_secret(token_data["access_token"], connection.tenant_id)

            existing_stmt = select(Ga4Token).where(Ga4Token.connection_id == connection_id)
            existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()

            if existing:
                existing.encrypted_refresh_token = encrypted_refresh
                existing.encrypted_access_token = encrypted_access
                existing.access_token_expires_at = expires_at
                token = existing
            else:
                token = Ga4Token(
                    connection_id=connection_id,
                    encrypted_refresh_token=encrypted_refresh,
                    encrypted_access_token=encrypted_access,
                    access_token_expires_at=expires_at,
                )
                self.db.add(token)

            await self.db.flush()
            await self.db.refresh(token)
            return token
        except Exception as exc:
            await self.handle_error("upsert_tokens", exc, connection_id=connection_id)

    async def _store_tokens(self, connection_id: str, token_data: Dict[str, str]) -> Ga4Token:
        return await self.upsert_tokens(connection_id, token_data)

    async def get_tokens(self, connection_id: str) -> Optional[Dict[str, str]]:
        """Retrieve decrypted tokens for a connection."""
        try:
            stmt = (
                select(Ga4Token, Ga4Connection.tenant_id)
                .join(Ga4Connection, Ga4Connection.id == Ga4Token.connection_id)
                .where(Ga4Token.connection_id == connection_id)
            )
            result = (await self.db.execute(stmt)).first()
            if not result:
                return None
            token, token_tenant_id = result
            tenant_for_token = token_tenant_id or self.tenant_id
            if not token:
                return None
            return {
                "refresh_token": decrypt_secret(token.encrypted_refresh_token, tenant_for_token),
                "access_token": decrypt_secret(token.encrypted_access_token, tenant_for_token) if token.encrypted_access_token else None,
                "access_token_expires_at": token.access_token_expires_at,
            }
        except Exception as exc:
            await self.handle_error("get_tokens", exc, connection_id=connection_id)
