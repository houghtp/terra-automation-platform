# Control: 2.4.2 - Ensure Priority accounts have 'Strict protection' presets
<# CIS_METADATA_START
{"Description": "Preset security policies have been established by Microsoft, utilizing observations and\nexperiences within datacenters to strike a balance between the exclusion of malicious\ncontent from users and limiting unwarranted disruptions. These policies can apply to all,\nor select users and encompass recommendations for addressing spam, malware, and\nphishing threats. The policy parameters are pre-determined and non-adjustable.\nStrict protection has the most aggressive protection of the 3 presets.\n- EOP: Anti-spam, Anti-malware and Anti-phishing\n- Defender: Spoof protection, Impersonation protection and Advanced phishing\n- Defender: Safe Links and Safe Attachments\nNOTE: The preset security polices cannot target Priority account TAGS currently,\ngroups should be used instead.", "Impact": "Strict policies are more likely to cause false positives in anti-spam, phishing,\nimpersonation, spoofing and intelligence responses.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Select to expand E-mail & collaboration.\n3. Select Policies & rules > Threat policies.\n4. From here visit each section in turn: Anti-phishing Anti-spam Anti-malware\nSafe Attachments Safe Links\n5. Ensure in each there is a policy named Strict Preset Security Policy\nwhich includes the organization's priority Accounts/Groups.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Select to expand E-mail & collaboration.\n3. Select Policies & rules > Threat policies > Preset security policies.\n4. Click to Manage protection settings for Strict protection preset.\n5. For Apply Exchange Online Protection select at minimum Specific\nrecipients and include the Accounts/Groups identified as Priority Accounts.\n6. For Apply Defender for Office 365 Protection select at minimum\nSpecific recipients and include the Accounts/Groups identified as Priority\nAccounts.\n7. For Impersonation protection click Next and add valid e-mails or priority\naccounts both internal and external that may be subject to impersonation.\n8. For Protected custom domains add the organization's domain name, along\nside other key partners.\n9. Click Next and finally Confirm", "Title": "Ensure Priority accounts have 'Strict protection' presets applied", "ProfileApplicability": "- E5 Level 1", "SubSection": "2.4 System", "DefaultValue": "By default, presets are not applied to any users or groups.", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"10.7\", \"title\": \"Use Behavior-Based Anti-Malware Software\", \"description\": \"- - Use behavior-based anti-malware software.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/defender-office-365/preset-security-\npolicies?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/defender-office-365/priority-accounts-security-\nrecommendations\n3. https://learn.microsoft.com/en-us/defender-office-365/recommended-settings-for-\neop-and-office365?view=o365-worldwide#impersonation-settings-in-anti-\nphishing-policies-in-microsoft-defender-for-office-365", "Rationale": "Enabling priority account protection for users in Microsoft 365 is necessary to enhance\nsecurity for accounts with access to sensitive data and high privileges, such as CEOs,\nCISOs, CFOs, and IT admins. These priority accounts are often targeted by spear\nphishing or whaling attacks and require stronger protection to prevent account\ncompromise.\nThe implementation of stringent, pre-defined policies may result in instances of false\npositive, however, the benefit of requiring the end-user to preview junk email before\naccessing their inbox outweighs the potential risk of mistakenly perceiving a malicious\nemail as safe due to its placement in the inbox.", "Section": "2 Microsoft 365 Defender", "RecommendationId": "2.4.2"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve all preset security policies
    $presetPolicies = Get-HostedContentFilterPolicy

    # Define the expected policy name for strict protection
    $expectedPolicyName = "Strict Preset Security Policy"

    # Retrieve priority accounts/groups (this should be defined elsewhere in your environment)
    $priorityAccounts = @("PriorityGroup1", "PriorityGroup2") # Example groups

    # Check each policy for compliance
    foreach ($policy in $presetPolicies) {
        $isCompliant = $false
        $currentValue = $policy.Name

        # Check if the policy name matches the expected strict protection policy
        if ($currentValue -eq $expectedPolicyName) {
            # Check if the policy applies to the priority accounts/groups
            $appliedRecipients = Get-HostedContentFilterPolicy | Where-Object { $_.Name -eq $currentValue } | Select-Object -ExpandProperty AppliedRecipients
            $isCompliant = $priorityAccounts | ForEach-Object { $appliedRecipients -contains $_ } | Where-Object { $_ -eq $false } | Measure-Object | Select-Object -ExpandProperty Count -eq 0
        }

        $resourceResults += @{
            ResourceName = $currentValue
            CurrentValue = $currentValue
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
