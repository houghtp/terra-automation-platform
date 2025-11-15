# Control: 1.1.4 - Ensure administrative accounts use licenses with a
<# CIS_METADATA_START
{"Description":"Administrative accounts are special privileged accounts that could have varying levels\nof access to data, users, and settings. A license can enable an account to gain access\nto a variety of different applications, depending on the license assigned.\nThe recommended state is to not license a privileged account or use licenses without\nassociated applications such as Microsoft Entra ID P1 or Microsoft Entra ID\nP2.","Impact":"Administrative users will have to switch accounts and utilize login/logout functionality\nwhen performing administrative tasks, as well as not benefiting from SSO.\nNote: Alerts will be sent to TenantAdmins, including Global Administrators, by default.\nTo ensure proper receipt, configure alerts to be sent to security or operations staff with\nvalid email addresses or a security operations center. Otherwise, after adoption of this\nrecommendation, alerts sent to TenantAdmins may go unreceived due to the lack of an\napplication-based license assigned to the Global Administrator accounts.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Users select Active users.\n3. Sort by the Licenses column.\n4. For each user account in an administrative role verify the account is assigned a\nlicense that is not associated with applications i.e. (Microsoft Entra ID P1,\nMicrosoft Entra ID P2).\no If an organization uses PIM to elevate a daily driver account to privileged\nlevels, this control and licensing requirement can be considered satisfied.\nNote: The final step assumes PIM is properly configured to best practices. Accounts\neligible for the Global Administrator role should require approval to activate. Using the\nPIM blade to permanently assign accounts to privileged roles would not satisfy this audit\nprocedure.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"RoleManagement.Read.Directory\",\"User.Read.All\"\n2. Run the following PowerShell script:\n$DirectoryRoles = Get-MgDirectoryRole\n# Get privileged role IDs\n$PrivilegedRoles = $DirectoryRoles | Where-Object {\n$_.DisplayName -like \"*Administrator*\" -or $_.DisplayName -eq \"Global\nReader\"\n}\n# Get the members of these various roles\n$RoleMembers = $PrivilegedRoles | ForEach-Object { Get-MgDirectoryRoleMember\n-DirectoryRoleId $_.Id } |\nSelect-Object Id -Unique\n# Retrieve details about the members in these roles\n$PrivilegedUsers = $RoleMembers | ForEach-Object {\nGet-MgUser -UserId $_.Id -Property UserPrincipalName, DisplayName, Id\n}\n$Report = [System.Collections.Generic.List[Object]]::new()\nforeach ($Admin in $PrivilegedUsers) {\n$License = $null\n$License = (Get-MgUserLicenseDetail -UserId $Admin.id).SkuPartNumber -\njoin \", \"\n$Object = [pscustomobject][ordered]@{\nDisplayName = $Admin.DisplayName\nUserPrincipalName = $Admin.UserPrincipalName\nLicense = $License\n}\n$Report.Add($Object)\n}\n$Report\n3. The output will display users assigned privileged roles alongside their assigned\nlicenses. Additional manual assessment is required to determine if the licensing\nis appropriate for the user.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Users select Active users\n3. Click Add a user.\n4. Fill out the appropriate fields for Name, user, etc.\n5. When prompted to assign licenses select as needed Microsoft Entra ID P1\nor Microsoft Entra ID P2, then click Next.\n6. Under the Option settings screen you may choose from several types of\nprivileged roles. Choose Admin center access followed by the appropriate role\nthen click Next.\n7. Select Finish adding.\nNote: Utilizing PIM to best practices will satisfy this control. CIS and Microsoft\nrecommend an organization keep zero permanently active assignments for roles other\nthan emergency access accounts.","Title":"Ensure administrative accounts use licenses with a","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"1.1 Users","DefaultValue":"N/A","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"5.4\", \"title\": \"Restrict Administrator Privileges to Dedicated\", \"description\": \"Administrator Accounts v8 Restrict administrator privileges to dedicated administrator accounts on - - - enterprise assets. Conduct general computing activities, such as internet browsing, email, and productivity suite use, from the user's primary, non-privileged account.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"4.1\", \"title\": \"Maintain Inventory of Administrative Accounts\", \"description\": \"v7 Use automated tools to inventory all administrative accounts, including domain - - and local accounts, to ensure that only authorized individuals have elevated privileges.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"1.2\", \"title\": \"Teams & groups\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/enterprise/protect-your-global-\nadministrator-accounts?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/entra/fundamentals/whatis#what-are-the-\nmicrosoft-entra-id-licenses\n3. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/permissions-reference\n4. https://learn.microsoft.com/en-us/microsoft-365/business-premium/m365bp-\nprotect-admin-accounts?view=o365-worldwide\n5. https://learn.microsoft.com/en-us/microsoft-365/enterprise/subscriptions-licenses-\naccounts-and-tenants-for-microsoft-cloud-offerings?view=o365-\nworldwide#licenses\n6. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/pim-deployment-plan#principle-of-least-privilege","Rationale":"Ensuring administrative accounts do not use licenses with applications assigned to\nthem will reduce the attack surface of high privileged identities in the organization's\nenvironment. Granting access to a mailbox or other collaborative tools increases the\nlikelihood that privileged users might interact with these applications, raising the risk of\nexposure to social engineering attacks or malicious content. These activities should be\nrestricted to an unprivileged 'daily driver' account.\nNote: In order to participate in Microsoft 365 security services such as Identity\nProtection, PIM and Conditional Access an administrative account will need a license\nattached to it. Ensure that the license used does not include any applications with\npotentially vulnerable services by using either Microsoft Entra ID P1 or Microsoft\nEntra ID P2 for the cloud-only account with administrator roles.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.1.4"}
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
    $PrivilegedRoles = $DirectoryRoles | Where-Object { $_.DisplayName -like "*Administrator*" -or $_.DisplayName -eq "Global" }

    # Get the members of these various roles
    $RoleMembers = $PrivilegedRoles | ForEach-Object { Get-MgBetaDirectoryRoleMember -DirectoryRoleId $_.Id } | Select-Object Id, @{Name='OdataType';Expression={$_.'@odata.type'}} -Unique

    # Filter only user objects and retrieve details (exclude service principals and groups)
    $PrivilegedUsers = $RoleMembers | Where-Object { $_.'OdataType' -eq '#microsoft.graph.user' } | ForEach-Object {
        try {
            Get-MgBetaUser -UserId $_.Id -Property UserPrincipalName, DisplayName, Id
        }
        catch {
            Write-Warning "Failed to retrieve user details for ID $($_.Id): $($_.Exception.Message)"
            # Skip this user and continue with others
            $null
        }
    } | Where-Object { $null -ne $_ }

    foreach ($Admin in $PrivilegedUsers) {
        $License = $null
        $License = (Get-MgBetaUserLicenseDetail -UserId $Admin.id).SkuPartNumber -join ", "

        $Object = [pscustomobject][ordered]@{
            DisplayName = $Admin.DisplayName
            UserPrincipalName = $Admin.UserPrincipalName
            Licenses = $License
            IsCompliant = if ($License) { $true } else { $false }
        }
        $resourceResults.Add($Object)
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
