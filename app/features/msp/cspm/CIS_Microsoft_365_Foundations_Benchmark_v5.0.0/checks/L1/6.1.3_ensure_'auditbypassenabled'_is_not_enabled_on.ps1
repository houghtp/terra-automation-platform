# Control: 6.1.3 - Ensure 'AuditBypassEnabled' is not enabled on
<# CIS_METADATA_START
{"Description":"When configuring a user or computer account to bypass mailbox audit logging, the\nsystem will not record any access, or actions performed by the said user or computer\naccount on any mailbox. Administratively this was introduced to reduce the volume of\nentries in the mailbox audit logs on trusted user or computer accounts.\nEnsure AuditBypassEnabled is not enabled on accounts without a written exception.","Impact":"None - this is the default behavior.","Audit":"To audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\n$MBX = Get-MailboxAuditBypassAssociation -ResultSize unlimited\n$MBX | where {$_.AuditBypassEnabled -eq $true} | Format-Table\nName,AuditBypassEnabled\n3. If nothing is returned, then there are no accounts with Audit Bypass enabled.","Remediation":"To remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. The following example PowerShell script will disable AuditBypass for all\nmailboxes which currently have it enabled:\n# Get mailboxes with AuditBypassEnabled set to $true\n$MBXAudit = Get-MailboxAuditBypassAssociation -ResultSize unlimited | Where-\nObject { $_.AuditBypassEnabled -eq $true }\nforeach ($mailbox in $MBXAudit) {\n$mailboxName = $mailbox.Name\nSet-MailboxAuditBypassAssociation -Identity $mailboxName -\nAuditBypassEnabled $false\nWrite-Host \"Audit Bypass disabled for mailbox Identity: $mailboxName\" -\nForegroundColor Green\n}","Title":"Ensure 'AuditBypassEnabled' is not enabled on","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.1 Audit","DefaultValue":"AuditBypassEnabled False","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"8.5\", \"title\": \"Collect Detailed Audit Logs\", \"description\": \"v8 Configure detailed audit logging for enterprise assets containing sensitive data. - - Include event source, date, username, timestamp, source addresses, destination addresses, and other useful elements that could assist in a forensic investigation.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"6.2\", \"title\": \"Mail flow\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/exchange/get-\nmailboxauditbypassassociation?view=exchange-ps","Rationale":"If a mailbox audit bypass association is added for an account, the account can access\nany mailbox in the organization to which it has been assigned access permissions,\nwithout generating any mailbox audit logging entries for such access or recording any\nactions taken, such as message deletions.\nEnabling this parameter, whether intentionally or unintentionally, could allow insiders or\nmalicious actors to conceal their activity on specific mailboxes. Ensuring proper logging\nof user actions and mailbox operations in the audit log will enable comprehensive\nincident response and forensics.","Section":"6 Exchange admin center","RecommendationId":"6.1.3"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Fetch mailboxes with AuditBypassEnabled
    $MBX = Get-MailboxAuditBypassAssociation -ResultSize unlimited
    $nonCompliantMailboxes = $MBX | Where-Object { $_.AuditBypassEnabled -eq $true }
    
    # Convert results to standard format
    foreach ($mailbox in $nonCompliantMailboxes) {
        $resourceResults += @{
            Mailbox = $mailbox.Identity
            AuditBypassEnabled = $mailbox.AuditBypassEnabled
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
