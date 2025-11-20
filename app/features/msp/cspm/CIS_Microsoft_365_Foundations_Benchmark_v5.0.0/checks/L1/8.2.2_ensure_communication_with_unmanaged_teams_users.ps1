# Control: 8.2.2 - Ensure communication with unmanaged Teams users
<# CIS_METADATA_START
{"Description": "This policy setting controls chats and meetings with external unmanaged Teams users\n(those not managed by an organization, such as Microsoft Teams (free)).\nThe recommended state is: People in my organization can communicate with\nunmanaged Teams accounts set to Off.", "Impact": "Users will be unable to communicate with Teams users who are not managed by an\norganization.\nOrganizations may choose create additional policies for specific groups needing to\ncommunicating with unmanaged external users.\nNote: The settings that govern chats and meetings with external unmanaged Teams\nusers aren't available in GCC, GCC High, or DOD deployments, or in private cloud\nenvironments.", "Audit": "The focus of this control at a minimum is the Global (Org-wide default) policy. If\nthe equivalent organization-wide setting is configured to Off, then this is also\nconsidered a passing state due to its increased restrictiveness.\nTo audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access\n3. Select the Policies tab.\n4. Click on the Global (Org-wide default) policy.\n5. Ensure People in my organization can communicate with unmanaged\nTeams accounts is set to Off.\nOrganization settings: Additional passing state\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access\n3. Select the Organization settings tab.\n4. Ensure People in my organization can communicate with unmanaged\nTeams accounts is set to Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nGet-CsExternalAccessPolicy -Identity Global\nEnsure EnableTeamsConsumerAccess is set to False.\nOrganization settings: Additional passing state\n1. Run the following command:\nGet-CsTenantFederationConfiguration | fl AllowTeamsConsumer\nEnsure AllowTeamsConsumer is False\nNote: The organization settings take precedence over the policy settings. The audit is\nconsidered satisfied if the organizational setting is configured as prescribed, regardless\nof whether the Global default policy value is True or False.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Policies tab\n4. Click on the Global (Org-wide default) policy.\n5. Set People in my organization can communicate with unmanaged Teams\naccounts to Off.\n6. Click Save.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nSet-CsExternalAccessPolicy -Identity Global -EnableTeamsConsumerAccess $false\nNote: Configuring the organization settings to block communication is also in\ncompliance with this control.", "Title": "Ensure communication with unmanaged Teams users is disabled", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "8.2 Users", "DefaultValue": "- EnableTeamsConsumerAccess : True", "Level": "L1", "CISControls": "[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoftteams/trusted-organizations-external-\nmeetings-chat?tabs=organization-settings\n2. https://cybersecurity.att.com/blogs/security-essentials/darkgate-malware-\ndelivered-via-microsoft-teams-detection-and-response\n3. https://www.microsoft.com/en-us/security/blog/2023/08/02/midnight-blizzard-\nconducts-targeted-social-engineering-over-microsoft-teams/\n4. https://www.bitdefender.com/blog/hotforsecurity/gifshell-attack-lets-hackers-\ncreate-reverse-shell-through-microsoft-teams-gifs/", "Rationale": "Allowing users to communicate with unmanaged Teams users presents a potential\nsecurity threat as little effort is required by threat actors to gain access to a trial or free\nMicrosoft Teams account.\nSome real-world attacks and exploits delivered via Teams over external access\nchannels include:\n- DarkGate malware\n- Social engineering / Phishing attacks by \"Midnight Blizzard\"\n- GIFShell\n- Username enumeration", "Section": "8 Microsoft Teams admin center", "RecommendationId": "8.2.2"}
CIS_METADATA_END #>
# Required Services: SharePoint, Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the Global External Access Policy
    $externalAccessPolicy = Get-CsExternalAccessPolicy -Identity Global
    $externalAccessPolicyResult = @{
        Name = "Global External Access Policy"
        IsCompliant = $null
        Details = $externalAccessPolicy
    }
    
    # Retrieve the Tenant Federation Configuration
    $tenantFederationConfig = Get-CsTenantFederationConfiguration
    $tenantFederationConfigResult = @{
        Name = "Tenant Federation Configuration"
        IsCompliant = $null
        AllowTeamsConsumer = $tenantFederationConfig.AllowTeamsConsumer
    }
    
    # Determine compliance based on AllowTeamsConsumer setting
    if ($tenantFederationConfig.AllowTeamsConsumer -eq $true) {
        $tenantFederationConfigResult.IsCompliant = $true
    } else {
        $tenantFederationConfigResult.IsCompliant = $false
    }
    
    # Add results to the results array
    $resourceResults += $externalAccessPolicyResult
    $resourceResults += $tenantFederationConfigResult
    
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
