# Control: 6.5.2 - Ensure MailTips are enabled for end users
<# CIS_METADATA_START
{"Description":"MailTips are informative messages displayed to users while they're composing a\nmessage. While a new message is open and being composed, Exchange analyzes the\nmessage (including recipients). If a potential problem is detected, the user is notified\nwith a MailTip prior to sending the message. Using the information in the MailTip, the\nuser can adjust the message to avoid undesirable situations or non-delivery reports\n(also known as NDRs or bounce messages).","Impact":"Not applicable.","Audit":"To audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-OrganizationConfig | fl MailTips*\n3. Verify the values for MailTipsAllTipsEnabled,\nMailTipsExternalRecipientsTipsEnabled, and\nMailTipsGroupMetricsEnabled are set to True and\nMailTipsLargeAudienceThreshold is set to an acceptable value; 25 is the\ndefault value.","Remediation":"To remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\n$TipsParams = @{\nMailTipsAllTipsEnabled = $true\nMailTipsExternalRecipientsTipsEnabled = $true\nMailTipsGroupMetricsEnabled = $true\nMailTipsLargeAudienceThreshold = '25'\n}\nSet-OrganizationConfig @TipsParams","Title":"Ensure MailTips are enabled for end users","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.5 Settings","DefaultValue":"MailTipsAllTipsEnabled: True MailTipsExternalRecipientsTipsEnabled: False\nMailTipsGroupMetricsEnabled: True MailTipsLargeAudienceThreshold: 25","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-\nonline/mailtips/mailtips\n2. https://learn.microsoft.com/en-us/powershell/module/exchange/set-\norganizationconfig?view=exchange-ps","Rationale":"Setting up MailTips gives a visual aid to users when they send emails to large groups of\nrecipients or send emails to recipients not within the tenant.","Section":"6 Exchange admin center","RecommendationId":"6.5.2"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original cmdlet to retrieve MailTips configuration
    $orgConfig = Get-OrganizationConfig | Select-Object MailTipsAllTipsEnabled
    
    # Check if MailTips are enabled
    $isCompliant = $orgConfig.MailTipsAllTipsEnabled -eq $true
    
    # Add the result to the results array
    $resourceResults += @{
        Name = "MailTipsAllTipsEnabled"
        IsCompliant = $isCompliant
        CurrentValue = $orgConfig.MailTipsAllTipsEnabled
        ExpectedValue = $true
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
