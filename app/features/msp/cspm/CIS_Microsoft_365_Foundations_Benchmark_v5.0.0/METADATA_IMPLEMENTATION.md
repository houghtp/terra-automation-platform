# CIS Metadata Implementation

## Overview
CIS benchmark metadata has been embedded into each check file and is now included in all check results for reporting and dashboard purposes.

## Metadata Fields Included

Each check now includes the following metadata from the CIS benchmark:

| Field | Description |
|-------|-------------|
| **RecommendationId** | CIS recommendation ID (e.g., "1.2.2") |
| **Level** | Compliance level (L1 or L2) |
| **Title** | Full check title |
| **Section** | Main section (e.g., "1 Microsoft 365 admin center") |
| **SubSection** | Sub-section (e.g., "1.2 Mailboxes") |
| **ProfileApplicability** | Applicable profiles (E3 Level 1, E5 Level 1, etc.) |
| **Description** | Full description of the control |
| **Rationale** | Why this control is important |
| **Impact** | Impact of implementing this control |
| **Audit** | How to audit this control (UI and PowerShell) |
| **Remediation** | How to remediate non-compliance |
| **DefaultValue** | Default Microsoft 365 configuration |
| **References** | Microsoft documentation links |
| **CISControls** | Mapping to CIS Controls framework (JSON) |

## Implementation Details

### 1. Metadata Storage
Metadata is embedded in each check file as a JSON block in PowerShell comments:

```powershell
<# CIS_METADATA_START
{"RecommendationId":"1.2.2","Level":"L1","Title":"Ensure sign-in to shared mailboxes is blocked",...}
CIS_METADATA_END #>
```

### 2. Metadata Extraction
The `Get-CheckMetadata` function in `Start-Checks.ps1` extracts metadata from check files:

```powershell
function Get-CheckMetadata {
    param([string]$CheckPath)
    
    $content = Get-Content $CheckPath -Raw
    if ($content -match '# CIS_METADATA_START\s*(.*?)\s*CIS_METADATA_END #>') {
        $jsonString = $matches[1]
        return $jsonString | ConvertFrom-Json
    }
    return $null
}
```

### 3. Results Structure
Each check result now includes metadata:

```json
{
  "CheckId": "1.2.2_ensure_sign-in_to_shared_mailboxes_is_blocked",
  "Status": "Fail",
  "TechType": "M365",
  "Category": "L1",
  "TenantId": "660636d5-cb4e-4816-b1b8-f5afc446f583",
  "StartTime": "2025-10-28T19:27:36Z",
  "EndTime": "2025-10-28T19:27:40Z",
  "Duration": 4.6927295,
  "Details": [...],
  "Error": null,
  "Metadata": {
    "RecommendationId": "1.2.2",
    "Level": "L1",
    "Title": "Ensure sign-in to shared mailboxes is blocked",
    "Section": "1 Microsoft 365 admin center",
    "SubSection": "1.2 Mailboxes",
    "ProfileApplicability": "- E3 Level 1\r\n- E5 Level 1",
    "Description": "...",
    "Rationale": "...",
    "Impact": "...",
    "Audit": "...",
    "Remediation": "...",
    "DefaultValue": "...",
    "References": "...",
    "CISControls": "[{...}]"
  }
}
```

## Usage for Dashboards

### Database Storage
Store the entire `Metadata` object in your database along with check results. This allows you to:

1. **Filter by Section**: Group checks by main section for navigation
2. **Filter by Level**: Show only L1 or L2 checks
3. **Filter by Profile**: Filter by E3/E5 applicability
4. **Display References**: Show Microsoft documentation links
5. **Show Remediation**: Display remediation steps for failed checks
6. **Map to CIS Controls**: Show alignment with CIS Controls framework

### Dashboard Examples

#### Compliance by Section
```sql
SELECT 
    Metadata.Section,
    COUNT(*) as TotalChecks,
    SUM(CASE WHEN Status = 'Pass' THEN 1 ELSE 0 END) as PassedChecks,
    SUM(CASE WHEN Status = 'Fail' THEN 1 ELSE 0 END) as FailedChecks
FROM Results
WHERE Metadata IS NOT NULL
GROUP BY Metadata.Section
```

#### Failed Checks with Remediation
```sql
SELECT 
    CheckId,
    Metadata.Title,
    Metadata.Section,
    Metadata.Remediation,
    Metadata.References
FROM Results
WHERE Status = 'Fail'
AND Metadata IS NOT NULL
ORDER BY Metadata.RecommendationId
```

#### CIS Controls Mapping
Extract and display which CIS Controls are covered by parsing the `CISControls` JSON field.

## Scripts

### Add-CheckMetadata.ps1
Adds CIS metadata to check files from the CSV source.

**Usage:**
```powershell
.\Add-CheckMetadata.ps1
```

**Features:**
- Reads metadata from CIS CSV file
- Matches by Recommendation ID
- Embeds metadata as JSON in check files
- Skips files that already have metadata
- Reports progress and summary

### Start-Checks.ps1 (Updated)
Now extracts and includes metadata in all check results.

**New Function:**
- `Get-CheckMetadata`: Extracts metadata from check files

**Updated Behavior:**
- Loads metadata when discovering checks
- Includes metadata in batch execution
- Stores metadata in results JSON

## Statistics

- **Total Check Files**: 130
- **Metadata Added**: 96 checks
- **Skipped**: 34 (filename format doesn't match X.X.X pattern)

## File Format Requirements

For metadata to be extracted, check files must:
1. Start with recommendation ID in format `X.X.X_description.ps1`
2. Have matching entry in CIS CSV file
3. Not already contain metadata block

## Next Steps

1. **Database Schema**: Create tables to store metadata separately or as JSON column
2. **API Endpoints**: Create endpoints to query checks by metadata fields
3. **Dashboard UI**: Build visualizations using metadata groupings
4. **Reporting**: Generate compliance reports with remediation guidance
5. **Trend Analysis**: Track compliance over time by section/level

## Benefits

✅ **Rich Reporting**: Full context for each compliance check  
✅ **Remediation Guidance**: Built-in remediation steps for failures  
✅ **Documentation Links**: Direct links to Microsoft documentation  
✅ **Framework Mapping**: Alignment with CIS Controls framework  
✅ **Filtering**: Flexible filtering by level, section, profile  
✅ **Auditing**: Complete audit procedures included  
