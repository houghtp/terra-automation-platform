# Control: 5.2.3.5 - Ensure weak authentication methods are disabled
<# CIS_METADATA_START
{"RecommendationId":"5.2.3.5","Level":"L1","Title":"Ensure weak authentication methods are disabled","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Authentication methods support a wide variety of scenarios for signing in to Microsoft\n365 resources. Some of these methods are inherently more secure than others but\nrequire more investment in time to get users enrolled and operational.\nSMS and Voice Call rely on telephony carrier communication methods to deliver the\nauthenticating factor.\nThe email one-time passcode feature is a way to authenticate B2B collaboration users\nwhen they can't be authenticated through other means, such as Microsoft Entra ID,\nMicrosoft account (MSA), or social identity providers. When a B2B guest user tries to\nredeem your invitation or sign in to your shared resources, they can request a\ntemporary passcode, which is sent to their email address. Then they enter this\npasscode to continue signing in.\nThe recommended state is to Disable these methods:\n- SMS\n- Voice Call\n- Email OTP","Rationale":"The SMS and Voice call methods are vulnerable to SIM swapping which could allow an\nattacker to gain access to your Microsoft 365 account.","Impact":"Disabling Email OTP will prevent one-time pass codes from being sent to unverified\nguest users accessing Microsoft 365 resources on the tenant such as \"@yahoo.com\".\nThey will be required to use a personal Microsoft account, a managed Microsoft Entra\naccount, be part of a federation or be configured as a guest in the host tenant's\nMicrosoft Entra ID.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select Policies.\n4. Verify that the following methods in the Enabled column or set to No.\no Method: SMS\no Method: Voice call\no Method: Email OTP\nTo audit using Powershell:\n1. Connect to Graph using Connect-MgGraph -Scopes \"Policy.Read.All\"\n2. Run the following:\n(Get-MgPolicyAuthenticationMethodPolicy).AuthenticationMethodConfigurations\n3. Ensure Sms, Voice and Email are each disabled.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select Policies.\n4. Inspect each method that is out of compliance and remediate:\no Click on the method to open it.\no Change the Enable toggle to the off position.\no Click Save.\nNote: If the save button remains greyed out after toggling a method off, then first turn it\nback on and then change the position of the Target selection (all users or select\ngroups). Turn the method off again and save. This was observed to be a bug in the UI\nat the time this document was published.\nTo remediate using Powershell:\n1. Connect to Graph using Connect-MgGraph -Scopes\n\"Policy.ReadWrite.AuthenticationMethod\"\n2. Run the following to disable all three authentication methods:\n$params = @(\n@{ Id = \"Sms\"; State = \"disabled\" },\n@{ Id = \"Voice\"; State = \"disabled\" },\n@{ Id = \"Email\"; State = \"disabled\" }\n)\nUpdate-MgPolicyAuthenticationMethodPolicy -AuthenticationMethodConfigurations\n$params","DefaultValue":"#NAME?","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-\nauthentication-methods-manage\n2. https://learn.microsoft.com/en-us/entra/external-id/one-time-passcode\n3. https://www.microsoft.com/en-us/microsoft-365-life-hacks/privacy-and-\nsafety/what-is-sim-swapping","CISControls":"[{\"version\": \"\", \"id\": \"6.3\", \"title\": \"Require MFA for Externally-Exposed Applications\", \"description\": \"v8 Require all externally-exposed enterprise or third-party applications to enforce - - MFA, where supported. Enforcing MFA through a directory service or SSO provider is a satisfactory implementation of this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Adapted script logic from the original script
    # Original command: (Get-MgPolicyAuthenticationMethodPolicy).AuthenticationMethodConfigurations
    $authMethodConfigurations = Get-MgPolicyAuthenticationMethodPolicy | Select-Object -ExpandProperty AuthenticationMethodConfigurations
    
    # Process each authentication method configuration
    foreach ($config in $authMethodConfigurations) {
        $isCompliant = $true
        
        # Example compliance check: Ensure method is not weak (e.g., not using SMS)
        if ($config.MethodType -eq 'sms') {
            $isCompliant = $false
        }
        
        # Add result to the results array
        $resourceResults += @{
            MethodType = $config.MethodType
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
