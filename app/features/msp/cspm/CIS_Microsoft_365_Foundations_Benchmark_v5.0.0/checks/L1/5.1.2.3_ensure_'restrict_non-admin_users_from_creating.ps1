# Control: 5.1.2.3 - Ensure 'Restrict non-admin users from creating
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.3","Level":"L1","Title":"Ensure 'Restrict non-admin users from creating tenants' is set to 'Yes'","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Non-privileged users can create tenants in the Microsoft Entra ID and Microsoft Entra\nadministration portal under \"Manage tenant\". The creation of a tenant is recorded in the\nAudit log as category \"DirectoryManagement\" and activity \"Create Company\". By\ndefault, the user who creates a Microsoft Entra tenant is automatically assigned the\nGlobal Administrator role. The newly created tenant doesn't inherit any settings or\nconfigurations.","Rationale":"Restricting tenant creation prevents unauthorized or uncontrolled deployment of\nresources and ensures that the organization retains control over its infrastructure. User\ngeneration of shadow IT could lead to multiple, disjointed environments that can make it\ndifficult for IT to manage and secure the organization's data, especially if other users in\nthe organization began using these tenants for business purposes under the\nmisunderstanding that they were secured by the organization's security team.","Impact":"Non-admin users will need to contact I.T. if they have a valid reason to create a tenant.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity> Users > User settings.\n3. Ensure Restrict non-admin users from creating tenants is set to Yes\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\"\n2. Run the following commands:\n(Get-MgPolicyAuthorizationPolicy).DefaultUserRolePermissions |\nSelect-Object AllowedToCreateTenants\n3. Ensure the returned value is False","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity> Users > User settings.\n3. Set Restrict non-admin users from creating tenants to Yes then Save.\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.ReadWrite.Authorization\"\n2. Run the following commands:\n# Create hashtable and update the auth policy\n$params = @{ AllowedToCreateTenants = $false }\nUpdate-MgPolicyAuthorizationPolicy -DefaultUserRolePermissions $params","DefaultValue":"No - Non-administrators can create tenants.\nAllowedToCreateTenants is True","References":"1. https://learn.microsoft.com/en-us/entra/fundamentals/users-default-\npermissions#restrict-member-users-default-permissions","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    # Removed Connect-MgGraph command as authentication is handled centrally
    $defaultUserRolePermissions = (Get-MgBetaPolicyAuthorizationPolicy).DefaultUserRolePermissions
    $allowedToCreateTenants = $defaultUserRolePermissions.AllowedToCreateTenants

    # Convert results to standard format
    $resourceResults += @{
        Name = "DefaultUserRolePermissions"
        Setting = "AllowedToCreateTenants"
        Value = $allowedToCreateTenants
        IsCompliant = -not $allowedToCreateTenants
    }
    
    # Determine overall status
    $overallStatus = if (($resourceResults | Where-Object { -not $_.IsCompliant })) { 'Fail' } else { 'Pass' }
    $status_id = if ($overallStatus -eq 'Pass') { 1 } else { 3 }
    
    return @{
        status = $overallStatus
        status_id = $status_id
        Details = $resourceResults
    }
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    return @{
        status = "Error"
        status_id = 3
        Details = @()
        Error = $_.Exception.Message
    }
}
