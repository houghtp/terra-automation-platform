# Content Broadcaster - Multi-Channel Publishing System

Manage, approve, schedule, and publish content across multiple platforms from a single interface.

## Overview

The Content Broadcaster enables teams to:
- Create and manage content collaboratively
- Implement approval workflows before publishing
- Schedule content for future publishing
- Publish to multiple platforms simultaneously
- Track delivery status and engagement metrics

## Workflow

```
┌──────────┐    ┌───────────┐    ┌───────────┐    ┌────────────┐    ┌───────────┐
│  Draft   │───▶│ In Review │───▶│ Scheduled │───▶│ Publishing │───▶│ Published │
└──────────┘    └───────────┘    └───────────┘    └────────────┘    └───────────┘
     │                 │
     │                 │
     ▼                 ▼
┌──────────┐    ┌──────────┐
│ Rejected │    │  Failed  │
└──────────┘    └──────────┘
```

## Content States

| State | Description | Next Actions |
|-------|-------------|--------------|
| **draft** | Initial state, content being created/edited | Submit for review, Delete |
| **in_review** | Awaiting approval | Approve, Reject |
| **scheduled** | Approved and scheduled for publishing | Cancel jobs, View jobs |
| **publishing** | Currently being published | Monitor status |
| **published** | Successfully published to all platforms | View deliveries |
| **failed** | Publishing failed | Retry jobs |
| **rejected** | Not approved | Edit, Resubmit |

## API Endpoints

Base path: `/features/content-broadcaster`

### Content Management

#### Create Content
```http
POST /api/create
Content-Type: application/json

{
  "title": "My Content Title",
  "body": "Content body text...",
  "metadata": {
    "category": "blog",
    "author": "John Doe"
  },
  "tags": ["tech", "tutorial"]
}
```

**Response:**
```json
{
  "id": "abc123",
  "tenant_id": "tenant-1",
  "title": "My Content Title",
  "body": "Content body text...",
  "state": "draft",
  "approval_status": "pending",
  "created_at": "2025-10-10T12:00:00Z",
  "created_by_email": "user@example.com",
  "created_by_name": "John Doe"
}
```

#### List Content
```http
GET /api/list?limit=20&offset=0&search=tutorial&state=draft&approval_status=pending
```

**Query Parameters:**
- `limit` (int, default: 100) - Number of items per page
- `offset` (int, default: 0) - Pagination offset
- `search` (string, optional) - Search in title and body
- `state` (string, optional) - Filter by state
- `created_by` (string, optional) - Filter by creator
- `approval_status` (string, optional) - Filter by approval status

**Response:**
```json
{
  "data": [
    { "id": "abc123", "title": "...", ... }
  ],
  "total": 150,
  "offset": 0,
  "limit": 20
}
```

#### Get Single Item
```http
GET /api/{content_id}
```

#### Update Content
```http
PUT /api/{content_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "body": "Updated content...",
  "tags": ["updated", "tutorial"]
}
```

**Note:** Can only update content in `draft` or `rejected` states.

#### Delete Content
```http
DELETE /api/{content_id}
```

**Note:** Can only delete content in `draft` or `rejected` states.

---

### Approval Workflow

#### Submit for Review
```http
POST /api/{content_id}/submit
```

Transitions content from `draft` → `in_review`.

#### Approve Content
```http
POST /api/{content_id}/approve
Content-Type: application/json

{
  "comment": "Looks good, approved for publishing",
  "auto_schedule": false
}
```

**Parameters:**
- `comment` (string, optional) - Approval comment
- `auto_schedule` (boolean, default: false) - Automatically transition to scheduled if scheduled_at is set

Transitions content from `in_review` → `draft` (or `scheduled` if auto_schedule=true).

#### Reject Content
```http
POST /api/{content_id}/reject
Content-Type: application/json

{
  "comment": "Please revise the introduction section"
}
```

**Parameters:**
- `comment` (string, required) - Rejection reason

Transitions content from `in_review` → `rejected`.

---

### Publishing & Scheduling

#### Schedule Content
```http
POST /api/{content_id}/schedule
Content-Type: application/json

{
  "scheduled_at": "2025-10-15T14:00:00Z",
  "connector_ids": ["twitter-connector-1", "linkedin-connector-2"]
}
```

**Parameters:**
- `scheduled_at` (datetime, required) - When to publish
- `connector_ids` (array, required) - List of connector IDs to publish to

**Requirements:**
- Content must be approved (`approval_status: "approved"`)
- Content must be in `draft` or `scheduled` state

**Creates:**
- One `PublishJob` per connector
- Jobs are set to `queued` status
- Content transitions to `scheduled` state

---

### Job Management

#### List Jobs
```http
GET /api/jobs?status=queued&connector_id=twitter-1&content_id=abc123
```

**Query Parameters:**
- `limit` (int) - Items per page
- `offset` (int) - Pagination offset
- `status` (string) - Filter by job status (queued, running, success, failed, retrying, canceled)
- `connector_id` (string) - Filter by connector
- `content_id` (string) - Filter by content item

**Response:**
```json
{
  "data": [
    {
      "id": "job-123",
      "content_item_id": "abc123",
      "connector_id": "twitter-1",
      "status": "queued",
      "run_at": "2025-10-15T14:00:00Z",
      "attempt": 0,
      "last_error": null
    }
  ],
  "total": 5,
  "offset": 0,
  "limit": 100
}
```

#### Retry Failed Job
```http
POST /api/jobs/{job_id}/retry
```

Resets a `failed` or `canceled` job back to `queued` status.

#### Cancel Job
```http
POST /api/jobs/{job_id}/cancel
```

Cancels a `queued` or `retrying` job.

---

### Dashboard

#### Get Summary Statistics
```http
GET /api/summary
```

**Response:**
```json
{
  "total_content": 250,
  "pending_approvals": 5,
  "scheduled_count": 12,
  "published_count": 220
}
```

#### Get Pending Approvals
```http
GET /api/approvals/pending?limit=20&offset=0
```

Returns content items in `in_review` state with `pending` approval status.

---

## Advanced Features

### SEO Content Generation
```http
POST /api/generate-seo-content
Content-Type: application/json

{
  "title": "Best Practices for API Design",
  "ai_provider": "openai",
  "fallback_ai": "anthropic",
  "search_provider": "serpapi",
  "scraping_provider": "firecrawl",
  "min_seo_score": 95,
  "max_iterations": 3,
  "auto_approve": false
}
```

Generates SEO-optimized content using AI. Content generation runs in background.

**Parameters:**
- `title` (string, required) - Content topic/title
- `ai_provider` (string, default: "openai") - Primary AI provider
- `fallback_ai` (string, default: "anthropic") - Fallback AI provider
- `search_provider` (string, default: "serpapi") - Search provider for research
- `scraping_provider` (string, default: "firecrawl") - Web scraping provider
- `min_seo_score` (int, default: 95) - Minimum acceptable SEO score (80-100)
- `max_iterations` (int, default: 3) - Maximum AI refinement iterations (1-5)
- `auto_approve` (boolean, default: false) - Auto-approve if SEO score meets threshold

---

## Data Models

### ContentItem

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| tenant_id | string | Tenant isolation |
| title | string(500) | Content title |
| body | text | Content body |
| state | enum | Content state (see states above) |
| scheduled_at | datetime | User-planned publish time |
| publish_at | datetime | Actual publish timestamp |
| approval_status | enum | pending, approved, rejected |
| approved_by | string | User ID who approved |
| approved_at | datetime | Approval timestamp |
| approval_comment | text | Approval/rejection comment |
| content_metadata | jsonb | Flexible metadata storage |
| tags | json | Content tags array |
| created_by_email | string | Creator email (from AuditMixin) |
| created_by_name | string | Creator name (from AuditMixin) |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |

### PublishJob

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| tenant_id | string | Tenant isolation |
| content_item_id | string | Foreign key to content_items |
| connector_id | string | Target connector ID |
| run_at | datetime | Scheduled execution time |
| status | enum | queued, running, success, failed, retrying, canceled |
| attempt | int | Retry attempt counter |
| last_error | text | Last error message |
| execution_metadata | jsonb | Execution details |
| created_at | datetime | Job creation time |
| updated_at | datetime | Last status update |

### Delivery

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| tenant_id | string | Tenant isolation |
| publish_job_id | string | Foreign key to publish_jobs |
| external_post_id | string | Platform's post ID |
| permalink | string | Public URL to post |
| response_json | jsonb | Full platform response |
| created_at | datetime | Delivery timestamp |

### EngagementSnapshot

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| tenant_id | string | Tenant isolation |
| delivery_id | string | Foreign key to deliveries |
| captured_at | datetime | Snapshot timestamp |
| likes | int | Like count |
| comments | int | Comment count |
| shares | int | Share count |
| views | int | View count |
| metrics_json | jsonb | Additional platform metrics |

---

## Multi-Tenant Isolation

All operations are automatically scoped to the current tenant via the `tenant_dependency`:

```python
tenant_id: str = Depends(tenant_dependency)
```

Content, jobs, deliveries, and snapshots are isolated per tenant. Cross-tenant access is prevented at the database query level.

---

## Authentication & Authorization

### Required:
- Valid authentication token in request headers
- Active user account

### Permissions:
- **Create/Edit/Delete:** Any authenticated user can manage their own content
- **Submit for Review:** Content creators
- **Approve/Reject:** ⚠️ Currently any authenticated user (RBAC not yet implemented)
- **Schedule:** Users with approved content
- **Job Management:** Users can manage jobs for their own content

---

## Error Handling

### Common Error Responses:

**404 Not Found**
```json
{
  "detail": "Content not found"
}
```

**400 Bad Request**
```json
{
  "detail": "Cannot approve content in draft state"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Failed to create content"
}
```

### State Transition Errors:

| Operation | Invalid From State | Error Message |
|-----------|-------------------|---------------|
| Submit | Not draft | "Cannot submit content in {state} state for review" |
| Approve | Not in_review | "Cannot approve content in {state} state" |
| Reject | Not in_review | "Cannot reject content in {state} state" |
| Update | published/scheduled | "Cannot update content in {state} state" |
| Delete | published/scheduled | "Cannot delete content in {state} state" |
| Schedule | Not approved | "Content must be approved before scheduling" |

---

## Usage Examples

### Complete Workflow Example

```python
import httpx

base_url = "https://api.example.com/features/content-broadcaster"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

# 1. Create content
response = httpx.post(
    f"{base_url}/api/create",
    json={
        "title": "10 Tips for Better Code Reviews",
        "body": "# Introduction\n\nCode reviews are...",
        "tags": ["engineering", "best-practices"]
    },
    headers=headers
)
content = response.json()
content_id = content["id"]
print(f"Created content: {content_id}")

# 2. Submit for review
httpx.post(f"{base_url}/api/{content_id}/submit", headers=headers)
print("Submitted for review")

# 3. Approve (as reviewer)
httpx.post(
    f"{base_url}/api/{content_id}/approve",
    json={
        "comment": "Great article! Ready to publish.",
        "auto_schedule": False
    },
    headers=headers
)
print("Approved")

# 4. Schedule for publishing
httpx.post(
    f"{base_url}/api/{content_id}/schedule",
    json={
        "scheduled_at": "2025-10-15T14:00:00Z",
        "connector_ids": ["twitter-main", "linkedin-company"]
    },
    headers=headers
)
print("Scheduled for 2 platforms")

# 5. Check job status
jobs_response = httpx.get(
    f"{base_url}/api/jobs?content_id={content_id}",
    headers=headers
)
jobs = jobs_response.json()
print(f"Created {len(jobs['data'])} publish jobs")

# 6. Monitor dashboard
stats_response = httpx.get(f"{base_url}/api/summary", headers=headers)
stats = stats_response.json()
print(f"Pending approvals: {stats['pending_approvals']}")
print(f"Scheduled items: {stats['scheduled_count']}")
```

---

## Integration with Connectors

The Content Broadcaster integrates with the [Connectors slice](../../connectors/connectors/README.md) for publishing to external platforms.

### Connector Requirements:
- Connector must be installed (status: "active")
- Connector must support publishing capability
- Authentication credentials must be configured

### Supported Platforms:
- Twitter/X (via OAuth)
- WordPress (via Basic Auth)
- LinkedIn (via OAuth)
- Medium (via API Key)

See [Connectors Documentation](../../connectors/connectors/README.md) for setup instructions.

---

## Background Worker (⚠️ Not Yet Implemented)

**Status:** The Celery background worker for automatic publishing is not yet implemented.

**Current Behavior:**
- Jobs are created with `queued` status
- Jobs remain in `queued` state indefinitely
- Manual intervention required to execute jobs

**Planned Implementation:**
```python
# Celery task (to be implemented)
@celery.task
def process_publish_jobs():
    # Poll for jobs where run_at <= now() and status = 'queued'
    # For each job:
    #   1. Update status to 'running'
    #   2. Get connector configuration
    #   3. Publish content via connector adapter
    #   4. Create delivery record on success
    #   5. Update job status to 'success' or 'failed'
    #   6. Update content state to 'published' or 'failed'
```

**Workaround:** Jobs can be manually processed using the service layer:
```python
from app.features.business_automations.content_broadcaster.services import ContentBroadcasterService
from app.features.connectors.connectors.services import ConnectorService

# Pseudo-code for manual publishing
async def manually_process_job(job_id):
    service = ContentBroadcasterService(session, tenant_id)
    connector_service = ConnectorService(session, tenant_id)

    # Get job and content
    # Publish via connector adapter
    # Create delivery record
    # Update statuses
```

---

## File Storage (⚠️ Not Yet Implemented)

**Planned directories:**
```
/storage/
├── drafts/           # Draft content files
│   └── {tenant_id}/
│       └── {content_id}/
└── published/        # Published content archives
    └── {tenant_id}/
        └── {content_id}/
            └── {delivery_id}/
```

---

## Monitoring & Observability

### Metrics Tracked:
- Total content items by state
- Pending approvals count
- Scheduled jobs count
- Published content count
- Job success/failure rates (when worker is implemented)

### Logging:
All operations are logged using structured logging:

```python
logger.info("Created content", content_id=content.id, tenant_id=tenant_id)
logger.info("Approved content", content_id=content_id, approved_by=user_id)
logger.error("Failed to schedule content", content_id=content_id, error=str(e))
```

### Health Checks:
Content Broadcaster status is included in the application health endpoint:
```http
GET /health
```

---

## Development

### Running Tests:
```bash
pytest app/features/business_automations/content_broadcaster/tests/
```

### Database Migrations:
Content Broadcaster tables are managed via Alembic:

```bash
# Check migration status
python3 manage_db.py current

# Apply migrations
python3 manage_db.py upgrade
```

### Service Layer Testing:
```python
from app.features.business_automations.content_broadcaster.services import ContentBroadcasterService

async def test_workflow():
    service = ContentBroadcasterService(session, tenant_id="test-tenant")

    # Create content
    content = await service.create_content(
        title="Test Content",
        body="Test body",
        created_by_user=user
    )

    # Submit for review
    await service.submit_for_review(content.id, user.id)

    # Approve
    await service.approve_content(content.id, reviewer_id, comment="LGTM")

    # Schedule
    await service.schedule_content(
        content.id,
        scheduled_at=datetime.now() + timedelta(hours=1),
        connector_ids=["connector-1"],
        updated_by=user.id
    )
```

---

## Roadmap

### Upcoming Features:
- [ ] Celery background worker implementation
- [ ] Role-based access control for approvals
- [ ] File storage integration
- [ ] Engagement tracking automation
- [ ] Bulk operations (bulk approve, bulk schedule)
- [ ] Content templates
- [ ] Scheduled recurring posts
- [ ] Multi-language support
- [ ] Advanced analytics dashboard

---

## Support & Documentation

- **Technical Spec:** [docs/PRP_Content_Broadcaster_Slice.md](docs/PRP_Content_Broadcaster_Slice.md)
- **Implementation Plan:** [docs/PROJECT_PLAN_Content_Broadcaster_Slice.md](docs/PROJECT_PLAN_Content_Broadcaster_Slice.md)
- **Current Status:** [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md)

---

## License

Part of the Terra Automation Platform. See main project LICENSE file.
