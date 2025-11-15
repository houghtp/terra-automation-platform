# Control: 8.5.9 - Ensure meeting recording is off by default
<# CIS_METADATA_START
{"Description":"This setting controls the ability for a user to initiate a recording of a meeting in progress.\nThe recommended state is Off for the Global (Org-wide default) meeting policy.","Impact":"If there are no additional policies allowing anyone to record, then recording will\neffectively be disabled.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under Recording & transcription verify that Meeting recording is set to Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to verify the recommended state:\nGet-CsTeamsMeetingPolicy -Identity Global | fl AllowCloudRecording\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Meetings select Meeting policies.\n3. Click Global (Org-wide default).\n4. Under Recording & transcription set Meeting recording to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Run the following command to set the recommended state:\nSet-CsTeamsMeetingPolicy -Identity Global -AllowCloudRecording $false","Title":"Ensure meeting recording is off by default","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"8.5 Meetings","DefaultValue":"On (True)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"16.10\", \"title\": \"Apply Secure Design Principles in Application\", \"description\": \"Architectures Apply secure design principles in application architectures. Secure design principles include the concept of least privilege and enforcing mediation to validate v8 every operation that the user makes, promoting the concept of \\\"never trust user - - input.\\\" Examples include ensuring that explicit error checking is performed and documented for all input, including for size, data type, and acceptable ranges or formats. Secure design also means minimizing the application infrastructure attack surface, such as turning off unprotected ports and services, removing unnecessary programs and files, and renaming or removing default accounts.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"8.6\", \"title\": \"Messaging\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoftteams/settings-policies-\nreference#recording--transcription","Rationale":"Disabling meeting recordings in the Global meeting policy ensures that only authorized\nusers, such as organizers, co-organizers, and leads, can initiate a recording. This\nmeasure helps safeguard sensitive information by preventing unauthorized individuals\nfrom capturing and potentially sharing meeting content. Restricting recording\ncapabilities to specific roles allows organizations to exercise greater control over what is\nrecorded, aligning it with the meeting's confidentiality requirements.\nNote: Creating a separate policy for users or groups who are allowed to record is\nexpected and in compliance. This control is only for the default meeting policy.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.5.9"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    $meetingPolicy = Get-CsTeamsMeetingPolicy -Identity Global
    
    # Check if AllowCloudRecording is set to False
    $isCompliant = -not $meetingPolicy.AllowCloudRecording
    $resourceResults += @{
        PolicyName = $meetingPolicy.Identity
        AllowCloudRecording = $meetingPolicy.AllowCloudRecording
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
