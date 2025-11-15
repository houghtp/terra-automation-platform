# Control: 5.2.2.4 - Ensure Sign-in frequency is enabled and browser
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.4","Level":"L1","Title":"Ensure Sign-in frequency is enabled and browser sessions are not persistent for Administrative users","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"In complex deployments, organizations might have a need to restrict authentication\nsessions. Conditional Access policies allow for the targeting of specific user accounts.\nSome scenarios might include:\n- Resource access from an unmanaged or shared device\n- Access to sensitive information from an external network\n- High-privileged users\n- Business-critical applications\nNote: This CA policy can be added to the previous CA policy in this benchmark \"Ensure\nmultifactor authentication is enabled for all users in administrative roles\"","Rationale":"Forcing a time out for MFA will help ensure that sessions are not kept alive for an\nindefinite period of time, ensuring that browser sessions are not persistent will help in\nprevention of drive-by attacks in web browsers, this also prevents creation and saving of\nsession cookies leaving nothing for an attacker to take.","Impact":"Users with Administrative roles will be prompted at the frequency set for MFA.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection > Conditional Access Select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify Directory roles specific to administrators are\nincluded.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected.\no Ensure that only documented resource exclusions exist and that they are\nreviewed annually.\no Under Session verify Sign-in frequency is checked and set to\nPeriodic reauthentication.\no Verify the timeframe is set to the time determined by the organization.\no Ensure Periodic reauthentication does not exceed 4 hours (or less).\no Verify Persistent browser session is set to Never persistent.\n4. Ensure Enable policy is set to On\nNote: Break-glass accounts should be excluded from all Conditional Access policies.\nNote: A list of directory roles applying to Administrators can be found in the remediation\nsection.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection > Conditional Access Select Policies.\n3. Click New policy.\no Under Users include Select users and groups and check Directory\nroles.\no At a minimum, include the directory roles listed below in this section of the\ndocument.\no Under Target resources include All resources (formerly 'All\ncloud apps').\no Under Grant select Grant Access and check Require multifactor\nauthentication.\no Under Session select Sign-in frequency select Periodic\nreauthentication and set it to 4 hours (or less).\no Check Persistent browser session then select Never persistent in\nthe drop-down menu.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\nAt minimum these directory roles should be included in the policy:\n- Application administrator\n- Authentication administrator\n- Billing administrator\n- Cloud application administrator\n- Conditional Access administrator\n- Exchange administrator\n- Global administrator\n- Global reader\n- Helpdesk administrator\n- Password administrator\n- Privileged authentication administrator\n- Privileged role administrator\n- Security administrator\n- SharePoint administrator\n- User administrator\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"The default configuration for user sign-in frequency is a rolling window of 90 days.","References":"1. https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-\nconditional-access-session-lifetime","CISControls":"[{\"version\": \"\", \"id\": \"4.3\", \"title\": \"Configure Automatic Session Locking on Enterprise\", \"description\": \"Assets Configure automatic session locking on enterprise assets after a defined period - - - of inactivity. For general purpose operating systems, the period must not exceed 15 minutes. For mobile end-user devices, the period must not exceed 2 minutes.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve all Conditional Access Policies
    $conditionalAccessPolicies = Get-MgIdentityConditionalAccessPolicy -All

    foreach ($policy in $conditionalAccessPolicies) {
        # Check if the policy is enabled
        $isPolicyEnabled = $policy.State -eq "Enabled"

        # Check if the policy includes the required directory roles
        $requiredRoles = @(
            "Application administrator", "Authentication administrator", "Billing administrator",
            "Cloud application administrator", "Conditional Access administrator", "Exchange administrator",
            "Global administrator", "Global reader", "Helpdesk administrator", "Password administrator",
            "Privileged authentication administrator", "Privileged role administrator", "Security administrator",
            "SharePoint administrator", "User administrator"
        )
        $includedRoles = $policy.Conditions.Users.IncludeRoles
        $rolesCompliant = $requiredRoles | ForEach-Object { $_ -in $includedRoles }

        # Check if all resources are targeted
        $allResourcesTargeted = $policy.Conditions.Applications.IncludeApplications -eq "All"

        # Check session controls for sign-in frequency and persistent browser session
        $sessionControls = $policy.SessionControls
        $signInFrequencyCompliant = $sessionControls.SignInFrequency -and $sessionControls.SignInFrequency.Period -le 4
        $persistentBrowserSessionCompliant = $sessionControls.PersistentBrowserSession -eq "NeverPersistent"

        # Determine compliance for this policy
        $isCompliant = $isPolicyEnabled -and $rolesCompliant -and $allResourcesTargeted -and $signInFrequencyCompliant -and $persistentBrowserSessionCompliant

        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsPolicyEnabled = $isPolicyEnabled
            RolesCompliant = $rolesCompliant
            AllResourcesTargeted = $allResourcesTargeted
            SignInFrequencyCompliant = $signInFrequencyCompliant
            PersistentBrowserSessionCompliant = $persistentBrowserSessionCompliant
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
