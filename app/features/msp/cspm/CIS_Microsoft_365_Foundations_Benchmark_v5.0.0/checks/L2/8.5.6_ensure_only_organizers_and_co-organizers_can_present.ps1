# Control: 8.5.6 - Ensure only organizers and co-organizers can present
<# CIS_METADATA_START
{"Description":"This policy setting controls who can present in a Teams meeting.\nNote: Organizers and co-organizers can change this setting when the meeting is set up.","Impact":"Only organizers and co-organizers will be able to present without being granted\npermission.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under content sharing verify Who can present is set to Only organizers and\nco-organizers.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl DesignatedPresenterRoleMode\n3. Ensure the returned value is OrganizerOnlyUserOverride.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under content sharing set Who can present to Only organizers and co-\norganizers.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -DesignatedPresenterRoleMode\n\"OrganizerOnlyUserOverride\"","Title":"Ensure only organizers and co-organizers can present","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"8.5 Meetings","DefaultValue":"Everyone (EveryoneUserOverride)","Level":"L2","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-US/microsoftteams/meeting-who-present-request-\ncontrol\n2. https://learn.microsoft.com/en-us/microsoftteams/meeting-who-present-request-\ncontrol#manage-who-can-present\n3. https://learn.microsoft.com/en-us/defender-office-365/step-by-step-\nguides/reducing-attack-surface-in-microsoft-teams?view=o365-\nworldwide#configure-meeting-settings-restrict-presenters\n4. https://learn.microsoft.com/en-us/powershell/module/skype/set-\ncsteamsmeetingpolicy?view=skype-ps","Rationale":"Ensuring that only authorized individuals are able to present reduces the risk that a\nmalicious user can inadvertently show content that is not appropriate.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.6"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Analyze the DesignatedPresenterRoleMode setting
    $isCompliant = $meetingPolicy.DesignatedPresenterRoleMode -eq 'OrganizerOnly'
    
    # Add result to the results array
    $resourceResults += @{
        PolicyName = $meetingPolicy.Identity
        DesignatedPresenterRoleMode = $meetingPolicy.DesignatedPresenterRoleMode
        IsCompliant = $isCompliant
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
