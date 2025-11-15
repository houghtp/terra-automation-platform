# M365 Certificate-Based Authentication Workflow

## Overview
Complete end-to-end workflow for setting up certificate-based authentication for M365 compliance scanning on Linux.

---

## 🔧 One-Time Setup (Per M365 Tenant)

### Step 1: Create App Registration with Certificate

Run the platform-integrated PowerShell script:

```bash
pwsh app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/Create-CISComplianceApp-Platform.ps1 -TenantName "customer1"
```

**What this does:**
- Creates Entra app registration: `CIS-Compliance-Scanner-customer1`
- Generates self-signed certificate with private key
- Exports certificate as PFX with secure password
- Converts PFX to base64 for database storage
- Outputs JSON with all credentials

**Example Output:**
```json
{
  "tenant_id": "660636d5-cb4e-4816-b1b8-f5afc446f583",
  "client_id": "12345678-1234-1234-1234-123456789012",
  "certificate_pfx_base64": "MIIKcAIBAzCCCi4GCSqGSIb3DQEHAaCCCh8Egg...",
  "certificate_password": "x7J9mP2nQ8vR5kL1..."
}
```

### Step 2: Grant API Permissions in Azure Portal

**IMPORTANT:** You must grant admin consent for the app registration in Azure Portal:

1. Navigate to: **Azure Portal** → **Entra ID** → **App registrations** → `CIS-Compliance-Scanner-customer1`
2. Go to: **API permissions**
3. Click: **Grant admin consent for [Tenant]**
4. Verify all permissions show "Granted" status

**Required Permissions:**
- Microsoft Graph (all CIS compliance checks)
- Exchange Online (email security checks)
- SharePoint (file sharing checks)
- Security & Compliance Center (DLP, retention policies)
- Teams (meeting policies)
- Power BI (dashboard security)

---

## 🌐 Platform Configuration

### Step 3: Add M365 Tenant to Platform

1. **Login to Platform** as admin
2. **Navigate to:** MSP → CSPM → M365 Tenants
3. **Click:** "Add M365 Tenant" button
4. **Fill in the form:**

   **Basic Information:**
   - **M365 Tenant ID:** `660636d5-cb4e-4816-b1b8-f5afc446f583` (from Step 1 output)
   - **M365 Domain:** `customer1.onmicrosoft.com`
   - **Description:** "Production tenant for Customer 1"

   **App Registration Credentials:**
   - **Client ID:** `12345678-1234-1234-1234-123456789012` (from Step 1 output)
   - **Client Secret:** (optional - for basic access only)
   - **Certificate PFX (Base64):** Paste the entire `certificate_pfx_base64` string from Step 1 output
   - **Certificate Password:** Paste the `certificate_password` from Step 1 output

5. **Click:** "Create Tenant"

**What happens:**
- M365 tenant record created in database
- All credentials encrypted with AES-256-GCM
- Secrets stored with naming pattern: `m365_{tenant_id}_certificate_pfx`, `m365_{tenant_id}_certificate_password`
- Fully tenant-aware (multi-tenant isolation)

---

## 🔍 Running Compliance Scans

### Step 4: Trigger Scan

1. **Navigate to:** MSP → CSPM → M365 Tenants
2. **Find your tenant** in the list
3. **Click:** "Run Scan" button
4. **Wait for scan to complete** (typically 2-5 minutes)

**Behind the scenes:**
1. Platform retrieves certificate credentials from encrypted secrets
2. Base64 PFX decoded to bytes
3. Temporary certificate file written to `/tmp/cert-{uuid}.pfx`
4. PowerShell script launched with certificate path
5. PowerShell authenticates to ALL M365 services:
   - ✅ Microsoft Graph
   - ✅ Teams (requires certificate)
   - ✅ Exchange Online (requires certificate)
   - ✅ Security & Compliance (requires certificate)
   - ✅ SharePoint
   - ✅ Power BI
6. CIS compliance checks executed (91 controls)
7. Results saved to database
8. Temporary certificate file deleted

### Step 5: View Results

1. **Navigate to:** MSP → CSPM → M365 Tenants
2. **Click:** "View Scans" for your tenant
3. **Select a scan** to view detailed results
4. **Filter by:**
   - Compliance status (Pass/Fail)
   - Control category (Identity, Data, Devices, etc.)
   - Severity level

---

## 🔒 Security Features

### Encryption & Storage
- ✅ **Database encryption:** All credentials encrypted with AES-256-GCM
- ✅ **Tenant isolation:** Multi-tenant aware, automatic filtering by `tenant_id`
- ✅ **No filesystem persistence:** Certificates decoded to temp files, auto-deleted after use
- ✅ **Password masking:** Password fields never shown in UI after creation

### Authentication Methods Comparison

| Method | Services Supported | Security | Recommendation |
|--------|-------------------|----------|----------------|
| **Client Secret** | Graph, SharePoint, Power BI | Good | Basic access only |
| **Certificate PFX** | ALL (Graph, Teams, Exchange, SharePoint, Security & Compliance, Power BI) | Excellent | ✅ **Recommended** |
| ~~Certificate Thumbprint~~ | ~~Windows only~~ | N/A | ❌ Not supported on Linux |
| ~~Username/Password~~ | ~~Legacy~~ | Poor | ❌ Deprecated by Microsoft |

### Why Certificate-Based Auth?

1. **No password expiration:** Certificates don't expire like user passwords
2. **No MFA prompts:** Unattended automation works reliably
3. **Least privilege:** Service principal with specific API permissions only
4. **Audit trail:** All operations logged with application identity
5. **Revocable:** Certificate can be removed from app registration instantly

---

## 🐛 Troubleshooting

### Issue: "Authentication needed. Please call Connect-MgGraph"

**Cause:** Client secret provided but certificate required for specific service

**Solution:** Add Certificate PFX and password to M365 tenant configuration

---

### Issue: "Unix LocalMachine X509Store is limited to Root and CertificateAuthority stores"

**Cause:** PowerShell trying to load certificate from Windows certificate store (thumbprint method)

**Solution:** This is fixed! The platform now uses file-based certificate authentication via PFX.

---

### Issue: "Certificate thumbprint provided but certificate not found"

**Cause:** Old certificate thumbprint field used instead of PFX

**Solution:** Use the new "Certificate PFX (Base64)" field instead of thumbprint

---

### Issue: Scan stuck in "pending" status

**Cause:** Background task worker not running or authentication failed

**Solution:**
1. Check server logs: `journalctl -u terra-automation-platform -f`
2. Verify certificate password is correct
3. Ensure admin consent granted in Azure Portal

---

## 📋 Checklist

Before running your first scan, ensure:

- [ ] App registration created in M365 tenant
- [ ] Certificate generated and exported as PFX
- [ ] Admin consent granted for API permissions in Azure Portal
- [ ] M365 tenant added to platform with certificate PFX and password
- [ ] Server running on Linux (WSL2, Ubuntu, etc.)
- [ ] PowerShell 7+ installed
- [ ] Required PowerShell modules installed (Microsoft.Graph, ExchangeOnlineManagement, etc.)

---

## 🎯 Quick Reference

**Files modified:**
- `app/features/msp/cspm/schemas.py` - Added certificate fields to schemas
- `app/features/msp/cspm/routes/form_routes.py` - Added certificate form parameters
- `app/features/msp/cspm/services/m365_tenant_service.py` - Store/retrieve certificate credentials
- `app/features/msp/cspm/services/powershell_executor.py` - Decode base64 PFX to temp file
- `app/features/msp/cspm/templates/cspm/partials/m365_tenant_form.html` - UI form fields

**PowerShell scripts:**
- `Create-CISComplianceApp-Platform.ps1` - Creates app registration with certificate
- `Connect-M365.ps1` - Handles certificate-based authentication
- `Start-Checks.ps1` - Executes compliance checks

**Secret naming pattern:**
- `m365_{tenant_id}_client_id`
- `m365_{tenant_id}_client_secret`
- `m365_{tenant_id}_certificate_pfx`
- `m365_{tenant_id}_certificate_password`

---

**Last Updated:** 2025-10-28
**Status:** ✅ Production Ready
