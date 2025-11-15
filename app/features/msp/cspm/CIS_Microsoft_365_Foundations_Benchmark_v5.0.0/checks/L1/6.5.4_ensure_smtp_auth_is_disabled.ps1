# Control: 6.5.4 - Ensure SMTP AUTH is disabled
<# CIS_METADATA_START
{"Description":"This setting enables or disables authenticated client SMTP submission (SMTP AUTH)\nat an organization level in Exchange Online.\nThe recommended state is Turn off SMTP AUTH protocol for your\norganization (checked).","Impact":"This enforces the default behavior, so no impact is expected unless the organization is\nusing it globally. A per-mailbox setting exists that overrides the tenant-wide setting,\nallowing an individual mailbox SMTP AUTH capability for special cases.","Audit":"To audit using the UI:\n1. Navigate to Exchange admin center https://admin.exchange.microsoft.com.\n2. Select Settings > Mail flow.\n3. Ensure Turn off SMTP AUTH protocol for your organization is checked.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-TransportConfig | Format-List SmtpClientAuthenticationDisabled\n3. Verify that the value returned is True.","Remediation":"To remediate using the UI:\n1. Navigate to Exchange admin center https://admin.exchange.microsoft.com.\n2. Select Settings > Mail flow.\n3. Uncheck Turn off SMTP AUTH protocol for your organization.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-TransportConfig -SmtpClientAuthenticationDisabled $true","Title":"Ensure SMTP AUTH is disabled","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.5 Settings","DefaultValue":"SmtpClientAuthenticationDisabled : True","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"12.6\", \"title\": \"Use of Secure Network Management and\", \"description\": \"v8 Communication Protocols - - Use secure network management and communication protocols (e.g., 802.1X, Wi-Fi Protected Access 2 (WPA2) Enterprise or greater). 7 SharePoint admin center The SharePoint admin center contains settings related to SharePoint and OneDrive. UI Direct link: https://admin.microsoft.com/sharepoint The PowerShell module most used in this section is Microsoft.Online.SharePoint.PowerShell and uses Connect-SPOService -Url https://contoso-admin.sharepoint.com as the connection cmdlet (replacing tenant name with your value). The latest version of the module can be downloaded here: https://www.powershellgallery.com/packages/Microsoft.Online.SharePoint.PowerShell/\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.1\", \"title\": \"Sites\", \"description\": \"This section is intentionally blank and exists to ensure the structure of the benchmark is consistent.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.2\", \"title\": \"Policies\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-\nonline/authenticated-client-smtp-submission","Rationale":"SMTP AUTH is a legacy protocol. Disabling it at the organization level supports the\nprinciple of least functionality and serves to further back additional controls that block\nlegacy protocols, such as in Conditional Access. Virtually all modern email clients that\nconnect to Exchange Online mailboxes in Microsoft 365 can do so without using SMTP\nAUTH.","Section":"6 Exchange admin center","RecommendationId":"6.5.4"}
CIS_METADATA_END #>
# Required Services: SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original command to check SMTP AUTH status
    $transportConfig = Get-TransportConfig
    
    # Check if SMTP Client Authentication is disabled
    $isSmtpAuthDisabled = $transportConfig.SmtpClientAuthenticationDisabled
    
    # Convert results to standard format
    $resourceResults += @{
        Resource = "SMTP Client Authentication"
        IsCompliant = $isSmtpAuthDisabled -eq $true
        Details = "SMTP Client Authentication is " + ($isSmtpAuthDisabled -eq $true ? "disabled" : "enabled")
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
