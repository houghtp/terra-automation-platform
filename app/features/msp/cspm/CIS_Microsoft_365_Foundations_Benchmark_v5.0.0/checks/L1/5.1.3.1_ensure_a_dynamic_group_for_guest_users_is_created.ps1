# Control: 5.1.3.1 - Ensure a dynamic group for guest users is created
<# CIS_METADATA_START
{"RecommendationId":"5.1.3.1","Level":"L1","Title":"Ensure a dynamic group for guest users is created","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"A dynamic group is a dynamic configuration of security group membership for Microsoft\nEntra ID. Administrators can set rules to populate groups that are created in Entra ID\nbased on user attributes (such as userType, department, or country/region). Members\ncan be automatically added to or removed from a security group based on their\nattributes.\nThe recommended state is to create a dynamic group that includes guest accounts.","Rationale":"Dynamic groups allow for an automated method to assign group membership.\nGuest user accounts will be automatically added to this group and through this existing\nconditional access rules, access controls and other security measures will ensure that\nnew guest accounts are restricted in the same manner as existing guest accounts.","Impact":"","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Groups select All groups.\n3. On the right of the search field click Add filter.\n4. Set Filter to Membership type and Value to Dynamic then apply.\n5. Identify a dynamic group and select it.\n6. Under manage, select Dynamic membership rules and ensure the rule syntax\ncontains (user.userType -eq \"Guest\")\n7. If necessary, inspect other dynamic groups for the value above.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Group.Read.All\"\n2. Run the following commands:\n$groups = Get-MgGroup | Where-Object { $_.GroupTypes -contains\n\"DynamicMembership\" }\n$groups | ft DisplayName,GroupTypes,MembershipRule\n3. Look for a dynamic group containing the rule (user.userType -eq \"Guest\")","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Groups select All groups.\n3. Select New group and assign the following values:\no Group type: Security\no Microsoft Entra roles can be assigned to the group: No\no Membership type: Dynamic User\n4. Select Add dynamic query.\n5. Above the Rule syntax text box, select Edit.\n6. Place the following expression in the box:\n(user.userType -eq \"Guest\")\n7. Select OK and Save\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Group.ReadWrite.All\"\n2. In the script below edit DisplayName and MailNickname as needed and run:\n$params = @{\nDisplayName = \"Dynamic Test Group\"\nMailNickname = \"DynGuestUsers\"\nMailEnabled = $false\nSecurityEnabled = $true\nGroupTypes = \"DynamicMembership\"\nMembershipRule = '(user.userType -eq \"Guest\")'\nMembershipRuleProcessingState = \"On\"\n}\nNew-MgGroup @params","DefaultValue":"Undefined","References":"1. https://learn.microsoft.com/en-us/entra/identity/users/groups-create-rule\n2. https://learn.microsoft.com/en-us/entra/identity/users/groups-dynamic-\nmembership\n3. https://learn.microsoft.com/en-us/entra/external-id/use-dynamic-groups","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications. 5.1.4 Devices This section is intentionally blank and exists to ensure the structure of the benchmark is consistent. 5.1.5 Applications\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()# Retrieve dynamic membership groups
    $groups = Get-MgBetaGroup | Where-Object { $_.GroupTypes -contains "DynamicMembership" }
    
    # Process each group to check for guest user membership rules
    foreach ($group in $groups) {
        $isCompliant = $false
        if ($group.MembershipRule -match "user.userType -eq 'Guest'") {
            $isCompliant = $true
        }
        
        # Add result to the results array
        $resourceResults += @{
            DisplayName = $group.DisplayName
            GroupTypes = $group.GroupTypes
            MembershipRule = $group.MembershipRule
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
