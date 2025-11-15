# Control: 9.1.3 - Ensure guest access to content is restricted
<# CIS_METADATA_START
{"Description":"This setting allows Microsoft Entra B2B guest users to have full access to the browsing\nexperience using the left-hand navigation pane in the organization. Guest users who\nhave been assigned workspace roles or specific item permissions will continue to have\nthose roles and/or permissions, even if this setting is disabled.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.","Impact":"Security groups will need to be more closely tended to and monitored.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Ensure that Guest users can browse and access Fabric content adheres\nto one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Set Guest users can browse and access Fabric content to one of these\nstates:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Title":"Ensure guest access to content is restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Disabled","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply data - - - access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.6\", \"title\": \"Protect Information through Access Control Lists\", \"description\": \"Protect all information stored on systems with file system, network share, v7 claims, application, or database specific access control lists. These controls will - - - enforce the principle that only authorized individuals should have access to the information based on their need to access the information as a part of their responsibilities.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-\nsharing","Rationale":"Establishing and enforcing a dedicated security group prevents unauthorized access to\nMicrosoft Fabric for guests collaborating in Entra that are new or assigned guest status\nfrom other applications. This upholds the principle of least privilege and uses role-based\naccess control (RBAC). These security groups can also be used for tasks like\nconditional access, enhancing risk management and user accountability across the\norganization.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.3"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve tenant settings related to guest access
    $tenantSettings = Get-MgBetaOrganization | Where-Object { $_.DisplayName -eq "TenantSettings" }
    
    # Check the specific setting for guest access
    $guestAccessSetting = $tenantSettings | Select-Object -ExpandProperty "GuestUsersCanBrowseAndAccessFabricContent"
    
    # Determine compliance based on the setting value
    $isCompliant = $false
    if ($guestAccessSetting -eq "Disabled" -or ($guestAccessSetting -eq "Enabled" -and $tenantSettings.SpecificSecurityGroups -ne $null)) {
        $isCompliant = $true
    }
    
    # Add result to the results array
    $resourceResults += @{
        ResourceName = "Guest Access to Fabric Content"
        CurrentValue = $guestAccessSetting
        IsCompliant = $isCompliant
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
