# Control: 5.1.6.2 - Ensure that guest user access is restricted
<# CIS_METADATA_START
{"RecommendationId":"5.1.6.2","Level":"L1","Title":"Ensure that guest user access is restricted","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Microsoft Entra ID, part of Microsoft Entra, allows you to restrict what external guest\nusers can see in their organization in Microsoft Entra ID. Guest users are set to a limited\npermission level by default in Microsoft Entra ID, while the default for member users is\nthe full set of user permissions.\nThese directory level permissions are enforced across Microsoft Entra services\nincluding Microsoft Graph, PowerShell v2, the Azure portal, and My Apps portal.\nMicrosoft 365 services leveraging Microsoft 365 groups for collaboration scenarios are\nalso affected, specifically Outlook, Microsoft Teams, and SharePoint. They do not\noverride the SharePoint or Microsoft Teams guest settings.\nThe recommended state is at least Guest users have limited access to\nproperties and memberships of directory objects or more restrictive.","Rationale":"By limiting guest access to the most restrictive state this helps prevent malicious group\nand user object enumeration in the Microsoft 365 environment. This first step, known as\nreconnaissance in The Cyber Kill Chain, is often conducted by attackers prior to more\nadvanced targeted attacks.","Impact":"The default is Guest users have limited access to properties and\nmemberships of directory objects.\nWhen using the 'most restrictive' setting, guests will only be able to access their own\nprofiles and will not be allowed to see other users' profiles, groups, or group\nmemberships.\nThere are some known issues with Yammer that will prevent guests that are signed in\nfrom leaving the group.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > External Identities select External\ncollaboration settings.\n3. Under Guest user access verify that Guest user access restrictions is set\nto one of the following:\no State: Guest users have limited access to properties and\nmemberships of directory objects\no State: Guest user access is restricted to properties and\nmemberships of their own directory objects (most\nrestrictive)\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\"\n2. Run the following command:\nGet-MgPolicyAuthorizationPolicy | fl GuestUserRoleId\n3. Ensure the value returned is 10dae51f-b6af-4016-8d66-8c2a99b929b3 or\n2af84b1e-32c8-42b7-82bc-daa82404023b (most restrictive)\nNote: Either setting allows for a passing state.\nNote 2: The value of a0b1b346-4d3e-4e8b-98f8-753987be4970 is equal to Guest\nusers have the same access as members (most inclusive) and should not be\nused.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > External Identities select External\ncollaboration settings.\n3. Under Guest user access set Guest user access restrictions to one of\nthe following:\no State: Guest users have limited access to properties and\nmemberships of directory objects\no State: Guest user access is restricted to properties and\nmemberships of their own directory objects (most\nrestrictive)\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.ReadWrite.Authorization\"\n2. Run the following command to set the guest user access restrictions to default:\n# Guest users have limited access to properties and memberships of directory\nobjects\nUpdate-MgPolicyAuthorizationPolicy -GuestUserRoleId '10dae51f-b6af-4016-8d66-\n8c2a99b929b3'\n3. Or, run the following command to set it to the \"most restrictive\":\n# Guest user access is restricted to properties and memberships of their own\ndirectory objects (most restrictive)\nUpdate-MgPolicyAuthorizationPolicy -GuestUserRoleId '2af84b1e-32c8-42b7-82bc-\ndaa82404023b'\nNote: Either setting allows for a passing state.","DefaultValue":"- UI: Guest users have limited access to properties and memberships\nof directory objects\n- PowerShell: 10dae51f-b6af-4016-8d66-8c2a99b929b3","References":"1. https://learn.microsoft.com/en-us/entra/identity/users/users-restrict-guest-\npermissions\n2. https://www.lockheedmartin.com/en-us/capabilities/cyber/cyber-kill-chain.html","CISControls":"[{\"version\": \"\", \"id\": \"6.1\", \"title\": \"Establish an Access Granting Process\", \"description\": \"Establish and follow a process, preferably automated, for granting access to - - - enterprise assets upon new hire, rights grant, or role change of a user.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the authorization policy
    $authPolicy = Get-MgBetaPolicyAuthorizationPolicy
    
    # Check the GuestUserRoleId
    $guestUserRoleId = $authPolicy.GuestUserRoleId
    $isCompliant = $guestUserRoleId -eq '2af84b1e-32c8-42b7-82bc-daa82404023b' # Most restrictive role ID
    
    # Add result to the results array
    $resourceResults += @{
        Name = "Guest User Role ID"
        Value = $guestUserRoleId
        IsCompliant = $isCompliant
        ExpectedValue = '2af84b1e-32c8-42b7-82bc-daa82404023b'
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
