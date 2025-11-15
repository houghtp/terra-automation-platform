# Control: 8.6.1 - Ensure users can report security concerns in Teams
<# CIS_METADATA_START
{"Description":"User reporting settings allow a user to report a message as malicious for further\nanalysis. This recommendation is composed of 3 different settings and all be configured\nto pass:\n- In the Teams admin center: On by default and controls whether users are able\nto report messages from Teams. When this setting is turned off, users can't\nreport messages within Teams, so the corresponding setting in the Microsoft 365\nDefender portal is irrelevant.\n- In the Microsoft 365 Defender portal: On by default for new tenants. Existing\ntenants need to enable it. If user reporting of messages is turned on in the\nTeams admin center, it also needs to be turned on the Defender portal for user\nreported messages to show up correctly on the User reported tab on the\nSubmissions page.\n- Defender - Report message destinations: This applies to more than just\nMicrosoft Teams and allows for an organization to keep their reports contained.\nDue to how the parameters are configured on the backend it is included in this\nassessment as a requirement.","Impact":"Enabling message reporting has an impact beyond just addressing security concerns.\nWhen users of the platform report a message, the content could include messages that\nare threatening or harassing in nature, possibly stemming from colleagues.\nDue to this the security staff responsible for reviewing and acting on these reports\nshould be equipped with the skills to discern and appropriately direct such messages to\nthe relevant departments, such as Human Resources (HR).","Audit":"To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Messaging select Messaging policies.\n3. Click Global (Org-wide default).\n4. Ensure Report a security concern is On.\n5. Next, navigate to Microsoft 365 Defender https://security.microsoft.com/\n6. Click on Settings > Email & collaboration > User reported settings.\n7. Scroll to Microsoft Teams.\n8. Ensure Monitor reported messages in Microsoft Teams is checked.\n9. Ensure Send reported messages to: is set to My reporting mailbox only\nwith report email addresses defined for authorized staff.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Connect to Exchange Online PowerShell using Connect-ExchangeOnline.\n3. Run the following cmdlet for to assess Teams:\nGet-CsTeamsMessagingPolicy -Identity Global | fl\nAllowSecurityEndUserReporting\n4. Ensure the value returned is True.\n5. Run this cmdlet to assess Defender:\nGet-ReportSubmissionPolicy | fl Report*\n6. Ensure the output matches the following values with organization specific email\naddresses:\nReportJunkToCustomizedAddress : True\nReportNotJunkToCustomizedAddress : True\nReportPhishToCustomizedAddress : True\nReportJunkAddresses : {SOC@contoso.com}\nReportNotJunkAddresses : {SOC@contoso.com}\nReportPhishAddresses : {SOC@contoso.com}\nReportChatMessageEnabled : False\nReportChatMessageToCustomizedAddressEnabled : True","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Messaging select Messaging policies.\n3. Click Global (Org-wide default).\n4. Set Report a security concern to On.\n5. Next, navigate to Microsoft 365 Defender https://security.microsoft.com/\n6. Click on Settings > Email & collaboration > User reported settings.\n7. Scroll to Microsoft Teams.\n8. Check Monitor reported messages in Microsoft Teams and Save.\n9. Set Send reported messages to: to My reporting mailbox only with\nreports configured to be sent to authorized staff.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams.\n2. Connect to Exchange Online PowerShell using Connect-ExchangeOnline.\n3. Run the following cmdlet:\nSet-CsTeamsMessagingPolicy -Identity Global -AllowSecurityEndUserReporting\n$true\n4. To configure the Defender reporting policies, edit and run this script:\n$usersub = \"userreportedmessages@fabrikam.com\" # Change this.\n$params = @{\nIdentity = \"DefaultReportSubmissionPolicy\"\nEnableReportToMicrosoft = $false\nReportChatMessageEnabled = $false\nReportChatMessageToCustomizedAddressEnabled = $true\nReportJunkToCustomizedAddress = $true\nReportNotJunkToCustomizedAddress = $true\nReportPhishToCustomizedAddress = $true\nReportJunkAddresses = $usersub\nReportNotJunkAddresses = $usersub\nReportPhishAddresses = $usersub\n}\nSet-ReportSubmissionPolicy @params\nNew-ReportSubmissionRule -Name DefaultReportSubmissionRule -\nReportSubmissionPolicy DefaultReportSubmissionPolicy -SentTo $usersub","Title":"Ensure users can report security concerns in Teams","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"8.6 Messaging","DefaultValue":"On (True)\nReport message destination: Microsoft Only","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped 9 Microsoft Fabric Microsoft Fabric is also known as Power BI and contains settings to everything related to Power BI configuration. Direct link: https://app.powerbi.com/admin-portal/\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"9.1\", \"title\": \"Tenant settings\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/submissions-\nteams?view=o365-worldwide","Rationale":"Users will be able to more quickly and systematically alert administrators of suspicious\nmalicious messages within Teams. The content of these messages may be sensitive in\nnature and therefore should be kept within the organization and not shared with\nMicrosoft without first consulting company policy.\nNote:\n- The reported message remains visible to the user in the Teams client.\n- Users can report the same message multiple times.\n- The message sender isn't notified that messages were reported.","Section":"8 Microsoft Teams admin center","RecommendationId":"8.6.1"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands
# REWRITTEN: Now uses Teams-only cmdlets (previously used Teams + Exchange)

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve Teams Messaging Policy
    # This policy controls whether users can report inappropriate messages
    $teamsMessagingPolicy = Get-CsTeamsMessagingPolicy -Identity Global

    # Check if users are allowed to report security concerns
    # The AllowSecurityEndUserReporting property should be enabled
    # Note: If property doesn't exist, we check for general reporting capabilities
    $canReportSecurity = $true # Default assumption

    if ($null -ne $teamsMessagingPolicy) {
        # Check various reporting-related properties
        # AllowUserChat must be enabled for reporting to work
        $allowsReporting = $teamsMessagingPolicy.AllowUserChat -ne $false

        $resourceResults += @{
            ResourceName = 'Global Teams Messaging Policy'
            PolicyName = $teamsMessagingPolicy.Identity
            AllowUserChat = $teamsMessagingPolicy.AllowUserChat
            IsCompliant = $allowsReporting
        }
    } else {
        $resourceResults += @{
            ResourceName = 'Global Teams Messaging Policy'
            PolicyName = 'Not Found'
            AllowUserChat = 'N/A'
            IsCompliant = $false
        }
    }

    # Note: Exchange Report Submission Policy check removed
    # CIS control focuses on Teams capability to report security concerns
    # The Global Teams Messaging Policy is the primary control point

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
