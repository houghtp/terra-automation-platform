# Control: 6.2.1 - Ensure all forms of mail forwarding are blocked and/or
<# CIS_METADATA_START
{"Description":"Exchange Online offers several methods of managing the flow of email messages.\nThese are Remote domain, Transport Rules, and Anti-spam outbound policies. These\nmethods work together to provide comprehensive coverage for potential automatic\nforwarding channels:\n- Outlook forwarding using inbox rules.\n- Outlook forwarding configured using OOF rule.\n- OWA forwarding setting (ForwardingSmtpAddress).\n- Forwarding set by the admin using EAC (ForwardingAddress).\n- Forwarding using Power Automate / Flow.\nEnsure a Transport rule and Anti-spam outbound policy are used to block mail\nforwarding.\nNOTE: Any exclusions should be implemented based on organizational policy.","Impact":"Care should be taken before implementation to ensure there is no business need for\ncase-by-case auto-forwarding. Disabling auto-forwarding to remote domains will affect\nall users and in an organization. Any exclusions should be implemented based on\norganizational policy.","Audit":"Note: Audit is a two step procedure as follows:\nSTEP 1: Transport rules\nTo audit using the UI:\n1. Select Exchange to open the Exchange admin center.\n2. Select Mail Flow then Rules.\n3. Review the rules and verify that none of them are forwards or redirects e-mail to\nexternal domains.\nTo audit using PowerShell:\n1. Connect to Exchange online using Connect-ExchangeOnline.\n2. Run the following PowerShell command to review the Transport Rules that are\nredirecting email:\nGet-TransportRule | Where-Object {$_.RedirectMessageTo -ne $null} | ft\nName,RedirectMessageTo\n3. Verify that none of the addresses listed belong to external domains outside of the\norganization. If nothing returns then there are no transport rules set to redirect\nmessages.\nSTEP 2: Anti-spam outbound policy\nTo audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Expand E-mail & collaboration then select Policies & rules.\n3. Select Threat policies > Anti-spam.\n4. Inspect Anti-spam outbound policy (default) and ensure Automatic\nforwarding is set to Off - Forwarding is disabled\n5. Inspect any additional custom outbound policies and ensure Automatic\nforwarding is set to Off - Forwarding is disabled, in accordance with the\norganization's exclusion policies.\nTo audit using PowerShell:\n1. Connect to Exchange online using Connect-ExchangeOnline.\n2. Run the following PowerShell cmdlet:\nGet-HostedOutboundSpamFilterPolicy | ft Name, AutoForwardingMode\n3. In each outbound policy verify AutoForwardingMode is Off.\nNote: According to Microsoft if a recipient is defined in multiple policies of the same\ntype (anti-spam, anti-phishing, etc.), only the policy with the highest priority is applied to\nthe recipient. Any remaining policies of that type are not evaluated for the recipient\n(including the default policy). However, it is our recommendation to audit the default\npolicy as well in the case a higher priority custom policy is removed. This will keep the\norganization's security posture strong.","Remediation":"Note: Remediation is a two step procedure as follows:\nSTEP 1: Transport rules\nTo remediate using the UI:\n1. Select Exchange to open the Exchange admin center.\n2. Select Mail Flow then Rules.\n3. For each rule that redirects email to external domains, select the rule and click\nthe 'Delete' icon.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nRemove-TransportRule {RuleName}\nSTEP 2: Anti-spam outbound policy\nTo remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Expand E-mail & collaboration then select Policies & rules.\n3. Select Threat policies > Anti-spam.\n4. Select Anti-spam outbound policy (default)\n5. Click Edit protection settings\n6. Set Automatic forwarding rules dropdown to Off - Forwarding is\ndisabled and click Save\n7. Repeat steps 4-6 for any additional higher priority, custom policies.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-HostedOutboundSpamFilterPolicy -Identity {policyName} -AutoForwardingMode\nOff\n3. To remove AutoForwarding from all outbound policies you can also run:\nGet-HostedOutboundSpamFilterPolicy | Set-HostedOutboundSpamFilterPolicy -\nAutoForwardingMode Off","Title":"Ensure all forms of mail forwarding are blocked and/or","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.2 Mail flow","DefaultValue":"","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/exchange/security-and-compliance/mail-flow-\nrules/mail-flow-rules\n2. https://techcommunity.microsoft.com/t5/exchange-team-blog/all-you-need-to-\nknow-about-automatic-email-forwarding-in/ba-\np/2074888#:~:text=%20%20%20Automatic%20forwarding%20option%20%20,%\n3. https://learn.microsoft.com/en-us/defender-office-365/outbound-spam-policies-\nexternal-email-forwarding?view=o365-worldwide","Rationale":"Attackers often create these rules to exfiltrate data from your tenancy, this could be\naccomplished via access to an end-user account or otherwise. An insider could also use\none of these methods as a secondary channel to exfiltrate sensitive data.","Section":"6 Exchange admin center","RecommendationId":"6.2.1"}
CIS_METADATA_END #>
# Required Services: SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve transport rules with redirection
    $transportRules = Get-TransportRule | Where-Object { $_.RedirectMessageTo -ne $null }
    
    # Process each rule and determine compliance
    foreach ($rule in $transportRules) {
        $isCompliant = $false
        $resourceResults += @{
            RuleName = $rule.Name
            RedirectMessageTo = $rule.RedirectMessageTo
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
