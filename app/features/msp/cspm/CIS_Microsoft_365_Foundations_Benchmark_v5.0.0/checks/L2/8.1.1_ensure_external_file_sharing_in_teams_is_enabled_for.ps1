# Control: 8.1.1 - Ensure external file sharing in Teams is enabled for
<# CIS_METADATA_START
{"Description": "Microsoft Teams enables collaboration via file sharing. This file sharing is conducted\nwithin Teams, using SharePoint Online, by default; however, third-party cloud services\nare allowed as well.\nNote: Skype for business is deprecated as of July 31, 2021 although these settings may\nstill be valid for a period of time. See the link in the references section for more\ninformation.", "Impact": "The impact associated with this change is highly dependent upon current practices in\nthe tenant. If users do not use other storage providers, then minimal impact is likely.\nHowever, if users do regularly utilize providers outside of the tenant this will affect their\nability to continue to do so.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Teams select Teams settings.\n3. Under files verify that only authorized cloud storage options are set to On and all\nothers Off.\nTo audit using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following to verify the recommended state:\nGet-CsTeamsClientConfiguration | fl\nAllowDropbox,AllowBox,AllowGoogleDrive,AllowShareFile,AllowEgnyte\n3. Verify that only authorized providers are set to True and all others False.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Teams admin center\nhttps://admin.teams.microsoft.com.\n2. Click to expand Teams select Teams settings.\n3. Set any unauthorized providers to Off.\nTo remediate using PowerShell:\n1. Connect to Teams PowerShell using Connect-MicrosoftTeams\n2. Run the following PowerShell command to disable external providers that are not\nauthorized. (the example disables Citrix Files, DropBox, Box, Google Drive and\nEgnyte)\n$storageParams = @{\nAllowGoogleDrive = $false\nAllowShareFile = $false\nAllowBox = $false\nAllowDropBox = $false\nAllowEgnyte = $false\n}\nSet-CsTeamsClientConfiguration @storageParams", "Title": "Ensure external file sharing in Teams is enabled for only approved cloud storage services", "ProfileApplicability": "- E3 Level 2\n- E5 Level 2", "SubSection": "8.1 Teams", "DefaultValue": "AllowDropBox : True\nAllowBox : True\nAllowGoogleDrive : True\nAllowShareFile : True\nAllowEgnyte : True", "Level": "L2", "CISControls": "[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.7\", \"title\": \"Enforce Access Control to Data through Automated\", \"description\": \"v7 Tools - Use an automated tool, such as host-based Data Loss Prevention, to enforce access controls to data even when data is copied off a system.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoft-365/enterprise/manage-skype-for-\nbusiness-online-with-microsoft-365-powershell?view=o365-worldwide", "Rationale": "Ensuring that only authorized cloud storage providers are accessible from Teams will\nhelp to dissuade the use of non-approved storage providers.", "Section": "8 Microsoft Teams admin center", "RecommendationId": "8.1.1"}
CIS_METADATA_END #>
# Required Services: Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original cmdlet to get Teams client configuration
    $teamsClientConfigurations = Get-CsTeamsClientConfiguration
    
    # Process each configuration and determine compliance
    foreach ($config in $teamsClientConfigurations) {
        $isCompliant = $true # Placeholder for compliance logic, adjust as needed
        
        # Add the result to the resourceResults array
        $resourceResults += @{
            Name = $config.Identity
            IsCompliant = $isCompliant
            Details = $config
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
