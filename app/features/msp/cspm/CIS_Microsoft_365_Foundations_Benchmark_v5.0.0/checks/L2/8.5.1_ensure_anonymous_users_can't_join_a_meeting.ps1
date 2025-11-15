# Control: 8.5.1 - Ensure anonymous users can't join a meeting
<# CIS_METADATA_START
{"Description":"Anonymous users are users whose identity can't be verified. They may be logged in to\nan organization without a mutual trust relationship or they may not have an account\n(guest or user). Anonymous participants appear with \"(Unverified)\" appended to their\nname in meetings.\nThese users could include:\n- Users who aren't logged in to Teams with a work or school account.\n- Users from non-trusted organizations (as configured in external access) and from\norganizations that you trust but which don't trust your organization. When\ndefining trusted organizations for external meetings and chat, ensure both\norganizations allow each other's domains. Meeting organizers and participants\nshould have user policies that allow external access. These settings prevent\nattendees from being considered anonymous due to external access settings.\nFor details, see IT Admins - Manage external meetings and chat with people and\norganizations using Microsoft identities\nThe recommended state is Anonymous users can join a meeting unverified set\nto Off.","Impact":"Individuals who were not sent or forwarded a meeting invite will not be able to join the\nmeeting automatically.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby verify that Anonymous users can join a meeting\nunverified is set to Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl\nAllowAnonymousUsersToJoinMeeting\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default)\n4. Under meeting join & lobby set Anonymous users can join a meeting\nunverified to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -AllowAnonymousUsersToJoinMeeting\n$false","Title":"Ensure anonymous users can't join a meeting","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"8.5 Meetings","DefaultValue":"On (True)","Level":"L2","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/step-by-step-\nguides/reducing-attack-surface-in-microsoft-teams?view=o365-\nworldwide#configure-meeting-settings\n2. https://learn.microsoft.com/en-us/microsoftteams/settings-policies-\nreference?WT.mc_id=TeamsAdminCenterCSH#meeting-join--lobby\n3. https://learn.microsoft.com/en-us/MicrosoftTeams/configure-meetings-sensitive-\nprotection\n4. https://learn.microsoft.com/en-us/microsoftteams/anonymous-users-in-meetings\n5. https://learn.microsoft.com/en-us/microsoftteams/plan-meetings-external-\nparticipants","Rationale":"For meetings that could contain sensitive information, it is best to allow the meeting\norganizer to vet anyone not directly sent an invite before admitting them to the meeting.\nThis will also prevent the anonymous user from using the meeting link to have meetings\nat unscheduled times.\nNote: Those companies that don't normally operate at a Level 2 environment, but do\ndeal with sensitive information, may want to consider this policy setting.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.1"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the Teams Meeting Policy
    $teamsMeetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Check if anonymous users are allowed to join meetings
    $isAnonymousJoinDisabled = $teamsMeetingPolicy.AllowAnonymousUsersToJoinMeeting -eq $false
    
    # Add the result to the results array
    $resourceResults += @{
        PolicyName = $teamsMeetingPolicy.Identity
        AllowAnonymousUsersToJoinMeeting = $teamsMeetingPolicy.AllowAnonymousUsersToJoinMeeting
        IsCompliant = $isAnonymousJoinDisabled
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
