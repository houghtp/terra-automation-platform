# Control: 1.3.1 - Ensure the 'Password expiration policy' is set to 'Set
<# CIS_METADATA_START
{"Description": "Microsoft cloud-only accounts have a pre-defined password policy that cannot be\nchanged. The only items that can change are the number of days until a password\nexpires and whether or whether passwords expire at all.", "Impact": "When setting passwords not to expire it is important to have other controls in place to\nsupplement this setting. See below for related recommendations and user guidance.\n- Ban common passwords.\n- Educate users to not reuse organization passwords anywhere else.\n- Enforce Multi-Factor Authentication registration for all users.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings select Org Settings.\n3. Click on Security & privacy.\n4. Select Password expiration policy ensure that Set passwords to never\nexpire (recommended) has been checked.\nTo audit using PowerShell:\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"Domain.Read.All\".\n2. Run the following Microsoft Online PowerShell command:\nGet-MgDomain | ft id,PasswordValidityPeriodInDays\n3. Verify the value returned for valid domains is 2147483647", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings select Org Settings.\n3. Click on Security & privacy.\n4. Check the Set passwords to never expire (recommended) box.\n5. Click Save.\nTo remediate using PowerShell:\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"Domain.ReadWrite.All\".\n2. Run the following Microsoft Graph PowerShell command:\nUpdate-MgDomain -DomainId <Domain> -PasswordValidityPeriodInDays 2147483647", "Title": "Ensure the 'Password expiration policy' is set to 'Set passwords to never expire (recommended)'", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "1.3 Settings", "DefaultValue": "If the property is not set, a default value of 90 days will be used", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"5.2\", \"title\": \"Use Unique Passwords\", \"description\": \"v8 Use unique passwords for all enterprise assets. Best practice implementation - - - includes, at a minimum, an 8-character password for accounts using MFA and a 14-character password for accounts not using MFA.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"4.4\", \"title\": \"Use Unique Passwords\", \"description\": \"v7 Where multi-factor authentication is not supported (such as local administrator, - - root, or service accounts), accounts will use passwords that are unique to that system.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://pages.nist.gov/800-63-3/sp800-63b.html\n2. https://www.cisecurity.org/white-papers/cis-password-policy-guide/\n3. https://learn.microsoft.com/en-us/microsoft-365/admin/misc/password-policy-\nrecommendations?view=o365-worldwide", "Rationale": "Organizations such as NIST and Microsoft have updated their password policy\nrecommendations to not arbitrarily require users to change their passwords after a\nspecific amount of time, unless there is evidence that the password is compromised, or\nthe user forgot it. They suggest this even for single factor (Password Only) use cases,\nwith a reasoning that forcing arbitrary password changes on users actually make the\npasswords less secure. Other recommendations within this Benchmark suggest the use\nof MFA authentication for at least critical accounts (at minimum), which makes\npassword expiration even less useful as well as password protection for Entra ID.", "Section": "1 Microsoft 365 admin center", "RecommendationId": "1.3.1"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve domain information
    $domains = Get-MgBetaDomain
    
    # Process each domain and check PasswordValidityPeriodInDays
    foreach ($domain in $domains) {
        $isCompliant = $domain.PasswordValidityPeriodInDays -gt 0
        $resourceResults += @{
            DomainId = $domain.Id
            PasswordValidityPeriodInDays = $domain.PasswordValidityPeriodInDays
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
