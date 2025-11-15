# Control: 8.5.8 - Ensure external meeting chat is off
<# CIS_METADATA_START
{"Description":"This meeting policy setting controls whether users can read or write messages in\nexternal meeting chats with untrusted organizations. If an external organization is on the\nlist of trusted organizations this setting will be ignored.","Impact":"When joining external meetings users will be unable to read or write chat messages in\nTeams meetings with organizations that they don't have a trust relationship with. This\nwill completely remove the chat functionality in meetings. From an I.T. perspective both\nthe upkeep of adding new organizations to the trusted list and the decision-making\nprocess behind whether to trust or not trust an external partner will increase time\nexpenditure.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting engagement verify that External meeting chat is set to Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl\nAllowExternalNonTrustedMeetingChat\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under meeting engagement set External meeting chat to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -AllowExternalNonTrustedMeetingChat\n$false","Title":"Ensure external meeting chat is off","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"8.5 Meetings","DefaultValue":"On(True)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"16.10\", \"title\": \"Apply Secure Design Principles in Application\", \"description\": \"Architectures Apply secure design principles in application architectures. Secure design principles include the concept of least privilege and enforcing mediation to validate v8 every operation that the user makes, promoting the concept of \\\"never trust user - - input.\\\" Examples include ensuring that explicit error checking is performed and documented for all input, including for size, data type, and acceptable ranges or formats. Secure design also means minimizing the application infrastructure attack surface, such as turning off unprotected ports and services, removing unnecessary programs and files, and renaming or removing default accounts.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/settings-policies-\nreference#meeting-engagement","Rationale":"Restricting access to chat in meetings hosted by external organizations limits the\nopportunity for an exploit like GIFShell or DarkGate malware from being delivered to\nusers.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.8"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Get the Teams Meeting Policy for the Global identity
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Check if external meeting chat is off
    $isExternalMeetingChatOff = $meetingPolicy.AllowChatInMeetings -eq $false
    
    # Add result to the results array
    $resourceResults += @{
        PolicyName = $meetingPolicy.Identity
        AllowChatInMeetings = $meetingPolicy.AllowChatInMeetings
        IsCompliant = $isExternalMeetingChatOff
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
