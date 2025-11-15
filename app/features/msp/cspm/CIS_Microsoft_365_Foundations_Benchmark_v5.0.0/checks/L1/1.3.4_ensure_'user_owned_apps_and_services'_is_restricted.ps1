# Control: 1.3.4 - Ensure 'User owned apps and services' is restricted
<# CIS_METADATA_START
{"Description":"By default, users can install add-ins in their Microsoft Word, Excel, and PowerPoint\napplications, allowing data access within the application.\nDo not allow users to install add-ins in Word, Excel, or PowerPoint.","Impact":"Implementation of this change will impact both end users and administrators. End users\nwill not be able to install add-ins that they may want to install.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings > Org settings.\n3. In Services select User owned apps and services.\n4. Verify Let users access the Office Store and Let users start trials\non behalf of your organization are not checked.\nTo Audit using PowerShell:\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"OrgSettings-AppsAndServices.Read.All\".\n2. Run the following Microsoft Graph PowerShell command:\n$Uri = \"https://graph.microsoft.com/beta/admin/appsAndServices/settings\"\nInvoke-MgGraphRequest -Uri $Uri\n3. Ensure both isOfficeStoreEnabled and isAppAndServicesTrialEnabled\nare False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings > Org settings.\n3. In Services select User owned apps and services.\n4. Uncheck Let users access the Office Store and Let users start\ntrials on behalf of your organization.\n5. Click Save.\nTo remediate using PowerShell\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"OrgSettings-AppsAndServices.ReadWrite.All\".\n2. Run the following Microsoft Graph PowerShell commands:\n$uri = \"https://graph.microsoft.com/beta/admin/appsAndServices\"\n$body = @{\n\"Settings\" = @{\n\"isAppAndServicesTrialEnabled\" = $false\n\"isOfficeStoreEnabled\" = $false\n}\n} | ConvertTo-Json\nInvoke-MgGraphRequest -Method PATCH -Uri $uri -Body $body","Title":"Ensure 'User owned apps and services' is restricted","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"1.3 Settings","DefaultValue":"Let users access the Office Store is Checked\nLet users start trials on behalf of your organization is Checked","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"5.1\", \"title\": \"Establish Secure Configurations\", \"description\": \"Maintain documented, standard security configuration standards for all - - - authorized operating systems and software.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/admin/manage/manage-addins-\nin-the-admin-center?view=o365-worldwide#manage-add-in-downloads-by-\nturning-onoff-the-office-store-across-all-apps-except-outlook","Rationale":"Attackers commonly use vulnerable and custom-built add-ins to access data in user\napplications.\nWhile allowing users to install add-ins by themselves does allow them to easily acquire\nuseful add-ins that integrate with Microsoft applications, it can represent a risk if not\nused and monitored carefully.\nDisable future user's ability to install add-ins in Microsoft Word, Excel, or PowerPoint\nhelps reduce your threat-surface and mitigate this risk.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.3.4"}
CIS_METADATA_END #>
# Required Services: MgGraph with OrgSettings-AppsAndServices.Read.All scope
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Define the URI for the apps and services settings
    $Uri = "https://graph.microsoft.com/beta/admin/appsAndServices/settings"

    # Invoke the request to get the apps and services settings
    $response = Invoke-MgGraphRequest -Uri $Uri

    # Process the response to check compliance
    if ($response -and $response.value) {
        foreach ($setting in $response.value) {
            # Check if the setting is disabled (False = restricted/compliant)
            $isCompliant = $setting.isEnabled -eq $false
            $resourceResults += @{
                SettingName = $setting.displayName
                IsCompliant = $isCompliant
                CurrentValue = $setting.isEnabled
                Details = "Setting: $($setting.displayName) - Enabled: $($setting.isEnabled)"
            }
        }
    } else {
        # Handle case where no settings are returned
        $resourceResults += @{
            SettingName = "User Owned Apps and Services"
            IsCompliant = $false
            CurrentValue = "No settings found"
            Details = "No apps and services settings were returned from the API"
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
