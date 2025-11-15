# Control: 6.1.1 - Ensure 'AuditDisabled' organizationally is set to 'False'
<# CIS_METADATA_START
{"Description":"The value False indicates that mailbox auditing on by default is turned on for the\norganization. Mailbox auditing on by default in the organization overrides the mailbox\nauditing settings on individual mailboxes. For example, if mailbox auditing is turned off\nfor a mailbox (the AuditEnabled property on the mailbox is False), the default mailbox\nactions are still audited for the mailbox, because mailbox auditing on by default is turned\non for the organization.\nTurning off mailbox auditing on by default ($true) has the following results:\n- Mailbox auditing is turned off for your organization.\n- From the time you turn off mailbox auditing on by default, no mailbox actions are\naudited, even if mailbox auditing is enabled on a mailbox (the AuditEnabled\nproperty on the mailbox is True).\n- Mailbox auditing isn't turned on for new mailboxes and setting the AuditEnabled\nproperty on a new or existing mailbox to True is ignored.\n- Any mailbox audit bypass association settings (configured by using the Set-\nMailboxAuditBypassAssociation cmdlet) are ignored.\n- Existing mailbox audit records are retained until the audit log age limit for the\nrecord expires.\nThe recommended state for this setting is False at the organization level. This will\nenable auditing and enforce the default.","Impact":"None - this is the default behavior as of 2019.","Audit":"To audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-OrganizationConfig | Format-List AuditDisabled\n3. Ensure AuditDisabled is set to False.","Remediation":"To remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-OrganizationConfig -AuditDisabled $false","Title":"Ensure 'AuditDisabled' organizationally is set to 'False'","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.1 Audit","DefaultValue":"False","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"8.2\", \"title\": \"Collect Audit Logs\", \"description\": \"Collect audit logs. Ensure that logging, per the enterprise's audit log - - - management process, has been enabled across enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Activate audit logging\", \"description\": \"Ensure that local logging has been enabled on all systems and networking - - - devices.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/purview/audit-mailboxes?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/powershell/module/exchange/set-\norganizationconfig?view=exchange-ps#-auditdisabled","Rationale":"Enforcing the default ensures auditing was not turned off intentionally or accidentally.\nAuditing mailbox actions will allow forensics and IR teams to trace various malicious\nactivities that can generate TTPs caused by inbox access and tampering.\nNote: Without advanced auditing (E5 function) the logs are limited to 90 days.","Section":"6 Exchange admin center","RecommendationId":"6.1.1"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the command to get the organization configuration
    $orgConfig = Get-OrganizationConfig
    
    # Check the 'AuditDisabled' property
    $auditDisabled = $orgConfig.AuditDisabled
    
    # Convert results to standard format
    $resourceResults += @{
        Name = "AuditDisabled"
        Value = $auditDisabled
        IsCompliant = -not $auditDisabled
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
