# Control: 5.2.4.1 - Ensure 'Self service password reset enabled' is set to
<# CIS_METADATA_START
{"RecommendationId":"5.2.4.1","Level":"L1","Title":"Ensure 'Self service password reset enabled' is set to 'All'","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Enabling self-service password reset allows users to reset their own passwords in Entra\nID. When users sign in to Microsoft 365, they will be prompted to enter additional\ncontact information that will help them reset their password in the future. If combined\nregistration is enabled additional information, outside of multi-factor, will not be needed.\nNote: Effective Oct. 1st, 2022, Microsoft will begin to enable combined registration for\nall users in Entra ID tenants created before August 15th, 2020. Tenants created after\nthis date are enabled with combined registration by default.","Rationale":"Users will no longer need to engage the helpdesk for password resets, and the\npassword reset mechanism will automatically block common, easily guessable\npasswords.","Impact":"Users will be required to provide additional contact information to enroll in self-service\npassword reset. Additionally, minor user education may be required for users that are\nused to calling a help desk for assistance with password resets.\nNote: This is unavailable if using Entra Connect / Sync in a hybrid environment.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection > Password reset select Properties.\n3. Ensure Self service password reset enabled is set to All","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection > Password reset select Properties.\n3. Set Self service password reset enabled to All","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/microsoft-365/admin/add-users/let-users-reset-\npasswords?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-sspr\n3. https://learn.microsoft.com/en-us/entra/identity/authentication/howto-registration-\nmfa-sspr-combined","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"5.3\", \"title\": \"Identity Governance\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the self-service password reset policy
    $ssprPolicy = Get-MgBetaPolicyAuthenticationMethodPolicy

    # Check if self-service password reset is enabled for all users
    $isCompliant = $ssprPolicy.IsSelfServicePasswordResetEnabled -eq $true

    # Add the result to the results array
    $resourceResults += @{
        ResourceName = "Self Service Password Reset"
        CurrentValue = if ($isCompliant) { "Enabled for All" } else { "Not Enabled for All" }
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
