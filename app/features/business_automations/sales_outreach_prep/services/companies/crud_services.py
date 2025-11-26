"""
Company CRUD service for Sales Outreach Prep.

Follows platform best practices:
- Inherits from BaseService for automatic tenant filtering
- Uses centralized imports from sqlalchemy_imports
- Structured logging with get_logger
- Proper error handling with handle_error()
"""

from typing import Dict, List, Optional, Tuple, Any

from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from app.features.business_automations.sales_outreach_prep.models import Company

logger = get_logger(__name__)


class CompanyCrudService(BaseService[Company]):
    """Service for managing companies in sales campaigns."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)

    async def list_companies(
        self,
        search: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Tuple[List[Company], int]:
        """
        List companies with optional filtering.

        Args:
            search: Search term for name/domain/industry
            industry: Filter by industry
            limit: Max results to return
            offset: Offset for pagination

        Returns:
            Tuple of (companies list, total count)
        """
        try:
            # Use create_base_query for automatic tenant filtering
            stmt = self.create_base_query(Company)

            # Apply filters
            if industry:
                stmt = stmt.where(Company.industry == industry)

            if search:
                stmt = self.apply_search_filters(
                    stmt,
                    Company,
                    search,
                    ['name', 'domain', 'industry', 'headquarters', 'description']
                )

            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await self.db.execute(count_stmt)).scalar_one()

            # Apply ordering and pagination
            stmt = stmt.order_by(Company.name.asc()).offset(offset).limit(limit)

            # Execute query
            result = await self.db.execute(stmt)
            companies = list(result.scalars().all())

            logger.info(
                "Listed companies",
                count=len(companies),
                total=total,
                tenant_id=self.tenant_id,
                filters={"search": search, "industry": industry}
            )

            return companies, int(total or 0)

        except Exception as e:
            await self.handle_error("list_companies", e, search=search, industry=industry)
            raise

    async def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """
        Get company by ID (tenant-scoped).

        Args:
            company_id: Company ID

        Returns:
            Company object or None
        """
        try:
            return await self.get_by_id(Company, company_id)
        except Exception as e:
            await self.handle_error("get_company_by_id", e, company_id=company_id)
            raise

    async def get_company_by_domain(self, domain: str) -> Optional[Company]:
        """
        Get company by domain (tenant-scoped).

        Args:
            domain: Company domain (e.g., 'acme.com')

        Returns:
            Company object or None
        """
        try:
            stmt = self.create_base_query(Company).where(Company.domain == domain)
            result = await self.db.execute(stmt)
            company = result.scalar_one_or_none()

            if company:
                logger.info("Company found by domain", domain=domain, company_id=company.id)
            else:
                logger.debug("Company not found by domain", domain=domain)

            return company

        except Exception as e:
            await self.handle_error("get_company_by_domain", e, domain=domain)
            raise

    async def create_company(self, data: Dict[str, Any], user) -> Company:
        """
        Create a new company.

        Args:
            data: Company data dict
            user: Current user for audit trail

        Returns:
            Created Company object

        Raises:
            ValueError: If validation fails or tenant_id is missing
        """
        try:
            # Validate tenant_id
            if not self.tenant_id or self.tenant_id == "global":
                raise ValueError("Tenant ID is required for creating companies")

            # Check for duplicate domain
            if data.get('domain'):
                existing = await self.get_company_by_domain(data['domain'])
                if existing:
                    raise ValueError(f"Company with domain {data['domain']} already exists")

            # Create company object
            company = Company(
                tenant_id=self.tenant_id,
                name=data.get('name'),
                domain=data.get('domain'),
                alternate_domains=data.get('alternate_domains', []),
                industry=data.get('industry'),
                headquarters=data.get('headquarters'),
                size=data.get('size'),
                description=data.get('description'),
                logo_url=data.get('logo_url'),
                linkedin_url=data.get('linkedin_url'),
                website_url=data.get('website_url'),
            )

            # Set audit fields
            if user:
                company.created_by = user.id
                company.created_by_name = user.name

            # Persist
            self.db.add(company)
            await self.db.flush()
            await self.db.refresh(company)

            # Log operation
            self.log_operation("company_creation", {
                "company_id": company.id,
                "company_name": company.name,
                "domain": company.domain
            })

            logger.info(
                "Company created",
                company_id=company.id,
                name=company.name,
                domain=company.domain,
                tenant_id=self.tenant_id
            )

            return company

        except Exception as e:
            await self.handle_error("create_company", e, name=data.get('name'))
            raise

    async def update_company(
        self,
        company_id: str,
        data: Dict[str, Any],
        user
    ) -> Optional[Company]:
        """
        Update an existing company.

        Args:
            company_id: Company ID
            data: Updated fields
            user: Current user for audit trail

        Returns:
            Updated Company object or None if not found
        """
        try:
            # Get existing company (tenant-scoped)
            company = await self.get_by_id(Company, company_id)
            if not company:
                logger.warning("Company not found for update", company_id=company_id)
                return None

            # Check for duplicate domain if changing
            if 'domain' in data and data['domain'] != company.domain:
                existing = await self.get_company_by_domain(data['domain'])
                if existing and existing.id != company_id:
                    raise ValueError(f"Company with domain {data['domain']} already exists")

            # Update fields (only if provided in data)
            for field in [
                'name', 'domain', 'alternate_domains', 'industry', 'headquarters',
                'size', 'description', 'logo_url', 'linkedin_url', 'website_url',
                'market_size', 'product_breadth', 'innovation_score',
                'completeness_of_vision', 'ability_to_execute'
            ]:
                if field in data:
                    setattr(company, field, data[field])

            # Update audit fields
            if user:
                company.updated_by = user.id
                company.updated_by_name = user.name

            # Persist
            await self.db.flush()
            await self.db.refresh(company)

            # Log operation
            self.log_operation("company_update", {
                "company_id": company.id,
                "updated_fields": list(data.keys())
            })

            logger.info(
                "Company updated",
                company_id=company.id,
                fields_updated=list(data.keys()),
                tenant_id=self.tenant_id
            )

            return company

        except Exception as e:
            await self.handle_error("update_company", e, company_id=company_id)
            raise

    async def delete_company(self, company_id: str) -> bool:
        """
        Delete a company (and cascade to prospects).

        Args:
            company_id: Company ID

        Returns:
            True if deleted, False if not found
        """
        try:
            company = await self.get_by_id(Company, company_id)
            if not company:
                logger.warning("Company not found for deletion", company_id=company_id)
                return False

            # Delete (cascade will handle prospects and campaign links)
            await self.db.delete(company)
            await self.db.flush()

            # Log operation
            self.log_operation("company_deletion", {
                "company_id": company_id,
                "company_name": company.name
            })

            logger.info(
                "Company deleted",
                company_id=company_id,
                tenant_id=self.tenant_id
            )

            return True

        except Exception as e:
            await self.handle_error("delete_company", e, company_id=company_id)
            raise

    async def search_companies_by_name(
        self,
        name_query: str,
        limit: int = 20
    ) -> List[Company]:
        """
        Search companies by name (for autocomplete/typeahead).

        Args:
            name_query: Partial company name
            limit: Max results

        Returns:
            List of matching companies
        """
        try:
            stmt = (
                self.create_base_query(Company)
                .where(Company.name.ilike(f"%{name_query}%"))
                .order_by(Company.name.asc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            companies = list(result.scalars().all())

            logger.debug(
                "Company name search",
                query=name_query,
                results=len(companies)
            )

            return companies

        except Exception as e:
            await self.handle_error("search_companies_by_name", e, query=name_query)
            raise
