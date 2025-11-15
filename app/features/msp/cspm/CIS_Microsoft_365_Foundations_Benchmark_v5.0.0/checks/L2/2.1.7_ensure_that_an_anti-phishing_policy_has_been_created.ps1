# Control: 2.1.7 - Ensure that an anti-phishing policy has been created
<# CIS_METADATA_START
{"Description":"By default, Office 365 includes built-in features that help protect users from phishing\nattacks. Set up anti-phishing polices to increase this protection, for example by refining\nsettings to better detect and prevent impersonation and spoofing attacks. The default\npolicy applies to all users within the organization and is a single view to fine-tune anti-\nphishing protection. Custom policies can be created and configured for specific users,\ngroups or domains within the organization and will take precedence over the default\npolicy for the scoped users.","Impact":"Mailboxes that are used for support systems such as helpdesk and billing systems send\nmail to internal users and are often not suitable candidates for impersonation protection.\nCare should be taken to ensure that these systems are excluded from Impersonation\nProtection.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules\n3. Select Threat policies.\n4. Under Policies select Anti-phishing.\n5. Ensure an AntiPhish policy exists that is On and meets the following criteria:\n6. Under Users, groups, and domains.\no Verify that the included domains and groups includes a majority of the\norganization.\n7. Under Phishing threshold & protection\no Verify Phishing email threshold is at least 3 - More Aggressive.\no Verify User impersonation protection is On and contains a subset of\nusers.\no Verify Domain impersonation protection is On for owned domains.\no Verify Mailbox intelligence and Mailbox intelligence for\nimpersonations and Spoof intelligence are On.\n8. Under Actions review the following:\no Verify If a message is detected as user impersonation is set to\nQuarantine the message.\no Verify If a message is detected as domain impersonation is set to\nQuarantine the message.\no Verify If Mailbox Intelligence detects an impersonated user is\nset to Quarantine the message.\no Verify First contact safety tip is On.\no Verify User impersonation safety tip is On.\no Verify Domain impersonation safety tip is On.\no Verify Unusual characters safety tip is On.\no Verify Honor DMARC record policy when the message is detected\nas spoof is On.\nNote: DefaultFullAccessWithNotificationPolicy is suggested but not required.\nUsers will be notified that impersonation emails are in the Quarantine.\nTo audit using PowerShell:\n1. Connect to Exchange Online service using Connect-ExchangeOnline.\n2. Run the following Exchange Online PowerShell commands:\n$params = @(\n\"name\",\"Enabled\",\"PhishThresholdLevel\",\"EnableTargetedUserProtection\"\n\"EnableOrganizationDomainsProtection\",\"EnableMailboxIntelligence\"\n\"EnableMailboxIntelligenceProtection\",\"EnableSpoofIntelligence\"\n\"TargetedUserProtectionAction\",\"TargetedDomainProtectionAction\"\n\"MailboxIntelligenceProtectionAction\",\"EnableFirstContactSafetyTips\"\n\"EnableSimilarUsersSafetyTips\",\"EnableSimilarDomainsSafetyTips\"\n\"EnableUnusualCharactersSafetyTips\",\"TargetedUsersToProtect\"\n\"HonorDmarcPolicy\"\n)\nGet-AntiPhishPolicy | fl $params\n3. Verify there is a policy created that has matching values for the following\nparameters:\nEnabled : True\nPhishThresholdLevel : 3\nEnableTargetedUserProtection : True\nEnableOrganizationDomainsProtection : True\nEnableMailboxIntelligence : True\nEnableMailboxIntelligenceProtection : True\nEnableSpoofIntelligence : True\nTargetedUserProtectionAction : Quarantine\nTargetedDomainProtectionAction : Quarantine\nMailboxIntelligenceProtectionAction : Quarantine\nEnableFirstContactSafetyTips : True\nEnableSimilarUsersSafetyTips : True\nEnableSimilarDomainsSafetyTips : True\nEnableUnusualCharactersSafetyTips : True\nTargetedUsersToProtect : {<contains users>}\nHonorDmarcPolicy : True\n4. Verify that TargetedUsersToProtect contains a subset of the organization, up\nto 350 users, for targeted Impersonation Protection.\n5. Use PowerShell to verify the AntiPhishRule is configured and enabled.\nGet-AntiPhishRule |\nft AntiPhishPolicy,Priority,State,SentToMemberOf,RecipientDomainIs\n6. Identity correct rule from the matching AntiPhishPolicy name in step 3. Ensure\nthe rule defines groups or domains that include the majority of the organization\nby inspecting SentToMemberOf or RecipientDomainIs.\nNote: Audit guidance is intended to help identify a qualifying AntiPhish policy+rule that\nmeets the recommended criteria while protecting the majority of the organization. It's\nunderstood some individual user exceptions may exist or exceptions for the entire policy\nif another product stands in as an equivalent control.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules\n3. Select Threat policies.\n4. Under Policies select Anti-phishing and click Create.\n5. Name the policy, continuing and clicking Next as needed:\no Add Groups and/or Domains that contain a majority of the organization.\no Set Phishing email threshold to 3 - More Aggressive\no Check Enable users to protect and add up to 350 users.\no Check Enable domains to protect and check Include domains I\nown.\no Check Enable mailbox intelligence (Recommended).\no Check Enable Intelligence for impersonation protection\n(Recommended).\no Check Enable spoof intelligence (Recommended).\n6. Under Actions configure the following:\no Set If a message is detected as user impersonation to\nQuarantine the message.\no Set If a message is detected as domain impersonation to\nQuarantine the message.\no Set If Mailbox Intelligence detects an impersonated user to\nQuarantine the message.\no Leave Honor DMARC record policy when the message is detected\nas spoof checked.\no Check Show first contact safety tip (Recommended).\no Check Show user impersonation safety tip.\no Check Show domain impersonation safety tip.\no Check Show user impersonation unusual characters safety tip.\n7. Finally click Next and Submit the policy.\nNote: DefaultFullAccessWithNotificationPolicy is suggested but not required.\nUsers will be notified that impersonation emails are in the Quarantine.\nTo remediate using PowerShell:\n1. Connect to Exchange Online service using Connect-ExchangeOnline.\n2. Run the following Exchange Online PowerShell script to create an AntiPhish\npolicy:\n# Create the Policy\n$params = @{\nName = \"CIS AntiPhish Policy\"\nPhishThresholdLevel = 3\nEnableTargetedUserProtection = $true\nEnableOrganizationDomainsProtection = $true\nEnableMailboxIntelligence = $true\nEnableMailboxIntelligenceProtection = $true\nEnableSpoofIntelligence = $true\nTargetedUserProtectionAction = 'Quarantine'\nTargetedDomainProtectionAction = 'Quarantine'\nMailboxIntelligenceProtectionAction = 'Quarantine'\nTargetedUserQuarantineTag = 'DefaultFullAccessWithNotificationPolicy'\nMailboxIntelligenceQuarantineTag =\n'DefaultFullAccessWithNotificationPolicy'\nTargetedDomainQuarantineTag = 'DefaultFullAccessWithNotificationPolicy'\nEnableFirstContactSafetyTips = $true\nEnableSimilarUsersSafetyTips = $true\nEnableSimilarDomainsSafetyTips = $true\nEnableUnusualCharactersSafetyTips = $true\nHonorDmarcPolicy = $true\n}\nNew-AntiPhishPolicy @params\n# Create the rule for all users in all valid domains and associate with\nPolicy\nNew-AntiPhishRule -Name $params.Name -AntiPhishPolicy $params.Name -\nRecipientDomainIs (Get-AcceptedDomain).Name -Priority 0\n3. The new policy can be edited in the UI or via PowerShell.\nNote: Remediation guidance is intended to help create a qualifying AntiPhish policy that\nmeets the recommended criteria while protecting the majority of the organization. It's\nunderstood some individual user exceptions may exist or exceptions for the entire policy\nif another product acts as a similiar control.","Title":"Ensure that an anti-phishing policy has been created","ProfileApplicability":"- E5 Level 2","SubSection":"2.1 Email & collaboration","DefaultValue":"","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing. 7 Email and Web Browser Protections Email and Web Browser Protections\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/anti-phishing-protection-\nabout\n2. https://learn.microsoft.com/en-us/defender-office-365/anti-phishing-policies-eop-\nconfigure","Rationale":"Protects users from phishing attacks (like impersonation and spoofing) and uses safety\ntips to warn users about potentially harmful messages.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.7"}
CIS_METADATA_END #>
# Required Services: SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Define parameters for Get-AntiPhishPolicy
    $params = @(
        "name","Enabled","PhishThresholdLevel","EnableTargetedUserProtection",
        "EnableOrganizationDomainsProtection","EnableMailboxIntelligence",
        "EnableMailboxIntelligenceProtection","EnableSpoofIntelligence",
        "TargetedUserProtectionAction","TargetedDomainProtectionAction",
        "MailboxIntelligenceProtectionAction","EnableFirstContactSafetyTips",
        "EnableSimilarUsersSafetyTips","EnableSimilarDomainsSafetyTips",
        "EnableUnusualCharactersSafetyTips","TargetedUsersToProtect",
        "HonorDmarcPolicy"
    )
    
    # Retrieve Anti-Phish Policy details
    $antiPhishPolicies = Get-AntiPhishPolicy | Select-Object $params
    
    # Check each policy for compliance
    foreach ($policy in $antiPhishPolicies) {
        $isCompliant = $true
        
        # Example compliance check (customize as needed)
        if ($policy.Enabled -ne $true) {
            $isCompliant = $false
        }
        
        # Add policy result to the results array
        $resourceResults += @{
            PolicyName = $policy.name
            IsCompliant = $isCompliant
            Details = $policy
        }
    }
    
    # Retrieve Anti-Phish Rule details
    $antiPhishRules = Get-AntiPhishRule | Select-Object AntiPhishPolicy, Priority, State, SentToMemberOf, RecipientDomainIs
    
    # Check each rule for compliance
    foreach ($rule in $antiPhishRules) {
        $isCompliant = $true
        
        # Example compliance check (customize as needed)
        if ($rule.State -ne 'Enabled') {
            $isCompliant = $false
        }
        
        # Add rule result to the results array
        $resourceResults += @{
            RuleName = $rule.AntiPhishPolicy
            IsCompliant = $isCompliant
            Details = $rule
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
