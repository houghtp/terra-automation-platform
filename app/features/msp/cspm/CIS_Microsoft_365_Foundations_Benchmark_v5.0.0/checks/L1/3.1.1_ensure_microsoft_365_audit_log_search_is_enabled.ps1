# Control: 3.1.1 - Ensure Microsoft 365 audit log search is Enabled
<# CIS_METADATA_START
{"Description":"When audit log search is enabled in the Microsoft Purview compliance portal, user and\nadmin activity within the organization is recorded in the audit log and retained for 180\ndays by default. However, some organizations may prefer to use a third-party security\ninformation and event management (SIEM) application to access their auditing data. In\nthis scenario, a global admin can choose to turn off audit log search in Microsoft 365.","Impact":"","Audit":"To audit using the UI:\n1. Navigate to Microsoft Purview https://purview.microsoft.com/\n2. Select Solutions and then Audit to open the audit search.\n3. Choose a date and time frame in the past 30 days.\n4. Verify search capabilities (e.g. try searching for Activities as Accessed file and\nresults should be displayed).\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-AdminAuditLogConfig | Select-Object UnifiedAuditLogIngestionEnabled\n3. Ensure UnifiedAuditLogIngestionEnabled is set to True.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Purview https://purview.microsoft.com/\n2. Select Solutions and then Audit to open the audit search.\n3. Click blue bar Start recording user and admin activity.\n4. Click Yes on the dialog box to confirm.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-AdminAuditLogConfig -UnifiedAuditLogIngestionEnabled $true","Title":"Ensure Microsoft 365 audit log search is Enabled","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"3.1 Audit","DefaultValue":"180 days","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"8.2\", \"title\": \"Collect Audit Logs\", \"description\": \"Collect audit logs. Ensure that logging, per the enterprise's audit log - - - management process, has been enabled across enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Activate audit logging\", \"description\": \"Ensure that local logging has been enabled on all systems and networking - - - devices.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"3.2\", \"title\": \"Data loss protection\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/purview/audit-log-enable-disable?view=o365-\nworldwide&tabs=microsoft-purview-portal\n2. https://learn.microsoft.com/en-us/powershell/module/exchange/set-\nadminauditlogconfig?view=exchange-ps","Rationale":"Enabling audit log search in the Microsoft Purview compliance portal can help\norganizations improve their security posture, meet regulatory compliance requirements,\nrespond to security incidents, and gain valuable operational insights.","Section":"3 Microsoft Purview","RecommendationId":"3.1.1"}
CIS_METADATA_END #>
# Required Services: SecurityCompliance, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the command to check UnifiedAuditLogIngestionEnabled status
    $auditLogConfig = Get-AdminAuditLogConfig | Select-Object UnifiedAuditLogIngestionEnabled
    $isCompliant = $auditLogConfig.UnifiedAuditLogIngestionEnabled -eq $true
    $resourceResults += @{
        Name = "UnifiedAuditLogIngestionEnabled"
        IsCompliant = $isCompliant
        CurrentValue = $auditLogConfig.UnifiedAuditLogIngestionEnabled
        ExpectedValue = $true
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
