# Control: 2.1.4 - Ensure Safe Attachments policy is enabled
<# CIS_METADATA_START
{"Description":"The Safe Attachments policy helps protect users from malware in email attachments by\nscanning attachments for viruses, malware, and other malicious content. When an email\nattachment is received by a user, Safe Attachments will scan the attachment in a secure\nenvironment and provide a verdict on whether the attachment is safe or not.","Impact":"Delivery of email with attachments may be delayed while scanning is occurring.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand E-mail & Collaboration select Policies & rules.\n3. On the Policies & rules page select Threat policies.\n4. Under Policies select Safe Attachments.\n5. Inspect the highest priority policy.\n6. Ensure Users and domains and Included recipient domains are in scope\nfor the organization.\n7. Ensure Safe Attachments detection response: is set to Block - Block\ncurrent and future messages and attachments with detected\nmalware.\n8. Ensure the Quarantine Policy is set to AdminOnlyAccessPolicy.\n9. Ensure the policy is not disabled.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-SafeAttachmentPolicy | ft Identity,Enable,Action,QuarantineTag\n3. Inspect the highest priority safe attachments policy and ensure the properties\nand values match the below:\nEnable : True\nAction : Block\nQuarantineTag : AdminOnlyAccessPolicy\nNote: To view the priority for a policy the Get-SafeAttachmentRule must be used.\nBuilt-in policies will always have a priority of lowest while presets like strict and\nstandard can be viewed with Get-ATPProtectionPolicyRule. Strict and standard\npresets always operate at a higher priority than custom policies.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand E-mail & Collaboration select Policies & rules.\n3. On the Policies & rules page select Threat policies.\n4. Under Policies select Safe Attachments.\n5. Click + Create.\n6. Create a Policy Name and Description, and then click Next.\n7. Select all valid domains and click Next.\n8. Select Block.\n9. Quarantine policy is AdminOnlyAccessPolicy.\n10. Leave Enable redirect unchecked.\n11. Click Next and finally Submit.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. To change an existing policy modify the example below and run the following\nPowerShell command:\nSet-SafeAttachmentPolicy -Identity 'Example policy' -Action 'Block' -\nQuarantineTag 'AdminOnlyAccessPolicy' -Enable $true\n3. Or, edit and run the below example to create a new safe attachments policy.\nNew-SafeAttachmentPolicy -Name \"CIS 2.1.4\" -Enable $true -Action 'Block' -\nQuarantineTag 'AdminOnlyAccessPolicy'\nNew-SafeAttachmentRule -Name \"CIS 2.1.4 Rule\" -SafeAttachmentPolicy \"CIS\n2.1.4\" -RecipientDomainIs 'exampledomain[.]com'\nNote: Policy targets such as users and domains should include domains, or groups that\nprovide coverage for a majority of users in the organization. Different inclusion and\nexclusion use cases are not covered in the benchmark.","Title":"Ensure Safe Attachments policy is enabled","ProfileApplicability":"- E5 Level 2","SubSection":"2.1 Email & collaboration","DefaultValue":"Identity : Built-In Protection Policy\nEnable : True\nAction : Block\nQuarantineTag : AdminOnlyAccessPolicy\nPriority : (lowest)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.10\", \"title\": \"Sandbox All Email Attachments\", \"description\": \"Use sandboxing to analyze and block inbound email attachments with - malicious behavior.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"8.1\", \"title\": \"Utilize Centrally Managed Anti-malware Software\", \"description\": \"Utilize centrally managed anti-malware software to continuously monitor and - - defend each of the organization's workstations and servers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/safe-attachments-about\n2. https://learn.microsoft.com/en-us/defender-office-365/safe-attachments-policies-\nconfigure","Rationale":"Enabling Safe Attachments policy helps protect against malware threats in email\nattachments by analyzing suspicious attachments in a secure, cloud-based environment\nbefore they are delivered to the user's inbox. This provides an additional layer of\nsecurity and can prevent new or unseen types of malware from infiltrating the\norganization's network.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.4"}
CIS_METADATA_END #>
# Required Services: SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Safe Attachment Policies
    $safeAttachmentPolicies = Get-SafeAttachmentPolicy

    # Process each policy and check compliance
    foreach ($policy in $safeAttachmentPolicies) {
        $isCompliant = $false
        if ($policy.Enable -eq $true) {
            $isCompliant = $true
        }

        # Add policy result to the results array
        $resourceResults += @{
            Identity = $policy.Identity
            IsCompliant = $isCompliant
            Enable = $policy.Enable
            Action = $policy.Action
            QuarantineTag = $policy.QuarantineTag
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
