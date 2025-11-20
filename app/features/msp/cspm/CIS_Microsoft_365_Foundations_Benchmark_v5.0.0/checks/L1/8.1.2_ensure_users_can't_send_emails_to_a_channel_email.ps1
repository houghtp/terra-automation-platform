# Control: 8.1.2 - Ensure users can't send emails to a channel email
<# CIS_METADATA_START
{"Description": "Teams channel email addresses are an optional feature that allows users to email the\nTeams channel directly.", "Impact": "Users will not be able to email the channel directly.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Teams select Teams settings.\n3. Under email integration verify that Users can send emails to a channel\nemail address is Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsClientConfiguration -Identity Global | fl AllowEmailIntoChannel\n3. Ensure the returned value is False.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Teams select Teams settings.\n3. Under email integration set Users can send emails to a channel email\naddress to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsClientConfiguration -Identity Global -AllowEmailIntoChannel $false", "Title": "Ensure users can't send emails to a channel email address", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "8.1 Teams", "DefaultValue": "On (True)", "Level": "L1", "CISControls": "[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"8.2\", \"title\": \"Users\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoft-365/security/office-365-security/step-\nby-step-guides/reducing-attack-surface-in-microsoft-teams?view=o365-\nworldwide#restricting-channel-email-messages-to-approved-domains\n2. https://learn.microsoft.com/en-us/powershell/module/skype/set-\ncsteamsclientconfiguration?view=skype-ps\n3. https://support.microsoft.com/en-us/office/send-an-email-to-a-channel-in-\nmicrosoft-teams-d91db004-d9d7-4a47-82e6-fb1b16dfd51e", "Rationale": "Channel email addresses are not under the tenant's domain and organizations do not\nhave control over the security settings for this email address. An attacker could email\nchannels directly if they discover the channel email address.", "Section": "8 Microsoft Teams admin center", "RecommendationId": "8.1.2"}
CIS_METADATA_END #>
# Required Services: Teams, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original cmdlet to get the Teams client configuration
    $teamsClientConfig = Get-CsTeamsClientConfiguration -Identity Global
    
    # Check the AllowEmailIntoChannel setting
    $allowEmailIntoChannel = $teamsClientConfig.AllowEmailIntoChannel
    
    # Determine compliance based on the AllowEmailIntoChannel setting
    $isCompliant = $allowEmailIntoChannel -eq $false
    
    # Add the result to the results array
    $resourceResults += @{
        Name = "AllowEmailIntoChannel"
        Setting = $allowEmailIntoChannel
        IsCompliant = $isCompliant
        Details = "AllowEmailIntoChannel is set to $allowEmailIntoChannel"
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
