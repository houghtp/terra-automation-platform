# Control: 8.5.3 - Ensure only people in my org can bypass the lobby
<# CIS_METADATA_START
{"Description":"This policy setting controls who can join a meeting directly and who must wait in the\nlobby until they're admitted by an organizer, co-organizer, or presenter of the meeting.\nThe recommended state is People who were invited or more restrictive.","Impact":"Individuals who are not part of the organization will have to wait in the lobby until they're\nadmitted by an organizer, co-organizer, or presenter of the meeting.\nAny individual who dials into the meeting regardless of status will also have to wait in\nthe lobby. This includes internal users who are considered unauthenticated when dialing\nin.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby verify Who can bypass the lobby is set to People\nwho were invited or a more restrictive value: People in my org, Only\norganizers and co-organizers.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl AutoAdmittedUsers\n3. Ensure the returned value is InvitedUsers or more restrictive:\nEveryoneInCompanyExcludingGuests, OrganizerOnly.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby set Who can bypass the lobby to People who\nwere invited or a more restrictive value: People in my org, Only\norganizers and co-organizers.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -AutoAdmittedUsers \"InvitedUsers\"\nNote: More restrictive values EveryoneInCompanyExcludingGuests or\nOrganizerOnly are also in compliance.","Title":"Ensure only people in my org can bypass the lobby","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.5 Meetings","DefaultValue":"People in my org and guests (EveryoneInCompany)","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"6.8\", \"title\": \"Define and Maintain Role-Based Access Control\", \"description\": \"Define and maintain role-based access control, through determining and v8 documenting the access rights necessary for each role within the enterprise to - successfully carry out its assigned duties. Perform access control reviews of enterprise assets to validate that all privileges are authorized, on a recurring schedule at a minimum annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/who-can-bypass-meeting-\nlobby#overview-of-lobby-settings-and-policies\n2. https://learn.microsoft.com/en-us/powershell/module/skype/set-\ncsteamsmeetingpolicy?view=skype-ps","Rationale":"For meetings that could contain sensitive information, it is best to allow the meeting\norganizer to vet anyone not directly sent an invite before admitting them to the meeting.\nThis will also prevent the anonymous user from using the meeting link to have meetings\nat unscheduled times.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.3"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    # Removed Connect-MicrosoftTeams as authentication is handled centrally
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Analyze the policy setting
    $isCompliant = $false
    if ($meetingPolicy.AutoAdmittedUsers -eq "EveryoneInCompany") {
        $isCompliant = $true
    }
    
    # Add result to the results array
    $resourceResults += @{
        PolicyName = $meetingPolicy.Identity
        AutoAdmittedUsers = $meetingPolicy.AutoAdmittedUsers
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
