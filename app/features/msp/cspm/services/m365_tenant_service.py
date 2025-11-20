"""
M365 Tenant Service

Manages M365 tenant records and credentials for compliance scanning.
"""

# Use centralized imports for consistency
from app.features.core.sqlalchemy_imports import *
from app.features.core.enhanced_base_service import BaseService
from datetime import datetime
from uuid import uuid4

from app.features.msp.cspm.models import M365Tenant, CSPMTenantBenchmark, CSPMBenchmark
from app.features.msp.cspm.schemas import (
    M365TenantCreate,
    M365TenantUpdate,
    M365TenantResponse,
    M365TenantCredentials
)
from app.features.administration.secrets.services.crud_services import SecretsCrudService
from app.features.administration.secrets.schemas import SecretCreate, SecretUpdate, SecretType, SecretResponse
from app.features.msp.cspm.services.powershell_executor import PowerShellExecutorService
from app.features.core.audit_mixin import AuditContext
from app.features.administration.tenants.db_models import Tenant
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)


class M365TenantService(BaseService[M365Tenant]):
    """
    Service for managing M365 tenant records and credentials.

    Handles CRUD operations, credential storage/retrieval, and connection testing.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, tenant_id)
        self.secrets_service = SecretsCrudService(db_session, tenant_id)
        self.ps_executor = PowerShellExecutorService()

    async def _get_default_benchmark(self) -> CSPMBenchmark:
        stmt = select(CSPMBenchmark).where(CSPMBenchmark.tech_type == 'M365').order_by(desc(CSPMBenchmark.created_at)).limit(1)
        # Cross-tenant query - benchmarks are global resources
        result = await self.execute(
            stmt,
            CSPMBenchmark,
            allow_cross_tenant=True,
            reason="Default M365 benchmark lookup - benchmarks are global resources"
        )
        benchmark = result.scalar_one_or_none()
        if not benchmark:
            raise ValueError("No default benchmark configured for M365 assignments")
        return benchmark

    async def _get_or_create_tenant_benchmark(
        self,
        tenant_id: str,
        benchmark: CSPMBenchmark,
        display_name: str,
        created_by_user: Optional[Any]
    ) -> CSPMTenantBenchmark:
        stmt = select(CSPMTenantBenchmark).where(
            CSPMTenantBenchmark.tenant_id == tenant_id,
            CSPMTenantBenchmark.benchmark_id == benchmark.id
        ).limit(1)
        # Tenant-scoped query - assignments belong to platform tenant
        result = await self.execute(stmt, CSPMTenantBenchmark)
        assignment = result.scalar_one_or_none()

        timestamp = datetime.now()
        audit_ctx = AuditContext.from_user(created_by_user)

        if assignment:
            if assignment.status != "active":
                assignment.status = "active"
            assignment.display_name = display_name
            assignment.tech_type = benchmark.tech_type
            assignment.updated_at = timestamp
            assignment.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            return assignment

        assignment = CSPMTenantBenchmark(
            id=str(uuid4()),
            tenant_id=tenant_id,
            benchmark_id=benchmark.id,
            tech_type=benchmark.tech_type,
            display_name=display_name,
            status="active",
            config_json={}
        )
        assignment.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
        assignment.created_at = timestamp
        assignment.updated_at = timestamp
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    def _enrich_tenant_response(self, tenant: M365Tenant) -> M365TenantResponse:
        assignment = tenant.tenant_benchmark
        benchmark = assignment.benchmark if assignment else None

        setattr(tenant, "tenant_benchmark_display_name", assignment.display_name if assignment else None)
        setattr(tenant, "tenant_benchmark_status", assignment.status if assignment else None)
        setattr(tenant, "tech_type", assignment.tech_type if assignment else None)
        setattr(tenant, "benchmark_id", benchmark.id if benchmark else None)
        setattr(tenant, "benchmark_display_name", benchmark.display_name if benchmark else None)
        setattr(tenant, "benchmark_key", benchmark.benchmark_key if benchmark else None)

        return M365TenantResponse.model_validate(tenant)

    async def create_m365_tenant(
        self,
        tenant_data: M365TenantCreate,
        created_by_user: Optional[Any] = None,
        target_tenant_id: Optional[str] = None
    ) -> M365TenantResponse:
        """
        Create new M365 tenant record with credentials.

        Args:
            tenant_data: M365 tenant creation data
            created_by_user: User creating the tenant (for audit)
            target_tenant_id: Platform tenant that should own this record (global admin only)

        Returns:
            Created M365 tenant response

        Raises:
            ValueError: If M365 tenant already exists for this platform tenant
        """
        logger.info(
            "Creating M365 tenant",
            m365_tenant_id=tenant_data.m365_tenant_id,
            m365_tenant_name=tenant_data.m365_tenant_name
        )

        effective_tenant_id = target_tenant_id or self.tenant_id
        if not effective_tenant_id:
            raise ValueError("Target tenant is required to create an M365 tenant.")

        tenant_exists_stmt = select(func.count(Tenant.id)).where(
            cast(Tenant.id, String) == effective_tenant_id
        )
        # Cross-tenant query - global admin creating M365 tenant for any platform tenant
        tenant_exists = await self.execute(
            tenant_exists_stmt,
            Tenant,
            allow_cross_tenant=True,
            reason="Global admin M365 tenant creation - validating target platform tenant exists"
        )
        if (tenant_exists.scalar() or 0) == 0:
            raise ValueError("Selected tenant does not exist.")

        dup_stmt = select(func.count(M365Tenant.id)).where(
            M365Tenant.tenant_id == effective_tenant_id,
            M365Tenant.m365_tenant_id == tenant_data.m365_tenant_id
        )
        # Tenant-scoped or cross-tenant depending on global admin status
        duplicate_count = await self.execute(dup_stmt, M365Tenant)
        if (duplicate_count.scalar() or 0) > 0:
            raise ValueError(
                f"M365 tenant {tenant_data.m365_tenant_id} already exists for this platform tenant"
            )

        # Cross-tenant query - global admin needs to fetch any platform tenant details
        tenant_row = await self.execute(
            select(Tenant).where(cast(Tenant.id, String) == effective_tenant_id),
            Tenant,
            allow_cross_tenant=True,
            reason="Fetching platform tenant details for M365 tenant creation"
        )
        tenant_obj = tenant_row.scalar_one_or_none()
        if not tenant_obj:
            raise ValueError("Selected tenant does not exist.")

        tenant_display_name = tenant_obj.name or f"Tenant {effective_tenant_id}"
        display_name = tenant_data.m365_tenant_name or tenant_display_name

        benchmark = await self._get_default_benchmark()
        assignment = await self._get_or_create_tenant_benchmark(
            tenant_id=effective_tenant_id,
            benchmark=benchmark,
            display_name=display_name,
            created_by_user=created_by_user
        )

        audit_ctx = AuditContext.from_user(created_by_user)
        timestamp = datetime.now()

        # Create M365 tenant record linked to tenant benchmark
        m365_tenant = M365Tenant(
            tenant_id=effective_tenant_id,
            tenant_benchmark_id=assignment.id,
            m365_tenant_id=tenant_data.m365_tenant_id,
            m365_tenant_name=display_name,
            m365_domain=tenant_data.m365_domain,
            description=tenant_data.description,
            status="active",
        )

        m365_tenant.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
        m365_tenant.created_at = timestamp
        m365_tenant.updated_at = timestamp

        self.db.add(m365_tenant)
        await self.db.flush()
        # Refresh tenant with relationships
        await self.db.refresh(
            m365_tenant,
            attribute_names=["tenant_benchmark"]
        )

        # Update assignment config with reference to M365 tenant record
        assignment.config_json = assignment.config_json or {}
        assignment.config_json.update({
            "m365_tenant_record_id": m365_tenant.id,
            "m365_tenant_id": m365_tenant.m365_tenant_id,
            "m365_tenant_name": m365_tenant.m365_tenant_name,
            "target_identifier": m365_tenant.m365_tenant_id,
            "target_display_name": m365_tenant.m365_tenant_name
        })
        assignment.updated_at = datetime.now()
        assignment.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

        # Store credentials in tenant_secrets if provided
        await self._store_credentials(
            m365_tenant_id=m365_tenant.id,
            credentials=tenant_data.model_dump(),
            audit_user=created_by_user,
            target_tenant_id=effective_tenant_id
        )

        self.log_operation(
            "m365_tenant_creation",
            {
                "m365_tenant_id": m365_tenant.m365_tenant_id,
                "m365_tenant_name": m365_tenant.m365_tenant_name
            }
        )

        await self.db.flush()
        await self.db.refresh(m365_tenant, attribute_names=["tenant_benchmark"])
        if m365_tenant.tenant_benchmark:
            await self.db.refresh(m365_tenant.tenant_benchmark, attribute_names=["benchmark"])

        return self._enrich_tenant_response(m365_tenant)

    async def update_m365_tenant(
        self,
        m365_tenant_id: str,
        tenant_data: M365TenantUpdate,
        updated_by_user: Optional[Any] = None
    ) -> M365TenantResponse:
        """
        Update M365 tenant record and optionally update credentials.

        Args:
            m365_tenant_id: ID of M365 tenant to update
            tenant_data: Update data
            updated_by_user: User updating the tenant (for audit)

        Returns:
            Updated M365 tenant response

        Raises:
            ValueError: If M365 tenant not found
        """
        logger.info("Updating M365 tenant", m365_tenant_id=m365_tenant_id)

        # Get existing tenant with assignment
        stmt = (
            self.create_base_query(M365Tenant)
            .options(
                selectinload(M365Tenant.tenant_benchmark)
                .selectinload(CSPMTenantBenchmark.benchmark)
            )
            .where(M365Tenant.id == m365_tenant_id)
            .limit(1)
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, M365Tenant)
        m365_tenant = result.scalar_one_or_none()
        if not m365_tenant:
            raise ValueError(f"M365 tenant {m365_tenant_id} not found")

        # Update fields
        if tenant_data.m365_domain is not None:
            m365_tenant.m365_domain = tenant_data.m365_domain
        if tenant_data.description is not None:
            m365_tenant.description = tenant_data.description
        if tenant_data.status is not None:
            m365_tenant.status = tenant_data.status

        assignment = None
        if m365_tenant.tenant_benchmark_id:
            # Tenant-scoped query - assignment belongs to same tenant as M365Tenant
            assignment_result = await self.execute(
                select(CSPMTenantBenchmark)
                .where(CSPMTenantBenchmark.id == m365_tenant.tenant_benchmark_id)
                .limit(1),
                CSPMTenantBenchmark
            )
            assignment = assignment_result.scalar_one_or_none()

        audit_ctx = AuditContext.from_user(updated_by_user)
        m365_tenant.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
        m365_tenant.updated_at = datetime.now()

        if assignment:
            if tenant_data.status is not None:
                assignment.status = tenant_data.status
            if tenant_data.description is not None:
                assignment.display_name = assignment.display_name or m365_tenant.m365_tenant_name
            assignment.updated_at = datetime.now()
            assignment.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

        # Update credentials if provided
        credentials = tenant_data.model_dump(exclude_unset=True)
        if any(key in credentials for key in ["client_id", "client_secret", "certificate_thumbprint", "username", "password"]):
            await self._store_credentials(
                m365_tenant_id=m365_tenant.id,
                credentials=credentials,
                audit_user=updated_by_user,
                target_tenant_id=m365_tenant.tenant_id
            )

        await self.db.flush()
        await self.db.refresh(m365_tenant, attribute_names=["tenant_benchmark"])
        if m365_tenant.tenant_benchmark:
            await self.db.refresh(m365_tenant.tenant_benchmark, attribute_names=["benchmark"])

        self.log_operation("m365_tenant_update", {"m365_tenant_id": m365_tenant_id})

        return self._enrich_tenant_response(m365_tenant)

    async def delete_m365_tenant(self, m365_tenant_id: str) -> bool:
        """
        Delete M365 tenant and associated credentials.

        Args:
            m365_tenant_id: ID of M365 tenant to delete

        Returns:
            True if deleted

        Raises:
            ValueError: If M365 tenant not found
        """
        logger.info("Deleting M365 tenant", m365_tenant_id=m365_tenant_id)

        stmt = (
            self.create_base_query(M365Tenant)
            .options(selectinload(M365Tenant.tenant_benchmark))
            .where(M365Tenant.id == m365_tenant_id)
            .limit(1)
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, M365Tenant)
        m365_tenant = result.scalar_one_or_none()
        if not m365_tenant:
            raise ValueError(f"M365 tenant {m365_tenant_id} not found")

        # Delete associated credentials
        await self._delete_credentials(m365_tenant_id)

        # Delete tenant record
        assignment_id = m365_tenant.tenant_benchmark_id
        await self.db.delete(m365_tenant)
        await self.db.flush()

        if assignment_id:
            # Tenant-scoped query - assignment belongs to same tenant
            assignment_result = await self.execute(
                select(CSPMTenantBenchmark).where(CSPMTenantBenchmark.id == assignment_id).limit(1),
                CSPMTenantBenchmark
            )
            assignment = assignment_result.scalar_one_or_none()
            if assignment:
                assignment.status = "inactive"
                assignment.config_json = assignment.config_json or {}
                if "target_identifier" not in assignment.config_json and assignment.config_json.get("m365_tenant_id"):
                    assignment.config_json["target_identifier"] = assignment.config_json["m365_tenant_id"]
                if "target_display_name" not in assignment.config_json and assignment.config_json.get("m365_tenant_name"):
                    assignment.config_json["target_display_name"] = assignment.config_json["m365_tenant_name"]
                audit_ctx = AuditContext.system()
                assignment.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
                assignment.updated_at = datetime.now()

        await self.db.flush()

        self.log_operation("m365_tenant_deletion", {"m365_tenant_id": m365_tenant_id})

        return True

    async def list_m365_tenants(self) -> List[M365TenantResponse]:
        """
        List all M365 tenants for the current platform tenant.

        Returns:
            List of M365 tenant responses
        """
        logger.debug("Listing M365 tenants")

        stmt = (
            self.create_base_query(M365Tenant)
            .options(
                selectinload(M365Tenant.tenant_benchmark)
                .selectinload(CSPMTenantBenchmark.benchmark)
            )
            .order_by(desc(M365Tenant.created_at))
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, M365Tenant)
        tenants = result.scalars().all()

        return [self._enrich_tenant_response(t) for t in tenants]

    async def get_m365_tenant(self, m365_tenant_id: str) -> Optional[M365TenantResponse]:
        """
        Get M365 tenant by ID.

        Args:
            m365_tenant_id: ID of M365 tenant

        Returns:
            M365 tenant response or None
        """
        stmt = (
            self.create_base_query(M365Tenant)
            .options(
                selectinload(M365Tenant.tenant_benchmark)
                .selectinload(CSPMTenantBenchmark.benchmark)
            )
            .where(M365Tenant.id == m365_tenant_id)
            .limit(1)
        )
        # Tenant-scoped query via create_base_query()
        result = await self.execute(stmt, M365Tenant)
        tenant = result.scalar_one_or_none()
        return self._enrich_tenant_response(tenant) if tenant else None

    async def get_tenant_credentials(self, m365_tenant_id: str) -> Dict[str, str]:
        """
        Retrieve decrypted M365 credentials for scanning.

        Args:
            m365_tenant_id: ID of M365 tenant

        Returns:
            Dictionary with auth parameters for PowerShell
            Format: {TenantId, ClientId, ClientSecret, CertificateThumbprint, Username, Password}

        Raises:
            ValueError: If M365 tenant not found or credentials missing
        """
        logger.info("Retrieving M365 credentials", m365_tenant_id=m365_tenant_id)

        # Get M365 tenant
        m365_tenant = await self.get_by_id(M365Tenant, m365_tenant_id)
        if not m365_tenant:
            raise ValueError(f"M365 tenant {m365_tenant_id} not found")

        # Build auth params dict
        auth_params = {
            "TenantId": m365_tenant.m365_tenant_id
        }

        # Add TenantDomain - extract from m365_domain or construct from tenant_id
        if m365_tenant.m365_domain:
            # If domain is like "contoso.onmicrosoft.com", use it directly
            # If it's a custom domain like "contoso.com", we still need the .onmicrosoft.com domain for some services
            if ".onmicrosoft.com" in m365_tenant.m365_domain:
                auth_params["TenantDomain"] = m365_tenant.m365_domain
            else:
                # Custom domain provided - try to construct .onmicrosoft.com domain
                # For now, use the custom domain and let PowerShell handle it
                auth_params["TenantDomain"] = m365_tenant.m365_domain
        else:
            # No domain stored - this might cause issues, but let PowerShell try to resolve it
            logger.warning("M365 tenant domain not configured", m365_tenant_id=m365_tenant_id)

        # Add SharePointAdminUrl - TEMPORARILY HARDCODED
        # TODO: SharePoint URL construction is unreliable (domain doesn't match actual URL)
        # Example: Domain "terrait.co.uk" but URL is "https://netorgft16254533-admin.sharepoint.com/"
        # For now, use hardcoded URL for testing - will implement proper solution later
        # (either manual field in M365Tenant model or API lookup)

        # TEMPORARY: Hardcoded SharePoint Admin URL for testing
        auth_params["SharePointAdminUrl"] = "https://netorgft16254533-admin.sharepoint.com"

        logger.info("Using hardcoded SharePoint Admin URL for testing",
                    m365_tenant_id=m365_tenant_id,
                    sharepoint_url=auth_params["SharePointAdminUrl"])

        # Retrieve credentials from secrets
        secret_prefix = f"m365_{m365_tenant.id}"
        client_id = await self._fetch_secret_value(
            f"{secret_prefix}_client_id",
            m365_tenant.tenant_id
        )
        if client_id:
            auth_params["ClientId"] = client_id

        client_secret = await self._fetch_secret_value(
            f"{secret_prefix}_client_secret",
            m365_tenant.tenant_id
        )
        if client_secret:
            auth_params["ClientSecret"] = client_secret

        cert_thumbprint = await self._fetch_secret_value(
            f"{secret_prefix}_certificate_thumbprint",
            m365_tenant.tenant_id
        )
        if cert_thumbprint:
            auth_params["CertificateThumbprint"] = cert_thumbprint

        # Retrieve certificate PFX (base64 encoded) and password for Linux/file-based auth
        cert_pfx_base64 = await self._fetch_secret_value(
            f"{secret_prefix}_certificate_pfx",
            m365_tenant.tenant_id
        )
        if cert_pfx_base64:
            auth_params["CertificatePfxBase64"] = cert_pfx_base64

        cert_password = await self._fetch_secret_value(
            f"{secret_prefix}_certificate_password",
            m365_tenant.tenant_id
        )
        if cert_password:
            auth_params["CertificatePassword"] = cert_password

        username = await self._fetch_secret_value(
            f"{secret_prefix}_username",
            m365_tenant.tenant_id
        )
        if username:
            auth_params["Username"] = username

        password = await self._fetch_secret_value(
            f"{secret_prefix}_password",
            m365_tenant.tenant_id
        )
        if password:
            auth_params["Password"] = password

        # Validate that we have at least one authentication method
        has_app_auth = "ClientId" in auth_params and ("ClientSecret" in auth_params or "CertificateThumbprint" in auth_params)
        has_user_auth = "Username" in auth_params and "Password" in auth_params

        if not (has_app_auth or has_user_auth):
            raise ValueError(
                f"M365 tenant {m365_tenant_id} has incomplete credentials. "
                "Need either (ClientId + ClientSecret/Certificate) or (Username + Password)"
            )

        logger.debug("Credentials retrieved", m365_tenant_id=m365_tenant_id, auth_methods=list(auth_params.keys()))

        return auth_params

    async def get_tenant_credentials_info(self, m365_tenant_id: str) -> M365TenantCredentials:
        """
        Get information about configured credentials (without revealing secrets).

        Args:
            m365_tenant_id: ID of M365 tenant

        Returns:
            Credentials info with masked values
        """
        m365_tenant = await self.get_by_id(M365Tenant, m365_tenant_id)
        if not m365_tenant:
            raise ValueError(f"M365 tenant {m365_tenant_id} not found")

        secret_prefix = f"m365_{m365_tenant.id}"
        client_id = await self._fetch_secret_value(
            f"{secret_prefix}_client_id",
            m365_tenant.tenant_id
        )
        client_secret = await self._fetch_secret_value(
            f"{secret_prefix}_client_secret",
            m365_tenant.tenant_id
        )
        cert_thumbprint = await self._fetch_secret_value(
            f"{secret_prefix}_certificate_thumbprint",
            m365_tenant.tenant_id
        )
        username = await self._fetch_secret_value(
            f"{secret_prefix}_username",
            m365_tenant.tenant_id
        )
        password = await self._fetch_secret_value(
            f"{secret_prefix}_password",
            m365_tenant.tenant_id
        )

        return M365TenantCredentials(
            has_client_secret=bool(client_secret),
            has_certificate=bool(cert_thumbprint),
            has_username_password=bool(username and password),
            client_id=client_id,
            certificate_thumbprint=cert_thumbprint,
            username=username
        )

    async def test_connection(self, m365_tenant_id: str) -> Dict[str, Any]:
        """
        Test M365 connection with stored credentials.

        Args:
            m365_tenant_id: ID of M365 tenant

        Returns:
            Test result with success/failure status

        Raises:
            ValueError: If M365 tenant not found or credentials incomplete
        """
        logger.info("Testing M365 connection", m365_tenant_id=m365_tenant_id)

        # Get credentials
        auth_params = await self.get_tenant_credentials(m365_tenant_id)

        # Execute connection test
        test_result = await self.ps_executor.test_m365_connection(auth_params)

        # Update M365 tenant with test results
        m365_tenant = await self.get_by_id(M365Tenant, m365_tenant_id)
        if m365_tenant:
            m365_tenant.last_test_at = test_result["tested_at"]
            m365_tenant.last_test_status = "success" if test_result["success"] else "failed"
            m365_tenant.last_test_error = None if test_result["success"] else test_result["message"]
            await self.db.flush()

        self.log_operation(
            "m365_connection_test",
            {
                "m365_tenant_id": m365_tenant_id,
                "success": test_result["success"]
            }
        )

        return test_result

    async def _store_credentials(
        self,
        m365_tenant_id: str,
        credentials: Dict[str, Any],
        audit_user: Optional[Any] = None,
        target_tenant_id: Optional[str] = None
    ) -> None:
        """
        Store M365 credentials in tenant_secrets.

        Args:
            m365_tenant_id: ID of M365 tenant record
            credentials: Dictionary with credential fields
            audit_user: User object or dict with audit fields
            target_tenant_id: Tenant that owns the credentials
        """
        secret_prefix = f"m365_{m365_tenant_id}"

        # Map of credential fields to secret types
        credential_mapping = {
            "client_id": ("client_id", SecretType.API_KEY),
            "client_secret": ("client_secret", SecretType.ACCESS_TOKEN),
            "certificate_thumbprint": ("certificate_thumbprint", SecretType.ENCRYPTION_KEY),
            "certificate_pfx": ("certificate_pfx", SecretType.ENCRYPTION_KEY),
            "certificate_password": ("certificate_password", SecretType.OTHER),
            "username": ("username", SecretType.OTHER),
            "password": ("password", SecretType.OTHER)
        }

        target_tenant_id = target_tenant_id or self.tenant_id
        if not target_tenant_id:
            raise ValueError("Target tenant is required to store credentials.")

        for field, (suffix, secret_type) in credential_mapping.items():
            if field in credentials and credentials[field]:
                secret_name = f"{secret_prefix}_{suffix}"

                # Create or update secret
                secret_data = SecretCreate(
                    name=secret_name,
                    secret_type=secret_type,
                    value=str(credentials[field]),
                    description=f"M365 {suffix} for tenant {m365_tenant_id}"
                )

                try:
                    await self.secrets_service.create_secret(
                        secret_data,
                        created_by_user=audit_user,
                        target_tenant_id=target_tenant_id
                    )
                except Exception:
                    target_service = SecretsCrudService(self.db, target_tenant_id)
                    existing_secret = await target_service.get_secret_by_name(secret_name)
                    if existing_secret:
                        await target_service.update_secret(
                            existing_secret.id,
                            SecretUpdate(value=str(credentials[field])),
                            updated_by_user=audit_user
                        )
                    else:
                        await target_service.create_secret(
                            secret_data,
                            created_by_user=audit_user,
                            target_tenant_id=target_tenant_id
                        )

        logger.debug("Credentials stored", m365_tenant_id=m365_tenant_id)

    async def _delete_credentials(self, m365_tenant_id: str) -> None:
        """
        Delete all credentials for M365 tenant.

        Args:
            m365_tenant_id: ID of M365 tenant record
        """
        secret_prefix = f"m365_{m365_tenant_id}"

        secret_suffixes = [
            "client_id",
            "client_secret",
            "certificate_thumbprint",
            "certificate_pfx",
            "certificate_password",
            "username",
            "password"
        ]

        for suffix in secret_suffixes:
            secret_name = f"{secret_prefix}_{suffix}"
            try:
                await self.secrets_service.delete_secret(secret_name)
            except Exception:
                # Ignore if secret doesn't exist
                pass

        logger.debug("Credentials deleted", m365_tenant_id=m365_tenant_id)

    async def _fetch_secret_value(
        self,
        secret_name: str,
        target_tenant_id: Optional[str]
    ) -> Optional[str]:
        effective_tenant = target_tenant_id or self.tenant_id
        if not effective_tenant:
            return None

        target_service = SecretsCrudService(self.db, effective_tenant)
        secret_meta: Optional[SecretResponse] = await target_service.get_secret_by_name(secret_name)
        if not secret_meta:
            return None

        secret_value = await target_service.get_secret_value(secret_meta.id, accessed_by_user=None)
        return secret_value.value if secret_value else None

    async def get_available_tenants_for_forms(self) -> List[Dict[str, Any]]:
        """
        Retrieve active tenants for global admin dropdowns.

        Returns:
            List of dictionaries containing tenant id and name.
        """
        try:
            stmt = select(
                Tenant.id,
                Tenant.name
            ).where(
                Tenant.status == 'active'
            ).order_by(Tenant.name)

            # Cross-tenant query - global admins need to see all platform tenants for dropdown
            result = await self.execute(
                stmt,
                Tenant,
                allow_cross_tenant=True,
                reason="Global admin form dropdown - listing all active platform tenants"
            )
            tenants = result.fetchall()

            tenant_list = [
                {"id": str(row.id), "name": row.name}
                for row in tenants
            ]

            self.log_operation("get_available_tenants_for_forms", {
                "tenant_count": len(tenant_list)
            })

            return tenant_list
        except Exception as e:
            await self.handle_error("get_available_tenants_for_forms", e)
