# Control: 5.2.2.10 - Ensure a managed device is required to register
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.10","Level":"L1","Title":"Ensure a managed device is required to register security information","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Conditional Access (CA) can be configured to enforce access based on the device's\ncompliance status or whether it is Entra hybrid joined. Collectively this allows CA to\nclassify devices as managed or not, providing more granular control over whether or not\na user can register MFA on a device.\nWhen using Require device to be marked as compliant, the device must pass\nchecks configured in Compliance policies defined within Intune (Endpoint Manager).\nBefore these checks can be applied, the device must first be enrolled in Intune MDM.\nBy selecting Require Microsoft Entra hybrid joined device this means the\ndevice must first be synchronized from an on-premises Active Directory to qualify for\nauthentication.\nWhen configured to the recommended state below only one condition needs to be met\nfor the user to register MFA from the device. This functions as an \"OR\" operator.\nThe recommended state is to restrict Register security information to a device\nthat is marked as compliant or Entra hybrid joined.","Rationale":"Requiring registration on a managed device significantly reduces the risk of bad actors\nusing stolen credentials to register security information. Accounts that are created but\nnever registered with an MFA method are particularly vulnerable to this type of attack.\nEnforcing this requirement will both reduce the attack surface for fake registrations and\nensure that legitimate users register using trusted devices which typically have\nadditional security measures in place already.","Impact":"The organization will be required to have a mature device management process. New\ndevices provided to users will need to be pre-enrolled in Intune, auto-enrolled or be\nEntra hybrid joined. Otherwise, the user will be unable to complete registration,\nrequiring additional resources from I.T. This could be more disruptive in remote worker\nenvironments where the MDM maturity is low.\nIn these cases where the person enrolling in MFA (enrollee) doesn't have physical\naccess to a managed device, a help desk process can be created using a Teams\nmeeting to complete enrollment using: 1) a durable process to verify the enrollee's\nidentity including government identification with a photograph held up to the camera,\ninformation only the enrollee should know, and verification by the enrollee's direct\nmanager in the same meeting; 2) complete enrollment in the same Teams meeting with\nthe enrollee being granted screen and keyboard access to the help desk person's\nInPrivate Edge browser session.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify User actions is selected with\nRegister security information checked.\no Under Grant verify that only Require device to be marked as\ncompliant and Require Microsoft Entra hybrid joined device\nare checked.\no Under Grant verify Require one of the selected controls is\nselected.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\no Under Users include All users.\no Under Target resources select User actions and check Register\nsecurity information.\no Under Grant select Grant access.\no Check only Require multifactor authentication and Require\nMicrosoft Entra hybrid joined device.\no Choose Require one of the selected controls and click Select at\nthe bottom.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-\nconditional-access-grant#require-device-to-be-marked-as-compliant\n2. https://learn.microsoft.com/en-us/entra/identity/devices/concept-hybrid-join\n3. https://learn.microsoft.com/en-us/mem/intune/fundamentals/deployment-guide-\nenrollment\n4. https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-\nconditional-access-cloud-apps#user-actions","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Conditional Access Policies
    $caPolicies = Get-MgIdentityConditionalAccessPolicy -All

    foreach ($policy in $caPolicies) {
        # Check if the policy is enabled
        $isEnabled = $policy.State -eq "Enabled"
        
        # Check if the policy includes all users
        $includesAllUsers = $policy.Conditions.Users.Include -contains "All"

        # Check if the policy targets 'Register security information'
        $targetsRegisterSecurityInfo = $policy.Conditions.Applications.Include -contains "RegisterSecurityInformation"

        # Check if the policy requires device compliance or hybrid join
        $requiresDeviceCompliance = $policy.GrantControls.BuiltInControls -contains "RequireDeviceCompliance"
        $requiresHybridJoin = $policy.GrantControls.BuiltInControls -contains "RequireHybridJoin"

        # Check if the policy requires one of the selected controls
        $requiresOneControl = $policy.GrantControls.Operator -eq "OR"

        # Determine compliance
        $isCompliant = $isEnabled -and $includesAllUsers -and $targetsRegisterSecurityInfo -and 
                       ($requiresDeviceCompliance -or $requiresHybridJoin) -and $requiresOneControl

        # Add results to the array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
            IsEnabled = $isEnabled
            IncludesAllUsers = $includesAllUsers
            TargetsRegisterSecurityInfo = $targetsRegisterSecurityInfo
            RequiresDeviceCompliance = $requiresDeviceCompliance
            RequiresHybridJoin = $requiresHybridJoin
            RequiresOneControl = $requiresOneControl
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
