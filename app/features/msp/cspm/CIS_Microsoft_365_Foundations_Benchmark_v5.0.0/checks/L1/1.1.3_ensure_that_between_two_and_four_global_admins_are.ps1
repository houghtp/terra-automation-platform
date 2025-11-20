# Control: 1.1.3 - Ensure that between two and four global admins are
<# CIS_METADATA_START
{"Description": "Between two and four global administrators should be designated in the tenant. Ideally,\nthese accounts will not have licenses assigned to them which supports additional\ncontrols found in this benchmark.", "Impact": "The potential impact associated with ensuring compliance with this requirement is\ndependent upon the current number of global administrators configured in the tenant. If\nthere is only one global administrator in a tenant, an additional global administrator will\nneed to be identified and configured. If there are more than four global administrators, a\nreview of role requirements for current global administrators will be required to identify\nwhich of the users require global administrator access.", "Audit": "To audit using the UI:\n1. Navigate to the Microsoft 365 admin center https://admin.microsoft.com\n2. Select Roles > Role assignments.\n3. Select the Global Administrator role from the list and click on Assigned.\n4. Review the list of Global Administrators.\no If there are groups present, then inspect each group and its members.\no Take note of the total number of Global Administrators in and outside of\ngroups.\n5. Ensure the number of Global Administrators is between two and four.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\nDirectory.Read.All\n2. Run the following PowerShell script:\n# Determine Id of GA role using the immutable RoleTemplateId value.\n$GlobalAdminRole = Get-MgDirectoryRole -Filter \"RoleTemplateId eq '62e90394-\n69f5-4237-9190-012177145e10'\"\n$RoleMembers = Get-MgDirectoryRoleMember -DirectoryRoleId $GlobalAdminRole.Id\n$GlobalAdmins = [System.Collections.Generic.List[Object]]::new()\nforeach ($object in $RoleMembers) {\n$Type = $object.AdditionalProperties.'@odata.type'\n# Check for and process role assigned groups\nif ($Type -eq '#microsoft.graph.group') {\n$GroupId = $object.Id\n$GroupMembers = (Get-MgGroupMember -GroupId\n$GroupId).AdditionalProperties\nforeach ($member in $GroupMembers) {\nif ($member.'@odata.type' -eq '#microsoft.graph.user') {\n$GlobalAdmins.Add([PSCustomObject][Ordered]@{\nDisplayName = $member.displayName\nUserPrincipalName = $member.userPrincipalName\n})\n}\n}\n} elseif ($Type -eq '#microsoft.graph.user') {\n$DisplayName = $object.AdditionalProperties.displayName\n$UPN = $object.AdditionalProperties.userPrincipalName\n$GlobalAdmins.Add([PSCustomObject][Ordered]@{\nDisplayName = $DisplayName\nUserPrincipalName = $UPN\n})\n}\n}\n$GlobalAdmins = $GlobalAdmins | select DisplayName,UserPrincipalName -Unique\nWrite-Host \"*** There are\" $GlobalAdmins.Count \"Global Administrators in the\norganization.\"\n3. Review the output and ensure there are between 2 and 4 Global Administrators.\nNote: When tallying the number of Global Administrators, the above does not account\nfor Partner relationships. Those are located under Settings > Partner\nRelationships and should be reviewed on a reoccurring basis.", "Remediation": "To remediate using the UI:\n1. Navigate to the Microsoft 365 admin center https://admin.microsoft.com\n2. Select Users > Active Users.\n3. In the Search field enter the name of the user to be made a Global Administrator.\n4. To create a new Global Admin:\n1. Select the user's name.\n2. A window will appear to the right.\n3. Select Manage roles.\n4. Select Admin center access.\n5. Check Global Administrator.\n6. Click Save changes.\n5. To remove Global Admins:\n1. Select User.\n2. Under Roles select Manage roles\n3. De-Select the appropriate role.\n4. Click Save changes.", "Title": "Ensure that between two and four global admins are designated", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "1.1 Users", "DefaultValue": "", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"5.1\", \"title\": \"Establish and Maintain an Inventory of Accounts\", \"description\": \"Establish and maintain an inventory of all accounts managed in the enterprise. v8 The inventory must include both user and administrator accounts. The inventory, at - - - a minimum, should contain the person's name, username, start/stop dates, and department. Validate that all active accounts are authorized, on a recurring schedule at a minimum quarterly, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"4.1\", \"title\": \"Maintain Inventory of Administrative Accounts\", \"description\": \"v7 Use automated tools to inventory all administrative accounts, including domain - - and local accounts, to ensure that only authorized individuals have elevated privileges.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-\nus/powershell/module/microsoft.graph.identity.directorymanagement/get-\nmgdirectoryrole?view=graph-powershell-1.0\n2. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/permissions-reference#all-roles\n3. https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/best-\npractices#5-limit-the-number-of-global-administrators-to-less-than-5", "Rationale": "If there is only one global administrator, they could perform malicious activities without\nbeing detected by another admin. Designating multiple global administrators eliminates\nthis risk and ensures redundancy if the sole remaining global administrator leaves the\norganization.\nHowever, to minimize the attack surface, there should be no more than four global\nadmins set for any tenant. A large number of global admins increases the likelihood of a\nsuccessful account breach by an external attacker.", "Section": "1 Microsoft 365 admin center", "RecommendationId": "1.1.3"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Determine Id of GA role using the immutable RoleTemplateId value.
    $GlobalAdminRole = Get-MgBetaDirectoryRole -Filter "RoleTemplateId eq '62e90394-69f5-4237-9190-012177145e10'"
    $RoleMembers = Get-MgBetaDirectoryRoleMember -DirectoryRoleId $GlobalAdminRole.Id
    $GlobalAdmins = [System.Collections.Generic.List[Object]]::new()
    
    foreach ($object in $RoleMembers) {
        $Type = $object.AdditionalProperties.'@odata.type'
        
        # Check for and process role assigned groups
        if ($Type -eq '#microsoft.graph.group') {
            $GroupId = $object.Id
            $GroupMembers = (Get-MgBetaGroupMember -GroupId $GroupId).AdditionalProperties
            foreach ($member in $GroupMembers) {
                if ($member.'@odata.type' -eq '#microsoft.graph.user') {
                    $GlobalAdmins.Add([PSCustomObject][Ordered]@{
                        DisplayName = $member.displayName
                        UserPrincipalName = $member.userPrincipalName
                    })
                }
            }
        } elseif ($Type -eq '#microsoft.graph.user') {
            $DisplayName = $object.AdditionalProperties.displayName
            $UPN = $object.AdditionalProperties.userPrincipalName
            $GlobalAdmins.Add([PSCustomObject][Ordered]@{
                DisplayName = $DisplayName
                UserPrincipalName = $UPN
            })
        }
    }
    
    $GlobalAdmins = $GlobalAdmins | Select-Object DisplayName, UserPrincipalName -Unique
    
    # Convert results to standard format
    foreach ($admin in $GlobalAdmins) {
        $resourceResults += [PSCustomObject]@{
            DisplayName = $admin.DisplayName
            UserPrincipalName = $admin.UserPrincipalName
            IsCompliant = $true
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
