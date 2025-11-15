# Control: 8.5.2 - Ensure anonymous users and dial-in callers can't start
<# CIS_METADATA_START
{"Description":"This policy setting controls if an anonymous participant can start a Microsoft Teams\nmeeting without someone in attendance. Anonymous users and dial-in callers must wait\nin the lobby until the meeting is started by someone in the organization or an external\nuser from a trusted organization.\nAnonymous participants are classified as:\n- Participants who are not logged in to Teams with a work or school account.\n- Participants from non-trusted organizations (as configured in external access).\n- Participants from organizations where there is not mutual trust.\nNote: This setting only applies when Who can bypass the lobby is set to Everyone.\nIf the anonymous users can join a meeting organization-level setting or meeting\npolicy is Off, this setting only applies to dial-in callers.","Impact":"Anonymous participants will not be able to start a Microsoft Teams meeting.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby verify that Anonymous users and dial-in\ncallers can start a meeting is set to Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl\nAllowAnonymousUsersToStartMeeting\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting join & lobby set Anonymous users and dial-in callers can\nstart a meeting to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -AllowAnonymousUsersToStartMeeting\n$false","Title":"Ensure anonymous users and dial-in callers can't start","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.5 Meetings","DefaultValue":"Off (False)","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/anonymous-users-in-meetings\n2. https://learn.microsoft.com/en-us/microsoftteams/who-can-bypass-meeting-\nlobby#overview-of-lobby-settings-and-policies","Rationale":"Not allowing anonymous participants to automatically join a meeting reduces the risk of\nmeeting spamming.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.2"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the Teams Meeting Policy
    $teamsMeetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Analyze the policy settings
    $isCompliant = $true
    if ($teamsMeetingPolicy.AllowAnonymousUsersToStartMeeting -eq $true -or $teamsMeetingPolicy.AllowDialInUsersToBypassLobby -eq $true) {
        $isCompliant = $false
    }
    
    # Add result to the results array
    $resourceResults += @{
        PolicyName = $teamsMeetingPolicy.Identity
        AllowAnonymousUsersToStartMeeting = $teamsMeetingPolicy.AllowAnonymousUsersToStartMeeting
        AllowDialInUsersToBypassLobby = $teamsMeetingPolicy.AllowDialInUsersToBypassLobby
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
