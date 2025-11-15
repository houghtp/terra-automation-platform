# Control: 6.1.2 - Ensure mailbox audit actions are configured
<# CIS_METADATA_START
{"Description":"Mailbox audit logging is turned on by default in all organizations. This effort started in\nJanuary 2019, and means that certain actions performed by mailbox owners, delegates,\nand admins are automatically logged. The corresponding mailbox audit records are\navailable for admins to search in the mailbox audit log.\nMailboxes and shared mailboxes have actions assigned to them individually in order to\naudit the data the organization determines valuable at the mailbox level.\nThe recommended state per mailbox is AuditEnabled to True including all default audit\nactions with additional actions outlined below in the audit and remediation sections.\nNote: Audit (Standard) licensing allows for up to 180 days log retention as of October\n2023.","Impact":"Adding additional audit action types and increasing the AuditLogAgeLimit from 90 to\n180 days will have a limited impact on mailbox storage. Mailbox audit log records are\nstored in a subfolder (named Audits) in the Recoverable Items folder in each user's\nmailbox.\n- Mailbox audit records count against the storage quota of the Recoverable Items\nfolder.\n- Mailbox audit records also count against the folder limit for the Recoverable\nItems folder. A maximum of 3 million items (audit records) can be stored in the\nAudits subfolder.\nThe following cmdlet in Exchange Online PowerShell can be run to display the size and\nnumber of items in the Audits subfolder in the Recoverable Items folder:\nGet-MailboxFolderStatistics -Identity <MailboxIdentity> -FolderScope\nRecoverableItems |\nWhere-Object {$_.Name -eq 'Audits'} | Format-List\nFolderPath,FolderSize,ItemsInFolder\nNote: It's unlikely that mailbox auditing on by default impacts the storage quota or the\nfolder limit for the Recoverable Items folder.","Audit":"Inspect each UserMailbox and ensure AuditEnabled is True and the following audit\nactions are included in addition to default actions of each sign-in type.\n- Admin actions: Copy, FolderBind and Move.\n- Delegate actions: FolderBind and Move.\n- Owner actions: Create, MailboxLogin and Move.\nNote: The defaults can be found in the Default Value section and the combined total\ncan be found in the scripts of the Audit/Remediation sections.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell script:\n$MailAudit = Get-EXOMailbox -PropertySets Audit -ResultSize Unlimited |\nSelect-Object UserPrincipalName, AuditEnabled, AuditAdmin, AuditDelegate,\nAuditOwner\n$MailAudit | Export-Csv -Path C:\\CIS\\AuditSettings.csv -NoTypeInformation\n3. Analyze the output and verify AuditEnabled is set to True and all audit actions\nare included in what is defined in the script in the remediation section.\nOptionally, this more comprehensive script can assess each user mailbox:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Execute the following script to verify the audit actions of each mailbox:\n$AdminActions = @(\n\"ApplyRecord\", \"Copy\", \"Create\", \"FolderBind\", \"HardDelete\",\n\"MailItemsAccessed\", \"Move\", \"MoveToDeletedItems\", \"SendAs\",\n\"SendOnBehalf\", \"Send\", \"SoftDelete\", \"Update\",\n\"UpdateCalendarDelegation\",\n\"UpdateFolderPermissions\", \"UpdateInboxRules\"\n)\n$DelegateActions = @(\n\"ApplyRecord\", \"Create\", \"FolderBind\", \"HardDelete\", \"Move\",\n\"MailItemsAccessed\", \"MoveToDeletedItems\", \"SendAs\", \"SendOnBehalf\",\n\"SoftDelete\", \"Update\", \"UpdateFolderPermissions\", \"UpdateInboxRules\"\n)\n$OwnerActions = @(\n\"ApplyRecord\", \"Create\", \"HardDelete\", \"MailboxLogin\", \"Move\",\n\"MailItemsAccessed\", \"MoveToDeletedItems\", \"Send\", \"SoftDelete\",\n\"Update\",\n\"UpdateCalendarDelegation\", \"UpdateFolderPermissions\", \"UpdateInboxRules\"\n)\nfunction VerifyActions {\nparam (\n[string]$type,\n[array]$actions,\n[array]$auditProperty,\n[string]$mailboxName\n)\n$missingActions = @()\n$actionCount = 0\nforeach ($action in $actions) {\nif ($auditProperty -notcontains $action) {\n$missingActions += \" Failure: Audit action '$action' missing\nfrom $type\"\n$actionCount++\n}\n}\nif ($actionCount -eq 0) {\nWrite-Host \"[$mailboxName]: $type actions are verified.\" -\nForegroundColor Green\n} else {\nWrite-Host \"[$mailboxName]: $type actions are not all verified.\" -\nForegroundColor Red\nforeach ($missingAction in $missingActions) {\nWrite-Host \" $missingAction\" -ForegroundColor Red\n}\n}\n}\n$mailboxes = Get-EXOMailbox -PropertySets Audit,Minimum -ResultSize Unlimited\n|\nWhere-Object { $_.RecipientTypeDetails -eq \"UserMailbox\" }\nforeach ($mailbox in $mailboxes) {\nWrite-Host \"--- Now assessing [$($mailbox.UserPrincipalName)] ---\"\nif ($mailbox.AuditEnabled) {\nWrite-Host \"[$($mailbox.UserPrincipalName)]: AuditEnabled is true\" -\nForegroundColor Green\n} else {\nWrite-Host \"[$($mailbox.UserPrincipalName)]: AuditEnabled is false\" -\nForegroundColor Red\n}\nVerifyActions -type \"AuditAdmin\" -actions $AdminActions -auditProperty\n$mailbox.AuditAdmin `\n-mailboxName $mailbox.UserPrincipalName\nVerifyActions -type \"AuditDelegate\" -actions $DelegateActions -\nauditProperty $mailbox.AuditDelegate `\n-mailboxName $mailbox.UserPrincipalName\nVerifyActions -type \"AuditOwner\" -actions $OwnerActions -auditProperty\n$mailbox.AuditOwner `\n-mailboxName $mailbox.UserPrincipalName\nWrite-Host\n}\n3. The script will inspect the audit actions in each sign-in type for every mailbox and\noutput the results to the console. Mailboxes missing audit actions will be\nhighlighted in red, along with the specific audit actions missing from each\ncategory.\nNote: Mailboxes with Audit (Premium) licenses, which is included with E5, can retain\naudit logs beyond 180 days.","Remediation":"For each UserMailbox ensure AuditEnabled is True and the following audit actions\nare included in addition to default actions of each sign-in type.\n- Admin actions: Copy, FolderBind and Move.\n- Delegate actions: FolderBind and Move.\n- Owner actions: Create, MailboxLogin and Move.\nNote: The defaults can be found in the Default Value section and the combined total\ncan be found in the scripts of the Audit/Remediation sections.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell script to remediate every 'UserMailbox' in the\norganization:\n$AuditAdmin = @(\n\"ApplyRecord\", \"Copy\", \"Create\", \"FolderBind\", \"HardDelete\",\n\"MailItemsAccessed\", \"Move\", \"MoveToDeletedItems\", \"SendAs\",\n\"SendOnBehalf\", \"Send\", \"SoftDelete\", \"Update\",\n\"UpdateCalendarDelegation\",\n\"UpdateFolderPermissions\", \"UpdateInboxRules\"\n)\n$AuditDelegate = @(\n\"ApplyRecord\", \"Create\", \"FolderBind\", \"HardDelete\", \"Move\",\n\"MailItemsAccessed\", \"MoveToDeletedItems\", \"SendAs\", \"SendOnBehalf\",\n\"SoftDelete\", \"Update\", \"UpdateFolderPermissions\", \"UpdateInboxRules\"\n)\n$AuditOwner = @(\n\"ApplyRecord\", \"Create\", \"HardDelete\", \"MailboxLogin\", \"Move\",\n\"MailItemsAccessed\", \"MoveToDeletedItems\", \"Send\", \"SoftDelete\",\n\"Update\",\n\"UpdateCalendarDelegation\", \"UpdateFolderPermissions\", \"UpdateInboxRules\"\n)\n$MBX = Get-EXOMailbox -ResultSize Unlimited | Where-Object {\n$_.RecipientTypeDetails -eq \"UserMailbox\" }\n$MBX | Set-Mailbox -AuditEnabled $true `\n-AuditLogAgeLimit 180 -AuditAdmin $AuditAdmin -AuditDelegate $AuditDelegate `\n-AuditOwner $AuditOwner\n3. The script will apply the prescribed Audit Actions for each sign-in type (Owner,\nDelegate, Admin) and the AuditLogAgeLimit to each UserMailbox in the\norganization.\nNote: Mailboxes with Audit (Premium) licenses, which is included with E5, can retain\naudit logs beyond 180 days.","Title":"Ensure mailbox audit actions are configured","ProfileApplicability":"- E5 Level 1\n- E3 Level 1","SubSection":"6.1 Audit","DefaultValue":"AuditEnabled: True for all mailboxes except below:\n- Resource Mailboxes\n- Public Folder Mailboxes\n- DiscoverySearch Mailbox\nAuditAdmin: ApplyRecord, Create, HardDelete, MailItemsAccessed,\nMoveToDeletedItems, Send, SendAs, SendOnBehalf, SoftDelete, Update,\nUpdateCalendarDelegation, UpdateFolderPermissions, UpdateInboxRules\nAuditDelegate: ApplyRecord, Create, HardDelete, MailItemsAccessed,\nMoveToDeletedItems, SendAs, SendOnBehalf, SoftDelete, Update,\nUpdateFolderPermissions, UpdateInboxRules\nAuditOwner: ApplyRecord, HardDelete, MailItemsAccessed, MoveToDeletedItems,\nSend, SoftDelete, Update, UpdateCalendarDelegation, UpdateFolderPermissions,\nUpdateInboxRules","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"8.2\", \"title\": \"Collect Audit Logs\", \"description\": \"Collect audit logs. Ensure that logging, per the enterprise's audit log - - - management process, has been enabled across enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Activate audit logging\", \"description\": \"Ensure that local logging has been enabled on all systems and networking - - - devices.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/purview/audit-mailboxes?view=o365-worldwide","Rationale":"Whether it is for regulatory compliance or for tracking unauthorized configuration\nchanges in Microsoft 365, enabling mailbox auditing and ensuring the proper mailbox\nactions are accounted for allows for Microsoft 365 teams to run security operations,\nforensics or general investigations on mailbox activities.\nThe following mailbox types ignore the organizational default and must have\nAuditEnabled set to True at the mailbox level in order to capture relevant audit data.\n- Resource Mailboxes\n- Public Folder Mailboxes\n- DiscoverySearch Mailbox","Section":"6 Exchange admin center","RecommendationId":"6.1.2"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Define audit actions
    $AdminActions = @(
        "ApplyRecord", "Copy", "Create", "FolderBind", "HardDelete", "MailItemsAccessed", "Move", "MoveToDeletedItems", "SendAs", "SendOnBehalf", "Send", "SoftDelete", "Update", "UpdateCalendarDelegation", "UpdateFolderPermissions", "UpdateInboxRules"
    )
    $DelegateActions = @(
        "ApplyRecord", "Create", "FolderBind", "HardDelete", "Move", "MailItemsAccessed", "MoveToDeletedItems", "SendAs", "SendOnBehalf", "SoftDelete", "Update", "UpdateFolderPermissions", "UpdateInboxRules"
    )
    $OwnerActions = @(
        "ApplyRecord", "Create", "HardDelete", "MailboxLogin", "Move", "MailItemsAccessed", "MoveToDeletedItems", "Send", "SoftDelete", "Update", "UpdateCalendarDelegation", "UpdateFolderPermissions", "UpdateInboxRules"
    )

    function VerifyActions {
        param (
            [string]$type, 
            [array]$actions, 
            [array]$auditProperty, 
            [string]$mailboxName
        )
        $missingActions = @()
        $actionCount = 0
        foreach ($action in $actions) {
            if ($auditProperty -notcontains $action) {
                $missingActions += "Failure: Audit action '$action' missing from $type"
                $actionCount++
            }
        }
        if ($actionCount -eq 0) {
            return @{
                MailboxName = $mailboxName
                Type = $type
                IsCompliant = $true
                MissingActions = @()
            }
        } else {
            return @{
                MailboxName = $mailboxName
                Type = $type
                IsCompliant = $false
                MissingActions = $missingActions
            }
        }
    }

    # Retrieve mailboxes
    $mailboxes = Get-EXOMailbox -PropertySets Audit,Minimum -ResultSize Unlimited | Where-Object { $_.RecipientTypeDetails -eq "UserMailbox" }
    foreach ($mailbox in $mailboxes) {
        $auditResults = @()
        if ($mailbox.AuditEnabled) {
            $auditResults += VerifyActions -type "Admin" -actions $AdminActions -auditProperty $mailbox.AuditAdmin -mailboxName $mailbox.UserPrincipalName
            $auditResults += VerifyActions -type "Delegate" -actions $DelegateActions -auditProperty $mailbox.AuditDelegate -mailboxName $mailbox.UserPrincipalName
            $auditResults += VerifyActions -type "Owner" -actions $OwnerActions -auditProperty $mailbox.AuditOwner -mailboxName $mailbox.UserPrincipalName
        } else {
            $auditResults += @{
                MailboxName = $mailbox.UserPrincipalName
                Type = "AuditEnabled"
                IsCompliant = $false
                MissingActions = "Audit is not enabled"
            }
        }
        $resourceResults += $auditResults
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
