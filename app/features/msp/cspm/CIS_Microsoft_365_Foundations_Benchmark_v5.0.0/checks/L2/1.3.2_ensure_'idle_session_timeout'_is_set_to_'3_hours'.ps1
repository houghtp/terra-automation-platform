# Control: 1.3.2 - Ensure 'Idle session timeout' is set to '3 hours (or less)'
<# CIS_METADATA_START
{"Description":"Idle session timeout allows the configuration of a setting which will timeout inactive\nusers after a pre-determined amount of time. When a user reaches the set idle timeout\nsession, they'll get a notification that they're about to be signed out. They must choose\nto stay signed in or they'll be automatically signed out of all Microsoft 365 web apps.\nCombined with a Conditional Access rule this will only impact unmanaged devices.\nA managed device is considered a device managed by Intune MDM or joined to a\ndomain (Entra ID or Hybrid joined).\nThe following Microsoft 365 web apps are supported.\n- Outlook Web App\n- OneDrive\n- SharePoint\n- Microsoft Fabric\n- Microsoft365.com and other start pages\n- Microsoft 365 web apps (Word, Excel, PowerPoint)\n- Microsoft 365 Admin Center\n- M365 Defender Portal\n- Microsoft Purview Compliance Portal\nThe recommended setting is 3 hours (or less) for unmanaged devices.\nNote: Idle session timeout doesn't affect Microsoft 365 desktop and mobile apps.","Impact":"If step 2 in the Audit/Remediation procedure is left out, then there is no issue with this\nfrom a security standpoint. However, it will require users on trusted devices to sign in\nmore frequently which could result in credential prompt fatigue.\nUsers don't get signed out in these cases:\n- If they get single sign-on (SSO) into the web app from the device joined account.\n- If they selected Stay signed in at the time of sign-in. For more info on hiding this\noption for your organization, see Add branding to your organization's sign-in\npage.\n- If they're on a managed device, that is compliant or joined to a domain and using\na supported browser, like Microsoft Edge, or Google Chrome with the Microsoft\nSingle Sign On extension.\nNote: Idle session timeout also affects the Azure Portal idle timeout if this is not\nexplicitly set to a different timeout. The Azure Portal idle timeout applies to all kind of\ndevices, not just unmanaged. See : change the directory timeout setting admin","Audit":"Step 1 - Ensure Idle session timeout is configured:\n1. Navigate to the Microsoft 365 admin center https://admin.microsoft.com/.\n2. Click to expand Settings Select Org settings.\n3. Click Security & Privacy tab.\n4. Select Idle session timeout.\n5. Verify Turn on to set the period of inactivity for users to be\nsigned off of Microsoft 365 web apps is set to 3 hours (or less).\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\":\n2. Run the following script:\n$TimeoutPolicy = Get-MgPolicyActivityBasedTimeoutPolicy\n$BenchmarkTimeSpan = [TimeSpan]::Parse('03:00:00') # 3 hours\nif ($TimeoutPolicy) {\n$PolicyDefinition = $TimeoutPolicy.Definition | ConvertFrom-Json\n$Timeout =\n$PolicyDefinition.ActivityBasedTimeoutPolicy.ApplicationPolicies[0].WebSessio\nnIdleTimeout\n$TimeSpan = [TimeSpan]::Parse($Timeout)\n$TimeoutReadable = \"{0} days, {1} hours, {2} minutes\" `\n-f $TimeSpan.Days, $TimeSpan.Hours, $TimeSpan.Minutes\nif ($TimeSpan -le $BenchmarkTimeSpan) {\nWrite-Host \"** PASS ** Timeout is set to $TimeoutReadable.\"\n} else {\nWrite-Host \"** FAIL ** Timeout is too long. It is set to\n$TimeoutReadable.\"\n}\n} else {\nWrite-Host \"** FAIL **: Idle session timeout is not configured.\"\n}\n3. Verify the policy exists and is 3 hours or less.\nStep 2 - Ensure the Conditional Access policy is in place:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Expand Protect > Conditional Access.\n3. Inspect existing conditional access rules for one that meets the below conditions:\no Users is set to All users.\no Cloud apps or actions > Select apps is set to Office 365.\no Conditions > Client apps is Browser and nothing else.\no Session is set to Use app enforced restrictions.\no Enable Policy is set to On\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\":\n2. Run the following script:\n$Caps = Get-MgIdentityConditionalAccessPolicy -All |\nWhere-Object {\n$_.SessionControls.ApplicationEnforcedRestrictions.IsEnabled }\n$CapReport = [System.Collections.Generic.List[Object]]::new()\n# Filter to policies with \"Use app enforced restrictions\" enabled\n# Loop through policies and generate a per policy report.\nforeach ($policy in $Caps) {\n$Name = $policy.DisplayName\n$Users = $policy.Conditions.Users.IncludeUsers\n$Targets = $policy.Conditions.Applications.IncludeApplications\n$ClientApps = $policy.Conditions.ClientAppTypes\n$Restrictions =\n$policy.SessionControls.ApplicationEnforcedRestrictions.IsEnabled\n$State = $policy.State\n$CountPass = $policy.Targets.count -eq 1 -and $ClientApps.count -eq 1\n$Pass = $Targets -eq 'Office365' -and $ClientApps -eq 'browser' -and\n$Restrictions -and $CountPass -and $State -eq 'enabled'\n$obj = [PSCustomObject]@{\nDisplayName = $Name\nAuditState = if ($Pass) { \"PASS\" } else { \"FAIL\" }\nIncludeUsers = $Users\nIncludeApplications = $Targets\nClientAppTypes = $ClientApps\nAppEnforcedRestrictions = $Restrictions\nState = $State\n}\n$CapReport.Add($obj)\n}\nif ($Caps) {\n$CapReport\n} else {\nWrite-Host \"** FAIL **: There are no qualifying conditional access\npolicies.\"\n}\n3. The script will output qualifying Conditional Access Policies. If one policy passes,\nthen the recommendation passes. A passing policy will have the following\nproperties:\nDisplayName : (CIS) Idle timeout for unmanaged\nAuditState : PASS\nIncludeUsers : {All} # IncludeUsers not currently scored\nIncludeApplications : {Office365}\nClientAppTypes : {browser}\nAppEnforcedRestrictions : True\nState : enabled\nNote: Both steps 1 and 2 must pass audit checks in order for the recommendation to\npass as a whole.","Remediation":"Step 1 - Configure Idle session timeout:\n1. Navigate to the Microsoft 365 admin center https://admin.microsoft.com/.\n2. Click to expand Settings Select Org settings.\n3. Click Security & Privacy tab.\n4. Select Idle session timeout.\n5. Check the box Turn on to set the period of inactivity for users to\nbe signed off of Microsoft 365 web apps\n6. Set a maximum value of 3 hours.\n7. Click save.\nStep 2 - Ensure the Conditional Access policy is in place:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Expand Protect > Conditional Access.\n3. Click New policy and give the policy a name.\no Select Users > All users.\no Select Cloud apps or actions > Select apps and select Office 365\no Select Conditions > Client apps > Yes check only Browser unchecking\nall other boxes.\no Select Sessions and check Use app enforced restrictions.\n4. Set Enable policy to On and click Create.\nNote: To ensure that idle timeouts affect only unmanaged devices, both steps 1 and 2\nmust be completed. Otherwise managed devices will also be impacted by the timeout\npolicy.","Title":"Ensure 'Idle session timeout' is set to '3 hours (or less)'","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"1.3 Settings","DefaultValue":"Not configured. (Idle sessions will not timeout.)","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"4.3\", \"title\": \"Configure Automatic Session Locking on Enterprise\", \"description\": \"Assets Configure automatic session locking on enterprise assets after a defined period - - - of inactivity. For general purpose operating systems, the period must not exceed 15 minutes. For mobile end-user devices, the period must not exceed 2 minutes.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/admin/manage/idle-session-\ntimeout-web-apps?view=o365-worldwide","Rationale":"Ending idle sessions through an automatic process can help protect sensitive company\ndata and will add another layer of security for end users who work on unmanaged\ndevices that can potentially be accessed by the public. Unauthorized individuals onsite\nor remotely can take advantage of systems left unattended over time. Automatic timing\nout of sessions makes this more difficult.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.3.2"}
CIS_METADATA_END #>
# Required Services: SharePoint, MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Check for Activity Based Timeout Policy
    $TimeoutPolicy = Get-MgPolicyActivityBasedTimeoutPolicy
    $BenchmarkTimeSpan = [TimeSpan]::Parse('03:00:00') # 3 hours

    if ($TimeoutPolicy) {
        $PolicyDefinition = $TimeoutPolicy.Definition | ConvertFrom-Json
        $Timeout = $PolicyDefinition.ActivityBasedTimeoutPolicy.ApplicationPolicies[0].WebSessionIdleTimeout
        $TimeSpan = [TimeSpan]::Parse($Timeout)
        $TimeoutReadable = "{0} days, {1} hours, {2} minutes" -f $TimeSpan.Days, $TimeSpan.Hours, $TimeSpan.Minutes

        $isCompliant = $TimeSpan -le $BenchmarkTimeSpan
        $resourceResults += [PSCustomObject]@{
            PolicyName = "Activity Based Timeout Policy"
            IsCompliant = $isCompliant
            Details = "Timeout is set to $TimeoutReadable."
        }
    } else {
        $resourceResults += [PSCustomObject]@{
            PolicyName = "Activity Based Timeout Policy"
            IsCompliant = $false
            Details = "Idle session timeout is not configured."
        }
    }

    # Check for Conditional Access Policies
    $Caps = Get-MgIdentityConditionalAccessPolicy -All | Where-Object { $_.SessionControls.ApplicationEnforcedRestrictions.IsEnabled }
    
    if ($Caps) {
        foreach ($policy in $Caps) {
            $Name = $policy.DisplayName
            $Targets = $policy.Conditions.Applications.IncludeApplications
            $ClientApps = $policy.Conditions.ClientAppTypes
            $Restrictions = $policy.SessionControls.ApplicationEnforcedRestrictions.IsEnabled
            $State = $policy.State
            $CountPass = $policy.Targets.count -eq 1 -and $ClientApps.count -eq 1
            $Pass = $Targets -eq 'Office365' -and $ClientApps -eq 'browser' -and $Restrictions -and $CountPass -and $State -eq 'enabled'

            $resourceResults += [PSCustomObject]@{
                PolicyName = $Name
                IsCompliant = $Pass
                Details = if ($Pass) { "Policy is compliant." } else { "Policy is not compliant." }
            }
        }
    } else {
        $resourceResults += [PSCustomObject]@{
            PolicyName = "Conditional Access Policies"
            IsCompliant = $false
            Details = "There are no qualifying conditional access policies."
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
