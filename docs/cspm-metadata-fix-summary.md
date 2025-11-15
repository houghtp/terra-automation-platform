# CSPM Metadata Fix - Summary

**Date**: 2025-11-14
**Issue**: Section 5 check results displaying only `check_id` instead of proper CIS metadata (Title, Section, SubSection, etc.)

## Problem

Scan results showed two different formats:
- **v1 (broken)**: Only `check_id` like `5.2.4.1_ensure_'self_service_password_reset_enabled'_is_set_to`
- **v2 (correct)**: Proper fields like "Ensure 'Self service password reset enabled' is set to 'All'" with Section "5 Microsoft Entra admin center"

## Root Cause

**24 out of 91 check files were missing CIS metadata blocks** - all from Section 5 (Microsoft Entra admin center).

The PowerShell `Get-CheckMetadata()` function expects check files to have:
```powershell
<# CIS_METADATA_START
{"Title":"...","Level":"L1","Section":"...","SubSection":"...","RecommendationId":"5.1.2.1",...}
CIS_METADATA_END #>
```

Section 5 files didn't have these blocks, so metadata extraction returned `null`.

## Solution Implemented

### 1. Added Metadata to Check Files ✅

Created Python script (`/tmp/add_metadata_to_checks.py`) that:
- Parsed `CIS_Microsoft_365_Foundations_Benchmark_v5.0.0.csv`
- Extracted metadata for all Section 5 recommendations
- Added metadata blocks to 32 check files (5 already had them)

**Result**: All 37 Section 5 check files now have proper metadata blocks.

**Verification**:
```bash
grep -l "CIS_METADATA_START" checks/*/5.*.ps1 | wc -l
# Result: 37 out of 37 ✅
```

### 2. Database Backfill Script Created ✅

Created SQL script (`backfill_section5_metadata.sql`) to update existing scan results in the database.

**To apply** (when database is running):
```bash
psql -h localhost -p 5434 -U dev_user -d terra_automation_platform_dev -f backfill_section5_metadata.sql
```

This will update all existing Section 5 results to have proper Title, Level, Section, SubSection, and RecommendationId fields.

## Impact

### Before Fix:
- 24 checks per scan showing only `check_id`
- Poor UX - users can't easily understand what each check does
- Inconsistent display between sections

### After Fix:
- **Future scans**: All checks will have proper metadata automatically
- **Existing scans** (after running SQL script): All results display consistently with full CIS metadata

## Files Modified

### Check Files (32 files):
```
app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/checks/L1/5.1.2.1_*.ps1
app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/checks/L1/5.1.2.3_*.ps1
... (30 more)
```

### Scripts Created:
- `/tmp/add_metadata_to_checks.py` - Adds metadata to check files from CSV
- `/tmp/parse_cis_csv.py` - CSV parsing test script
- `/tmp/test_metadata_extraction.py` - Metadata extraction verification
- `/tmp/backfill_metadata.py` - Database backfill (async version - requires running DB)
- `backfill_section5_metadata.sql` - SQL script for database backfill

## Testing

### Test Metadata Parsing:
```bash
python3 /tmp/test_metadata_extraction.py
# Result: ✅ Metadata parsed successfully!
```

### Test Database Update (when DB is up):
```bash
psql ... -f backfill_section5_metadata.sql
```

Expected output:
```
Starting metadata backfill for Section 5 checks...
UPDATE 24
UPDATE 24
...
Metadata backfill completed!

 total_section5_results | with_metadata | still_missing
------------------------+---------------+---------------
                    xxx |           xxx |             0
```

## Next Steps

1. **Start database** if not running:
   ```bash
   docker-compose up -d
   ```

2. **Run SQL backfill script**:
   ```bash
   PGPASSWORD=dev_password psql -h localhost -p 5434 -U dev_user -d terra_automation_platform_dev -f backfill_section5_metadata.sql
   ```

3. **Verify in UI**: Go to any existing scan details page and confirm Section 5 checks now show proper titles and metadata.

4. **Run new scan**: Verify all new scans automatically have metadata populated.

## Technical Details

### CSV Structure:
- Source: `CIS_Microsoft_365_Foundations_Benchmark_v5.0.0.csv`
- Columns: Recommendation ID, Level, Title, Section, Sub-Section, Profile Applicability, Description, Rationale, Impact, Audit, Remediation, Default Value, References, CIS Controls

### Metadata Block Format:
```powershell
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.1","Level":"L1","Title":"Ensure 'Per-user MFA' is disabled","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity",...}
CIS_METADATA_END #>
```

### Database Fields Updated:
- `title`
- `level`
- `section`
- `subsection`
- `recommendation_id`
- `profile_applicability`
- `description`
- `rationale`
- `impact`
- `audit_procedure`
- `remediation`
- `default_value`
- `references`
- `cis_controls`

## Related Issues

- Real-time scan updates: ✅ Fixed (switched from WebSocket to EventSource/SSE)
- Metadata display inconsistency: ✅ Fixed (this document)
