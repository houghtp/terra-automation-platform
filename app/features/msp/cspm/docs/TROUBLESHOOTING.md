# Troubleshooting: CIS Metadata Not Showing

## Issue 1: Results Page Shows Old Format

### Problem
After implementing CIS metadata columns, the scan results page still shows the old format without:
- Check titles
- Section/subsection
- Level badges (L1/L2)
- Remediation details

### Root Cause
**Existing scan results were created BEFORE the database migration** and don't have metadata populated.

The metadata columns exist in the database but are `NULL` for all existing records:

```sql
SELECT scan_id, check_id, title, level, section
FROM cspm_compliance_results
LIMIT 5;

 scan_id      | check_id                    | title | level | section
--------------+-----------------------------+-------+-------+---------
 eb5de558...  | 1.1.1_ensure_admin...       |       |       |
 eb5de558...  | 1.1.2_ensure_two...         |       |       |
```

All metadata fields are empty (NULL).

### Solution
**Run a new compliance scan** after the changes were deployed.

1. Navigate to MSP → CSPM → M365 Tenants
2. Click "Start Scan" on any tenant
3. Wait for scan to complete
4. View results - **metadata will be populated automatically**

The PowerShell scripts already return metadata in the results. The new service code will automatically parse and store it.

---

## Issue 2: Start Scan Button Not Working

### Symptoms
- Click "Start Scan" button
- Modal appears
- Fill out form
- Click submit
- Nothing happens

### Possible Causes

#### 1. Browser Console Errors
Check browser developer console (F12) for JavaScript errors:
- HTMX not loaded
- Form validation errors
- CORS issues

#### 2. Server Not Running
```bash
# Check if server is running
curl http://127.0.0.1:8000/health

# If not running, start it
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Template Cache
If running without `--reload`, templates might be cached:
```bash
# Restart with reload flag
pkill -f uvicorn
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. Modal Form HTMX Issue
The form uses HTMX for submission:
```html
<form hx-post="/msp/cspm/scans/start-form"
      hx-target="#modal-body"
      hx-swap="innerHTML">
```

Check browser network tab:
- POST request to `/msp/cspm/scans/start-form` should fire
- Should return HTML with success message or validation errors

#### 5. Database Connection Issue
Check server logs for database errors:
```bash
# View server logs
tail -f /path/to/logs/app.log

# Or if running in foreground, check stdout
```

### Debug Steps

1. **Check Browser Console** (F12 → Console tab):
   ```
   Look for errors like:
   - "HTMX is not defined"
   - "Failed to fetch"
   - "Network error"
   ```

2. **Check Network Tab** (F12 → Network tab):
   - Clear network log
   - Click "Start Scan"
   - Look for POST request to `/msp/cspm/scans/start-form`
   - Check response status (should be 200)
   - Check response body (should be HTML)

3. **Check Server Logs**:
   ```bash
   # If running in background
   journalctl -u your-service-name -f

   # If running in foreground
   # Check stdout/stderr for errors
   ```

4. **Test Form Endpoint Directly**:
   ```bash
   curl -X GET http://127.0.0.1:8000/msp/cspm/scans/form \
        -H "Cookie: your-session-cookie"
   ```

5. **Verify Routes Are Registered**:
   ```bash
   # Check if route exists
   curl http://127.0.0.1:8000/openapi.json | jq '.paths' | grep "scans/start-form"
   ```

---

## How Metadata Population Works

### 1. PowerShell Check Files
Check files contain embedded metadata:
```powershell
<# CIS_METADATA_START
{
    "Title": "Ensure only organizers can present",
    "Level": "L2",
    "Section": "8 Microsoft Teams admin center",
    "SubSection": "8.5 Meetings",
    "RecommendationId": "8.5.6",
    "Remediation": "1. Go to Teams admin center...",
    ...
}
CIS_METADATA_END #>
```

### 2. PowerShell Execution
`Start-Checks.ps1` extracts metadata and includes it in results:
```powershell
$result = @{
    CheckId = "8.5.6"
    Status = "Fail"
    Details = @(...)
    Metadata = $check.Metadata  # Full metadata object
}
```

### 3. Service Layer Parsing
`cspm_scan_service.py` → `bulk_insert_results()`:
```python
# Extract metadata from PowerShell result
metadata = result_data.get("Metadata", {}) or {}

result_record = CSPMComplianceResult(
    check_id=result_data.get("CheckId"),
    title=metadata.get("Title"),
    level=metadata.get("Level"),
    section=metadata.get("Section"),
    remediation=metadata.get("Remediation"),
    # ... all metadata fields
)
```

### 4. Database Storage
Metadata stored in `cspm_compliance_results` table with indexes on:
- `level` (for L1/L2 filtering)
- `section` (for grouping)
- `subsection` (for drill-down)
- `recommendation_id` (for CIS ID lookup)

### 5. Frontend Display
Template renders rich metadata:
- Table shows title, section, level
- Expandable details show full metadata
- Filters work on level/status

---

## Verification Checklist

### After Running New Scan

Check database for metadata:
```sql
SELECT
    scan_id,
    check_id,
    title,
    level,
    section,
    subsection,
    recommendation_id
FROM cspm_compliance_results
WHERE scan_id = 'your-new-scan-id'
LIMIT 5;
```

**Expected Output** (with metadata):
```
 scan_id      | check_id     | title                       | level | section                 | subsection  | recommendation_id
--------------+--------------+-----------------------------+-------+-------------------------+-------------+-------------------
 abc123...    | 8.5.6_...    | Ensure only organizers...   | L2    | 8 Microsoft Teams...    | 8.5 Meetings| 8.5.6
```

### Frontend Verification

1. ✅ Navigate to scan detail page
2. ✅ Table shows:
   - Check titles (not just IDs)
   - Section/subsection columns
   - L1/L2 badges
3. ✅ Filter dropdown works (L1/L2/All)
4. ✅ Click "Details" button:
   - Expandable row appears
   - Shows description, rationale
   - Shows remediation (green highlighted)
   - Shows references, CIS controls
5. ✅ Combined filtering works:
   - Filter by "Fail" + "L2"
   - Only failed L2 checks show

---

## Common Issues and Fixes

### Issue: "Check titles still showing as IDs"

**Cause**: Old scan data (before migration)

**Fix**: Run new scan

---

### Issue: "Level filter shows no results"

**Cause**: Metadata not populated in database

**Fix**: Run new scan after deployment

---

### Issue: "Remediation section is empty"

**Cause**: PowerShell check file missing metadata

**Fix**:
1. Check if PowerShell check file has `CIS_METADATA_START` block
2. Verify JSON is valid
3. Run `Get-CheckMetadata` function on the file to test

---

### Issue: "Start Scan button doesn't open modal"

**Cause**: JavaScript not loaded or button not wired up

**Fix**:
1. Check browser console for errors
2. Verify HTMX is loaded: `window.htmx !== undefined`
3. Check button has correct data attributes

---

### Issue: "Start Scan modal opens but submit does nothing"

**Cause**:
- HTMX POST failing
- Validation errors not shown
- Network request blocked

**Fix**:
1. Open browser Network tab
2. Click submit
3. Look for POST to `/msp/cspm/scans/start-form`
4. Check response for errors

---

## Next Steps

1. **Run a new compliance scan** to populate metadata
2. **Verify metadata appears** in scan results page
3. **Test filtering** by L1/L2 and status
4. **Expand details** to see remediation steps
5. **Fix any scan form issues** if button not working

---

## Contact/Support

If issues persist:
1. Check server logs for errors
2. Check browser console for JavaScript errors
3. Verify database migration applied: `SELECT * FROM alembic_version;`
4. Verify columns exist: `\d cspm_compliance_results` in psql
