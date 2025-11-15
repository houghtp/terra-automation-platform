# Control: 8.5.4 - Ensure users dialing in can't bypass the lobby
<# CIS_METADATA_START
{"Description":"This policy setting controls if users who dial in by phone can join the meeting directly or\nmust wait in the lobby. Admittance to the meeting from the lobby is authorized by the\nmeeting organizer, co-organizer, or presenter of the meeting.","Impact":"Individuals who are dialing in to the meeting must wait in the lobby until a meeting\norganizer, co-organizer, or presenter admits them.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby verify that People dialing in can bypass the\nlobby is set to Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl AllowPSTNUsersToBypassLobby\n3. Ensure the value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby set People dialing in can bypass the lobby to\nOff.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -AllowPSTNUsersToBypassLobby $false","Title":"Ensure users dialing in can't bypass the lobby","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.5 Meetings","DefaultValue":"Off (False)","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/who-can-bypass-meeting-\nlobby#overview-of-lobby-settings-and-policies\n2. https://learn.microsoft.com/en-us/powershell/module/skype/set-\ncsteamsmeetingpolicy?view=skype-ps","Rationale":"For meetings that could contain sensitive information, it is best to allow the meeting\norganizer to vet anyone not directly from the organization.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.4"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Get the Teams Meeting Policy for Global
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Check if PSTN users are allowed to bypass the lobby
    $allowPSTNBypass = $meetingPolicy.AllowPSTNUsersToBypassLobby
    
    # Convert results to standard format
    $result = @{
        PolicyName = 'Global'
        AllowPSTNUsersToBypassLobby = $allowPSTNBypass
        IsCompliant = -not $allowPSTNBypass
    }
    
    # Add result to the results array
    $resourceResults += $result
    
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
