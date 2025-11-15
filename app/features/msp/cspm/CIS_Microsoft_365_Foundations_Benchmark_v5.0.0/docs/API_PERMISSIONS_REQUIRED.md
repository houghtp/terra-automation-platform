# Required API Permissions for M365 CIS Compliance Checks

Based on the error analysis, these additional API permissions may be required:

## Microsoft Graph API Permissions

### Identity and Access Management
- `Policy.Read.All` - For Conditional Access policies
- `Directory.Read.All` - For directory settings
- `User.Read.All` - For user MFA status
- `RoleManagement.Read.All` - For privileged roles

### Security and Compliance
- `SecurityEvents.Read.All` - For security alerts
- `InformationProtectionPolicy.Read.All` - For DLP policies
- `Reports.Read.All` - For access reviews

### PowerBI Admin
- `PowerBITenant.Read.All` - For PowerBI settings

## Exchange Online Permissions
The account needs **Exchange Administrator** or **Global Administrator** role for:
- Anti-spam policies
- Safe Links/Attachments
- Transport rules

## SharePoint Online Permissions
- **SharePoint Administrator** role for tenant settings

## Security & Compliance Center
- **Compliance Administrator** role for:
  - DLP policies
  - Sensitivity labels
  - Information protection

## To Grant Permissions:
1. In Azure AD, go to App Registrations > Your App > API Permissions
2. Add the permissions listed above
3. Click "Grant admin consent for [tenant]"

## Alternative: Use Global Administrator
If configuring granular permissions is complex, ensure the account has **Global Administrator** role, which includes all necessary permissions.