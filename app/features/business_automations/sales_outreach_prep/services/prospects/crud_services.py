"""
Prospect CRUD service for Sales Outreach Prep.

Follows platform best practices:
- Inherits from BaseService for automatic tenant filtering
- Uses centralized imports from sqlalchemy_imports
- Structured logging with get_logger
- Proper error handling with handle_error()
"""

from typing import Dict, List, Optional, Tuple, Any

from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from app.features.business_automations.sales_outreach_prep.models import Prospect, Campaign, Company

logger = get_logger(__name__)


class ProspectCrudService(BaseService[Prospect]):
    """Service for managing prospects in sales campaigns."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def list_prospects(
        self,
        campaign_id: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        enrichment_status: Optional[str] = None,
        seniority_level: Optional[str] = None,
        company_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Tuple[List[Prospect], int]:
        """
        List prospects with optional filtering.

        Args:
            campaign_id: Filter by campaign
            search: Search term for name/title/email
            status: Filter by status
            enrichment_status: Filter by enrichment status
            seniority_level: Filter by seniority level
            company_id: Filter by company
            tags: Filter by tags (any match)
            limit: Max results to return
            offset: Offset for pagination

        Returns:
            Tuple of (prospects list, total count)
        """
        try:
            # Use create_base_query for automatic tenant filtering
            stmt = self.create_base_query(Prospect)

            # Apply filters
            if campaign_id:
                stmt = stmt.where(Prospect.campaign_id == campaign_id)

            if status:
                stmt = stmt.where(Prospect.status == status)

            if enrichment_status:
                stmt = stmt.where(Prospect.enrichment_status == enrichment_status)

            if seniority_level:
                stmt = stmt.where(Prospect.seniority_level == seniority_level)

            if company_id:
                stmt = stmt.where(Prospect.company_id == company_id)

            if tags:
                # Match any of the provided tags
                for tag in tags:
                    stmt = stmt.where(Prospect.tags.contains([tag]))

            if search:
                stmt = self.apply_search_filters(
                    stmt,
                    Prospect,
                    search,
                    ['full_name', 'first_name', 'last_name', 'job_title', 'email', 'location']
                )

            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await self.db.execute(count_stmt)).scalar_one()

            # Apply ordering and pagination
            stmt = stmt.order_by(Prospect.created_at.desc()).offset(offset).limit(limit)

            # Execute query
            result = await self.db.execute(stmt)
            prospects = list(result.scalars().all())

            logger.info(
                "Listed prospects",
                count=len(prospects),
                total=total,
                tenant_id=self.tenant_id,
                filters={
                    "campaign_id": campaign_id,
                    "search": search,
                    "status": status,
                    "enrichment_status": enrichment_status
                }
            )

            return prospects, int(total or 0)

        except Exception as e:
            await self.handle_error("list_prospects", e, campaign_id=campaign_id, search=search)
            raise

    async def get_prospect_by_id(self, prospect_id: str) -> Optional[Prospect]:
        """
        Get prospect by ID (tenant-scoped).

        Args:
            prospect_id: Prospect ID

        Returns:
            Prospect object or None
        """
        try:
            return await self.get_by_id(Prospect, prospect_id)
        except Exception as e:
            await self.handle_error("get_prospect_by_id", e, prospect_id=prospect_id)
            raise

    async def create_prospect(self, data: Dict[str, Any], user) -> Prospect:
        """
        Create a new prospect.

        Args:
            data: Prospect data dict
            user: Current user for audit trail

        Returns:
            Created Prospect object

        Raises:
            ValueError: If validation fails or tenant_id is missing
        """
        try:
            # Validate tenant_id
            if not self.tenant_id or self.tenant_id == "global":
                raise ValueError("Tenant ID is required for creating prospects")

            # Validate campaign exists and belongs to tenant
            campaign_id = data.get('campaign_id')
            if not campaign_id:
                raise ValueError("Campaign ID is required")

            campaign_stmt = self.create_base_query(Campaign).where(Campaign.id == campaign_id)
            campaign_result = await self.db.execute(campaign_stmt)
            campaign = campaign_result.scalar_one_or_none()

            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found or access denied")

            # Split full_name into first/last if provided
            full_name = data.get('full_name', '')
            first_name = data.get('first_name')
            last_name = data.get('last_name')

            if not first_name or not last_name:
                parts = full_name.split(' ', 1)
                first_name = parts[0] if len(parts) > 0 else ''
                last_name = parts[1] if len(parts) > 1 else ''

            # Create prospect object
            prospect = Prospect(
                tenant_id=self.tenant_id,
                campaign_id=campaign_id,
                company_id=data.get('company_id'),
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                job_title=data.get('job_title'),
                seniority_level=data.get('seniority_level'),
                location=data.get('location'),
                region=data.get('region'),
                email=data.get('email'),
                phone=data.get('phone'),
                linkedin_url=data.get('linkedin_url'),
                linkedin_snippet=data.get('linkedin_snippet'),
                enrichment_status=data.get('enrichment_status', 'not_started'),
                status=data.get('status', 'new'),
                tags=data.get('tags', []),
                notes=data.get('notes'),
                discovered_via=data.get('discovered_via', 'manual'),
                discovery_query=data.get('discovery_query'),
            )

            # Set audit fields
            if user:
                prospect.created_by = user.id
                prospect.created_by_name = user.name

            # Persist
            self.db.add(prospect)
            await self.db.flush()
            await self.db.refresh(prospect)

            # Log operation
            self.log_operation("prospect_creation", {
                "prospect_id": prospect.id,
                "full_name": prospect.full_name,
                "campaign_id": campaign_id
            })

            logger.info(
                "Prospect created",
                prospect_id=prospect.id,
                name=prospect.full_name,
                campaign_id=campaign_id,
                tenant_id=self.tenant_id
            )

            return prospect

        except Exception as e:
            await self.handle_error("create_prospect", e, name=data.get('full_name'))
            raise

    async def update_prospect(
        self,
        prospect_id: str,
        data: Dict[str, Any],
        user
    ) -> Optional[Prospect]:
        """
        Update an existing prospect.

        Args:
            prospect_id: Prospect ID
            data: Updated fields
            user: Current user for audit trail

        Returns:
            Updated Prospect object or None if not found
        """
        try:
            # Get existing prospect (tenant-scoped)
            prospect = await self.get_by_id(Prospect, prospect_id)
            if not prospect:
                logger.warning("Prospect not found for update", prospect_id=prospect_id)
                return None

            # Update fields (only if provided in data)
            for field in [
                'full_name', 'first_name', 'last_name', 'job_title', 'seniority_level',
                'location', 'region', 'email', 'email_confidence', 'email_status',
                'phone', 'linkedin_url', 'linkedin_snippet', 'enrichment_status',
                'enriched_at', 'enrichment_source', 'status', 'tags', 'notes',
                'company_id'
            ]:
                if field in data:
                    setattr(prospect, field, data[field])

            # Update audit fields
            if user:
                prospect.updated_by = user.id
                prospect.updated_by_name = user.name

            # Persist
            await self.db.flush()
            await self.db.refresh(prospect)

            # Log operation
            self.log_operation("prospect_update", {
                "prospect_id": prospect.id,
                "updated_fields": list(data.keys())
            })

            logger.info(
                "Prospect updated",
                prospect_id=prospect.id,
                fields_updated=list(data.keys()),
                tenant_id=self.tenant_id
            )

            return prospect

        except Exception as e:
            await self.handle_error("update_prospect", e, prospect_id=prospect_id)
            raise

    async def delete_prospect(self, prospect_id: str) -> bool:
        """
        Delete a prospect (and cascade delete enrichment logs).

        Args:
            prospect_id: Prospect ID

        Returns:
            True if deleted, False if not found
        """
        try:
            prospect = await self.get_by_id(Prospect, prospect_id)
            if not prospect:
                logger.warning("Prospect not found for deletion", prospect_id=prospect_id)
                return False

            # Delete (cascade will handle enrichment_logs)
            await self.db.delete(prospect)
            await self.db.flush()

            # Log operation
            self.log_operation("prospect_deletion", {
                "prospect_id": prospect_id,
                "prospect_name": prospect.full_name
            })

            logger.info(
                "Prospect deleted",
                prospect_id=prospect_id,
                tenant_id=self.tenant_id
            )

            return True

        except Exception as e:
            await self.handle_error("delete_prospect", e, prospect_id=prospect_id)
            raise

    async def update_prospect_enrichment(
        self,
        prospect_id: str,
        enrichment_data: Dict[str, Any]
    ) -> Optional[Prospect]:
        """
        Update prospect with enrichment data (email, phone, etc.).

        Args:
            prospect_id: Prospect ID
            enrichment_data: Enrichment data from Hunter.io, etc.

        Returns:
            Updated Prospect object or None if not found
        """
        try:
            prospect = await self.get_by_id(Prospect, prospect_id)
            if not prospect:
                logger.warning("Prospect not found for enrichment", prospect_id=prospect_id)
                return None

            # Update enrichment fields
            if 'email' in enrichment_data:
                prospect.email = enrichment_data['email']
                prospect.email_confidence = enrichment_data.get('email_confidence')
                prospect.email_status = enrichment_data.get('email_status')

            if 'phone' in enrichment_data:
                prospect.phone = enrichment_data['phone']

            if 'enrichment_source' in enrichment_data:
                prospect.enrichment_source = enrichment_data['enrichment_source']

            # Update status
            prospect.enrichment_status = enrichment_data.get('enrichment_status', 'enriched')
            prospect.enriched_at = datetime.now()

            # If email found, promote status from 'new' to 'enriched'
            if prospect.email and prospect.status == 'new':
                prospect.status = 'enriched'

            await self.db.flush()
            await self.db.refresh(prospect)

            logger.info(
                "Prospect enriched",
                prospect_id=prospect.id,
                email=prospect.email,
                enrichment_source=prospect.enrichment_source
            )

            return prospect

        except Exception as e:
            await self.handle_error("update_prospect_enrichment", e, prospect_id=prospect_id)
            raise

    async def get_prospects_for_enrichment(
        self,
        campaign_id: str,
        limit: int = 50
    ) -> List[Prospect]:
        """
        Get prospects ready for enrichment (have LinkedIn but no email).

        Args:
            campaign_id: Campaign ID
            limit: Max prospects to return

        Returns:
            List of prospects ready for enrichment
        """
        try:
            stmt = (
                self.create_base_query(Prospect)
                .where(
                    Prospect.campaign_id == campaign_id,
                    Prospect.enrichment_status == 'not_started',
                    Prospect.linkedin_url.isnot(None)
                )
                .order_by(Prospect.created_at.asc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            prospects = list(result.scalars().all())

            logger.info(
                "Retrieved prospects for enrichment",
                campaign_id=campaign_id,
                count=len(prospects)
            )

            return prospects

        except Exception as e:
            await self.handle_error("get_prospects_for_enrichment", e, campaign_id=campaign_id)
            raise

    async def bulk_update_status(
        self,
        prospect_ids: List[str],
        new_status: str,
        user
    ) -> int:
        """
        Bulk update prospect status.

        Args:
            prospect_ids: List of prospect IDs
            new_status: New status to set
            user: Current user for audit

        Returns:
            Number of prospects updated
        """
        try:
            stmt = (
                update(Prospect)
                .where(
                    Prospect.id.in_(prospect_ids),
                    Prospect.tenant_id == self.tenant_id
                )
                .values(
                    status=new_status,
                    updated_by=user.id if user else None,
                    updated_by_name=user.name if user else None
                )
            )

            result = await self.db.execute(stmt)
            count = result.rowcount

            logger.info(
                "Bulk status update",
                count=count,
                new_status=new_status,
                tenant_id=self.tenant_id
            )

            return count

        except Exception as e:
            await self.handle_error("bulk_update_status", e, new_status=new_status)
            raise
