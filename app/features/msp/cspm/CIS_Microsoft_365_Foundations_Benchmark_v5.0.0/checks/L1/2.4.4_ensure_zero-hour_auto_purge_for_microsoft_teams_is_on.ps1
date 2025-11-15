# Control: 2.4.4 - Ensure Zero-hour auto purge for Microsoft Teams is on
<# CIS_METADATA_START
{"Description":"Zero-hour auto purge (ZAP) is a protection feature that retroactively detects and\nneutralizes malware and high confidence phishing. When ZAP for Teams protection\nblocks a message, the message is blocked for everyone in the chat. The initial block\nhappens right after delivery, but ZAP occurs up to 48 hours after delivery.","Impact":"As with any anti-malware or anti-phishing product, false positives may occur.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Defender https://security.microsoft.com/\n2. Click to expand System select Settings > Email & collaboration >\nMicrosoft Teams protection.\n3. Ensure Zero-hour auto purge (ZAP) is set to On (Default)\n4. Under Exclude these participants review the list of exclusions and ensure\nthey are justified and within tolerance for the organization.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following cmdlets:\nGet-TeamsProtectionPolicy | fl ZapEnabled\nGet-TeamsProtectionPolicyRule | fl ExceptIf*\n3. Ensure ZapEnabled is True.\n4. Review the list of exclusions and ensure they are justified and within tolerance for\nthe organization. If nothing returns from the 2nd cmdlet then there are no\nexclusions defined.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Defender https://security.microsoft.com/\n2. Click to expand System select Settings > Email & collaboration >\nMicrosoft Teams protection.\n3. Set Zero-hour auto purge (ZAP) to On (Default)\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following cmdlet:\nSet-TeamsProtectionPolicy -Identity \"Teams Protection Policy\" -ZapEnabled\n$true","Title":"Ensure Zero-hour auto purge for Microsoft Teams is on","ProfileApplicability":"- E5 Level 1","SubSection":"2.4 System","DefaultValue":"On (Default)","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"10.1\", \"title\": \"Deploy and Maintain Anti-Malware Software\", \"description\": \"v8 - - - Deploy and maintain anti-malware software on all enterprise assets. 3 Microsoft Purview Microsoft Purview, also known as Compliance, contains settings related to all things compliance, data governance, information protection and risk management. Direct link: https://compliance.microsoft.com/\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"3.1\", \"title\": \"Audit\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/zero-hour-auto-\npurge?view=o365-worldwide#zero-hour-auto-purge-zap-in-microsoft-teams\n2. https://learn.microsoft.com/en-us/defender-office-365/mdo-support-teams-\nabout?view=o365-worldwide#configure-zap-for-teams-protection-in-defender-for-\noffice-365-plan-2","Rationale":"ZAP is intended to protect users that have received zero-day malware messages or\ncontent that is weaponized after being delivered to users. It does this by continually\nmonitoring spam and malware signatures taking automated retroactive action on\nmessages that have already been delivered.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.4.4"}
CIS_METADATA_END #>
# Required Services: Teams, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Check Anti-malware policies for ZAP settings (affects Teams as well)
    $malwarePolicies = Get-MalwareFilterPolicy
    foreach ($policy in $malwarePolicies) {
        $isCompliant = $policy.ZapEnabled -eq $true
        $resourceResults += @{
            PolicyName = $policy.Name
            ZapEnabled = $policy.ZapEnabled
            IsCompliant = $isCompliant
        }
    }

    # Check Anti-malware policy rules for exceptions
    $malwarePolicyRules = Get-MalwareFilterRule
    foreach ($rule in $malwarePolicyRules) {
        $hasExceptions = ($rule.ExceptIfSentTo -or $rule.ExceptIfSentToMemberOf -or $rule.ExceptIfRecipientDomainIs)
        $isCompliant = -not $hasExceptions
        $resourceResults += @{
            RuleName = $rule.Name
            HasExceptions = $hasExceptions
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
