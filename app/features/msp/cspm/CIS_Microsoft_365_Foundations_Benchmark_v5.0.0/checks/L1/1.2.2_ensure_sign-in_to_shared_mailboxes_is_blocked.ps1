# Control: 1.2.2 - Ensure sign-in to shared mailboxes is blocked
<# CIS_METADATA_START
{"Description":"Shared mailboxes are used when multiple people need access to the same mailbox,\nsuch as a company information or support email address, reception desk, or other\nfunction that might be shared by multiple people.\nUsers with permissions to the group mailbox can send as or send on behalf of the\nmailbox email address if the administrator has given that user permissions to do that.\nThis is particularly useful for help and support mailboxes because users can send\nemails from \"Contoso Support\" or \"Building A Reception Desk.\"\nShared mailboxes are created with a corresponding user account using a system\ngenerated password that is unknown at the time of creation.\nThe recommended state is Sign in blocked for Shared mailboxes.","Impact":"","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com/\n2. Click to expand Teams & groups and select Shared mailboxes.\n3. Take note of all shared mailboxes.\n4. Click to expand Users and select Active users.\n5. Select a shared mailbox account to open its properties pane, and review.\n6. Ensure the text under the name reads Sign-in blocked.\n7. Repeat for any additional shared mailboxes.\nNote: If sign-in is not blocked there will be an option to Block sign-in. This means the\nshared mailbox is out of compliance with this recommendation.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline\n2. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"User.Read.All\"\n3. Run the following PowerShell commands:\n$MBX = Get-EXOMailbox -RecipientTypeDetails SharedMailbox -ResultSize\nUnlimited\n$MBX | ForEach-Object { Get-MgUser -UserId $_.ExternalDirectoryObjectId `\n-Property DisplayName, UserPrincipalName, AccountEnabled } |\nFormat-Table DisplayName, UserPrincipalName, AccountEnabled\n4. Ensure AccountEnabled is set to False for all Shared Mailboxes.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com/\n2. Click to expand Teams & groups and select Shared mailboxes.\n3. Take note of all shared mailboxes.\n4. Click to expand Users and select Active users.\n5. Select a shared mailbox account to open it's properties pane and then select\nBlock sign-in.\n6. Check the box for Block this user from signing in.\n7. Repeat for any additional shared mailboxes.\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"User.ReadWrite.All\"\n2. Connect to Exchange Online using Connect-ExchangeOnline.\n3. To disable sign-in for a single account:\n$MBX = Get-EXOMailbox -Identity TestUser@example.com\nUpdate-MgUser -UserId $MBX.ExternalDirectoryObjectId -AccountEnabled:$false\n3. The following will block sign-in to all Shared Mailboxes.\n$MBX = Get-EXOMailbox -RecipientTypeDetails SharedMailbox\n$MBX | ForEach-Object { Update-MgUser -UserId $_.ExternalDirectoryObjectId -\nAccountEnabled:$false }","Title":"Ensure sign-in to shared mailboxes is blocked","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"1.2 Teams & groups","DefaultValue":"AccountEnabled: True","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"1.3\", \"title\": \"Settings\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/admin/email/about-shared-\nmailboxes?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/microsoft-365/admin/email/create-a-shared-\nmailbox?view=o365-worldwide#block-sign-in-for-the-shared-mailbox-account\n3. https://learn.microsoft.com/en-us/microsoft-365/enterprise/block-user-accounts-\nwith-microsoft-365-powershell?view=o365-worldwide#block-individual-user-\naccounts","Rationale":"The intent of the shared mailbox is the only allow delegated access from other\nmailboxes. An admin could reset the password, or an attacker could potentially gain\naccess to the shared mailbox allowing the direct sign-in to the shared mailbox and\nsubsequently the sending of email from a sender that does not have a unique identity.\nTo prevent this, block sign-in for the account that is associated with the shared mailbox.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.2.2"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands
# REWRITTEN: Now uses Graph-only cmdlets (previously used Exchange + Graph)

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Get all users and filter for shared mailboxes using Graph
    # SharedMailbox users typically have RecipientTypeDetails set in Exchange
    # In Graph, we identify them by:
    # 1. UserType = "Member" (not Guest)
    # 2. AssignedLicenses is empty or has specific shared mailbox SKU
    # 3. AccountEnabled should be False for compliance

    # Get all users with shared mailbox characteristics
    # Note: Graph doesn't have direct RecipientTypeDetails, so we check users without licenses
    # that match shared mailbox pattern (MailNickname exists but no licenses)
    # Note: We can't use "mail ne null" filter (NotEqualsMatch not supported), so we filter after retrieval
    $allUsers = Get-MgBetaUser -All -Property Id, DisplayName, UserPrincipalName, AccountEnabled, AssignedLicenses, Mail, MailNickname -Filter "userType eq 'Member'" | Where-Object { $null -ne $_.Mail }

    # Shared mailboxes typically:
    # - Have no licenses assigned (AssignedLicenses is empty)
    # - Have Mail/MailNickname set
    # - Should have AccountEnabled = False
    $sharedMailboxUsers = $allUsers | Where-Object {
        $_.AssignedLicenses.Count -eq 0 -and
        $null -ne $_.Mail -and
        $null -ne $_.MailNickname
    }

    # Check each shared mailbox for sign-in status
    foreach ($user in $sharedMailboxUsers) {
        $isCompliant = -not $user.AccountEnabled
        $resourceResults += @{
            DisplayName = $user.DisplayName
            UserPrincipalName = $user.UserPrincipalName
            AccountEnabled = $user.AccountEnabled
            IsCompliant = $isCompliant
        }
    }

    # If no shared mailboxes found, mark as Pass (nothing to check)
    if ($sharedMailboxUsers.Count -eq 0) {
        $resourceResults += @{
            DisplayName = "No shared mailboxes found"
            UserPrincipalName = "N/A"
            AccountEnabled = "N/A"
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
