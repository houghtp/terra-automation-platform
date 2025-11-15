# CSPM Analytics Implementation

**Date**: 2025-11-14
**Feature**: Analytics charts for compliance scans dashboard and scan details

## Overview

Added comprehensive analytics visualizations to CSPM scan pages using the `chart-widget` web component. All analytics are **tenant-scoped by default** and support global admin cross-tenant views.

## Implementation Summary

### 1. Service Layer ✅

**File**: `app/features/msp/cspm/services/analytics_service.py`

**Class**: `CSPMAnalyticsService(BaseService[CSPMScan])`

**Methods**:
- `get_scans_overview(days=30)` - Total scans, completed, failed, running, avg pass rate
- `get_compliance_over_time(days=30, limit=10)` - Historical trend data for line chart
- `get_scan_status_distribution()` - Scan counts by status for donut chart
- `get_scan_results_breakdown(scan_id)` - Pass/Fail/Error counts for donut chart
- `get_compliance_by_section(scan_id)` - Pass rate per section for bar chart
- `get_level_distribution(scan_id)` - Check counts by level (L1/L2) for donut chart
- `get_top_failures(scan_id, limit=10)` - List of top failed checks

**Tenant Isolation**:
- All methods use `BaseService.create_base_query()` for automatic tenant filtering
- Global admins (`tenant_id=None`) see data across all tenants
- Cross-tenant aggregations use `allow_cross_tenant=True` with audit trail

### 2. API Routes ✅

**File**: `app/features/msp/cspm/routes/analytics_routes.py`

**Endpoints**:
```
GET /msp/cspm/analytics/overview?days=30
GET /msp/cspm/analytics/compliance-trend?days=30&limit=10
GET /msp/cspm/analytics/status-distribution
GET /msp/cspm/analytics/scan/{scan_id}/results-breakdown
GET /msp/cspm/analytics/scan/{scan_id}/by-section
GET /msp/cspm/analytics/scan/{scan_id}/by-level
GET /msp/cspm/analytics/scan/{scan_id}/top-failures?limit=10
```

**Authentication**: All endpoints require authenticated user via `get_current_user`

**Tenant Context**: Extracted via `tenant_dependency` (supports global admin with `tenant_id="global"`)

### 3. Scans Dashboard ✅

**File**: `app/features/msp/cspm/templates/cspm/partials/scan_list_content.html`

**Charts Added**:

#### Overview Stats (col-md-3)
- **Type**: Stats cards
- **API**: `/msp/cspm/analytics/overview`
- **Shows**: Total scans, completed, failed, running, avg pass rate

#### Compliance Over Time (col-md-6)
- **Type**: Line chart
- **API**: `/msp/cspm/analytics/compliance-trend`
- **X-axis**: Date/time of scan completion
- **Y-axis**: Pass rate percentage
- **Shows**: Historical compliance trend (last 10 scans)

#### Scan Status Distribution (col-md-3)
- **Type**: Donut chart
- **API**: `/msp/cspm/analytics/status-distribution`
- **Colors**:
  - Completed: #28a745 (green)
  - Failed: #dc3545 (red)
  - Running: #17a2b8 (cyan)
  - Pending: #6c757d (gray)
  - Cancelled: #ffc107 (yellow)

**Layout**: 3-column row above the scans table

### 4. Scan Details Page ✅

**File**: `app/features/msp/cspm/templates/cspm/scan_detail.html`

**Charts Added** (only shown for completed scans):

#### Results Distribution (col-md-4)
- **Type**: Donut chart
- **API**: `/msp/cspm/analytics/scan/{scan_id}/results-breakdown`
- **Shows**: Passed, Failed, Errors counts
- **Colors**:
  - Passed: #28a745 (green)
  - Failed: #dc3545 (red)
  - Errors: #ffc107 (yellow)

#### Compliance by Section (col-md-5)
- **Type**: Horizontal bar chart
- **API**: `/msp/cspm/analytics/scan/{scan_id}/by-section`
- **X-axis**: Pass rate percentage
- **Y-axis**: Section names (e.g., "1 Microsoft 365 admin center")
- **Shows**: Pass rate for each benchmark section

#### Level Distribution (col-md-3)
- **Type**: Donut chart
- **API**: `/msp/cspm/analytics/scan/{scan_id}/by-level`
- **Shows**: Check counts by level (L1 vs L2)
- **Colors**:
  - L1: #007bff (blue)
  - L2: #6f42c1 (purple)

**Layout**: 3-column row between scan info card and results table

### 5. Script Dependencies ✅

**Files Updated**:
- `app/features/msp/cspm/templates/cspm/scans.html` - Added chart-widget.js
- `app/features/msp/cspm/templates/cspm/scan_detail.html` - Added chart-widget.js

**Script Loading**:
```html
<script src="/features/dashboard/static/js/chart-widget.js"></script>
```

### 6. Router Registration ✅

**File**: `app/features/msp/cspm/routes/__init__.py`

```python
from .analytics_routes import router as analytics_router
cspm_router.include_router(analytics_router)
```

## Data Flow

### Dashboard Analytics Flow
```
User loads /msp/cspm/scans
  ↓
chart-widget fetches /msp/cspm/analytics/overview
  ↓
analytics_routes.get_scans_overview()
  ↓
CSPMAnalyticsService.get_scans_overview(tenant_id)
  ↓
BaseService applies tenant filter (or not, for global admin)
  ↓
Returns aggregated data
  ↓
chart-widget renders visualization
```

### Scan Details Analytics Flow
```
User views /msp/cspm/scans/{scan_id}
  ↓
chart-widget fetches /msp/cspm/analytics/scan/{scan_id}/results-breakdown
  ↓
analytics_routes.get_scan_results_breakdown()
  ↓
CSPMAnalyticsService.get_scan_results_breakdown(scan_id, tenant_id)
  ↓
BaseService validates tenant access to scan
  ↓
Returns scan-specific data
  ↓
chart-widget renders donut chart
```

## Tech-Agnostic Design

All analytics use **common fields** that work across technology types:

### Common Fields Used:
- `status` - Scan status (completed, failed, running, pending, cancelled)
- `total_checks` - Total number of checks run
- `passed` - Number of passed checks
- `failed` - Number of failed checks
- `errors` - Number of errored checks
- `section` - Benchmark section (e.g., "1 Microsoft 365 admin center", "2 Azure Security Center")
- `level` - Check level (L1, L2, etc.)
- `completed_at` - Scan completion timestamp
- `created_at` - Scan creation timestamp

### Works With:
- ✅ M365 CIS Benchmark
- ✅ Azure CIS Benchmark (future)
- ✅ AWS CIS Benchmark (future)
- ✅ Any benchmark with section/level structure

## Global Admin Support

### Tenant-Scoped Views (Regular Users)
- See only their tenant's scans and results
- Analytics filtered by `tenant_id`
- Cannot access other tenants' data

### Cross-Tenant Views (Global Admins)
- `tenant_id = "global"` in JWT → converted to `None` by BaseService
- See aggregated data across **all tenants**
- No tenant filter applied to queries
- Useful for:
  - Platform-wide compliance metrics
  - Multi-tenant comparisons
  - SLA monitoring

### Security
- All endpoints require authentication (`get_current_user`)
- Tenant context validated by `tenant_dependency`
- BaseService enforces tenant isolation automatically
- Cross-tenant queries logged with reason for audit trail

## Testing Checklist

### Scans Dashboard
- [ ] Load `/msp/cspm/scans` and verify 3 charts render
- [ ] Check "Overview" stats show correct counts
- [ ] Check "Compliance Over Time" shows trend line
- [ ] Check "Scan Status" donut shows status distribution
- [ ] Verify charts update when new scan completes

### Scan Details Page
- [ ] View a completed scan details page
- [ ] Verify 3 analytics charts render above results table
- [ ] Check "Results Distribution" shows Pass/Fail/Error breakdown
- [ ] Check "Compliance by Section" shows horizontal bars
- [ ] Check "Level Distribution" shows L1/L2 breakdown
- [ ] Verify charts don't show for running/failed scans

### Global Admin
- [ ] Login as global admin
- [ ] Verify dashboard shows data from all tenants
- [ ] Create scans in multiple tenants
- [ ] Verify analytics aggregate cross-tenant data

### API Testing
```bash
# Test overview endpoint
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/msp/cspm/analytics/overview

# Test trend endpoint
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/msp/cspm/analytics/compliance-trend?days=30&limit=10

# Test scan-specific breakdown
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/msp/cspm/analytics/scan/{scan_id}/results-breakdown
```

## Future Enhancements

### Dashboard
- [ ] Add date range picker for trend data
- [ ] Export charts as PNG/PDF
- [ ] Add comparison view (compare 2 scans side-by-side)
- [ ] Add benchmark-specific widgets (M365, Azure, AWS tabs)

### Scan Details
- [ ] Add "Top Failures" widget with clickable links to check details
- [ ] Add timeline view showing when checks were executed
- [ ] Add remediation progress tracking
- [ ] Add historical comparison (this scan vs previous scan)

### Global Admin
- [ ] Add tenant comparison matrix
- [ ] Add SLA compliance tracking
- [ ] Add trend analysis across all tenants
- [ ] Add tenant health scores

## Files Created/Modified

### Created:
- `app/features/msp/cspm/services/analytics_service.py` - Analytics business logic
- `app/features/msp/cspm/routes/analytics_routes.py` - API endpoints
- `docs/cspm-analytics-implementation.md` - This documentation

### Modified:
- `app/features/msp/cspm/routes/__init__.py` - Registered analytics router
- `app/features/msp/cspm/templates/cspm/scans.html` - Added chart-widget script
- `app/features/msp/cspm/templates/cspm/partials/scan_list_content.html` - Added 3 charts
- `app/features/msp/cspm/templates/cspm/scan_detail.html` - Added 3 charts + script

## Dependencies

- ✅ `chart-widget.js` - Web component for rendering charts (already exists)
- ✅ `BaseService` - Tenant isolation and query builders (already exists)
- ✅ Chart.js - JavaScript charting library (loaded by chart-widget)
- ✅ Tabler CSS - UI framework (already loaded in base.html)

## Performance Considerations

- Analytics queries use indexed fields (`tenant_id`, `status`, `scan_id`)
- Trend data limited to 10 most recent scans by default
- Donut charts aggregate pre-calculated counts (no expensive joins)
- Section breakdowns use simple GROUP BY queries
- All endpoints support query parameter tuning (`days`, `limit`)

## Related Features

- Real-time scan updates: ✅ Fixed (EventSource/SSE)
- CIS metadata display: ✅ Fixed (Section 5 metadata added)
- Analytics visualizations: ✅ Implemented (this feature)
