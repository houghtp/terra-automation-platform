# M365 CIS Compliance - Certificate Setup Guide

## Overview

This guide explains how to set up certificate-based authentication for M365 CIS compliance scanning on Linux using the Terra Automation Platform.

## Why Certificates?

While Client Secret authentication works for some M365 services, **certificate authentication is required** for:

- ✅ Microsoft Graph (works with both)
- ✅ SharePoint Online (works with both)
- ✅ Power BI (works with both)
- ❌ **Microsoft Teams** (requires certificate)
- ❌ **Exchange Online** (requires certificate)
- ❌ **Security & Compliance** (requires certificate)

## Architecture

### Storage

Certificates are stored **securely in the platform's secrets slice**:

```
secrets table (AES-256 encrypted):
├── m365_{tenant_id}_client_id
├── m365_{tenant_id}_client_secret
├── m365_{tenant_id}_certificate_pfx          ← Base64-encoded PFX file
├── m365_{tenant_id}_certificate_password     ← PFX password
└── m365_{tenant_id}_certificate_thumbprint   ← Certificate thumbprint
```

### Flow

1. **Setup**: Run `Create-CISComplianceApp-Platform.ps1` for each M365 tenant
2. **Storage**: Script outputs JSON → Save to secrets via platform UI/API
3. **Execution**: When scan runs:
   - Python retrieves base64 PFX from secrets
   - Decodes and writes to temp file
   - PowerShell loads cert from temp file
   - Authenticates to all M365 services
   - Temp file deleted after scan

## Setup Steps

### Step 1: Run Certificate Creation Script

On a **Windows machine** or **Windows VM** (certificate generation requires Windows for Azure app registration):

```powershell
# Navigate to the CIS script directory
cd /home/paul/repos/terra-automation-platform/app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0

# Run the platform-integrated setup script
pwsh ./Create-CISComplianceApp-Platform.ps1 -TenantName "customer1"
```

**Important**: Replace `"customer1"` with your actual customer/tenant identifier.

### Step 2: Grant Admin Consent

After the script runs, it will output a URL like:

```
https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{client-id}
```

1. Open this URL in a browser
2. Sign in as **Global Administrator**
3. Click **"Grant admin consent for {organization}"**
4. Click **"Yes"** to approve permissions

### Step 3: Save Credentials to Platform

The script outputs JSON like this:

```json
{
  "tenant_name": "customer1",
  "tenant_id": "REDACTED_TENANT_ID",
  "client_id": "REDACTED_AZURE_CLIENT_ID_2",
  "client_secret": "REDACTED_AZURE_CLIENT_SECRET_2",
  "certificate_thumbprint": "REDACTED_CERTIFICATE_THUMBPRINT",
  "certificate_pfx_base64": "MIIKXAIBAzCCChoGCSqGSIb3DQEHA...[truncated]",
  "certificate_password": "REDACTED_CERTIFICATE_PASSWORD_2"
}
```

**Save these to the platform secrets:**

#### Option A: Via Platform UI

1. Navigate to **Administration → Secrets**
2. Add the following secrets for the M365 tenant:
   - `m365_{m365_tenant_db_id}_client_id` → `{client_id}`
   - `m365_{m365_tenant_db_id}_client_secret` → `{client_secret}`
   - `m365_{m365_tenant_db_id}_certificate_pfx` → `{certificate_pfx_base64}`
   - `m365_{m365_tenant_db_id}_certificate_password` → `{certificate_password}`
   - `m365_{m365_tenant_db_id}_certificate_thumbprint` → `{certificate_thumbprint}`

#### Option B: Via API/Script

```bash
# Get the M365 tenant ID from platform
M365_TENANT_ID="..." # From m365_tenants table

# Save secrets via API
curl -X POST http://127.0.0.1:8000/api/administration/secrets \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "m365_'$M365_TENANT_ID'_client_id",
    "value": "{client_id}",
    "tenant_id": "{platform_tenant_id}"
  }'

# Repeat for all 5 secrets...
```

### Step 4: Test Authentication

After saving secrets, trigger a compliance scan from the platform UI. Check the scan results to verify all services authenticated successfully.

## Troubleshooting

### Issue: "Unix LocalMachine X509Store is limited..."

**Cause**: Script trying to load certificate from Windows cert store on Linux.

**Solution**: Ensure secrets are saved correctly and PowerShell executor is decoding the PFX properly.

### Issue: "Authentication needed. Please call Connect-MgGraph."

**Causes**:
1. Secrets not configured correctly
2. Admin consent not granted
3. Service principal lacks required permissions

**Solution**:
1. Verify all 5 secrets exist in the secrets table
2. Check admin consent in Azure Portal
3. Verify app registration has all required API permissions

### Issue: Teams/Exchange authentication fails

**Cause**: These services require certificate authentication.

**Solution**: Ensure certificate secrets (`certificate_pfx`, `certificate_password`) are configured.

### Issue: Certificate password incorrect

**Cause**: Password mismatch or incorrect encoding.

**Solution**: Re-run the setup script and carefully copy the password from JSON output.

## Security Considerations

✅ **Secure**:
- Certificates stored encrypted in database (AES-256-GCM)
- Per-tenant isolation
- Temporary certificate files deleted after use
- Secrets only accessible with proper authorization

❌ **Do NOT**:
- Commit certificate files to version control
- Share PFX passwords via email/chat
- Store certificates on filesystem permanently
- Use same certificate for multiple environments

## Certificate Rotation

Certificates expire after **2 years**. To rotate:

1. Run `Create-CISComplianceApp-Platform.ps1` again
2. Script will create new certificate
3. Update secrets with new certificate data
4. Old certificate remains valid until expiry

## Required Permissions

The app registration requires these **Application permissions**:

### Microsoft Graph
- User.Read.All
- Group.Read.All
- Directory.Read.All
- Organization.Read.All
- AuditLog.Read.All
- Reports.Read.All
- Policy.Read.All
- Sites.Read.All
- Mail.Read

### Exchange Online
- Exchange.ManageAsApp

### SharePoint Online
- Sites.FullControl.All (via PnP)

### Power BI
- Tenant.Read.All
- Tenant.ReadWrite.All

## References

- [Microsoft Graph permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference)
- [Exchange Online app-only authentication](https://learn.microsoft.com/en-us/powershell/exchange/app-only-auth-powershell-v2)
- [CIS Microsoft 365 Foundations Benchmark](https://www.cisecurity.org/benchmark/microsoft_365)
