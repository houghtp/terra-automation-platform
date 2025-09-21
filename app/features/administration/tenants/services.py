"""
Tenant management service for global administrators.
Provides comprehensive tenant CRUD operations and user assignment.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload

from app.features.administration.tenants.db_models import Tenant
from app.features.auth.models import User
from app.features.administration.tenants.models import (
    TenantCreate, TenantUpdate, TenantResponse, TenantStats,
    TenantDashboardStats, TenantSearchFilter, TenantUserResponse
)

logger = logging.getLogger(__name__)


class TenantManagementService:
    """
    Comprehensive tenant management service for global administrators.
    
    Provides:
    - Full tenant CRUD operations
    - User assignment and management
    - Statistics and reporting
    - Search and filtering
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_tenant(self, tenant_data: TenantCreate) -> TenantResponse:
        """
        Create a new tenant with full configuration.
        
        Args:
            tenant_data: Tenant creation data
            
        Returns:
            TenantResponse: Created tenant information
        """
        try:
            # Check if tenant with this name already exists
            existing = await self.get_tenant_by_name(tenant_data.name)
            if existing:
                raise ValueError(f"Tenant with name '{tenant_data.name}' already exists")

            # Create tenant record
            tenant = Tenant(
                name=tenant_data.name,
                description=tenant_data.description,
                status=tenant_data.status.value,
                tier=tenant_data.tier.value,
                contact_email=tenant_data.contact_email,
                contact_name=tenant_data.contact_name,
                website=tenant_data.website,
                max_users=tenant_data.max_users,
                features=tenant_data.features,
                settings=tenant_data.settings
            )

            self.db.add(tenant)
            await self.db.flush()
            await self.db.refresh(tenant)
            
            # Get user count (will be 0 for new tenant)
            user_count = await self._get_tenant_user_count(tenant.id)
            
            logger.info(f"Created tenant: {tenant.name} (ID: {tenant.id})")
            
            return self._tenant_to_response(tenant, user_count)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create tenant: {e}")
            raise

    async def get_tenant_by_id(self, tenant_id: int) -> Optional[TenantResponse]:
        """Get tenant by ID with user count."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return None
            
        user_count = await self._get_tenant_user_count(tenant_id)
        return self._tenant_to_response(tenant, user_count)

    async def get_tenant_by_name(self, name: str) -> Optional[TenantResponse]:
        """Get tenant by name with user count."""
        stmt = select(Tenant).where(Tenant.name == name)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            return None
            
        user_count = await self._get_tenant_user_count(tenant.id)
        return self._tenant_to_response(tenant, user_count)

    async def update_tenant(self, tenant_id: int, tenant_data: TenantUpdate) -> Optional[TenantResponse]:
        """Update tenant information."""
        try:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await self.db.execute(stmt)
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                return None

            # Update fields if provided
            update_fields = tenant_data.dict(exclude_unset=True)
            
            for field, value in update_fields.items():
                if hasattr(tenant, field):
                    if field in ['status', 'tier'] and hasattr(value, 'value'):
                        setattr(tenant, field, value.value)
                    else:
                        setattr(tenant, field, value)

            await self.db.flush()
            await self.db.refresh(tenant)
            
            user_count = await self._get_tenant_user_count(tenant_id)
            
            logger.info(f"Updated tenant: {tenant.name} (ID: {tenant_id})")
            
            return self._tenant_to_response(tenant, user_count)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update tenant {tenant_id}: {e}")
            raise

    async def delete_tenant(self, tenant_id: int) -> bool:
        """
        Delete tenant and handle user reassignment/cleanup.
        
        Args:
            tenant_id: Tenant ID to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await self.db.execute(stmt)
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                return False

            # Check if tenant has users
            user_count = await self._get_tenant_user_count(tenant_id)
            if user_count > 0:
                raise ValueError(f"Cannot delete tenant with {user_count} active users. Please reassign or remove users first.")

            await self.db.delete(tenant)
            await self.db.flush()
            
            logger.info(f"Deleted tenant: {tenant.name} (ID: {tenant_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise

    async def list_tenants(self, filters: Optional[TenantSearchFilter] = None) -> List[TenantResponse]:
        """List tenants with optional filtering."""
        try:
            stmt = select(Tenant)
            
            # Apply filters if provided
            if filters:
                conditions = []
                
                if filters.search:
                    search_term = f"%{filters.search}%"
                    conditions.append(
                        or_(
                            Tenant.name.ilike(search_term),
                            Tenant.description.ilike(search_term),
                            Tenant.contact_email.ilike(search_term),
                            Tenant.contact_name.ilike(search_term)
                        )
                    )
                
                if filters.status:
                    conditions.append(Tenant.status == filters.status.value)
                    
                if filters.tier:
                    conditions.append(Tenant.tier == filters.tier.value)
                
                if filters.created_after:
                    conditions.append(Tenant.created_at >= filters.created_after)
                    
                if filters.created_before:
                    conditions.append(Tenant.created_at <= filters.created_before)
                
                if conditions:
                    stmt = stmt.where(and_(*conditions))
            
            # Apply ordering and pagination
            stmt = stmt.order_by(Tenant.created_at.desc())
            
            if filters:
                stmt = stmt.offset(filters.offset).limit(filters.limit)
            
            result = await self.db.execute(stmt)
            tenants = result.scalars().all()
            
            # Get user counts for all tenants
            tenant_responses = []
            for tenant in tenants:
                user_count = await self._get_tenant_user_count(tenant.id)
                
                # Apply user count filter if specified
                if filters and filters.has_users is not None:
                    if filters.has_users and user_count == 0:
                        continue
                    if not filters.has_users and user_count > 0:
                        continue
                
                tenant_responses.append(self._tenant_to_response(tenant, user_count))
            
            return tenant_responses
            
        except Exception as e:
            logger.error(f"Failed to list tenants: {e}")
            raise

    async def get_tenant_users(self, tenant_id: int, limit: int = 50, offset: int = 0) -> List[TenantUserResponse]:
        """Get users belonging to a specific tenant."""
        try:
            # Check if tenant exists
            tenant = await self.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")

            stmt = select(User).where(
                and_(
                    User.tenant_id == str(tenant_id),
                    User.role != "global_admin"  # Exclude global admins
                )
            ).order_by(User.created_at.desc()).offset(offset).limit(limit)
            
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            return [
                TenantUserResponse(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    role=user.role,
                    status=user.status,
                    enabled=user.enabled,
                    created_at=user.created_at.isoformat() if user.created_at else None,
                    last_login=None  # TODO: Add last login tracking
                )
                for user in users
            ]
            
        except Exception as e:
            logger.error(f"Failed to get users for tenant {tenant_id}: {e}")
            raise

    async def assign_user_to_tenant(self, user_id: str, tenant_id: int, role: str = "user") -> bool:
        """
        Assign an existing user to a tenant.
        
        Args:
            user_id: User ID to assign
            tenant_id: Target tenant ID
            role: Role in the tenant (user, admin)
            
        Returns:
            bool: True if assignment successful
        """
        try:
            # Check if tenant exists and has capacity
            tenant = await self.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            if tenant.user_count >= tenant.max_users:
                raise ValueError(f"Tenant {tenant.name} has reached maximum user limit ({tenant.max_users})")

            # Get the user
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Update user's tenant assignment
            user.tenant_id = str(tenant_id)
            user.role = role
            
            await self.db.flush()
            
            logger.info(f"Assigned user {user.email} to tenant {tenant.name} with role {role}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to assign user {user_id} to tenant {tenant_id}: {e}")
            raise

    async def remove_user_from_tenant(self, user_id: str, tenant_id: int) -> bool:
        """Remove user from tenant (deactivate)."""
        try:
            stmt = select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_id == str(tenant_id)
                )
            )
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False

            # Deactivate user instead of deleting
            user.is_active = False
            await self.db.flush()
            
            logger.info(f"Removed user {user.email} from tenant {tenant_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to remove user {user_id} from tenant {tenant_id}: {e}")
            raise

    async def get_dashboard_stats(self) -> TenantDashboardStats:
        """Get comprehensive dashboard statistics for tenant management."""
        try:
            # Total tenant counts by status
            status_counts = await self.db.execute(
                select(
                    Tenant.status,
                    func.count(Tenant.id)
                ).group_by(Tenant.status)
            )
            status_map = dict(status_counts.fetchall())
            
            # Tier distribution
            tier_counts = await self.db.execute(
                select(
                    Tenant.tier,
                    func.count(Tenant.id)
                ).group_by(Tenant.tier)
            )
            tier_map = dict(tier_counts.fetchall())
            
            # Total users across all tenants (excluding global admins)
            total_users_result = await self.db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.is_active == True,
                        User.role != "global_admin"
                    )
                )
            )
            total_users = total_users_result.scalar() or 0
            
            # Recent tenants (last 5)
            recent_tenants_stmt = select(Tenant).order_by(
                Tenant.created_at.desc()
            ).limit(5)
            recent_result = await self.db.execute(recent_tenants_stmt)
            recent_tenants = recent_result.scalars().all()
            
            recent_tenant_responses = []
            for tenant in recent_tenants:
                user_count = await self._get_tenant_user_count(tenant.id)
                recent_tenant_responses.append(self._tenant_to_response(tenant, user_count))
            
            return TenantDashboardStats(
                total_tenants=sum(status_map.values()),
                active_tenants=status_map.get("active", 0),
                inactive_tenants=status_map.get("inactive", 0),
                suspended_tenants=status_map.get("suspended", 0),
                total_users=total_users,
                tenants_by_tier=tier_map,
                recent_tenants=recent_tenant_responses
            )
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            raise

    async def _get_tenant_user_count(self, tenant_id: int) -> int:
        """Get count of active users for a tenant."""
        try:
            # Handle both string and integer tenant IDs for compatibility
            result = await self.db.execute(
                select(func.count(User.id)).where(
                    and_(
                        or_(
                            User.tenant_id == str(tenant_id),
                            User.tenant_id == tenant_id
                        ),
                        User.is_active == True,
                        User.role != "global_admin"
                    )
                )
            )
            return result.scalar() or 0
        except Exception:
            return 0

    def _tenant_to_response(self, tenant: Tenant, user_count: int = 0) -> TenantResponse:
        """Convert Tenant model to TenantResponse schema."""
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            status=tenant.status,
            tier=tenant.tier,
            contact_email=tenant.contact_email,
            contact_name=tenant.contact_name,
            website=tenant.website,
            max_users=tenant.max_users,
            user_count=user_count,
            features=tenant.features or {},
            settings=tenant.settings or {},
            created_at=tenant.created_at.isoformat() if tenant.created_at else None,
            updated_at=tenant.updated_at.isoformat() if tenant.updated_at else None
        )