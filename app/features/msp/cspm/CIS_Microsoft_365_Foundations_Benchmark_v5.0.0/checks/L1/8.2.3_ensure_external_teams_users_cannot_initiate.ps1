# Control: 8.2.3 - Ensure external Teams users cannot initiate
<# CIS_METADATA_START
{"Description": "This setting prevents external users who are not managed by an organization from\ninitiating contact with users in the protected organization.\nThe recommended state is to uncheck External users with Teams accounts not\nmanaged by an organization can contact users in my organization.\nNote: Disabling this setting is used as an additional stop gap for the previous setting\nwhich disables communication with unmanaged Teams users entirely. If an organization\nchooses to have an exception to (L1) Ensure communication with unmanaged\nTeams users is disabled they can do so while also disabling the ability for the same\ngroup of users to initiate contact. Disabling communication entirely will also disable the\nability for unmanaged users to initiate contact.", "Impact": "The impact of disabling this is very low.\nOrganizations may choose to create additional policies for specific groups that need to\ncommunicate with unmanaged external users.\nNote: Chats and meetings with external unmanaged Teams users isn't available in\nGCC, GCC High, or DOD deployments, or in private cloud environments.", "Audit": "The focus of this control at a minimum is the Global (Org-wide default) policy. If\nthe equivalent organization-wide setting is disabled, then this is also considered a\npassing state due to its increased restrictiveness.\nTo audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Policies tab.\n4. Click on the Global (Org-wide default) policy.\n5. Ensure External users with Teams accounts not managed by an\norganization can contact users in my organization is not checked\n(false).\nOrganization settings: Additional passing state\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Organization settings tab.\n4. Locate the parent setting People in my organization can communicate with\nunmanaged Teams accounts.\n5. Ensure External users with Teams accounts not managed by an\norganization can contact users in my organization is not checked\n(false).\nNote: If the parent setting People in my organization can communicate with\nunmanaged Teams accounts is already set to Off then this setting will not be visible in\nthe UI.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nGet-CsExternalAccessPolicy -Identity Global\nEnsure EnableTeamsConsumerInbound is False\nOrganization settings: Additional passing state\n1. Run the following command:\nGet-CsTenantFederationConfiguration | fl AllowTeamsConsumerInbound\nEnsure AllowTeamsConsumerInbound is False\nNote: The organization settings take precedence over the policy settings. The audit is\nconsidered satisfied if the organizational setting is configured as prescribed, regardless\nof whether the Global default policy value is True or False.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Policies tab.\n4. Click on the Global (Org-wide default) policy.\n5. Locate the parent setting People in my organization can communicate with\nunmanaged Teams accounts.\n6. Uncheck External users with Teams accounts not managed by an\norganization can contact users in my organization.\n7. Click Save.\nNote: If People in my organization can communicate with unmanaged Teams\naccounts is already set to Off then this setting will not be visible and will satisfy the\nrequirements of this recommendation.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nSet-CsExternalAccessPolicy -Identity Global -EnableTeamsConsumerInbound\n$false\nNote: Configuring the organization settings to block inbound communication is also in\ncompliance with this control.", "Title": "Ensure external Teams users cannot initiate conversations", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "8.2 Users", "DefaultValue": "- EnableTeamsConsumerInbound : True", "Level": "L1", "CISControls": "[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoftteams/trusted-organizations-external-\nmeetings-chat?tabs=organization-settings\n2. https://cybersecurity.att.com/blogs/security-essentials/darkgate-malware-\ndelivered-via-microsoft-teams-detection-and-response\n3. https://www.microsoft.com/en-us/security/blog/2023/08/02/midnight-blizzard-\nconducts-targeted-social-engineering-over-microsoft-teams/\n4. https://www.bitdefender.com/blog/hotforsecurity/gifshell-attack-lets-hackers-\ncreate-reverse-shell-through-microsoft-teams-gifs/", "Rationale": "Allowing users to communicate with unmanaged Teams users presents a potential\nsecurity threat as little effort is required by threat actors to gain access to a trial or free\nMicrosoft Teams account.\nSome real-world attacks and exploits delivered via Teams over external access\nchannels include:\n- DarkGate malware\n- Social engineering / Phishing attacks by \"Midnight Blizzard\"\n- GIFShell\n- Username enumeration", "Section": "8 Microsoft Teams admin center", "RecommendationId": "8.2.3"}
CIS_METADATA_END #>
# Required Services: SharePoint, Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Check the Global External Access Policy
    $externalAccessPolicy = Get-CsExternalAccessPolicy -Identity Global
    $isExternalAccessPolicyCompliant = $externalAccessPolicy -ne $null
    
    # Check the Tenant Federation Configuration
    $tenantFederationConfig = Get-CsTenantFederationConfiguration
    $isTenantFederationConfigCompliant = $tenantFederationConfig.AllowTeamsConsumerInbound -eq $false
    
    # Add results to the results array
    $resourceResults += @{
        Name = "External Access Policy"
        IsCompliant = $isExternalAccessPolicyCompliant
        Details = if ($isExternalAccessPolicyCompliant) { "External Access Policy is configured." } else { "External Access Policy is not configured." }
    }
    
    $resourceResults += @{
        Name = "Tenant Federation Configuration"
        IsCompliant = $isTenantFederationConfigCompliant
        Details = if ($isTenantFederationConfigCompliant) { "Teams Consumer Inbound is not allowed." } else { "Teams Consumer Inbound is allowed." }
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
