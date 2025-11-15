# Control: 5.1.2.2 - Ensure third party integrated applications are not
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.2","Level":"L2","Title":"Ensure third party integrated applications are not allowed","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"App registration allows users to register custom-developed applications for use within\nthe directory.","Rationale":"Third-party integrated applications connection to services should be disabled unless\nthere is a very clear value and robust security controls are in place. While there are\nlegitimate uses, attackers can grant access from breached accounts to third party\napplications to exfiltrate data from your tenancy without having to maintain the breached\naccount.","Impact":"The implementation of this change will impact both end users and administrators. End\nusers will not be able to integrate third-party applications that they may wish to use.\nAdministrators are likely to receive requests from end users to grant them permission to\nthe necessary third-party applications.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users select Users settings.\n3. Verify Users can register applications is set to No.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\"\n2. Run the following command:\n(Get-MgPolicyAuthorizationPolicy).DefaultUserRolePermissions | fl\nAllowedToCreateApps\n3. Ensure the returned value is False.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Users select Users settings.\n3. Set Users can register applications to No.\n4. Click Save.\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.ReadWrite.Authorization\"\n2. Run the following commands:\n$param = @{ AllowedToCreateApps = \"$false\" }\nUpdate-MgPolicyAuthorizationPolicy -DefaultUserRolePermissions $param","DefaultValue":"Yes (Users can register applications.)","References":"1. https://learn.microsoft.com/en-us/entra/identity-platform/how-applications-are-\nadded","CISControls":"[{\"version\": \"\", \"id\": \"2.5\", \"title\": \"Allowlist Authorized Software\", \"description\": \"v8 Use technical controls, such as application allowlisting, to ensure that only - - authorized software can execute or be accessed. Reassess bi-annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"18.4\", \"title\": \"Only Use Up-to-date And Trusted Third-Party\", \"description\": \"v7 Components - - Only use up-to-date and trusted third-party components for the software developed by the organization.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the default user role permissions from the authorization policy
    $defaultUserRolePermissions = Get-MgBetaPolicyAuthorizationPolicy | Select-Object -ExpandProperty DefaultUserRolePermissions
    
    # Convert results to standard format
    $resourceResults += @{
        Name = "Default User Role Permissions"
        IsCompliant = $defaultUserRolePermissions -eq $null -or $defaultUserRolePermissions.Count -eq 0
        Details = $defaultUserRolePermissions
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
