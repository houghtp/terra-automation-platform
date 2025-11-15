# Control: 5.2.2.12 - Ensure the device code sign-in flow is blocked
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.12","Level":"L1","Title":"Ensure the device code sign-in flow is blocked","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"The Microsoft identity platform supports the device authorization grant, which allows\nusers to sign in to input-constrained devices such as a smart TV, IoT device, or a\nprinter. To enable this flow, the device has the user visit a webpage in a browser on\nanother device to sign in. Once the user signs in, the device is able to get access\ntokens and refresh tokens as needed.\nThe recommended state is to Block access for Device code flow in Conditional\nAccess.","Rationale":"Since August 2024, Microsoft has observed threat actors, such as Storm-2372,\nemploying \"device code phishing\" attacks. These attacks deceive users into logging into\nproductivity applications, capturing authentication tokens to gain further access to\ncompromised accounts.\nTo mitigate this specific attack, block authentication code flows and permit only those\nfrom devices within trusted environments, identified by specific IP addresses.","Impact":"Some administrative overhead will be required for stricter management of these\ndevices. Since exclusions do not violate compliance, this feature can still be utilized\neffectively within a controlled environment.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify Resources (formerly cloud apps)\nincludes All resources (formerly 'All cloud apps')\no Under Conditions > Authentication flows verify Configure is set to\nYes and Device code flow is checked.\no Under Grant verify Block access is selected.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\no Under Users include All users.\no Under Target resources > Resources (formerly cloud apps)\ninclude All resources (formerly 'All cloud apps').\no Under Conditions > Authentication flows set Configure is set to\nYes, select Device code flow and click Save.\no Under Grant select Block access and click Select.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code\n2. https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-\nauthentication-flows\n3. https://www.microsoft.com/en-us/security/blog/2025/02/13/storm-2372-conducts-\ndevice-code-phishing-campaign/\n4. https://securing365.com/secure-your-device-code-auth-flows-now/\n5. https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-block-\nauthentication-flows#device-code-flow-policies","CISControls":"[{\"version\": \"\", \"id\": \"16.7\", \"title\": \"Use Standard Hardening Configuration Templates for\", \"description\": \"Application Infrastructure Use standard, industry-recommended hardening configuration templates for - - application infrastructure components. This includes underlying servers, databases, and web servers, and applies to cloud containers, Platform as a Service (PaaS) components, and SaaS components. Do not allow in-house developed software to weaken configuration hardening. 5.2.3 Authentication Methods\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve all Conditional Access policies
    $policies = Get-MgIdentityConditionalAccessPolicy -All

    foreach ($policy in $policies) {
        # Check if the policy is enabled
        $isEnabled = $policy.State -eq "enabled"
        
        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"
        
        # Check if the policy targets all resources (cloud apps)
        $targetsAllResources = $policy.Conditions.Applications.Include -contains "All"
        
        # Check if the policy blocks device code flow
        $blocksDeviceCodeFlow = $policy.Conditions.ClientAppTypes -contains "deviceCode"

        # Check if the policy grants block access
        $grantsBlockAccess = $policy.GrantControls.BuiltInControls -contains "Block"

        # Determine compliance
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsAllResources -and $blocksDeviceCodeFlow -and $grantsBlockAccess
        
        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsAllResources = $targetsAllResources
            BlocksDeviceCodeFlow = $blocksDeviceCodeFlow
            GrantsBlockAccess = $grantsBlockAccess
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
