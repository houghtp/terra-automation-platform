# CSPM Testing Checklist

**Date**: 2025-11-19
**Features**: Credential Flow + Title Fixes

---

## Pre-Test Setup ✅

- [ ] Application is running (`make dev-server` or `uvicorn app.main:app --reload`)
- [ ] Database is accessible
- [ ] M365 tenant credentials are in database (verified)
- [ ] PowerShell is installed with required modules
- [ ] Changes are uncommitted (ready to rollback if needed)

---

## Test 1: Credential Flow Verification

### Step 1: Navigate to CSPM
- [ ] Go to: `http://localhost:8000/features/msp/cspm/m365-tenants`
- [ ] Confirm M365 tenant "terrait.co.uk" is listed
- [ ] Tenant ID shows: `660636d5-cb4e-4816-b1b8-f5afc446f583`

### Step 2: Initiate Scan
- [ ] Click on "terrait.co.uk" tenant row
- [ ] Click "Run Scan" button
- [ ] Select benchmark: **CIS Microsoft 365 Foundations Benchmark v5.0.0**
- [ ] Select level: **L1** (or both L1 + L2)
- [ ] Click "Start Scan"

### Step 3: Monitor Scan Progress
- [ ] Scan status changes to "In Progress"
- [ ] Progress bar updates in real-time
- [ ] WebSocket connection shows live updates

### Step 4: Check Authentication (Terminal)

Open a new terminal window:

```bash
# Find the most recent scan directory
ls -lt /tmp/cspm_scan_* | head -1

# Tail the PowerShell log
tail -f /tmp/cspm_scan_*/start-checks_*.log
```

**Look for**:
- [ ] `Auth Parameters Loaded:` message appears
- [ ] Parameters include: `TenantId`, `ClientId`, `SharePointAdminUrl`
- [ ] **NO** hardcoded credentials used (should see database values)
- [ ] Authentication succeeds (no 401/403 errors)

### Step 5: Verify SharePoint URL

```bash
# Check the auth params file
cat /tmp/cspm_scan_*/auth_params_*.json | jq .
```

**Expected**:
```json
{
  "TenantId": "660636d5-cb4e-4816-b1b8-f5afc446f583",
  "TenantDomain": "terrait.co.uk",
  "SharePointAdminUrl": "https://netorgft16254533-admin.sharepoint.com",
  "ClientId": "...",
  "ClientSecret": "...",
  ...
}
```

- [ ] SharePointAdminUrl is `https://netorgft16254533-admin.sharepoint.com`
- [ ] ClientId is present (not empty)
- [ ] One of the auth methods has values (Client Secret / Certificate / Username+Password)

### Step 6: Wait for Completion
- [ ] Scan completes successfully
- [ ] Status changes to "Completed"
- [ ] No authentication errors in logs
- [ ] Results are stored in database

**✅ Credential Flow Test: PASS / FAIL**

---

## Test 2: Check Title Verification

### Step 1: Navigate to Scan Results
- [ ] Go to: `http://localhost:8000/features/msp/cspm/scans`
- [ ] Click on the most recent scan
- [ ] Scan detail page loads

### Step 2: Verify Specific Titles

**Check these 5 key examples**:

| Check ID | Expected Full Title | Visible in UI? |
|----------|-------------------|----------------|
| 1.1.2 | Ensure two emergency access accounts have been **defined** | [ ] ✅ |
| 1.1.4 | Ensure administrative accounts use licenses **with a reduced application footprint** | [ ] ✅ |
| 2.1.10 | Ensure DMARC Records for all Exchange Online **domains are published** | [ ] ✅ |
| 7.2.11 | Ensure the SharePoint default sharing link permission **is set to 'View'** | [ ] ✅ |
| 8.5.2 | Ensure anonymous users and dial-in callers can't start **a meeting** | [ ] ✅ |

### Step 3: Database Verification

```sql
-- Check titles from most recent scan
SELECT
    recommendation_id,
    title,
    CASE
        WHEN title LIKE '%...' THEN 'TRUNCATED ❌'
        WHEN LENGTH(title) < 50 THEN 'POSSIBLY TRUNCATED ⚠️'
        ELSE 'OK ✅'
    END as status
FROM cspm_compliance_results
WHERE scan_id = (SELECT id FROM cspm_compliance_scans ORDER BY created_at DESC LIMIT 1)
  AND recommendation_id IN ('1.1.2', '1.1.4', '2.1.10', '7.2.11', '8.5.2')
ORDER BY recommendation_id;
```

**Expected Results**:
- [ ] All 5 titles end with complete phrases (no "...")
- [ ] 1.1.2 ends with "defined"
- [ ] 1.1.4 ends with "reduced application footprint"
- [ ] 2.1.10 ends with "domains are published"
- [ ] 7.2.11 ends with "is set to 'View'"
- [ ] 8.5.2 ends with "a meeting"

### Step 4: Scan Detail Page Visual Check

Scroll through scan results and verify:

- [ ] No titles end with "..."
- [ ] No titles appear cut off mid-sentence
- [ ] Titles are readable and complete
- [ ] Control requirements are clear from titles

**✅ Title Display Test: PASS / FAIL**

---

## Test 3: Overall System Health

### Application Logs
```bash
# Check application logs for errors
tail -n 100 logs/app.log | grep -i error
```

- [ ] No credential-related errors
- [ ] No title parsing errors
- [ ] No database errors

### Database Integrity
```sql
-- Check scan completed successfully
SELECT
    id,
    status,
    created_at,
    (SELECT COUNT(*) FROM cspm_compliance_results WHERE scan_id = cspm_compliance_scans.id) as result_count
FROM cspm_compliance_scans
ORDER BY created_at DESC
LIMIT 1;
```

**Expected**:
- [ ] Status: `completed`
- [ ] Result count: ~130 checks
- [ ] Created timestamp is recent

### PowerShell Logs Review
```bash
# Check for any errors in PowerShell execution
grep -i "error\|exception\|failed" /tmp/cspm_scan_*/start-checks_*.log
```

- [ ] No authentication failures
- [ ] No module loading errors
- [ ] No unexpected exceptions

**✅ System Health Test: PASS / FAIL**

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| Credential Flow | [ ] PASS / [ ] FAIL | |
| Title Display | [ ] PASS / [ ] FAIL | |
| System Health | [ ] PASS / [ ] FAIL | |

---

## If Tests PASS ✅

1. **Review Changes**:
   ```bash
   git status
   git diff app/features/msp/cspm/services/
   git diff app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/checks/ | head -100
   ```

2. **Commit Changes**:
   ```bash
   git add app/features/msp/cspm/services/async_scan_runtime.py
   git add app/features/msp/cspm/services/m365_tenant_service.py
   git add app/features/msp/cspm/services/powershell_executor.py
   git add app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/checks/

   git commit -m "feat(cspm): Enable database credential flow and fix truncated check titles

   - Remove test overrides to enable credential retrieval from database
   - Pass all authentication parameters to PowerShell (Client Secret, Certificate, Username/Password)
   - Hardcode SharePoint Admin URL temporarily (awaiting proper solution)
   - Fix 53 truncated check titles in PowerShell metadata to match CSV
   - Update Title field in CIS_METADATA blocks for complete display in scan results

   Credential Flow:
   - async_scan_runtime.py: Call get_tenant_credentials() instead of empty dict
   - powershell_executor.py: Create auth_params JSON file
   - m365_tenant_service.py: Set hardcoded SharePoint URL

   Title Fixes:
   - Updated 53 PowerShell check scripts with full titles from CSV
   - Examples: 1.1.2 (defined), 1.1.4 (reduced application footprint),
     2.1.10 (domains are published), 8.5.2 (a meeting)"

   git push
   ```

3. **Document Success**:
   - [ ] Update project status
   - [ ] Note any findings or observations
   - [ ] Plan next steps (SharePoint URL solution)

---

## If Tests FAIL ❌

### Rollback Steps

1. **Revert Changes**:
   ```bash
   git checkout app/features/msp/cspm/services/async_scan_runtime.py
   git checkout app/features/msp/cspm/services/m365_tenant_service.py
   git checkout app/features/msp/cspm/services/powershell_executor.py
   git checkout app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/checks/
   ```

2. **Restart Application**:
   ```bash
   # Restart dev server to reload old code
   # Ctrl+C in dev server terminal, then:
   make dev-server
   ```

3. **Document Issues**:
   - [ ] What failed?
   - [ ] Error messages?
   - [ ] Stack traces?
   - [ ] Reproduction steps?

4. **Troubleshoot**:
   - Check credential decryption
   - Verify PowerShell module installation
   - Check SharePoint URL validity
   - Review authentication method compatibility

---

## Common Issues & Solutions

### Issue: Authentication Fails (401/403)

**Possible Causes**:
- Credentials expired/revoked
- Wrong client ID/secret
- Certificate password incorrect
- SharePoint URL wrong

**Solutions**:
1. Verify credentials in database are current
2. Test credentials manually with PowerShell
3. Check M365 tenant admin portal for app registration
4. Verify SharePoint URL is accessible

### Issue: Titles Still Truncated

**Possible Causes**:
- PowerShell metadata not updated
- Database still has old scan results
- Template rendering issue

**Solutions**:
1. Verify PowerShell files have new metadata: `grep -A 1 "\"Title\":" checks/L1/1.1.2*.ps1`
2. Run a fresh scan (don't use old scan results)
3. Check template rendering in `scan_detail` page

### Issue: Scan Hangs/Freezes

**Possible Causes**:
- PowerShell timeout
- Authentication waiting for input
- Module not loaded

**Solutions**:
1. Check PowerShell process: `ps aux | grep pwsh`
2. Check logs for "waiting for input" messages
3. Verify all required modules installed

---

## Next Steps After Testing

### If Successful:
1. [ ] Implement proper SharePoint URL solution (manual field or API lookup)
2. [ ] Add credential validation before scan
3. [ ] Add credential refresh/rotation support
4. [ ] Consider adding authentication method selection in UI

### If Issues Found:
1. [ ] Document issues thoroughly
2. [ ] Investigate root causes
3. [ ] Implement fixes
4. [ ] Re-test

---

**Tester**: _______________
**Test Date**: 2025-11-19
**Test Duration**: _____ minutes
**Overall Result**: [ ] PASS / [ ] FAIL
**Comments**:
```


```
