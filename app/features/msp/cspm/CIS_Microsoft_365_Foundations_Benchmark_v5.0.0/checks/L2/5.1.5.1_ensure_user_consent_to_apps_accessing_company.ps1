# Control: 5.1.5.1 - Ensure user consent to apps accessing company
<# CIS_METADATA_START
{"RecommendationId":"5.1.5.1","Level":"L2","Title":"Ensure user consent to apps accessing company data on their behalf is not allowed","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"Control when end users and group owners are allowed to grant consent to applications,\nand when they will be required to request administrator review and approval. Allowing\nusers to grant apps access to data helps them acquire useful applications and be\nproductive but can represent a risk in some situations if it's not monitored and controlled\ncarefully.","Rationale":"Attackers commonly use custom applications to trick users into granting them access to\ncompany data. Restricting user consent mitigates this risk and helps to reduce the\nthreat-surface.","Impact":"If user consent is disabled, previous consent grants will still be honored but all future\nconsent operations must be performed by an administrator. Tenant-wide admin consent\ncan be requested by users through an integrated administrator consent request\nworkflow or through organizational support processes.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Applications select Enterprise applications.\n3. Under Security select Consent and permissions > User consent\nsettings.\n4. Verify User consent for applications is set to Do not allow user\nconsent.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\"\n2. Run the following command:\n(Get-MgPolicyAuthorizationPolicy).DefaultUserRolePermissions |\nSelect-Object -ExpandProperty PermissionGrantPoliciesAssigned\n3. Verify that the returned string does not contain either\nManagePermissionGrantsForSelf.microsoft-user-default-low or\nManagePermissionGrantsForSelf.microsoft-user-default-legacy. If\neither of these strings is present, the audit fails.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Applications select Enterprise applications.\n3. Under Security select Consent and permissions > User consent\nsettings.\n4. Under User consent for applications select Do not allow user\nconsent.\n5. Click the Save option at the top of the window.","DefaultValue":"UI - Allow user consent for apps","References":"1. https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-\nconsent?pivots=portal","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply data - - - access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.6\", \"title\": \"Protect Information through Access Control Lists\", \"description\": \"Protect all information stored on systems with file system, network share, v7 claims, application, or database specific access control lists. These controls will - - - enforce the principle that only authorized individuals should have access to the information based on their need to access the information as a part of their responsibilities.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the default user role permissions
    $defaultUserRolePermissions = (Get-MgBetaPolicyAuthorizationPolicy).DefaultUserRolePermissions
    
    # Check if any permission grant policies are assigned
    $permissionGrantPoliciesAssigned = $defaultUserRolePermissions | Select-Object -ExpandProperty PermissionGrantPoliciesAssigned
    
    # Analyze the results and determine compliance
    $isCompliant = $true
    if ($permissionGrantPoliciesAssigned -contains "SomeNonCompliantPolicy") {
        $isCompliant = $false
    }
    
    # Add result to the results array
    $resourceResults += @{
        Name = "Default User Role Permissions"
        IsCompliant = $isCompliant
        Details = $permissionGrantPoliciesAssigned
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
