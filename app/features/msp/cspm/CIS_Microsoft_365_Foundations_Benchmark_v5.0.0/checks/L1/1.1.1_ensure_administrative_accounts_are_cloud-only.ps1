# Control: 1.1.1 - Ensure Administrative accounts are cloud-only
<# CIS_METADATA_START
{"Description":"Administrative accounts are special privileged accounts that could have varying levels\nof access to data, users, and settings. Regular user accounts should never be utilized\nfor administrative tasks and care should be taken, in the case of a hybrid environment,\nto keep administrative accounts separate from on-prem accounts. Administrative\naccounts should not have applications assigned so that they have no access to\npotentially vulnerable services (EX. email, Teams, SharePoint, etc.) and only access to\nperform tasks as needed for administrative purposes.\nEnsure administrative accounts are not On-premises sync enabled.","Impact":"Administrative users will need to utilize login/logout functionality to switch accounts\nwhen performing administrative tasks, which means they will not benefit from SSO. This\nwill require a migration process from the 'daily driver' account to a dedicated admin\naccount.\nOnce the new admin account is created, permission sets should be migrated from the\n'daily driver' account to the new admin account. This includes both M365 and Azure\nRBAC roles. Failure to migrate Azure RBAC roles could prevent an admin from seeing\ntheir subscriptions/resources while using their admin account.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users and select All users.\n3. To the right of the search box click the Add filter button.\n4. Add the On-premises sync enabled filter and click Apply.\n5. Verify that no user accounts in administrative roles are present in the filtered list.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"RoleManagement.Read.Directory\",\"User.Read.All\"\n2. Run the following PowerShell script:\n$DirectoryRoles = Get-MgDirectoryRole\n# Get privileged role IDs\n$PrivilegedRoles = $DirectoryRoles | Where-Object {\n$_.DisplayName -like \"*Administrator*\" -or $_.DisplayName -eq \"Global\nReader\"\n}\n# Get the members of these various roles\n$RoleMembers = $PrivilegedRoles | ForEach-Object { Get-MgDirectoryRoleMember\n-DirectoryRoleId $_.Id } |\nSelect-Object Id -Unique\n# Retrieve details about the members in these roles\n$PrivilegedUsers = $RoleMembers | ForEach-Object {\nGet-MgUser -UserId $_.Id -Property UserPrincipalName, DisplayName, Id,\nOnPremisesSyncEnabled\n}\n$PrivilegedUsers | Where-Object { $_.OnPremisesSyncEnabled -eq $true } |\nft DisplayName,UserPrincipalName,OnPremisesSyncEnabled\n3. The script will output any hybrid users that are also members of privileged roles.\nIf nothing returns, then no users with that criteria exist.","Remediation":"Remediation will require first identifying the privileged accounts that are synced from on-\npremises and then creating a new cloud-only account for that user. Once a replacement\naccount is established, the hybrid account should have its role reduced to that of a non-\nprivileged user or removed depending on the need.","Title":"Ensure Administrative accounts are cloud-only","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"1.1 Users","DefaultValue":"N/A","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"5.4\", \"title\": \"Restrict Administrator Privileges to Dedicated\", \"description\": \"Administrator Accounts v8 Restrict administrator privileges to dedicated administrator accounts on - - - enterprise assets. Conduct general computing activities, such as internet browsing, email, and productivity suite use, from the user's primary, non-privileged account.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"4.1\", \"title\": \"Maintain Inventory of Administrative Accounts\", \"description\": \"v7 Use automated tools to inventory all administrative accounts, including domain - - and local accounts, to ensure that only authorized individuals have elevated privileges.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/admin/add-users/add-\nusers?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/microsoft-365/enterprise/protect-your-global-\nadministrator-accounts?view=o365-worldwide\n3. https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/best-\npractices#9-use-cloud-native-accounts-for-microsoft-entra-roles\n4. https://learn.microsoft.com/en-us/entra/fundamentals/whatis\n5. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/permissions-reference","Rationale":"In a hybrid environment, having separate accounts will help ensure that in the event of a\nbreach in the cloud, that the breach does not affect the on-prem environment and vice\nversa.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.1.1"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Adapted script logic from the original script
    $DirectoryRoles = Get-MgBetaDirectoryRole

    # Get privileged role IDs
    $PrivilegedRoles = $DirectoryRoles | Where-Object { $_.DisplayName -like "*Administrator*" -or $_.DisplayName -eq "Global Administrator" }

    # Get the members of these various roles
    $RoleMembers = $PrivilegedRoles | ForEach-Object { Get-MgBetaDirectoryRoleMember -DirectoryRoleId $_.Id } | Select-Object Id, @{Name='OdataType';Expression={$_.'@odata.type'}} -Unique

    # Filter only user objects and retrieve details (exclude service principals and groups)
    $PrivilegedUsers = $RoleMembers | Where-Object { $_.'OdataType' -eq '#microsoft.graph.user' } | ForEach-Object {
        try {
            Get-MgBetaUser -UserId $_.Id -Property UserPrincipalName, DisplayName, Id, OnPremisesSyncEnabled
        }
        catch {
            Write-Warning "Failed to retrieve user details for ID $($_.Id): $($_.Exception.Message)"
            # Skip this user and continue with others
            $null
        }
    } | Where-Object { $null -ne $_ }

    # Check if users are cloud-only
    $PrivilegedUsers | ForEach-Object {
        $isCompliant = -not $_.OnPremisesSyncEnabled
        $resourceResults += @{
            DisplayName = $_.DisplayName
            UserPrincipalName = $_.UserPrincipalName
            OnPremisesSyncEnabled = $_.OnPremisesSyncEnabled
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
