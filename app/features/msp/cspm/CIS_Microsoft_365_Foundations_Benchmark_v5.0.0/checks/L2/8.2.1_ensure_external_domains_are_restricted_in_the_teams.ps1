# Control: 8.2.1 - Ensure external domains are restricted in the Teams
<# CIS_METADATA_START
{"Description": "This policy controls whether external domains are allowed, blocked or permitted based\non an allowlist or denylist. When external domains are allowed, users in your\norganization can chat, add users to meetings, and use audio video conferencing with\nusers in external organizations.\nThe recommended state is Allow only specific external domains or Block all\nexternal domains.", "Impact": "The impact in terms of the type of collaboration users are allowed to participate in and\nthe I.T. resources expended to manage an allowlist will increase. If a user attempts to\njoin the inviting organization's meeting they will be prevented from joining unless they\nwere created as a guest in EntraID or their domain was added to the allowed external\ndomains list.\nNote Organizations may choose create additional policies for specific groups needing\nexternal access.", "Audit": "The focus of this control at a minimum is the Global (Org-wide default) policy. If\nthe organization-wide setting is configured to Allow only specific external\ndomains or Block all external domains, then this is also considered a passing\nstate due to its increased restrictiveness.\nTo audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Policies tab.\n4. Click on the Global (Org-wide default) policy.\n5. Ensure Teams and Skype for Business users in external\norganizations is set to Off.\nOrganization settings: Additional passing state\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Organization settings tab.\n4. Ensure Teams and Skype for Business users in external\norganizations is set to one of the following:\no Allowlist: Allow only specific external domains\no Disabled: Block all external domains\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command:\nGet-CsExternalAccessPolicy -Identity Global\n3. Ensure EnableFederationAccess is False.\nOrganization settings: Additional passing state\n1. Run the following command:\nGet-CsTenantFederationConfiguration | fl AllowFederatedUsers,AllowedDomains\nEnsure the following conditions:\n- State: AllowFederatedUsers is set to False OR,\n- If: AllowFederatedUsers is True then ensure AllowedDomains contains\nauthorized domain names and is not set to AllowAllKnownDomains.\nNote: The organization settings take precedence over the policy settings. The audit is\nconsidered satisfied if the organizational setting is configured as prescribed, regardless\nof whether the Global default policy value is True or False.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com/.\n2. Click to expand Users select External access.\n3. Select the Policies tab\n4. Click on the Global (Org-wide default) policy.\n5. Set Teams and Skype for Business users in external organizations to\nOff.\n6. Click Save.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command to configure the Global (Org-wide default)` policy.\nSet-CsExternalAccessPolicy -Identity Global -EnableFederationAccess $false\nNote: Configuring the organization settings to block external access or to use a domain\nallowlist is also ni compliance with this control.", "Title": "Ensure external domains are restricted in the Teams admin center", "ProfileApplicability": "- E3 Level 2\n- E5 Level 2", "SubSection": "8.2 Users", "DefaultValue": "EnableFederationAccess - $True", "Level": "L2", "CISControls": "[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoftteams/trusted-organizations-external-\nmeetings-chat?tabs=organization-settings\n2. https://cybersecurity.att.com/blogs/security-essentials/darkgate-malware-\ndelivered-via-microsoft-teams-detection-and-response\n3. https://www.microsoft.com/en-us/security/blog/2023/08/02/midnight-blizzard-\nconducts-targeted-social-engineering-over-microsoft-teams/\n4. https://www.bitdefender.com/blog/hotforsecurity/gifshell-attack-lets-hackers-\ncreate-reverse-shell-through-microsoft-teams-gifs/", "Rationale": "Allowlisting external domains that an organization is collaborating with allows for\nstringent controls over who an organization's users are allowed to make contact with.\nSome real-world attacks and exploits delivered via Teams over external access\nchannels include:\n- DarkGate malware\n- Social engineering / Phishing attacks by \"Midnight Blizzard\"\n- GIFShell\n- Username enumeration", "Section": "8 Microsoft Teams admin center", "RecommendationId": "8.2.1"}
CIS_METADATA_END #>
# Required Services: SharePoint, Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the Global External Access Policy
    $externalAccessPolicy = Get-CsExternalAccessPolicy -Identity Global
    $resourceResults += @{
        Name = "External Access Policy"
        IsCompliant = $externalAccessPolicy -ne $null
        Details = $externalAccessPolicy
    }
    
    # Retrieve the Tenant Federation Configuration
    $tenantFederationConfig = Get-CsTenantFederationConfiguration
    $resourceResults += @{
        Name = "Tenant Federation Configuration"
        IsCompliant = $tenantFederationConfig.AllowFederatedUsers -eq $false -and $tenantFederationConfig.AllowedDomains.Count -eq 0
        Details = @{
            AllowFederatedUsers = $tenantFederationConfig.AllowFederatedUsers
            AllowedDomains = $tenantFederationConfig.AllowedDomains
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
