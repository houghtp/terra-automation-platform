# Control: 9.1.1 - Ensure guest user access is restricted
<# CIS_METADATA_START
{"Description":"This setting allows business-to-business (B2B) guests access to Microsoft Fabric, and\ncontents that they have permissions to. With the setting turned off, B2B guest users\nreceive an error when trying to access Power BI.\nThe recommended state is Enabled for a subset of the organization or\nDisabled.","Impact":"Security groups will need to be more closely tended to and monitored.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Ensure that Guest users can access Microsoft Fabric adheres to one of\nthese states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Fabric https://app.powerbi.com/admin-portal\n2. Select Tenant settings.\n3. Scroll to Export and Sharing settings.\n4. Set Guest users can access Microsoft Fabric to one of these states:\no State 1: Disabled\no State 2: Enabled with Specific security groups selected and defined.\nImportant: If the organization doesn't actively use this feature it is recommended to\nkeep it Disabled.","Title":"Ensure guest user access is restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"9.1 Tenant settings","DefaultValue":"Enabled for Entire Organization","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply data - - - access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"6.8\", \"title\": \"Define and Maintain Role-Based Access Control\", \"description\": \"Define and maintain role-based access control, through determining and v8 documenting the access rights necessary for each role within the enterprise to - successfully carry out its assigned duties. Perform access control reviews of enterprise assets to validate that all privileges are authorized, on a recurring schedule at a minimum annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-export-\nsharing","Rationale":"Establishing and enforcing a dedicated security group prevents unauthorized access to\nMicrosoft Fabric for guests collaborating in Azure that are new or assigned guest status\nfrom other applications. This upholds the principle of least privilege and uses role-based\naccess control (RBAC). These security groups can also be used for tasks like\nconditional access, enhancing risk management and user accountability across the\norganization.","Section":"9 Microsoft Fabric","RecommendationId":"9.1.1"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the tenant settings for Microsoft Fabric
    $tenantSettings = Get-MgBetaOrganization
    
    # Check the setting for guest user access to Microsoft Fabric
    $guestAccessSetting = $tenantSettings | Where-Object { $_.Name -eq "Guest users can access Microsoft Fabric" }
    
    # Determine compliance based on the setting value
    if ($guestAccessSetting) {
        $currentValue = $guestAccessSetting.Value
        $isCompliant = $currentValue -eq "Disabled" -or ($currentValue -eq "Enabled" -and $guestAccessSetting.SecurityGroups -ne $null)
        
        $resourceResults += @{
            ResourceName = "Guest users can access Microsoft Fabric"
            CurrentValue = $currentValue
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "Guest users can access Microsoft Fabric"
            CurrentValue = "Not Found"
            IsCompliant = $false
        }
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
