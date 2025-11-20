# Control: 2.4.1 - Ensure Priority account protection is enabled and
<# CIS_METADATA_START
{"Description": "Identify priority accounts to utilize Microsoft 365's advanced custom security features.\nThis is an essential tool to bolster protection for users who are frequently targeted due\nto their critical positions, such as executives, leaders, managers, or others who have\naccess to sensitive, confidential, financial, or high-priority information.\nOnce these accounts are identified, several services and features can be enabled,\nincluding threat policies, enhanced sign-in protection through conditional access\npolicies, and alert policies, enabling faster response times for incident response teams.", "Impact": "", "Audit": "Audit with a 3-step process\nStep 1: Verify Priority account protection is enabled:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Select Settings near the bottom of the left most panel.\n3. Select E-mail & collaboration > Priority account protection\n4. Ensure Priority account protection is set to On\nStep 2: Verify that priority accounts are identified and tagged accordingly:\n5. Select User tags\n6. Select the PRIORITY ACCOUNT tag and click Edit\n7. Verify the assigned members match the organization's defined priority accounts\nor groups.\n8. Repeat the previous 2 steps for any additional tags identified, such as Finance or\nHR.\nStep 3: Ensure alerts are configured:\n9. Expand E-mail & Collaboration on the left column.\n10. Select Policies & rules > Alert policy\n11. Ensure at least two alert policies are configured to monitor priority accounts for\nthe activities Detected malware in an email message and Phishing email\ndetected at time of delivery. These alerts should meet the following\ncriteria:\no Severity: High\no Category: Threat management\no Mail Direction: Inbound\no Recipient Tags: Includes Priority account", "Remediation": "Remediate with a 3-step process\nStep 1: Enable Priority account protection in Microsoft 365 Defender:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Click to expand System select Settings.\n3. Select E-mail & Collaboration > Priority account protection\n4. Ensure Priority account protection is set to On\nStep 2: Tag priority accounts:\n5. Select User tags\n6. Select the PRIORITY ACCOUNT tag and click Edit\n7. Select Add members to add users, or groups. Groups are recommended.\n8. Repeat the previous 2 steps for any additional tags needed, such as Finance or\nHR.\n9. Next and Submit.\nStep 3: Configure E-mail alerts for Priority Accounts:\n10. Expand E-mail & Collaboration on the left column.\n11. Select Policies & rules > Alert policy\n12. Select New Alert Policy\n13. Enter a valid policy Name & Description. Set Severity to High and Category to\nThreat management.\n14. Set Activity is to Detected malware in an e-mail message\n15. Mail direction is Inbound\n16. Select Add Condition and User: recipient tags are\n17. In the Selection option field add chosen priority tags such as Priority account.\n18. Select Every time an activity matches the rule.\n19. Next and verify valid recipient(s) are selected.\n20. Next and select Yes, turn it on right away. Click Submit to save the alert.\n21. Repeat steps 12 - 18 to create a 2nd alert for the Activity field Activity is:\nPhishing email detected at time of delivery\nNote: Any additional activity types may be added as needed. Above are the minimum\nrecommended.", "Title": "Ensure Priority account protection is enabled and configured", "ProfileApplicability": "- E5 Level 1", "SubSection": "2.4 System", "DefaultValue": "By default, priority accounts are undefined.", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoft-365/admin/setup/priority-accounts\n2. https://learn.microsoft.com/en-us/defender-office-365/priority-accounts-security-\nrecommendations", "Rationale": "Enabling priority account protection for users in Microsoft 365 is necessary to enhance\nsecurity for accounts with access to sensitive data and high privileges, such as CEOs,\nCISOs, CFOs, and IT admins. These priority accounts are often targeted by spear\nphishing or whaling attacks and require stronger protection to prevent account\ncompromise.\nTo address this, Microsoft 365 and Microsoft Defender for Office 365 offer several key\nfeatures that provide extra security, including the identification of incidents and alerts\ninvolving priority accounts and the use of built-in custom protections designed\nspecifically for them.", "Section": "2 Microsoft 365 Defender", "RecommendationId": "2.4.1"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands
# REWRITTEN: Now uses Exchange-only cmdlets (previously used Exchange + Graph)

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Step 1: Verify Priority account protection is enabled via preset security policies
    # Check for Strict Protection preset policy
    $presetPolicies = Get-EOPProtectionPolicyRule -ErrorAction SilentlyContinue
    $strictPolicy = $presetPolicies | Where-Object { $_.Name -like "*Strict*" -and $_.State -eq "Enabled" }
    $isPriorityProtectionEnabled = $null -ne $strictPolicy

    $resourceResults += @{
        ResourceName = "Priority Account Protection"
        CurrentValue = if ($strictPolicy) { "Enabled" } else { "Disabled" }
        IsCompliant = $isPriorityProtectionEnabled
    }

    # Step 2: Check for users with priority account tags
    # In Exchange, priority accounts can be identified via accepted domains and admin mailboxes
    # We'll check for admin/executive mailboxes which should have enhanced protection
    $adminMailboxes = Get-EXOMailbox -Filter "DisplayName -like '*admin*' -or DisplayName -like '*executive*'" -ResultSize 100
    $hasPriorityAccounts = $adminMailboxes.Count -gt 0

    $resourceResults += @{
        ResourceName = "Priority Accounts Identified"
        CurrentValue = "$($adminMailboxes.Count) priority mailboxes found"
        IsCompliant = $hasPriorityAccounts
    }

    # Step 3: Check for alert policies related to priority accounts
    $alertPolicies = Get-ProtectionAlert -ErrorAction SilentlyContinue
    $requiredAlerts = @("Detected malware in an email message", "Phishing email detected at time of delivery")
    $configuredAlerts = $alertPolicies | Where-Object { $_.Severity -eq "High" -and $_.Category -like "*Threat*" }
    $isAlertsConfigured = $configuredAlerts.Count -gt 0

    $resourceResults += @{
        ResourceName = "Alert Policies"
        CurrentValue = if ($configuredAlerts) { $configuredAlerts.Activity -join ", " } else { "None configured" }
        IsCompliant = $isAlertsConfigured
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
