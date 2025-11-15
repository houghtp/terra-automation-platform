# 🚀 TerraAutomationPlatform

A comprehensive, production-ready **Multi-Tenant SaaS Platform** built with **FastAPI**, **Vertical Slice Architecture**, **HTMX**, and **Tabler Admin Dashboard**.

**Purpose**: Enterprise-grade automation platform for MSPs, content teams, and business operations with robust tenant isolation, AI-powered features, and multi-channel integrations.

## ✨ Platform Highlights

- 🏢 **Multi-Tenant Architecture** - Complete tenant isolation with global admin capabilities
- 🤖 **AI-Powered Content** - AI research, generation, and SEO optimization
- 🔐 **Enterprise Security** - CSP-compliant, secrets management, audit logging
- 🔌 **Multi-Channel Publishing** - WordPress, LinkedIn, Twitter/X integration
- 📊 **MSP Tools** - CSPM compliance scanning, M365 security benchmarks
- 👥 **Community Platform** - Member management, groups, events (Radium)
- 🎨 **Modern UI** - Tabler v1.0.0-beta20, HTMX, Tabulator tables
- 🐳 **Production Ready** - Docker, monitoring, structured logging, CI/CD compliance

## 🏗️ Project Structure

## 🏗️ Architecture

### Vertical Slice Architecture

Each feature module is a **complete vertical slice** owning its entire stack:

```
app/features/
├── administration/          # Platform administration
│   ├── users/              # User management
│   ├── tenants/            # Tenant management (global admin only)
│   ├── audit/              # Audit log viewer
│   ├── logs/               # Application log viewer
│   ├── secrets/            # Secrets management (encrypted)
│   ├── smtp/               # SMTP configuration
│   ├── ai_prompts/         # AI prompt templates
│   └── api_keys/           # API key management
├── auth/                    # Authentication & authorization
│   ├── models/             # User, session models
│   ├── services/           # Auth, JWT services
│   └── routes/             # Login, logout, registration
├── business_automations/    # Business automation features
│   └── content_broadcaster/ # AI content generation & publishing
│       ├── models/         # Content, jobs, deliveries
│       ├── services/       # Planning, AI generation, publishing
│       ├── routes/         # API + HTMX endpoints
│       ├── templates/      # UI views
│       └── static/         # JS tables, CSS
├── community/               # Radium community platform
│   ├── models/             # Members, posts, groups, events
│   ├── services/           # Community management
│   └── routes/             # Community endpoints
├── connectors/              # Multi-channel integrations
│   └── connectors/
│       ├── models/         # Connector configurations
│       ├── services/       # OAuth, API integrations
│       └── adapters/       # Platform-specific adapters
├── msp/                     # MSP tools & services
│   └── cspm/               # Cloud Security Posture Management
│       ├── models/         # Scans, benchmarks, results
│       ├── services/       # M365 CIS compliance
│       └── routes/         # CSPM dashboard & API
└── core/                    # Shared infrastructure
    ├── base_service.py     # Service base class
    ├── database.py         # DB configuration
    ├── route_imports.py    # Centralized route utilities
    ├── service_imports.py  # Centralized service utilities
    └── bootstrap.py        # Global admin bootstrap
```

### Multi-Tenancy

**3-Layer Tenant Isolation:**

1. **Middleware Layer** (`app/middleware/tenant.py`)
   - Extracts `tenant_id` from JWT, headers, or subdomain
   - Stores in `ContextVar` for request-scoped logging

2. **Dependency Layer** (`app/deps/tenant.py`)
   - Validates `tenant_id` from JWT claims
   - Returns validated tenant or `"global"` for global admins
   - Checks header/token consistency

3. **Service Layer** (`BaseService`)
   - Automatically filters queries by `tenant_id`
   - Converts `tenant_id="global"` → `None` (global admins see all)
   - Enforces tenant isolation at database level

**Global Admin Pattern:**
- `tenant_id = "global"` in JWT and database
- `role = "global_admin"`
- Can manage all tenants, create users across tenants
- Helper: `is_global_admin(user)` from `route_imports`

## 📦 Core Features

### 🔐 Administration

#### **User Management** (`/features/administration/users`)
- Multi-tenant user CRUD
- Role-based access control (user, admin, global_admin)
- Global admins can create users in any tenant
- Password management, account activation
- User activity tracking

#### **Tenant Management** (`/features/administration/tenants`) 🌐
- Create and manage tenant organizations
- **Global admin only** - protected with `get_global_admin_user`
- Tenant metadata, configuration, status
- User assignment per tenant
- Tenant-level settings and quotas

#### **Audit Logs** (`/features/administration/audit`)
- Comprehensive audit trail for all actions
- Tracks: user, action, resource, changes, timestamp
- Tenant-isolated audit records
- Advanced filtering and search
- Export capabilities

#### **Application Logs** (`/features/administration/logs`)
- Structured JSON logging with `structlog`
- Request correlation IDs
- Tenant context in every log
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Real-time log viewer with filtering

#### **Secrets Management** (`/features/administration/secrets`)
- Encrypted secret storage (Fernet encryption)
- Secret types: API keys, passwords, tokens, certificates
- Tenant-isolated secrets
- Audit trail for secret access
- Used by: AI services, connectors, SMTP

#### **SMTP Configuration** (`/features/administration/smtp`)
- Per-tenant email server configuration
- Test email functionality
- Encrypted credential storage
- Email templates and settings

#### **AI Prompts** (`/features/administration/ai_prompts`)
- Centralized AI prompt templates
- Versioned prompts for content generation
- Prompt variables and templates
- Usage tracking per prompt

#### **API Keys** (`/features/administration/api_keys`)
- Generate and manage API keys
- Rate limiting per key
- Usage tracking and quotas
- Revocation and expiration

### 🤖 Business Automations

#### **Content Broadcaster** (`/features/content-broadcaster`) ⭐

**AI-Powered Content Planning, Generation & Multi-Channel Publishing**

**Workflow:**
```
Content Plan → AI Research → AI Generation → SEO Optimization →
Human Review → Approval → Multi-Channel Scheduling → Publishing → Engagement Tracking
```

**Features:**
- 📝 **Content Planning**: Create content ideas with target channels, audience, tone
- 🔬 **AI Research**: Google search, competitor analysis, web scraping (SerpAPI)
- 🤖 **AI Generation**: OpenAI-powered content creation with SEO optimization
- ✅ **SEO Validation**: Iterative refinement until SEO score ≥ threshold
- 👤 **Humanization**: De-AI patterns, tone adjustment, readability
- 📊 **Approval Workflow**: Submit → Review → Approve/Reject → Publish
- ⏰ **Scheduling**: Schedule content for future publishing
- 🔌 **Multi-Channel**: Publish to WordPress, LinkedIn, Twitter, Medium
- 📈 **Engagement**: Track views, clicks, shares per platform
- 💾 **Versioning**: All drafts, research, iterations saved to disk

**API Endpoints:**
- `POST /planning/create` - Create content plan
- `POST /planning/{id}/process` - AI research + generation
- `GET /api/{id}` - Get generated content
- `POST /api/{id}/submit` - Submit for approval
- `POST /api/{id}/approve` - Approve content
- `POST /api/{id}/schedule` - Schedule publishing
- `GET /api/jobs` - List publish jobs
- `GET /api/summary` - Dashboard statistics

**Services:**
- `ContentPlanningService` - Manage content ideas
- `AIResearchService` - Competitor analysis, web scraping
- `AIGenerationService` - OpenAI content generation
- `AIValidationService` - SEO scoring, refinement feedback
- `AIRefinementService` - Humanization, de-AI
- `ContentBroadcasterService` - Content lifecycle
- `ApprovalService` - Review workflows
- `ScheduleService` - Job scheduling
- `PublishService` - Connector integration
- `EngagementService` - Metrics tracking

**Models:**
- `ContentPlan` - Content ideas (planning stage)
- `ContentItem` - Generated content (draft → published)
- `ContentVariant` - Platform-specific variants
- `PublishJob` - Scheduled publishing tasks
- `Delivery` - Published content tracking
- `EngagementSnapshot` - Metrics snapshots

**Status:** ✅ Core implemented, ⏸️ Workers pending

### 🔌 Connectors

#### **Multi-Platform Integrations** (`/features/connectors/connectors`)

**Supported Platforms:**
- **WordPress** - Basic Auth, REST API publishing
- **LinkedIn** - OAuth 2.0, personal + company pages
- **Twitter/X** - OAuth 1.0a, tweet publishing
- **Medium** - API key, story publishing

**Features:**
- 🔐 OAuth flow handling (authorization + callback)
- 🔑 Encrypted credential storage
- ✅ Connection testing
- 📊 Connector catalog with capabilities
- 🔌 Pluggable adapter pattern
- 🔄 Automatic token refresh
- 📝 Usage logging

**Connector States:**
- `not_installed` - Available in catalog
- `installed` - Configured but not authenticated
- `active` - Authenticated and ready
- `error` - Authentication failed

**Models:**
- `ConnectorInstallation` - User's connector config
- `ConnectorCatalog` - Available connectors
- `ConnectorOAuthState` - OAuth flow state

**Services:**
- `ConnectorService` - Installation, configuration
- `ConnectorAdapter` - Base adapter class
- Platform-specific adapters (WordPress, LinkedIn, etc.)

### 🛡️ MSP Tools

#### **CSPM - Cloud Security Posture Management** (`/features/msp/cspm`)

**M365 CIS Benchmark Compliance Scanning**

**Features:**
- 🔍 **Compliance Scans**: CIS Microsoft 365 Foundations v5.0.0
- 📊 **Multi-Tenant M365**: Manage multiple M365 tenants
- ✅ **Benchmark Results**: Pass/Fail/Manual/NotApplicable
- 📈 **Dashboard**: Compliance score, trending, exceptions
- 🔧 **Remediation**: Guidance for failed controls
- 📅 **Scheduled Scans**: Recurring compliance checks
- 📤 **Export**: PDF reports, CSV exports
- 🔔 **Webhooks**: Scan completion notifications

**Scan Workflow:**
```
Create M365 Tenant → Configure Credentials → Run Scan →
Review Results → Remediate Failures → Re-scan → Track Progress
```

**Models:**
- `M365Tenant` - M365 tenant configurations
- `CSPMBenchmark` - Benchmark definitions (CIS v5.0.0)
- `ComplianceScan` - Scan executions
- `ComplianceResult` - Individual control results
- `TenantBenchmark` - Tenant-specific benchmark configs

**Services:**
- `M365TenantService` - M365 tenant management
- `CSPMScanService` - Scan execution
- `BenchmarkService` - Benchmark configuration
- `ResultService` - Result analysis

**PowerShell Integration:**
- Microsoft.Graph (Entra ID, Users, Groups)
- Microsoft.Graph.Beta (Preview APIs)
- ExchangeOnlineManagement (Mailbox security)
- MicrosoftTeams (Teams policies)
- PnP.PowerShell (SharePoint)
- MicrosoftPowerBIMgmt (Power BI/Fabric)

**Status:** ⚡ Active development

### 👥 Community Platform

#### **Radium Community** (`/features/community`) 🌟

**Professional Community for Financial Advisors**

**Phases:**
1. **Foundation** - Members, partners, profiles
2. **Networking** - Groups, messaging, events
3. **Content** - Articles, podcasts, videos, news
4. **Opportunities** - Jobs, succession planning
5. **Tools** - Calculators, resources, reviews
6. **Engagement** - Gamification, rewards
7. **Premium** - Paid features, mentorship

**Models:**
- `Member` - Community members
- `Partner` - Service providers
- `Group` - Discussion groups
- `Event` - Calendar events
- `Content` - Articles, resources
- `Job` - Career opportunities

**Status:** 📋 Planned (PRD complete)

## 🔧 Development

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Docker & Docker Compose
- PowerShell 7+ (for CSPM features)

### Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd terra-automation-platform

# 2. Setup environment
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, etc.

# 3. Start database
make db-start  # or: docker compose up -d postgres

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run migrations
make db-migrate  # or: alembic upgrade head

# 6. Create global admin
python scripts/manage_global_admin.py create admin@example.com --password <password>

# 7. Seed demo data (optional)
python app/seed_data.py

# 8. Start server
make dev-server  # or: uvicorn app.main:app --reload
```

**Access:**
- Web App: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Admin Login: admin@example.com

### Creating New Feature Slices

```bash
# Use the slice creation script
python scripts/create_slice.py my_feature

# This creates:
app/features/my_feature/
├── __init__.py
├── models.py                   # SQLAlchemy models
├── services.py                 # Business logic
├── routes/
│   ├── __init__.py
│   ├── crud_routes.py         # API endpoints
│   └── form_routes.py         # HTMX/UI routes
├── templates/
│   └── my_feature/
│       ├── dashboard.html
│       └── partials/
├── static/
│   └── js/
│       └── my-feature-table.js
└── tests/
    ├── test_models.py
    ├── test_services.py
    └── test_routes.py
```

### Architectural Patterns

#### ✅ Service Pattern (Gold Standard)
```python
from app.features.core.service_imports import *

class MyFeatureService(BaseService[MyModel]):
    """Service for managing my feature with tenant isolation."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db_session, MyModel, tenant_id)
        self.logger = structlog.get_logger(__name__)

    async def get_items(self, limit: int = 100) -> List[MyModel]:
        """Get items with automatic tenant filtering."""
        stmt = select(MyModel).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
```

#### ✅ Route Pattern (Gold Standard)
```python
from app.features.core.route_imports import *

router = APIRouter(tags=["my-feature"])

@router.get("/api/list")
async def get_items_list(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(tenant_dependency),
    service: MyFeatureService = Depends(get_service)
):
    """List items - returns simple array for Tabulator."""
    items = await service.get_items()
    return [item.to_dict() for item in items]  # Simple array, not wrapped!

@router.get("/partials/item_details")
async def get_item_details(
    request: Request,
    item_id: int,
    service: MyFeatureService = Depends(get_service)
):
    """HTMX partial for modal."""
    item = await service.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return templates.TemplateResponse(
        "my_feature/partials/item_details.html",
        {"request": request, "item": item}
    )
```

#### ✅ Tabulator Table Pattern
```javascript
window.initializeMyFeatureTable = function () {
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#my-feature-table", {
        ...advancedTableConfig,  // MANDATORY: Centralized config
        ajaxURL: "/features/my-feature/api/list",
        columns: [
            {
                title: "Name",
                field: "name",
                minWidth: 150,  // Use minWidth for flexible columns
                headerFilter: "input"
            },
            {
                title: "Status",
                field: "status",
                width: 100,  // Fixed width for predictable content
                headerFilter: "list"
            },
            {
                title: "Actions",
                field: "id",
                width: 80,
                headerSort: false,
                formatter: (cell) => formatViewAction(cell, 'viewItemDetails')
            }
        ]
    });

    // MANDATORY: Global registry
    window.myFeatureTable = table;
    window.appTables["my-feature-table"] = table;

    return table;
};

// MANDATORY: Standard export function
window.exportTable = function (format) {
    return exportTabulatorTable('my-feature-table', format, 'my_feature_items');
};

// Standard initialization
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("my-feature-table");
    if (tableElement && !window.myFeatureTableInitialized) {
        window.myFeatureTableInitialized = true;
        initializeMyFeatureTable();

        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'my-feature-table');
        }, 100);
    }
});
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add my_feature table"

# Review generated migration
# Edit migrations/versions/<hash>_add_my_feature_table.py

# Apply migration
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See current version
alembic current
```

## 🧪 Testing & Compliance

### Compliance Tests (Architectural Linting)

**Automated compliance tests** ensure consistent patterns across all feature slices:

```bash
# Run all compliance checks
make all-compliance-checks

# Individual compliance tests
make compliance-check                # Tenant CRUD patterns
make logging-compliance-check        # Structured logging
make route-structure-compliance      # Route organization, Tabulator
make global-admin-compliance         # Global admin security
```

**Test Suites:**

1. **Tenant CRUD Compliance** - Tenant isolation, BaseService inheritance
2. **Logging Compliance** - Structured logging with `structlog`
3. **Route Structure Compliance** - crud_routes vs form_routes, API format
4. **Global Admin Compliance** - Security patterns, authorization
5. **Service Imports Compliance** - Centralized imports from `service_imports`
6. **Route Imports Compliance** - Centralized imports from `route_imports`

See [`tests/compliance/README.md`](tests/compliance/README.md) for details.

### Unit & Integration Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/integration/test_tenant_isolation.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Test categories
make test-unit           # Unit tests only
make test-integration    # Integration tests only
make test-ui            # Playwright UI tests
```

## 🔐 Security

### Multi-Tenant Isolation
- **Database Level**: All queries filtered by `tenant_id`
- **Service Level**: `BaseService` enforces tenant context
- **Middleware**: Request-scoped tenant extraction
- **Global Admin**: Special `tenant_id="global"` with override capability

### Secrets Management
- **Encryption**: Fernet symmetric encryption
- **Storage**: PostgreSQL with encrypted values
- **Access**: Secrets fetched at runtime, never cached
- **Audit**: All secret access logged

### Authentication & Authorization
- **JWT Tokens**: HS256 signed, tenant_id in claims
- **Role Hierarchy**: user → admin → global_admin
- **Dependencies**: `get_current_user`, `get_admin_user`, `get_global_admin_user`
- **RBAC**: Role-based access control per feature

### CSP Compliance
- ✅ No inline `<script>` or `<style>` tags
- ✅ All JavaScript in external files
- ✅ All CSS in external files or classes
- ✅ HTMX for dynamic behavior (CSP-safe)

## 📊 Monitoring & Observability

### Structured Logging
```python
import structlog

logger = structlog.get_logger(__name__)

# Context automatically includes: tenant_id, request_id, user_id
logger.info("content_created", content_id=content_id, state="draft")
logger.error("publish_failed", job_id=job_id, connector="wordpress", error=str(e))
```

### Metrics (Prometheus)
- Request duration, error rates
- Database query performance
- Background job success/failure
- Tenant-specific metrics

### Tracing
- Request correlation IDs
- Tenant context in all logs
- Full audit trail for compliance

## 📚 Documentation

Comprehensive documentation in [`docs/`](docs/):

- **[Index](docs/INDEX.md)** - Documentation overview
- **[Template Usage](docs/TEMPLATE_USAGE.md)** - Using this as a template
- **[Production Deployment](docs/PRODUCTION.md)** - Production setup
- **[Global Admin System](docs/global_admin.md)** - Global admin patterns
- **[Tenant CRUD Standards](docs/tenant-crud.md)** - Multi-tenancy patterns
- **[Logging Standards](docs/logging-standards.md)** - Structured logging
- **[Monitoring Guide](docs/MONITORING_COMPLETE.md)** - Observability
- **[Slice Creation Guide](docs/slice_creation_guide.md)** - Creating features

### Feature Documentation

- **Content Broadcaster**: [`app/features/business_automations/content_broadcaster/README.md`](app/features/business_automations/content_broadcaster/README.md)
- **Connectors**: [`app/features/connectors/connectors/QUICKSTART.md`](app/features/connectors/connectors/QUICKSTART.md)
- **CSPM**: [`app/features/msp/cspm/README.md`](app/features/msp/cspm/README.md)
- **Community (Radium)**: [`app/features/community/docs/radium_prd.md`](app/features/community/docs/radium_prd.md)

## 🐳 Docker Deployment

### Development
```bash
docker-compose up -d
```

### Production
```bash
# Build production image
docker build -f Dockerfile.production -t terra-platform:latest .

# Run production container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e SECRET_KEY=... \
  terra-platform:latest
```

### Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/terra_platform

# Security
SECRET_KEY=<random-256-bit-key>
ENCRYPTION_KEY=<fernet-key>  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Application
DEBUG=false
ALLOWED_HOSTS=["example.com"]
CORS_ORIGINS=["https://example.com"]

# AI Services (OpenAI)
OPENAI_API_KEY=sk-...  # Or store in Secrets slice

# External APIs
SERPAPI_KEY=...  # For web search/scraping (Content Broadcaster)

# Monitoring
PROMETHEUS_ENABLED=true
LOGGING_LEVEL=INFO
```

## 🛠️ Make Commands

```bash
# Development
make install                    # Install dependencies
make dev-server                # Start development server
make db-migrate                # Run database migrations

# Testing
make test                      # Run all tests
make test-unit                 # Unit tests only
make test-integration          # Integration tests only
make test-ui                   # UI tests (Playwright)

# Compliance
make all-compliance-checks     # Run all compliance tests
make compliance-check          # Tenant CRUD patterns
make logging-compliance-check  # Structured logging
make route-structure-compliance # Route organization
make global-admin-compliance   # Global admin patterns

# Database
make db-reset                  # Reset database (DESTRUCTIVE!)
make seed-connectors          # Seed connector catalog

# Code Quality
make lint                      # Flake8 + mypy
make format                    # Black + isort
make security-check           # Bandit + safety

# Docker
make docker-build             # Build Docker image
make docker-run               # Run Docker container
make docker-compose-up        # Start with docker-compose

# CI/CD Simulation
make ci-test                  # Full CI/CD pipeline locally
```

## 📈 Roadmap

### ✅ Completed
- ✅ Multi-tenant architecture with global admin
- ✅ User management with RBAC
- ✅ Audit logging and application logs
- ✅ Secrets management (encrypted)
- ✅ Content Broadcaster (AI + publishing)
- ✅ Connector integrations (WordPress, LinkedIn, Twitter)
- ✅ CSPM M365 compliance scanning
- ✅ Compliance testing framework
- ✅ Tabler v1.0.0-beta20 UI
- ✅ Structured logging (structlog)

### 🚧 In Progress
- ⏳ Content Broadcaster background workers (Celery)
- ⏳ CSPM benchmark expansion (AWS, Azure, GCP)
- ⏳ Community platform (Radium) - Phase 1

### 📋 Planned
- 🔜 Real-time notifications (WebSockets)
- 🔜 Advanced analytics dashboard
- 🔜 Multi-language support (i18n)
- 🔜 Mobile app (React Native)
- 🔜 SSO integration (SAML, OIDC)
- 🔜 API rate limiting per tenant
- 🔜 Automated testing for all features
- 🔜 Performance optimization and caching

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Follow architectural patterns (see `.github/instructions/instructions.instructions.md`)
4. Run compliance tests: `make all-compliance-checks`
5. Write tests for new features
6. Submit pull request

### Code Standards
- ✅ Use type hints everywhere
- ✅ Add docstrings to all functions/classes
- ✅ Follow SOLID principles
- ✅ Keep slices self-contained
- ✅ Use centralized imports (`route_imports`, `service_imports`)
- ✅ Follow route organization (crud_routes vs form_routes)
- ✅ Use `is_global_admin()` helper for admin checks
- ✅ Return simple arrays from list APIs (for Tabulator)
- ✅ Use `advancedTableConfig` for all Tabulator tables

### Compliance Requirements
All pull requests must pass:
- Tenant CRUD compliance
- Logging compliance (structlog)
- Route structure compliance
- Global admin compliance
- Service/route import compliance

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Tabler** - Beautiful admin dashboard UI
- **HTMX** - Simplicity in dynamic UIs
- **SQLAlchemy** - Python SQL toolkit
- **Structlog** - Structured logging made easy

---

**Built with ❤️ by the TerraAutomationPlatform team**

For questions, issues, or contributions, please visit our [GitHub repository](https://github.com/yourusername/terra-automation-platform).

**Happy coding!** 🚀
