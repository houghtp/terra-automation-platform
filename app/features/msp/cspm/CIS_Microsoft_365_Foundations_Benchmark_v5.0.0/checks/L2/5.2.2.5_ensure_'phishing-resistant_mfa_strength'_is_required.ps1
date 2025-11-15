# Control: 5.2.2.5 - Ensure 'Phishing-resistant MFA strength' is required
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.5","Level":"L2","Title":"Ensure 'Phishing-resistant MFA strength' is required for Administrators","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"Authentication strength is a Conditional Access control that allows administrators to\nspecify which combination of authentication methods can be used to access a resource.\nFor example, they can make only phishing-resistant authentication methods available to\naccess a sensitive resource. But to access a non-sensitive resource, they can allow less\nsecure multifactor authentication (MFA) combinations, such as password + SMS.\nMicrosoft has 3 built-in authentication strengths. MFA strength, Passwordless MFA\nstrength, and Phishing-resistant MFA strength. Ensure administrator roles are using a\nCA policy with Phishing-resistant MFA strength.\nAdministrators can then enroll using one of 3 methods:\n- FIDO2 Security Key\n- Windows Hello for Business\n- Certificate-based authentication (Multi-Factor)\nNote: Additional steps to configure methods such as FIDO2 keys are not covered here\nbut can be found in related MS articles in the references section. The Conditional\nAccess policy only ensures 1 of the 3 methods is used.\nWarning: Administrators should be pre-registered for a strong authentication\nmechanism before this Conditional Access Policy is enforced. Additionally, as stated\nelsewhere in the CIS Benchmark a break-glass administrator account should be\nexcluded from this policy to ensure unfettered access in the case of an emergency.","Rationale":"Sophisticated attacks targeting MFA are more prevalent as the use of it becomes more\nwidespread. These 3 methods are considered phishing-resistant as they remove\npasswords from the login workflow. It also ensures that public/private key exchange can\nonly happen between the devices and a registered provider which prevents login to fake\nor phishing websites.","Impact":"If administrators aren't pre-registered for a strong authentication method prior to a\nconditional access policy being created, then a condition could occur where a user can't\nregister for strong authentication because they don't meet the conditional access policy\nrequirements and therefore are prevented from signing in.\nAdditionally, Internet Explorer based credential prompts in PowerShell do not support\nprompting for a security key. Implementing phishing-resistant MFA with a security key\nmay prevent admins from running their existing sets of PowerShell scripts. Device\nAuthorization Grant Flow can be used as a workaround in some instances.","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify Directory roles specific to administrators are\nincluded.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Directory Roles should include at minimum the roles listed in the\nremediation section.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected with no exclusions.\no Under Grant verify Grant Access is selected and Require\nauthentication strength is checked with Phishing-resistant MFA\nset as the value.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Click New policy.\no Under Users include Select users and groups and check Directory\nroles.\no At a minimum, include the directory roles listed below in this section of the\ndocument.\no Under Target resources include All resources (formerly 'All\ncloud apps') and do not create any exclusions.\no Under Grant select Grant Access and check Require authentication\nstrength and set Phishing-resistant MFA in the dropdown box.\no Click Select.\n4. Under Enable policy set it to Report-only until the organization is ready to\nenable it.\n5. Click Create.\nAt minimum these directory roles should be included for the policy:\n- Application administrator\n- Authentication administrator\n- Billing administrator\n- Cloud application administrator\n- Conditional Access administrator\n- Exchange administrator\n- Global administrator\n- Global reader\n- Helpdesk administrator\n- Password administrator\n- Privileged authentication administrator\n- Privileged role administrator\n- Security administrator\n- SharePoint administrator\n- User administrator\nWarning: Ensure administrators are pre-registered with strong authentication before\nenforcing the policy. After which the policy must be set to On.","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-\nauthentication-passwordless#fido2-security-keys\n2. https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-enable-\npasskey-fido2\n3. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-\nauthentication-strengths\n4. https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-\nconfigure-mfa-policy","CISControls":"[{\"version\": \"\", \"id\": \"6.5\", \"title\": \"Require MFA for Administrative Access\", \"description\": \"Require MFA for all administrative access accounts, where supported, on all - - - enterprise assets, whether managed on-site or through a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve Conditional Access Policies
    $caPolicies = Get-MgIdentityConditionalAccessPolicy -All

    # Define required directory roles
    $requiredRoles = @(
        "Application administrator",
        "Authentication administrator",
        "Billing administrator",
        "Cloud application administrator",
        "Conditional Access administrator",
        "Exchange administrator",
        "Global administrator",
        "Global reader",
        "Helpdesk administrator",
        "Password administrator",
        "Privileged authentication administrator",
        "Privileged role administrator",
        "Security administrator",
        "SharePoint administrator",
        "User administrator"
    )

    # Check each policy for compliance
    foreach ($policy in $caPolicies) {
        $isCompliant = $false

        # Check if policy is enabled
        if ($policy.State -eq "Enabled") {
            # Check if policy includes required roles
            $includedRoles = $policy.Conditions.Users.IncludeRoles
            $rolesCompliant = $requiredRoles | ForEach-Object { $_ -in $includedRoles }

            # Check if policy targets all resources
            $targetsAllResources = $policy.Conditions.Applications.IncludeApplications -contains "All"

            # Check if policy requires Phishing-resistant MFA
            $grantControls = $policy.GrantControls.BuiltInControls
            $requiresPhishingResistantMFA = $grantControls -contains "RequireAuthenticationStrength:PhishingResistantMFA"

            # Determine compliance
            $isCompliant = $rolesCompliant -and $targetsAllResources -and $requiresPhishingResistantMFA
        }

        # Add result to array
        $resourceResults += @{
            PolicyName = $policy.DisplayName
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
