# Control: 6.3.1 - Ensure users installing Outlook add-ins is not allowed
<# CIS_METADATA_START
{"Description":"Specify the administrators and users who can install and manage add-ins for Outlook in\nExchange Online\nBy default, users can install add-ins in their Microsoft Outlook Desktop client, allowing\ndata access within the client application.","Impact":"Implementing this change will impact both end users and administrators. End users will\nbe unable to integrate third-party applications they desire, and administrators may\nreceive requests to grant permission for necessary third-party apps.","Audit":"To audit using the UI:\n1. Navigate to Exchange admin center https://admin.exchange.microsoft.com.\n2. Click to expand Roles select User roles.\n3. Select Default Role Assignment Policy.\n4. In the properties pane on the right click on Manage permissions.\n5. Under Other roles verify My Custom Apps, My Marketplace Apps and My\nReadWriteMailboxApps are unchecked.\nNote: As of this release of the Benchmark the manage permissions link no longer\ndisplays anything when a user assigned the Global Reader role clicks on it. Global\nReaders as an alternative can inspect the Roles column or use the PowerShell method\nto perform the audit.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following script:\n$RoleList = @(\n\"My Custom Apps\", \"My Marketplace Apps\", \"My ReadWriteMailbox Apps\"\n)\n$AssignedPolicies = Get-EXOMailbox -PropertySets Policy |\nSelect-Object -Unique RoleAssignmentPolicy\n$Report = foreach ($policy in $AssignedPolicies) {\n$RolePolicy = Get-RoleAssignmentPolicy -Identity `\n$policy.RoleAssignmentPolicy\n$NonCompliantRoles = $RolePolicy.AssignedRoles |\nWhere-Object { $RoleList -eq $_ }\n[pscustomobject]@{\nIdentity = $RolePolicy.Identity\nFailingRoles = if ($NonCompliantRoles) {\n($NonCompliantRoles -join \", \")\n}\nelse { \"None\" }\n}\n}\n$Report\n3. The output will show a list of all assigned policies and along with any roles\nassigned to those policies that are not compliant.\no Verify My Custom Apps, My Marketplace Apps and My\nReadWriteMailboxApps are not present in any policy (Identity) displayed.","Remediation":"To remediate using the UI:\n1. Navigate to Exchange admin center https://admin.exchange.microsoft.com.\n2. Click to expand Roles select User roles.\n3. Select Default Role Assignment Policy.\n4. In the properties pane on the right click on Manage permissions.\n5. Under Other roles uncheck My Custom Apps, My Marketplace Apps and My\nReadWriteMailboxApps.\n6. Click Save changes.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following command:\n$policy = \"Role Assignment Policy - Prevent Add-ins\"\n$roles = \"MyTextMessaging\", \"MyDistributionGroups\", `\n\"MyMailSubscriptions\", \"MyBaseOptions\", \"MyVoiceMail\", `\n\"MyProfileInformation\", \"MyContactInformation\",\n\"MyRetentionPolicies\", `\n\"MyDistributionGroupMembership\"\nNew-RoleAssignmentPolicy -Name $policy -Roles $roles\nSet-RoleAssignmentPolicy -id $policy -IsDefault\n# Assign new policy to all mailboxes\nGet-EXOMailbox -ResultSize Unlimited | Set-Mailbox -RoleAssignmentPolicy\n$policy\nIf you have other Role Assignment Policies modify the last line to filter out your\ncustom policies","Title":"Ensure users installing Outlook add-ins is not allowed","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"6.3 Roles","DefaultValue":"UI - My Custom Apps, My Marketplace Apps, and My ReadWriteMailboxApps are\nchecked\nPowerShell - My Custom Apps My Marketplace Apps and My\nReadWriteMailboxApps are assigned","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"9.4\", \"title\": \"Restrict Unnecessary or Unauthorized Browser and\", \"description\": \"Email Client Extensions Restrict, either through uninstalling or disabling, any unauthorized or - - unnecessary browser or email client plugins, extensions, and add-on applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"5.1\", \"title\": \"Establish Secure Configurations\", \"description\": \"Maintain documented, standard security configuration standards for all - - - authorized operating systems and software.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"6.4\", \"title\": \"Reports\", \"description\": \"This section is intentionally blank and exists to ensure the structure of the benchmark is consistent.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"6.5\", \"title\": \"Settings\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-\nonline/add-ins-for-outlook/specify-who-can-install-and-manage-add-\nins?source=recommendations\n2. https://learn.microsoft.com/en-us/exchange/permissions-exo/role-assignment-\npolicies","Rationale":"Attackers exploit vulnerable or custom add-ins to access user data. Disabling user-\ninstalled add-ins in Microsoft Outlook reduces this threat surface.","Section":"6 Exchange admin center","RecommendationId":"6.3.1"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    $RoleList = @("My Custom Apps", "My Marketplace Apps", "My ReadWriteMailbox Apps")
    $AssignedPolicies = Get-EXOMailbox -PropertySets Policy | Select-Object -Unique RoleAssignmentPolicy
    
    foreach ($policy in $AssignedPolicies) {
        $RolePolicy = Get-RoleAssignmentPolicy -Identity $policy.RoleAssignmentPolicy
        $NonCompliantRoles = $RolePolicy.AssignedRoles | Where-Object { $RoleList -eq $_ }
        
        $isCompliant = if ($NonCompliantRoles) { $false } else { $true }
        
        $resourceResults += [pscustomobject]@{
            Identity      = $RolePolicy.Identity
            FailingRoles  = if ($NonCompliantRoles) { ($NonCompliantRoles -join ", ") } else { "None" }
            IsCompliant   = $isCompliant
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
