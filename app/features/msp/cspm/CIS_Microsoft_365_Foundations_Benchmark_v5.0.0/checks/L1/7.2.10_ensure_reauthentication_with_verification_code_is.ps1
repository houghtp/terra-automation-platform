# Control: 7.2.10 - Ensure reauthentication with verification code is
<# CIS_METADATA_START
{"Description": "This setting configures if guests who use a verification code to access the site or links\nare required to reauthenticate after a set number of days.\nThe recommended state is 15 or less.", "Impact": "Guests who use Microsoft 365 in their organization can sign in using their work or\nschool account to access the site or document. After the one-time passcode for\nverification has been entered for the first time, guests will authenticate with their work or\nschool account and have a guest account created in the host's organization.\nNote: If OneDrive and SharePoint integration with Entra ID B2B is enabled as per the\nCIS Benchmark the one-time-passcode experience will be replaced. Please visit Secure\nexternal sharing in SharePoint - SharePoint in Microsoft 365 | Microsoft Learn for more\ninformation.", "Audit": "To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to and expand More external sharing settings.\n4. Ensure People who use a verification code must reauthenticate\nafter this many days is set to 15 or less.\nTo audit using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nGet-SPOTenant | fl EmailAttestationRequired,EmailAttestationReAuthDays\n3. Ensure the following values are returned:\no EmailAttestationRequired True\no EmailAttestationReAuthDays 15 or less days.", "Remediation": "To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click to expand Policies > Sharing.\n3. Scroll to and expand More external sharing settings.\n4. Set People who use a verification code must reauthenticate after\nthis many days to 15 or less.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online service using Connect-SPOService.\n2. Run the following cmdlet:\nSet-SPOTenant -EmailAttestationRequired $true -EmailAttestationReAuthDays 15", "Title": "Ensure reauthentication with verification code is restricted", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "7.2 Policies", "DefaultValue": "EmailAttestationRequired : False\nEmailAttestationReAuthDays : 30", "Level": "L1", "CISControls": "[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/sharepoint/what-s-new-in-sharing-in-targeted-\nrelease\n2. https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-\noff#change-the-organization-level-external-sharing-setting\n3. https://learn.microsoft.com/en-us/entra/external-id/one-time-passcode", "Rationale": "By increasing the frequency of times guests need to reauthenticate this ensures guest\nuser access to data is not prolonged beyond an acceptable amount of time.", "Section": "7 SharePoint admin center", "RecommendationId": "7.2.10"}
CIS_METADATA_END #>
# Required Services: SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve tenant settings
        # Get SharePoint tenant settings using PnP PowerShell
    $tenantSettings = Get-PnPTenant | Select-Object EmailAttestationRequired, EmailAttestationReAuthDays

    # Check compliance
    $isCompliant = $false
    if ($tenantSettings.EmailAttestationRequired -eq $true -and $tenantSettings.EmailAttestationReAuthDays -le 15) {
        $isCompliant = $true
    }

    # Add result to the results array
    $resourceResults += @{
        Setting = "Email Attestation"
        EmailAttestationRequired = $tenantSettings.EmailAttestationRequired
        EmailAttestationReAuthDays = $tenantSettings.EmailAttestationReAuthDays
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
