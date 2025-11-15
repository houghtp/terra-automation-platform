# Control: 2.1.2 - Ensure the Common Attachment Types Filter is
<# CIS_METADATA_START
{"Description":"The Common Attachment Types Filter lets a user block known and custom malicious\nfile types from being attached to emails.","Impact":"Blocking common malicious file types should not cause an impact in modern computing\nenvironments.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules.\n3. On the Policies & rules page select Threat policies.\n4. Under Policies select Anti-malware and click on the Default (Default)\npolicy.\n5. On the policy page that appears on the righthand pane, under Protection\nsettings, verify that the Enable the common attachments filter has the\nvalue of On.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following Exchange Online PowerShell command:\nGet-MalwareFilterPolicy -Identity Default | Select-Object EnableFileFilter\n3. Verify EnableFileFilter is set to True.\nNote: Audit and Remediation guidance may focus on the Default policy however, if a\nCustom Policy exists in the organization's tenant, then ensure the setting is set as\noutlined in the highest priority policy listed.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com.\n2. Click to expand Email & collaboration select Policies & rules.\n3. On the Policies & rules page select Threat policies.\n4. Under polices select Anti-malware and click on the Default (Default) policy.\n5. On the Policy page that appears on the right hand pane scroll to the bottom and\nclick on Edit protection settings, check the Enable the common\nattachments filter.\n6. Click Save.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following Exchange Online PowerShell command:\nSet-MalwareFilterPolicy -Identity Default -EnableFileFilter $true\nNote: Audit and Remediation guidance may focus on the Default policy however, if a\nCustom Policy exists in the organization's tenant, then ensure the setting is set as\noutlined in the highest priority policy listed.","Title":"Ensure the Common Attachment Types Filter is","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"2.1 Email & collaboration","DefaultValue":"Always on","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"9.6\", \"title\": \"Block Unnecessary File Types\", \"description\": \"Block unnecessary file types attempting to enter the enterprise's email - - gateway.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"7.9\", \"title\": \"Block Unnecessary File Types\", \"description\": \"Block all e-mail attachments entering the organization's e-mail gateway if the - - file types are unnecessary for the organization's business.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"8.1\", \"title\": \"Utilize Centrally Managed Anti-malware Software\", \"description\": \"Utilize centrally managed anti-malware software to continuously monitor and - - defend each of the organization's workstations and servers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/exchange/get-\nmalwarefilterpolicy?view=exchange-ps\n2. https://learn.microsoft.com/en-us/defender-office-365/anti-malware-policies-\nconfigure?view=o365-worldwide","Rationale":"Blocking known malicious file types can help prevent malware-infested files from\ninfecting a host.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.2"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the command to get the malware filter policy
    $malwareFilterPolicy = Get-MalwareFilterPolicy -Identity Default | Select-Object EnableFileFilter
    
    # Check if the EnableFileFilter is enabled
    $isCompliant = $malwareFilterPolicy.EnableFileFilter -eq $true
    
    # Add the result to the results array
    $resourceResults += @{
        PolicyName = 'Default'
        EnableFileFilter = $malwareFilterPolicy.EnableFileFilter
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
