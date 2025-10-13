"""
API Keys CRUD service for managing customer/tenant API keys.

Provides admin interface for managing external API keys used to access the platform.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from app.features.core.api_security import APIKey, APIKeyStatus, APIKeyScope, APIKeyManager

logger = get_logger(__name__)


class APIKeyCrudService(BaseService[APIKey]):
    """
    Service for managing API keys with proper tenant isolation.

    Inherits from BaseService for consistent patterns.
    """

    async def get_api_key_stats(self) -> Dict[str, Any]:
        """
        Get API key usage statistics.

        Returns:
            Dict with total_keys, active_keys, revoked_keys, expired_keys, top_tenants
        """
        try:
            # Base query with tenant filtering
            base_query = self.create_base_query(APIKey)

            # Total keys
            total_stmt = select(func.count(APIKey.id)).select_from(base_query.subquery())
            total_result = await self.db.execute(total_stmt)
            total_keys = total_result.scalar() or 0

            # Active keys
            active_stmt = select(func.count(APIKey.id)).select_from(
                base_query.where(
                    APIKey.status == APIKeyStatus.ACTIVE.value,
                    APIKey.is_active == True
                ).subquery()
            )
            active_result = await self.db.execute(active_stmt)
            active_keys = active_result.scalar() or 0

            # Revoked keys
            revoked_stmt = select(func.count(APIKey.id)).select_from(
                base_query.where(APIKey.status == APIKeyStatus.REVOKED.value).subquery()
            )
            revoked_result = await self.db.execute(revoked_stmt)
            revoked_keys = revoked_result.scalar() or 0

            # Expired keys
            expired_stmt = select(func.count(APIKey.id)).select_from(
                base_query.where(APIKey.expires_at < datetime.now()).subquery()
            )
            expired_result = await self.db.execute(expired_stmt)
            expired_keys = expired_result.scalar() or 0

            # Get top tenants by usage (only if global admin)
            top_tenants = []
            if self.tenant_id is None:  # Global admin
                top_tenants_stmt = select(
                    APIKey.tenant_id,
                    func.sum(APIKey.usage_count).label('total_usage')
                ).group_by(APIKey.tenant_id).order_by(
                    func.sum(APIKey.usage_count).desc()
                ).limit(5)

                top_tenants_result = await self.db.execute(top_tenants_stmt)
                top_tenants = [
                    {"tenant_id": row.tenant_id, "usage_count": row.total_usage}
                    for row in top_tenants_result
                ]

            self.log_operation("api_key_stats", {
                "total_keys": total_keys,
                "active_keys": active_keys
            })

            return {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "revoked_keys": revoked_keys,
                "expired_keys": expired_keys,
                "total_requests_today": 0,  # Would need daily tracking
                "top_tenants": top_tenants
            }

        except Exception as e:
            await self.handle_error("get_api_key_stats", e)
            return {
                "total_keys": 0,
                "active_keys": 0,
                "revoked_keys": 0,
                "expired_keys": 0,
                "total_requests_today": 0,
                "top_tenants": []
            }

    async def create_api_key(
        self,
        name: str,
        target_tenant_id: str,
        scopes: List[str],
        created_by_user_id: str,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_hour: int = 1000,
        rate_limit_per_day: int = 10000
    ) -> Tuple[Optional[APIKey], Optional[str]]:
        """
        Create new API key for a tenant.

        Args:
            name: Human-readable name for the key
            target_tenant_id: Tenant ID the key belongs to
            scopes: List of permission scopes
            created_by_user_id: User ID who created the key
            description: Optional description
            expires_in_days: Optional expiration in days
            rate_limit_per_hour: Requests per hour limit
            rate_limit_per_day: Requests per day limit

        Returns:
            Tuple of (APIKey, secret) if successful, (None, None) otherwise
        """
        try:
            # Validate scopes
            valid_scopes = [scope.value for scope in APIKeyScope]
            invalid_scopes = [s for s in scopes if s not in valid_scopes]
            if invalid_scopes:
                raise ValueError(f"Invalid scopes: {invalid_scopes}")

            # Create API key using APIKeyManager
            api_key, secret = await APIKeyManager.create_api_key(
                session=self.db,
                name=name,
                tenant_id=target_tenant_id,
                scopes=scopes,
                created_by=created_by_user_id,
                description=description,
                expires_in_days=expires_in_days,
                rate_limit_per_hour=rate_limit_per_hour,
                rate_limit_per_day=rate_limit_per_day
            )

            if not api_key:
                raise ValueError("Failed to create API key")

            self.log_operation("api_key_created", {
                "key_id": api_key.key_id,
                "name": name,
                "target_tenant_id": target_tenant_id,
                "scopes": scopes
            })

            logger.info("API key created",
                       key_id=api_key.key_id,
                       name=name,
                       target_tenant_id=target_tenant_id,
                       created_by=created_by_user_id)

            return api_key, secret

        except ValueError:
            raise
        except Exception as e:
            await self.handle_error("create_api_key", e, name=name, target_tenant_id=target_tenant_id)
            return None, None

    async def list_api_keys(
        self,
        filter_tenant_id: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[APIKey]:
        """
        List API keys with optional filtering.

        Args:
            filter_tenant_id: Optional tenant ID to filter by
            include_inactive: Include inactive keys
            limit: Number of keys to return
            offset: Offset for pagination

        Returns:
            List of APIKey instances
        """
        try:
            # Start with base query (tenant-scoped)
            stmt = self.create_base_query(APIKey)

            # Apply additional tenant filter if specified
            if filter_tenant_id:
                stmt = stmt.where(APIKey.tenant_id == filter_tenant_id)

            # Filter by active status
            if not include_inactive:
                stmt = stmt.where(APIKey.is_active == True)

            # Apply pagination and ordering
            stmt = stmt.order_by(desc(APIKey.created_at)).limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            api_keys = result.scalars().all()

            self.log_operation("list_api_keys", {
                "count": len(api_keys),
                "filter_tenant_id": filter_tenant_id,
                "include_inactive": include_inactive
            })

            return list(api_keys)

        except Exception as e:
            await self.handle_error("list_api_keys", e)
            return []

    async def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """
        Get API key by key_id.

        Args:
            key_id: Public key identifier

        Returns:
            APIKey if found, None otherwise

        Raises:
            ValueError: If key not found
        """
        try:
            stmt = self.create_base_query(APIKey).where(APIKey.key_id == key_id)
            result = await self.db.execute(stmt)
            api_key = result.scalar_one_or_none()

            if not api_key:
                raise ValueError(f"API key {key_id} not found")

            return api_key

        except ValueError:
            raise
        except Exception as e:
            await self.handle_error("get_api_key", e, key_id=key_id)
            raise

    async def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: Public key identifier

        Returns:
            True if revoked successfully

        Raises:
            ValueError: If key not found
        """
        try:
            # Find the API key first
            api_key = await self.get_api_key(key_id)

            if not api_key:
                raise ValueError(f"API key {key_id} not found")

            # Revoke the key using APIKeyManager
            success = await APIKeyManager.revoke_api_key(
                session=self.db,
                key_id=key_id,
                tenant_id=api_key.tenant_id
            )

            if not success:
                raise ValueError("Failed to revoke API key")

            self.log_operation("api_key_revoked", {
                "key_id": key_id,
                "tenant_id": api_key.tenant_id
            })

            logger.info("API key revoked", key_id=key_id, tenant_id=api_key.tenant_id)

            return True

        except ValueError:
            raise
        except Exception as e:
            await self.handle_error("revoke_api_key", e, key_id=key_id)
            raise

    async def get_available_scopes(self) -> Dict[str, Dict[str, str]]:
        """
        Get list of available API key scopes with descriptions.

        Returns:
            Dict mapping scope values to name and description
        """
        scopes = {
            scope.value: {
                "name": scope.name,
                "description": {
                    "read": "Read-only access to resources",
                    "write": "Create and update resources",
                    "admin": "Full administrative access",
                    "webhook": "Webhook and event access",
                    "monitoring": "System monitoring and metrics"
                }.get(scope.value, f"Access scope: {scope.value}")
            }
            for scope in APIKeyScope
        }

        return scopes
