# Control: 5.2.3.3 - Ensure password protection is enabled for on-prem
<# CIS_METADATA_START
{"RecommendationId":"5.2.3.3","Level":"L1","Title":"Ensure password protection is enabled for on-prem Active Directory","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Microsoft Entra Password Protection provides a global and custom banned password\nlist. A password change request fails if there's a match in these banned password list.\nTo protect on-premises Active Directory Domain Services (AD DS) environment, install\nand configure Entra Password Protection.\nNote: This recommendation applies to Hybrid deployments only and will have no impact\nunless working with on-premises Active Directory.","Rationale":"This feature protects an organization by prohibiting the use of weak or leaked\npasswords. In addition, organizations can create custom banned password lists to\nprevent their users from using easily guessed passwords that are specific to their\nindustry. Deploying this feature to Active Directory will strengthen the passwords that\nare used in the environment.","Impact":"The potential impact associated with implementation of this setting is dependent upon\nthe existing password policies in place in the environment. For environments that have\nstrong password policies in place, the impact will be minimal. For organizations that do\nnot have strong password policies in place, implementation of Microsoft Entra Password\nProtection may require users to change passwords and adhere to more stringent\nrequirements than they have been accustomed to.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select Password protection and ensure that Enable password protection\non Windows Server Active Directory is set to Yes and that Mode is set to\nEnforced.","Remediation":"To remediate using the UI:\n- Download and install the Azure AD Password Proxies and DC Agents from\nthe following location:\nhttps://www.microsoft.com/download/details.aspx?id=57071 After installed follow\nthe steps below.\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Protection select Authentication methods.\n3. Select Password protection and set Enable password protection on\nWindows Server Active Directory to Yes and Mode to Enforced.","DefaultValue":"Enable - Yes\nMode - Audit","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/howto-password-\nban-bad-on-premises-operations","CISControls":"[{\"version\": \"\", \"id\": \"5.2\", \"title\": \"Use Unique Passwords\", \"description\": \"v8 Use unique passwords for all enterprise assets. Best practice implementation - - - includes, at a minimum, an 8-character password for accounts using MFA and a 14-character password for accounts not using MFA.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"4.4\", \"title\": \"Use Unique Passwords\", \"description\": \"v7 Where multi-factor authentication is not supported (such as local administrator, - - root, or service accounts), accounts will use passwords that are unique to that system.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Implement check logic based on audit procedure
    # Using Microsoft Graph API to check password protection settings
    # Note: Get-MgBetaDirectorySetting doesn't support -Filter, must get all and filter locally
    $allSettings = Get-MgBetaDirectorySetting -All
    $passwordProtectionSettings = $allSettings | Where-Object { $_.DisplayName -eq 'PasswordProtection' }

    if ($passwordProtectionSettings) {
        $enablePasswordProtection = $passwordProtectionSettings.Values | Where-Object { $_.Name -eq "EnablePasswordProtectionOnWindowsServerAD" } | Select-Object -ExpandProperty Value
        $mode = $passwordProtectionSettings.Values | Where-Object { $_.Name -eq "Mode" } | Select-Object -ExpandProperty Value

        $isCompliant = ($enablePasswordProtection -eq "Yes" -and $mode -eq "Enforced")

        $resourceResults += @{
            ResourceName = "Password Protection Settings"
            EnablePasswordProtection = $enablePasswordProtection
            Mode = $mode
            IsCompliant = $isCompliant
        }
    }
    else {
        $resourceResults += @{
            ResourceName = "Password Protection Settings"
            EnablePasswordProtection = "Not Found"
            Mode = "Not Found"
            IsCompliant = $false
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
