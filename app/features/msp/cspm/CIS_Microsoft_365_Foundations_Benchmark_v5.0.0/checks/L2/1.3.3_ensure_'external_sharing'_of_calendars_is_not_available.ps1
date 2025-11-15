# Control: 1.3.3 - Ensure 'External sharing' of calendars is not available
<# CIS_METADATA_START
{"Description":"External calendar sharing allows an administrator to enable the ability for users to share\ncalendars with anyone outside of the organization. Outside users will be sent a URL that\ncan be used to view the calendar.","Impact":"This functionality is not widely used. As a result, it is unlikely that implementation of this\nsetting will cause an impact to most users. Users that do utilize this functionality are\nlikely to experience a minor inconvenience when scheduling meetings or synchronizing\ncalendars with people outside the tenant.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings select Org settings.\n3. In the Services section click Calendar.\n4. Verify Let your users share their calendars with people outside of\nyour organization who have Office 365 or Exchange is unchecked.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following Exchange Online PowerShell command:\nGet-SharingPolicy -Identity \"Default Sharing Policy\" | ft Name,Enabled\n3. Verify Enabled is set to False","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings select Org settings.\n3. In the Services section click Calendar.\n4. Uncheck Let your users share their calendars with people outside\nof your organization who have Office 365 or Exchange.\n5. Click Save.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following Exchange Online PowerShell command:\nSet-SharingPolicy -Identity \"Default Sharing Policy\" -Enabled $False","Title":"Ensure 'External sharing' of calendars is not available","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"1.3 Settings","DefaultValue":"Enabled (True)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"v8 Enterprise Assets and Software - - Uninstall or disable unnecessary services on enterprise assets and software, such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.6\", \"title\": \"Protect Information through Access Control Lists\", \"description\": \"Protect all information stored on systems with file system, network share, v7 claims, application, or database specific access control lists. These controls will - - - enforce the principle that only authorized individuals should have access to the information based on their need to access the information as a part of their responsibilities.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/admin/manage/share-calendars-\nwith-external-users?view=o365-worldwide","Rationale":"Attackers often spend time learning about organizations before launching an attack.\nPublicly available calendars can help attackers understand organizational relationships\nand determine when specific users may be more vulnerable to an attack, such as when\nthey are traveling.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.3.3"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original command to get sharing policy
    $sharingPolicy = Get-SharingPolicy -Identity "Default Sharing Policy"

    # Process the results and convert to standard format
    foreach ($policy in $sharingPolicy) {
        $isCompliant = -not $policy.Enabled
        $resourceResults += @{
            Name = $policy.Name
            Enabled = $policy.Enabled
            IsCompliant = $isCompliant
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
