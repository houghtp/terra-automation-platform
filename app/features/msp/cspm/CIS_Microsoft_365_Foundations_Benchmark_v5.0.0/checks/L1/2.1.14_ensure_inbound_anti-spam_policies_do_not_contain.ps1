# Control: 2.1.14 - Ensure inbound anti-spam policies do not contain
<# CIS_METADATA_START
{"Description": "Anti-spam protection is a feature of Exchange Online that utilizes policies to help to\nreduce the amount of junk email, bulk and phishing emails a mailbox receives. These\npolicies contain lists to allow or block specific senders or domains.\n- The allowed senders list\n- The allowed domains list\n- The blocked senders list\n- The blocked domains list\nThe recommended state is: Do not define any Allowed domains", "Impact": "This is the default behavior. Allowed domains may reduce false positives, however, this\nbenefit is outweighed by the importance of having a policy which scans all messages\nregardless of the origin. As an alternative consider sender based lists. This supports the\nprinciple of zero trust.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules > Threat\npolicies.\n3. Under Policies select Anti-spam.\n4. Inspect each inbound anti-spam policy\n5. Ensure that Allowed domains does not contain any domain names.\n6. Repeat as needed for any additional inbound anti-spam policy.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-HostedContentFilterPolicy | ft Identity,AllowedSenderDomains\n3. Ensure AllowedSenderDomains is undefined for each inbound policy.\nNote: Each inbound policy must pass for this recommendation to be considered to be in\na passing state.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules> Threat\npolicies.\n3. Under Policies select Anti-spam.\n4. Open each out of compliance inbound anti-spam policy by clicking on it.\n5. Click Edit allowed and blocked senders and domains.\n6. Select Allow domains.\n7. Delete each domain from the domains list.\n8. Click Done > Save.\n9. Repeat as needed.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-HostedContentFilterPolicy -Identity <Policy name> -AllowedSenderDomains\n@{}\nOr, run this to remove allowed domains from all inbound anti-spam policies:\n$AllowedDomains = Get-HostedContentFilterPolicy | Where-Object\n{$_.AllowedSenderDomains}\n$AllowedDomains | Set-HostedContentFilterPolicy -AllowedSenderDomains @{}", "Title": "Ensure inbound anti-spam policies do not contain allowed domains", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "2.1 Email & collaboration", "DefaultValue": "AllowedSenderDomains : {}", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"2.2\", \"title\": \"Cloud apps\", \"description\": \"This section contains recommendations for Microsoft Defender for Cloud apps\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/defender-office-365/anti-spam-protection-\nabout#allow-and-block-lists-in-anti-spam-policies", "Rationale": "Messages from entries in the allowed senders list or the allowed domains list bypass\nmost email protection (except malware and high confidence phishing) and email\nauthentication checks (SPF, DKIM and DMARC). Entries in the allowed senders list or\nthe allowed domains list create a high risk of attackers successfully delivering email to\nthe Inbox that would otherwise be filtered. The risk is increased even more when\nallowing common domain names as these can be easily spoofed by attackers.\nMicrosoft specifies in its documentation that allowed domains should be used for testing\npurposes only.", "Section": "2 Microsoft 365 Defender", "RecommendationId": "2.1.14"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve Hosted Content Filter Policies
    $policies = Get-HostedContentFilterPolicy | Select-Object Identity, AllowedSenderDomains
    
    # Process each policy to determine compliance
    foreach ($policy in $policies) {
        $isCompliant = if ($policy.AllowedSenderDomains -eq $null -or $policy.AllowedSenderDomains.Count -eq 0) { $true } else { $false }
        
        # Add the result to the results array
        $resourceResults += @{
            Identity = $policy.Identity
            AllowedSenderDomains = $policy.AllowedSenderDomains
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
