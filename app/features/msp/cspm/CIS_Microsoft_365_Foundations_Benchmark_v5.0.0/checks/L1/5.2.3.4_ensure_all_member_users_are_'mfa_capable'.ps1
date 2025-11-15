# Control: 5.2.3.4 - Ensure all member users are 'MFA capable'
<# CIS_METADATA_START
{"RecommendationId":"5.2.3.4","Level":"L1","Title":"Ensure all member users are 'MFA capable'","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Microsoft defines Multifactor authentication capable as being registered and enabled for\na strong authentication method. The method must also be allowed by the authentication\nmethods policy.\nEnsure all member users are MFA capable.","Rationale":"Multifactor authentication requires an individual to present a minimum of two separate\nforms of authentication before access is granted.\nUsers who are not MFA Capable have never registered a strong authentication method\nfor multifactor authentication that is within policy and may not be using MFA. This could\nbe a result of having never signed in, exclusion from a Conditional Access (CA) policy\nrequiring MFA, or a CA policy does not exist. Reviewing this list of users will help\nidentify possible lapses in policy or procedure.","Impact":"When using the UI audit method guest users will appear in the report and unless the\norganization is applying MFA rules to guests then they will need to be manually filtered.\nAccounts that provide on-premises directory synchronization also appear in these\nreports.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select User registration details.\n4. Set the filter option Multifactor authentication capable to Not Capable.\n5. Review the non-guest users in this list.\n6. Excluding any exceptions users found in this report may require remediation.\nTo audit using PowerShell:\n1. Connect to Graph using Connect-MgGraph -Scopes\n\"UserAuthenticationMethod.Read.All,AuditLog.Read.All\"\n2. Run the following:\nGet-MgReportAuthenticationMethodUserRegistrationDetail `\n-Filter \"IsMfaCapable eq false and UserType eq 'Member'\" |\nft UserPrincipalName,IsMfaCapable,IsAdmin\n3. Ensure IsMfaCapable is set to True.\n4. Excluding any exceptions users found in this report may require remediation.\nNote: The CA rule must be in place for a successful deployment of Multifactor\nAuthentication. This policy is outlined in the conditional access section 5.2.2\nNote 2: Possible exceptions include on-premises synchronization accounts.","Remediation":"Remediation steps will depend on the status of the personnel in question or\nconfiguration of Conditional Access policies and will not be covered in detail.\nAdministrators should review each user identified on a case-by-case basis using the\nconditions below.\nUser has never signed on:\n- Employment status should be reviewed, and appropriate action taken on the user\naccount's roles, licensing and enablement.\nConditional Access policy applicability:\n- Ensure a CA policy is in place requiring all users to use MFA.\n- Ensure the user is not excluded from the CA MFA policy.\n- Ensure the policy's state is set to On.\n- Use What if to determine applicable CA policies. (Protection > Conditional\nAccess > Policies)\n- Review the user account in Sign-in logs. Under the Activity Details pane\nclick the Conditional Access tab to view applied policies.\nNote: Conditional Access is covered step by step in section 5.2.2","DefaultValue":"","References":"1. https://learn.microsoft.com/en-\nus/powershell/module/microsoft.graph.reports/update-\nmgreportauthenticationmethoduserregistrationdetail?view=graph-powershell-\n1.0#-ismfacapable\n2. https://learn.microsoft.com/en-us/entra/identity/monitoring-health/how-to-view-\napplied-conditional-access-policies\n3. https://learn.microsoft.com/en-us/entra/identity/conditional-access/what-if-tool\n4. https://learn.microsoft.com/en-us/entra/identity/authentication/howto-\nauthentication-methods-activity","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    $users = Get-MgBetaReportAuthenticationMethodUserRegistrationDetail `
        -Filter "IsMfaCapable eq false and UserType eq 'Member'"
    
    foreach ($user in $users) {
        $isCompliant = $user.IsMfaCapable -eq $true
        $resourceResults += @{
            UserPrincipalName = $user.UserPrincipalName
            IsMfaCapable = $user.IsMfaCapable
            IsAdmin = $user.IsAdmin
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
