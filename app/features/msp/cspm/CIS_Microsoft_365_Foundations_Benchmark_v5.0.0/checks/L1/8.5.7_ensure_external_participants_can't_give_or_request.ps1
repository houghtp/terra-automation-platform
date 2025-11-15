# Control: 8.5.7 - Ensure external participants can't give or request
<# CIS_METADATA_START
{"Description":"This policy setting allows control of who can present in meetings and who can request\ncontrol of the presentation while a meeting is underway.","Impact":"External participants will not be able to present or request control during the meeting.\nWarning: This setting also affects webinars.\nNote: At this time, to give and take control of shared content during a meeting, both\nparties must be using the Teams desktop client. Control isn't supported when either\nparty is running Teams in a browser.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under content sharing verify that External participants can give or\nrequest control is Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl\nAllowExternalParticipantGiveRequestControl\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under content sharing set External participants can give or request\ncontrol to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -\nAllowExternalParticipantGiveRequestControl $false","Title":"Ensure external participants can't give or request","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.5 Meetings","DefaultValue":"Off (False)","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/meeting-who-present-request-\ncontrol\n2. https://learn.microsoft.com/en-us/powershell/module/skype/set-\ncsteamsmeetingpolicy?view=skype-ps","Rationale":"Ensuring that only authorized individuals and not external participants are able to\npresent and request control reduces the risk that a malicious user can inadvertently\nshow content that is not appropriate.\nExternal participants are categorized as follows: external users, guests, and anonymous\nusers.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.7"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the Teams Meeting Policy
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Analyze the policy settings
    $isCompliant = $true
    if ($meetingPolicy.AllowExternalParticipantsToGiveRequestControl -eq $true) {
        $isCompliant = $false
    }
    
    # Add the result to the results array
    $resourceResults += @{
        PolicyName = $meetingPolicy.Identity
        AllowExternalParticipantsToGiveRequestControl = $meetingPolicy.AllowExternalParticipantsToGiveRequestControl
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
