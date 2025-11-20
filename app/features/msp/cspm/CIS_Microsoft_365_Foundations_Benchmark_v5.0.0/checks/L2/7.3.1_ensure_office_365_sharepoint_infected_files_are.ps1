# Control: 7.3.1 - Ensure Office 365 SharePoint infected files are not downloadable
<# CIS_METADATA_START
{"Description": "By default, SharePoint online allows files that Defender for Office 365 has detected as\ninfected to be downloaded.", "Impact": "The only potential impact associated with implementation of this setting is potential\ninconvenience associated with the small percentage of false positive detections that\nmay occur.", "Audit": "To audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService -Url\nhttps://tenant-admin.sharepoint.com, replacing \"tenant\" with the\nappropriate value.\n2. Run the following PowerShell command:\nGet-SPOTenant | Select-Object DisallowInfectedFileDownload\n3. Ensure the value for DisallowInfectedFileDownload is set to True.\nNote: According to Microsoft, SharePoint cannot be accessed through PowerShell by\nusers with the Global Reader role. For further information, please refer to the reference\nsection.", "Remediation": "To remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService -Url\nhttps://tenant-admin.sharepoint.com, replacing \"tenant\" with the\nappropriate value.\n2. Run the following PowerShell command to set the recommended value:\nSet-SPOTenant -DisallowInfectedFileDownload $true\nNote: The Global Reader role cannot access SharePoint using PowerShell according to\nMicrosoft. See the reference section for more information.", "Title": "Ensure Office 365 SharePoint infected files are disallowed for download", "ProfileApplicability": "- E5 Level 2", "SubSection": "7.3 Settings", "DefaultValue": "False", "Level": "L2", "CISControls": "[{\"version\": \"\", \"id\": \"10.1\", \"title\": \"Deploy and Maintain Anti-Malware Software\", \"description\": \"v8 - - - Deploy and maintain anti-malware software on all enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.10\", \"title\": \"Sandbox All Email Attachments\", \"description\": \"Use sandboxing to analyze and block inbound email attachments with - malicious behavior.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"8.1\", \"title\": \"Utilize Centrally Managed Anti-malware Software\", \"description\": \"Utilize centrally managed anti-malware software to continuously monitor and - - defend each of the organization's workstations and servers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/defender-office-365/safe-attachments-for-spo-\nodfb-teams-configure?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/defender-office-365/anti-malware-protection-\nfor-spo-odfb-teams-about?view=o365-worldwide\n3. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/permissions-reference#global-reader", "Rationale": "Defender for Office 365 for SharePoint, OneDrive, and Microsoft Teams protects your\norganization from inadvertently sharing malicious files. When an infected file is detected\nthat file is blocked so that no one can open, copy, move, or share it until further actions\nare taken by the organization's security team.", "Section": "7 SharePoint admin center", "RecommendationId": "7.3.1"}
CIS_METADATA_END #>
# Required Services: PnP PowerShell (Linux compatible)
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Use PnP PowerShell instead of SharePoint Online PowerShell (Linux compatible)
    $tenantSettings = Get-PnPTenant | Select-Object DisallowInfectedFileDownload

    # Analyze the setting and prepare the result
    $isCompliant = $tenantSettings.DisallowInfectedFileDownload -eq $true
    $resourceResults += @{
        Setting = "DisallowInfectedFileDownload"
        IsCompliant = $isCompliant
        CurrentValue = $tenantSettings.DisallowInfectedFileDownload
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
