# Control: 2.1.13 - Ensure the connection filter safe list is off
<# CIS_METADATA_START
{"Description":"In Microsoft 365 organizations with Exchange Online mailboxes or standalone\nExchange Online Protection (EOP) organizations without Exchange Online mailboxes,\nconnection filtering and the default connection filter policy identify good or bad source\nemail servers by IP addresses. The key components of the default connection filter\npolicy are IP Allow List, IP Block List and Safe list.\nThe safe list is a pre-configured allow list that is dynamically updated by Microsoft.\nThe recommended safe list state is: Off or False","Impact":"This is the default behavior. IP Allow lists may reduce false positives, however, this\nbenefit is outweighed by the importance of a policy which scans all messages\nregardless of the origin. This supports the principle of zero trust.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules > Threat\npolicies.\n3. Under Policies select Anti-spam.\n4. Click on the Connection filter policy (Default).\n5. Ensure Safe list is Off.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-HostedConnectionFilterPolicy -Identity Default | fl EnableSafeList\n3. Ensure EnableSafeList is False","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules> Threat\npolicies.\n3. Under Policies select Anti-spam.\n4. Click on the Connection filter policy (Default).\n5. Click Edit connection filter policy.\n6. Uncheck Turn on safe list.\n7. Click Save.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-HostedConnectionFilterPolicy -Identity Default -EnableSafeList $false","Title":"Ensure the connection filter safe list is off","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"2.1 Email & collaboration","DefaultValue":"EnableSafeList : False","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/connection-filter-policies-\nconfigure\n2. https://learn.microsoft.com/en-us/defender-office-365/create-safe-sender-lists-in-\noffice-365#use-the-ip-allow-list\n3. https://learn.microsoft.com/en-us/defender-office-365/how-policies-and-\nprotections-are-combined#user-and-tenant-settings-conflict","Rationale":"Without additional verification like mail flow rules, email from sources in the IP Allow List\nskips spam filtering and sender authentication (SPF, DKIM, DMARC) checks. This\nmethod creates a high risk of attackers successfully delivering email to the Inbox that\nwould otherwise be filtered. Messages that are determined to be malware or high\nconfidence phishing are filtered.\nThe safe list is managed dynamically by Microsoft, and administrators do not have\nvisibility into which sender are included. Incoming messages from email servers on the\nsafe list bypass spam filtering.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.13"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    $policy = Get-HostedConnectionFilterPolicy -Identity Default
    $enableSafeList = $policy.EnableSafeList
    
    # Convert results to standard format
    $resourceResults += @{
        Name = "Connection Filter Safe List"
        IsCompliant = -not $enableSafeList
        CurrentValue = $enableSafeList
        ExpectedValue = $false
        Details = "Safe List is " + ($enableSafeList ? "enabled" : "disabled")
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
