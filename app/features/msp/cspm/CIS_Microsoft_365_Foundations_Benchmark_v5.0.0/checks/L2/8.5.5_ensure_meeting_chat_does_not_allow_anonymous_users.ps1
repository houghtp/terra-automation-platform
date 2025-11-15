# Control: 8.5.5 - Ensure meeting chat does not allow anonymous users
<# CIS_METADATA_START
{"Description":"This policy setting controls who has access to read and write chat messages during a\nmeeting.","Impact":"Only authorized individuals will be able to read and write chat messages during a\nmeeting.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting engagement verify that Meeting chat is set to On for\neveryone but anonymous users.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl MeetingChatEnabledType\n3. Ensure the returned value is EnabledExceptAnonymous.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting engagement set Meeting chat to On for everyone but\nanonymous users.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -MeetingChatEnabledType\n\"EnabledExceptAnonymous\"","Title":"Ensure meeting chat does not allow anonymous users","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"8.5 Meetings","DefaultValue":"On for everyone (Enabled)","Level":"L2","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/skype/set-\ncsteamsmeetingpolicy?view=skype-ps#-meetingchatenabledtype","Rationale":"Ensuring that only authorized individuals can read and write chat messages during a\nmeeting reduces the risk that a malicious user can inadvertently show content that is not\nappropriate or view sensitive information.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.5"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the Teams Meeting Policy
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Check if MeetingChatEnabledType is set to a compliant value
    $isCompliant = $meetingPolicy.MeetingChatEnabledType -ne 'EnabledForAnonymousUsers'
    
    # Add result to the results array
    $resourceResults += @{
        PolicyName = $meetingPolicy.Identity
        MeetingChatEnabledType = $meetingPolicy.MeetingChatEnabledType
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
