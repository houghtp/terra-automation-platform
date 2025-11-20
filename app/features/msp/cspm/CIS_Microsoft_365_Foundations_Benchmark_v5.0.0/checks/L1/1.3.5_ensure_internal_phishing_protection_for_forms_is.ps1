# Control: 1.3.5 - Ensure internal phishing protection for Forms is enabled
<# CIS_METADATA_START
{"Description": "Microsoft Forms can be used for phishing attacks by asking personal or sensitive\ninformation and collecting the results. Microsoft 365 has built-in protection that will\nproactively scan for phishing attempt in forms such personal information request.", "Impact": "If potential phishing was detected, the form will be temporarily blocked and cannot be\ndistributed, and response collection will not happen until it is unblocked by the\nadministrator or keywords were removed by the creator.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings then select Org settings.\n3. Under Services select Microsoft Forms.\n4. Ensure the checkbox labeled Add internal phishing protection is checked\nunder Phishing protection.\nTo Audit using PowerShell:\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"OrgSettings-Forms.Read.All\".\n2. Run the following Microsoft Graph PowerShell commands:\n$uri = 'https://graph.microsoft.com/beta/admin/forms/settings'\nInvoke-MgGraphRequest -Uri $uri | select isInOrgFormsPhishingScanEnabled\n3. Ensure isInOrgFormsPhishingScanEnabled is 'True'.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings then select Org settings.\n3. Under Services select Microsoft Forms.\n4. Click the checkbox labeled Add internal phishing protection under\nPhishing protection.\n5. Click Save.\nTo remediate using PowerShell\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"OrgSettings-AppsAndServices.ReadWrite.All\".\n2. Run the following Microsoft Graph PowerShell commands:\n$uri = 'https://graph.microsoft.com/beta/admin/forms/settings'\n$body = @{ \"isInOrgFormsPhishingScanEnabled\" = $true } | ConvertTo-Json\nInvoke-MgGraphRequest -Method PATCH -Uri $uri -Body $body", "Title": "Ensure internal phishing protection for Forms is enabled", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "1.3 Settings", "DefaultValue": "Internal Phishing Protection is enabled.", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"10.1\", \"title\": \"Deploy and Maintain Anti-Malware Software\", \"description\": \"v8 - - - Deploy and maintain anti-malware software on all enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.2\", \"title\": \"Train Workforce Members to Recognize Social\", \"description\": \"v8 Engineering Attacks - - - Train workforce members to recognize social engineering attacks, such as phishing, pre-texting, and tailgating.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-US/microsoft-forms/administrator-settings-\nmicrosoft-forms\n2. https://learn.microsoft.com/en-US/microsoft-forms/review-unblock-forms-users-\ndetected-blocked-potential-phishing", "Rationale": "Enabling internal phishing protection for Microsoft Forms will prevent attackers using\nforms for phishing attacks by asking personal or other sensitive information and URLs.", "Section": "1 Microsoft 365 admin center", "RecommendationId": "1.3.5"}
CIS_METADATA_END #>
# Required Services: MgGraph with OrgSettings-Forms.Read.All scope
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Define the URI for Forms settings
    $uri = 'https://graph.microsoft.com/beta/admin/forms/settings'

    # Invoke the request to get Forms settings
    $response = Invoke-MgGraphRequest -Uri $uri

    # Check the isInOrgFormsPhishingScanEnabled setting
    if ($response) {
        $isCompliant = $response.isInOrgFormsPhishingScanEnabled -eq $true
        $resourceResults += @{
            Name = "Forms Internal Phishing Protection"
            IsCompliant = $isCompliant
            CurrentValue = $response.isInOrgFormsPhishingScanEnabled
            Details = "isInOrgFormsPhishingScanEnabled: $($response.isInOrgFormsPhishingScanEnabled)"
        }
    } else {
        # Handle case where no response is returned
        $resourceResults += @{
            Name = "Forms Internal Phishing Protection"
            IsCompliant = $false
            CurrentValue = "No response"
            Details = "No Forms settings were returned from the API"
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
