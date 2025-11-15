# Control: 5.1.6.3 - Ensure guest user invitations are limited to the Guest
<# CIS_METADATA_START
{"RecommendationId":"5.1.6.3","Level":"L2","Title":"Ensure guest user invitations are limited to the Guest Inviter role","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"By default, all users in the organization, including B2B collaboration guest users, can\ninvite external users to B2B collaboration. The ability to send invitations can be limited\nby turning it on or off for everyone, or by restricting invitations to certain roles.\nThe recommended state for guest invite restrictions is Only users assigned to\nspecific admin roles can invite guest users.","Rationale":"Restricting who can invite guests limits the exposure the organization might face from\nunauthorized accounts.","Impact":"This introduces an obstacle to collaboration by restricting who can invite guest users to\nthe organization. Designated Guest Inviters must be assigned, and an approval process\nestablished and clearly communicated to all users.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > External Identities select External\ncollaboration settings.\n3. Under Guest invite settings verify that Guest invite restrictions is set to\nOnly users assigned to specific admin roles can invite guest\nusers or more restrictive.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\"\n2. Run the following command:\nGet-MgPolicyAuthorizationPolicy | fl AllowInvitesFrom\n3. Ensure the value returned is adminsAndGuestInviters or more restrictive.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > External Identities select External\ncollaboration settings.\n3. Under Guest invite settings set Guest invite restrictions to Only users\nassigned to specific admin roles can invite guest users.\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.ReadWrite.Authorization\"\n2. Run the following command:\nUpdate-MgPolicyAuthorizationPolicy -AllowInvitesFrom 'adminsAndGuestInviters'\nNote: The more restrictive position of the value will also pass audit, it is however not\nrequired.","DefaultValue":"#NAME?","References":"1. https://learn.microsoft.com/en-us/entra/external-id/external-collaboration-settings-\nconfigure\n2. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/permissions-reference#guest-inviter","CISControls":"[{\"version\": \"\", \"id\": \"6.1\", \"title\": \"Establish an Access Granting Process\", \"description\": \"Establish and follow a process, preferably automated, for granting access to - - - enterprise assets upon new hire, rights grant, or role change of a user.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider. 5.1.7 User experiences This section is intentionally blank and exists to ensure the structure of the benchmark is consistent. 5.1.8 Hybrid management\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the authorization policy
    $authPolicy = Get-MgBetaPolicyAuthorizationPolicy
    
    # Check the AllowInvitesFrom property
    foreach ($policy in $authPolicy) {
        $isCompliant = $policy.AllowInvitesFrom -eq 'Guest'
        
        # Add the result to the results array
        $resourceResults += [PSCustomObject]@{
            PolicyId = $policy.Id
            AllowInvitesFrom = $policy.AllowInvitesFrom
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
