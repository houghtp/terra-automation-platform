# Check Title Fixes - Examples

**Date**: 2025-11-19
**Total Fixes**: 53 out of 130 checks (41.4%)

---

## Most Notable Fixes

### Section 1: Identity (Users & Access)

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **1.1.2** | Ensure two emergency access accounts have been | Ensure two emergency access accounts have been **defined** ✅ |
| **1.1.3** | Ensure that between two and four global admins are | Ensure that between two and four global admins **are designated** ✅ |
| **1.1.4** | Ensure administrative accounts use licenses with a | Ensure administrative accounts use licenses **with a reduced application footprint** ✅ |
| **1.3.1** | Ensure the 'Password expiration policy' is set to 'Set | Ensure the 'Password expiration policy' is set to **'Set passwords to never expire (recommended)'** ✅ |
| **1.3.5** | Ensure internal phishing protection for Forms is | Ensure internal phishing protection for Forms **is enabled** ✅ |

### Section 2: Email & Defender (Exchange Online)

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **2.1.2** | Ensure the Common Attachment Types Filter is | Ensure the Common Attachment Types Filter **is enabled** ✅ |
| **2.1.3** | Ensure notifications for internal users sending malware | Ensure notifications for internal users sending malware **is Enabled** ✅ |
| **2.1.6** | Ensure Exchange Online Spam Policies are set to | Ensure Exchange Online Spam Policies are set to **'Quarantine'** ✅ |
| **2.1.8** | Ensure that SPF records are published for all Exchange | Ensure that SPF records are published for all Exchange **Online Domains** ✅ |
| **2.1.9** | Ensure that DKIM is enabled for all Exchange Online | Ensure that DKIM is enabled for all Exchange Online **Domains** ✅ |
| **2.1.10** | Ensure DMARC Records for all Exchange Online | Ensure DMARC Records for all Exchange Online **domains are published** ✅ |
| **2.1.14** | Ensure inbound anti-spam policies do not contain | Ensure inbound anti-spam policies do not contain **allowed domains** ✅ |

### Section 2: Priority Accounts & Defender

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **2.4.1** | Ensure priority account protection is enabled and | Ensure priority account protection is enabled and **configured** ✅ |
| **2.4.2** | Ensure priority accounts have 'Strict protection' presets | Ensure priority accounts have 'Strict protection' presets **configured** ✅ |
| **2.4.3** | Ensure Microsoft Defender for Cloud Apps is enabled | Ensure Microsoft Defender for Cloud Apps **is enabled** ✅ |

### Section 3: Data Protection

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **3.3.1** | Ensure Information Protection Sensitivity Label policies | Ensure Information Protection Sensitivity Label policies **are published** ✅ |

### Section 5: Privileged Identity Management (PIM)

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **5.3.1** | Ensure 'Privileged Identity Management' is used to | Ensure 'Privileged Identity Management' **is used to manage roles** ✅ |
| **5.3.3** | Ensure 'Access Reviews' for privileged roles are | Ensure 'Access Reviews' for privileged roles **are configured** ✅ |
| **5.3.4** | Ensure approval is required for Global Administrator | Ensure approval is required for Global Administrator **role activation** ✅ |
| **5.3.5** | Ensure approval is required for privileged role | Ensure approval is required for privileged role **assignment** ✅ |

### Section 6: Exchange Online Configuration

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **6.1.3** | Ensure 'AuditBypassEnabled' is not enabled on | Ensure 'AuditBypassEnabled' is not enabled on **mailboxes** ✅ |
| **6.2.1** | Ensure all forms of mail forwarding are blocked and/or | Ensure all forms of mail forwarding are blocked **and/or disabled** ✅ |
| **6.2.2** | Ensure mail transport rules do not whitelist specific | Ensure mail transport rules do not whitelist specific **domains** ✅ |
| **6.5.1** | Ensure modern authentication for Exchange Online is | Ensure modern authentication for Exchange Online **is enabled** ✅ |
| **6.5.3** | Ensure additional storage providers are restricted in | Ensure additional storage providers are restricted **in Outlook on the web** ✅ |

### Section 7: SharePoint & OneDrive

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **7.2.1** | Ensure modern authentication for SharePoint | Ensure modern authentication for SharePoint **applications is required** ✅ |
| **7.2.2** | Ensure SharePoint and OneDrive integration with | Ensure SharePoint and OneDrive integration with **Azure AD B2B is enabled** ✅ |
| **7.2.5** | Ensure that SharePoint guest users cannot share items | Ensure that SharePoint guest users cannot share items **they don't own** ✅ |
| **7.2.6** | Ensure SharePoint external sharing is managed | Ensure SharePoint external sharing is managed **through domain whitelist/blacklists** ✅ |
| **7.2.7** | Ensure link sharing is restricted in SharePoint and | Ensure link sharing is restricted in SharePoint and **OneDrive** ✅ |
| **7.2.9** | Ensure guest access to a site or OneDrive will expire | Ensure guest access to a site or OneDrive will expire **automatically** ✅ |
| **7.2.10** | Ensure reauthentication with verification code is | Ensure reauthentication with verification code **is restricted** ✅ |
| **7.2.11** | Ensure the SharePoint default sharing link permission | Ensure the SharePoint default sharing link permission **is set to 'View'** ✅ |
| **7.3.1** | Ensure Office 365 SharePoint infected files are | Ensure Office 365 SharePoint infected files are **disallowed for download** ✅ |
| **7.3.2** | Ensure OneDrive sync is restricted for unmanaged | Ensure OneDrive sync is restricted for unmanaged **devices** ✅ |
| **7.3.3** | Ensure custom script execution is restricted on | Ensure custom script execution is restricted on **personal sites** ✅ |
| **7.3.4** | Ensure custom script execution is restricted on site | Ensure custom script execution is restricted on site **collections** ✅ |

### Section 8: Microsoft Teams

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **8.1.1** | Ensure external file sharing in Teams is enabled for | Ensure external file sharing in Teams is enabled for **only approved cloud storage services** ✅ |
| **8.1.2** | Ensure users can't send emails to a channel email | Ensure users can't send emails to a channel email **address** ✅ |
| **8.2.1** | Ensure external domains are restricted in the Teams | Ensure external domains are restricted in the Teams **admin center** ✅ |
| **8.2.2** | Ensure communication with unmanaged Teams users | Ensure communication with unmanaged Teams users **is restricted** ✅ |
| **8.2.3** | Ensure external Teams users cannot initiate | Ensure external Teams users cannot initiate **contact with internal users** ✅ |
| **8.5.2** | Ensure anonymous users and dial-in callers can't start | Ensure anonymous users and dial-in callers can't start **a meeting** ✅ |
| **8.5.7** | Ensure external participants can't give or request | Ensure external participants can't give or request **control** ✅ |

### Section 9: Power Platform & Apps

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **9.1.5** | Ensure 'Interact with and share R and Python' visuals is | Ensure 'Interact with and share R and Python' visuals **is disabled** ✅ |
| **9.1.6** | Ensure 'Allow users to apply sensitivity labels for | Ensure 'Allow users to apply sensitivity labels for **content' is Enabled** ✅ |
| **9.1.10** | Ensure access to APIs by service principals is | Ensure access to APIs by service principals **is controlled** ✅ |
| **9.1.11** | Ensure service principals cannot create and use | Ensure service principals cannot create and use **credentials** ✅ |

### L2 (Advanced) Controls

| Check ID | Before (Truncated) | After (Full Title) |
|----------|-------------------|-------------------|
| **1.2.1** | Ensure that only organizationally managed/approved | Ensure that only organizationally managed/approved **public groups exist** ✅ |
| **1.3.2** | Ensure 'Idle session timeout' is set to '3 hours | Ensure 'Idle session timeout' is set to **'3 hours (or less) for unmanaged devices'** ✅ |
| **1.3.7** | Ensure 'Third-party storage services' are restricted in | Ensure 'Third-party storage services' are restricted in **Microsoft 365 on the web** ✅ |
| **1.3.8** | Ensure that Sways cannot be shared with people | Ensure that Sways cannot be shared with people **outside of your organization** ✅ |
| **2.1.5** | Ensure Safe Attachments for SharePoint, OneDrive, | Ensure Safe Attachments for SharePoint, OneDrive, **and Microsoft Teams is Enabled** ✅ |

---

## Impact on User Experience

### Before Fix:
```
Scan Detail Page:

1.1.2 - Ensure two emergency access accounts have been
1.1.4 - Ensure administrative accounts use licenses with a
2.1.10 - Ensure DMARC Records for all Exchange Online
8.5.2 - Ensure anonymous users and dial-in callers can't start
```

**Problem**: Titles cut off mid-sentence, unclear what the control requires.

### After Fix:
```
Scan Detail Page:

1.1.2 - Ensure two emergency access accounts have been defined
1.1.4 - Ensure administrative accounts use licenses with a reduced application footprint
2.1.10 - Ensure DMARC Records for all Exchange Online domains are published
8.5.2 - Ensure anonymous users and dial-in callers can't start a meeting
```

**Result**: Complete titles, clear understanding of control requirements.

---

## Summary Statistics

- **Total PowerShell checks**: 130
- **Checks with truncated titles**: 53 (41.4%)
- **Checks already correct**: 75 (57.7%)
- **Checks with missing metadata**: 2 (1.5%) - checks 4.1, 4.2

### Breakdown by Section:

| Section | Truncated | Fixed | Percentage |
|---------|-----------|-------|------------|
| 1 (Identity) | 8 | 8 | 100% |
| 2 (Email & Defender) | 11 | 11 | 100% |
| 3 (Data Protection) | 1 | 1 | 100% |
| 5 (PIM) | 4 | 4 | 100% |
| 6 (Exchange) | 6 | 6 | 100% |
| 7 (SharePoint) | 12 | 12 | 100% |
| 8 (Teams) | 7 | 7 | 100% |
| 9 (Power Platform) | 4 | 4 | 100% |

---

## Verification Steps

To verify fixes in database after next scan:

```sql
-- Check specific examples
SELECT recommendation_id, title
FROM cspm_compliance_results
WHERE scan_id = (SELECT id FROM cspm_compliance_scans ORDER BY created_at DESC LIMIT 1)
  AND recommendation_id IN ('1.1.2', '1.1.4', '2.1.10', '8.5.2')
ORDER BY recommendation_id;

-- Expected results:
-- 1.1.2 | Ensure two emergency access accounts have been defined
-- 1.1.4 | Ensure administrative accounts use licenses with a reduced application footprint
-- 2.1.10 | Ensure DMARC Records for all Exchange Online domains are published
-- 8.5.2 | Ensure anonymous users and dial-in callers can't start a meeting
```

---

**Status**: ✅ All 53 titles fixed and ready for testing
