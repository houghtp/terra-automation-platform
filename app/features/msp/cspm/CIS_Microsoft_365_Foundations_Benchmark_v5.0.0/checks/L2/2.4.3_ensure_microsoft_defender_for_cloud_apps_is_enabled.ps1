# Control: 2.4.3 - Ensure Microsoft Defender for Cloud Apps is enabled
<# CIS_METADATA_START
{"Description":"Microsoft Defender for Cloud Apps is a Cloud Access Security Broker (CASB). It\nprovides visibility into suspicious activity in Microsoft 365, enabling investigation into\npotential security issues and facilitating the implementation of remediation measures if\nnecessary.\nSome risk detection methods provided by Entra Identity Protection also require\nMicrosoft Defender for Cloud Apps:\n- Suspicious manipulation of inbox rules\n- Suspicious inbox forwarding\n- New country detection\n- Impossible travel detection\n- Activity from anonymous IP addresses\n- Mass access to sensitive files","Impact":"","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Click to expand System select Settings > Cloud apps.\n3. Scroll to Connected apps and select App connectors.\n4. Ensure that Microsoft 365 and Microsoft Azure both show in the list as\nConnected.\n5. Go to Cloud Discovery > Microsoft Defender for Endpoint and check if\nthe integration is enabled.\n6. Go to Information Protection > Files and verify Enable file monitoring\nis checked.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com/\n2. Click to expand System select Settings > Cloud apps.\n3. Scroll to Information Protection and select Files.\n4. Check Enable file monitoring.\n5. Scroll up to Cloud Discovery and select Microsoft Defender for\nEndpoint.\n6. Check Enforce app access, configure a Notification URL and Save.\nNote: Defender for Endpoint requires a Defender for Endpoint license.\nConfigure App Connectors:\n1. Scroll to Connected apps and select App connectors.\n2. Click on Connect an app and select Microsoft 365.\n3. Check all Azure and Office 365 boxes then click Connect Office 365.\n4. Repeat for the Microsoft Azure application.","Title":"Ensure Microsoft Defender for Cloud Apps is enabled","ProfileApplicability":"- E5 Level 2","SubSection":"2.4 System","DefaultValue":"Disabled","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"10.1\", \"title\": \"Deploy and Maintain Anti-Malware Software\", \"description\": \"v8 - - - Deploy and maintain anti-malware software on all enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"10.5\", \"title\": \"Enable Anti-Exploitation Features\", \"description\": \"Enable anti-exploitation features on enterprise assets and software, where possible, such as Microsoft\\u00ae Data Execution Prevention (DEP), Windows\\u00ae - - Defender Exploit Guard (WDEG), or Apple\\u00ae System Integrity Protection (SIP) and Gatekeeper\\u2122.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Activate audit logging\", \"description\": \"Ensure that local logging has been enabled on all systems and networking - - - devices. 16 Account Monitoring and Control Account Monitoring and Control\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-cloud-apps/protect-office-\n365#connect-microsoft-365-to-microsoft-defender-for-cloud-apps\n2. https://learn.microsoft.com/en-us/defender-cloud-apps/protect-azure#connect-\nazure-to-microsoft-defender-for-cloud-apps\n3. https://learn.microsoft.com/en-us/defender-cloud-apps/best-practices\n4. https://learn.microsoft.com/en-us/defender-cloud-apps/get-started\n5. https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-\nrisks","Rationale":"Security teams can receive notifications of triggered alerts for atypical or suspicious\nactivities, see how the organization's data in Microsoft 365 is accessed and used,\nsuspend user accounts exhibiting suspicious activity, and require users to log back in to\nMicrosoft 365 apps after an alert has been triggered.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.4.3"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Check if Microsoft Defender for Cloud Apps is enabled
    # This is a placeholder for the actual cmdlet to retrieve the settings
    # Replace with the appropriate cmdlet and properties
    $cloudAppSettings = Get-MgSecurityCloudAppSecuritySettings -All

    foreach ($setting in $cloudAppSettings) {
        $isConnected = $setting.ConnectedApps -contains "Microsoft 365" -and $setting.ConnectedApps -contains "Microsoft Azure"
        $isFileMonitoringEnabled = $setting.FileMonitoringEnabled
        $isDefenderForEndpointEnabled = $setting.DefenderForEndpointIntegrationEnabled

        $isCompliant = $isConnected -and $isFileMonitoringEnabled -and $isDefenderForEndpointEnabled

        $resourceResults += @{
            ResourceName = $setting.DisplayName
            ConnectedApps = $setting.ConnectedApps
            FileMonitoringEnabled = $isFileMonitoringEnabled
            DefenderForEndpointEnabled = $isDefenderForEndpointEnabled
            IsCompliant = $isCompliant
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
