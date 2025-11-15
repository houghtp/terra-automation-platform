# Control: 5.1.2.4 - Ensure access to the Entra admin center is restricted
<# CIS_METADATA_START
{"RecommendationId":"5.1.2.4","Level":"L1","Title":"Ensure access to the Entra admin center is restricted","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Restrict non-privileged users from signing into the Microsoft Entra admin center.\nNote: This recommendation only affects access to the web portal. It does not prevent\nprivileged users from using other methods such as Rest API or PowerShell to obtain\ninformation. Those channels are addressed elsewhere in this document.","Rationale":"The Microsoft Entra admin center contains sensitive data and permission settings,\nwhich are still enforced based on the user's role. However, an end user may\ninadvertently change properties or account settings that could result in increased\nadministrative overhead. Additionally, a compromised end user account could be used\nby a malicious attacker as a means to gather additional information and escalate an\nattack.\nNote: Users will still be able to sign into Microsoft Entra admin center but will be unable\nto see directory information.","Impact":"In the event there are resources a user owns that need to be changed in the Entra\nAdmin center, then an administrator would need to make those changes.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity> Users > User settings.\n3. Verify under the Administration center section that Restrict access to\nMicrosoft Entra admin center is set to Yes.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity> Users > User settings.\n3. Set Restrict access to Microsoft Entra admin center to Yes then Save.","DefaultValue":"No - Non-administrators can access the Microsoft Entra admin center.","References":"1. https://learn.microsoft.com/en-us/entra/fundamentals/users-default-\npermissions#restrict-member-users-default-permissions","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Get authorization policy which contains admin center access restriction setting
    $authPolicy = Get-MgBetaPolicyAuthorizationPolicy

    # Check if non-admin users are restricted from accessing the Entra admin center
    # AllowedToUseEntraIDAdminCenter: false = restricted (compliant), true = allowed (non-compliant)
    $isRestricted = -not $authPolicy.AllowedToUseEntraIDAdminCenter
    $isCompliant = $isRestricted

    $resourceResults += @{
        ResourceName = "Microsoft Entra Admin Center Access Restriction"
        CurrentValue = if ($isRestricted) { "Restricted (Compliant)" } else { "Allowed (Non-Compliant)" }
        IsCompliant = $isCompliant
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
