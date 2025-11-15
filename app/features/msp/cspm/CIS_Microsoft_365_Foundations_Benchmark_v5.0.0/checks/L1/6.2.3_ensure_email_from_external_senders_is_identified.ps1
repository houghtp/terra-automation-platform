# Control: 6.2.3 - Ensure email from external senders is identified
<# CIS_METADATA_START
{"Description":"External callouts provide a native experience to identify emails from senders outside the\norganization. This is achieved by presenting a new tag on emails called \"External\" (the\nstring is localized based on the client language setting) and exposing related user\ninterface at the top of the message reading view to see and verify the real sender's\nemail address.\nThe recommended state is ExternalInOutlook set to Enabled True","Impact":"Mail flow rules using external tagging must be disabled, along with third-party mail\nfiltering tools that offer similar features, to avoid duplicate [External] tags.\nExternal tags can consume additional screen space on systems with limited real estate,\nsuch as thin clients or mobile devices.\nAfter enabling this feature via PowerShell, it may take 24-48 hours for users to see the\nExternal sender tag in emails from outside your organization. Rolling back the feature\ntakes the same amount of time.\nNote: Third-party tools that provide similar functionality will also meet compliance\nrequirements, although Microsoft recommends using the native experience for better\ninteroperability.","Audit":"To audit using PowerShell:\n1. Connect to Exchange online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-ExternalInOutlook\n3. For each identity verify Enabled is set to True and the AllowList only contains\nemail addresses the organization has permitted to bypass external tagging.","Remediation":"To remediate using PowerShell:\n1. Connect to Exchange online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-ExternalInOutlook -Enabled $true","Title":"Ensure email from external senders is identified","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.2 Mail flow","DefaultValue":"Disabled (False)","Level":"L1","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"6.3\", \"title\": \"Roles\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://techcommunity.microsoft.com/t5/exchange-team-blog/native-external-\nsender-callouts-on-email-in-outlook/ba-p/2250098\n2. https://learn.microsoft.com/en-us/powershell/module/exchange/set-\nexternalinoutlook?view=exchange-ps","Rationale":"Tagging emails from external senders helps to inform end users about the origin of the\nemail. This can allow them to proceed with more caution and make informed decisions\nwhen it comes to identifying spam or phishing emails.\nMail flow rules are often used by Exchange administrators to accomplish the External\nemail tagging by appending a tag to the front of a subject line. There are limitations to\nthis outlined here. The preferred method in the CIS Benchmark is to use the native\nexperience.\nNote: Existing emails in a user's inbox from external senders are not tagged\nretroactively.","Section":"6 Exchange admin center","RecommendationId":"6.2.3"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()# Original command to get external email settings
    $externalInOutlookSettings = Get-ExternalInOutlook
    
    # Process each setting to determine compliance
    foreach ($setting in $externalInOutlookSettings) {
        $isCompliant = $true
        
        # Example compliance check logic (customize as needed)
        if ($setting.AllowedSenders -ne $null -and $setting.AllowedSenders.Count -gt 0) {
            $isCompliant = $false
        }
        
        # Add result to the results array
        $resourceResults += @{
            SettingName = $setting.Name
            IsCompliant = $isCompliant
            AllowedSenders = $setting.AllowedSenders
        }
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
