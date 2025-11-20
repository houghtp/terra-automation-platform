# Control: 2.1.6 - Ensure Exchange Online Spam Policies are set to
<# CIS_METADATA_START
{"Description": "In Microsoft 365 organizations with mailboxes in Exchange Online or standalone\nExchange Online Protection (EOP) organizations without Exchange Online mailboxes,\nemail messages are automatically protected against spam (junk email) by EOP.\nConfigure Exchange Online Spam Policies to copy emails and notify someone when a\nsender in the organization has been blocked for sending spam emails.", "Impact": "Notification of users that have been blocked should not cause an impact to the user.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules > Threat\npolicies.\n3. Under Policies select Anti-spam.\n4. Click on the Anti-spam outbound policy (default).\n5. Verify that Send a copy of suspicious outbound messages or message\nthat exceed these limits to these users and groups is set to On,\nensure the email address is correct.\n6. Verify that Notify these users and groups if a sender is blocked due\nto sending outbound spam is set to On, ensure the email address is correct.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-HostedOutboundSpamFilterPolicy | Select-Object Bcc*, Notify*\n3. Verify both BccSuspiciousOutboundMail and NotifyOutboundSpam are set to\nTrue and the email addresses to be notified are correct.\nNote: Audit and Remediation guidance may focus on the Default policy however, if a\nCustom Policy exists in the organization's tenant, then ensure the setting is set as\noutlined in the highest priority policy listed.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules> Threat\npolicies.\n3. Under Policies select Anti-spam.\n4. Click on the Anti-spam outbound policy (default).\n5. Select Edit protection settings then under Notifications\n6. Check Send a copy of suspicious outbound messages or message that\nexceed these limits to these users and groups then enter the desired\nemail addresses.\n7. Check Notify these users and groups if a sender is blocked due to\nsending outbound spam then enter the desired email addresses.\n8. Click Save.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\n$BccEmailAddress = @(\"<INSERT-EMAIL>\")\n$NotifyEmailAddress = @(\"<INSERT-EMAIL>\")\nSet-HostedOutboundSpamFilterPolicy -Identity Default -\nBccSuspiciousOutboundAdditionalRecipients $BccEmailAddress -\nBccSuspiciousOutboundMail $true -NotifyOutboundSpam $true -\nNotifyOutboundSpamRecipients $NotifyEmailAddress\nNote: Audit and Remediation guidance may focus on the Default policy however, if a\nCustom Policy exists in the organization's tenant, then ensure the setting is set as\noutlined in the highest priority policy listed.", "Title": "Ensure Exchange Online Spam Policies are set to notify administrators", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "2.1 Email & collaboration", "DefaultValue": "BccSuspiciousOutboundAdditionalRecipients : {}\nBccSuspiciousOutboundMail : False\nNotifyOutboundSpamRecipients : {}\nNotifyOutboundSpam : False", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"17.5\", \"title\": \"Assign Key Roles and Responsibilities\", \"description\": \"Assign key roles and responsibilities for incident response, including staff from legal, IT, information security, facilities, public relations, human resources, incident - - responders, and analysts, as applicable. Review annually, or when significant enterprise changes occur that could impact this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"7.9\", \"title\": \"Block Unnecessary File Types\", \"description\": \"Block all e-mail attachments entering the organization's e-mail gateway if the file - - types are unnecessary for the organization's business.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"7.10\", \"title\": \"Sandbox All Email Attachments\", \"description\": \"Use sandboxing to analyze and block inbound email attachments with malicious - behavior.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/defender-office-365/outbound-spam-protection-\nabout", "Rationale": "A blocked account is a good indication that the account in question has been breached,\nand an attacker is using it to send spam emails to other people.", "Section": "2 Microsoft 365 Defender", "RecommendationId": "2.1.6"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the Hosted Outbound Spam Filter Policies
    $policies = Get-HostedOutboundSpamFilterPolicy | Select-Object Identity, BccSuspiciousOutboundMail, BccSuspiciousOutboundAdditionalRecipients, NotifyOutboundSpam, NotifyOutboundSpamRecipients
    
    foreach ($policy in $policies) {
        # Check compliance for BccSuspiciousOutboundMail
        $isBccCompliant = $policy.BccSuspiciousOutboundMail -eq $true
        # Check compliance for NotifyOutboundSpam
        $isNotifyCompliant = $policy.NotifyOutboundSpam -eq $true
        
        # Determine if both settings are compliant
        $isCompliant = $isBccCompliant -and $isNotifyCompliant
        
        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.Identity
            BccSuspiciousOutboundMail = $policy.BccSuspiciousOutboundMail
            BccRecipients = $policy.BccSuspiciousOutboundAdditionalRecipients -join ", "
            NotifyOutboundSpam = $policy.NotifyOutboundSpam
            NotifyRecipients = $policy.NotifyOutboundSpamRecipients -join ", "
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
