# Control: 5.2.3.2 - Ensure custom banned passwords lists are used
<# CIS_METADATA_START
{"RecommendationId":"5.2.3.2","Level":"L1","Title":"Ensure custom banned passwords lists are used","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"With Entra Password Protection, default global banned password lists are automatically\napplied to all users in an Entra ID tenant. To support business and security needs,\ncustom banned password lists can be defined. When users change or reset their\npasswords, these banned password lists are checked to enforce the use of strong\npasswords.\nA custom banned password list should include some of the following examples:\n- Brand names\n- Product names\n- Locations, such as company headquarters\n- Company-specific internal terms\n- Abbreviations that have specific company meaning","Rationale":"Creating a new password can be difficult regardless of one's technical background. It is\ncommon to look around one's environment for suggestions when building a password,\nhowever, this may include picking words specific to the organization as inspiration for a\npassword. An adversary may employ what is called a 'mangler' to create permutations\nof these specific words in an attempt to crack passwords or hashes making it easier to\nreach their goal.","Impact":"If a custom banned password list includes too many common dictionary words, or short\nwords that are part of compound words, then perfectly secure passwords may be\nblocked. The organization should consider a balance between security and usability\nwhen creating a list.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Protection > Authentication methods\n3. Select Password protection\n4. Verify Enforce custom list is set to Yes\n5. Verify Custom banned password list contains entries specific to the\norganization or matches a pre-determined list.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Directory.Read.All\"\n2. Run the following commands:\n$PwRuleSettings = '5cf42378-d67d-4f36-ba46-e8b86229381d'\nGet-MgGroupSetting | Where-Object TemplateId -eq $PwRuleSettings |\nSelect-Object -ExpandProperty Values\n3. Ensure EnableBannedPasswordCheck is True and BannedPasswordList is\npopulated with banned passwords.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Protection > Authentication methods\n3. Select Password protection\n4. Set Enforce custom list to Yes\n5. In Custom banned password list create a list using suggestions outlined in\nthis document.\n6. Click Save\nNote: Below is a list of examples that can be used as a starting place. The references\nsection contains more suggestions.\n- Brand names\n- Product names\n- Locations, such as company headquarters\n- Company-specific internal terms\n- Abbreviations that have specific company meaning","DefaultValue":"","References":"1. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-password-\nban-bad#custom-banned-password-list\n2. https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-configure-\ncustom-password-protection","CISControls":"[{\"version\": \"\", \"id\": \"5.2\", \"title\": \"Use Unique Passwords\", \"description\": \"v8 Use unique passwords for all enterprise assets. Best practice implementation - - - includes, at a minimum, an 8-character password for accounts using MFA and a 14-character password for accounts not using MFA.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Get tenant-wide directory settings instead of group settings
    $PwRuleSettings = '5cf42378-d67d-4f36-ba46-e8b86229381d'
    $directorySettings = Get-MgBetaDirectorySetting | Where-Object { $_.TemplateId -eq $PwRuleSettings }

    if ($directorySettings) {
        foreach ($setting in $directorySettings) {
            $isCompliant = $false
            $customBannedPasswordsEnabled = $setting.Values | Where-Object { $_.Name -eq 'EnableBannedPasswordCheck' } | Select-Object -ExpandProperty Value
            $customBannedPasswordsList = $setting.Values | Where-Object { $_.Name -eq 'BannedPasswordList' } | Select-Object -ExpandProperty Value

            if ($customBannedPasswordsEnabled -eq 'True' -and -not [string]::IsNullOrEmpty($customBannedPasswordsList)) {
                $isCompliant = $true
            }

            $resourceResults += @{
                SettingId = $setting.Id
                IsCompliant = $isCompliant
                EnableBannedPasswordCheck = $customBannedPasswordsEnabled
                BannedPasswordList = if ($customBannedPasswordsList) { $customBannedPasswordsList.Split(',').Count } else { 0 }
            }
        }
    } else {
        # No password policy settings found - this is non-compliant
        $resourceResults += @{
            SettingId = "None"
            IsCompliant = $false
            EnableBannedPasswordCheck = "Not configured"
            BannedPasswordList = 0
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
