# Control: 1.1.2 - Ensure two emergency access accounts have been
<# CIS_METADATA_START
{"Description": "Emergency access or \"break glass\" accounts are limited for emergency scenarios\nwhere normal administrative accounts are unavailable. They are not assigned to a\nspecific user and will have a combination of physical and technical controls to prevent\nthem from being accessed outside a true emergency. These emergencies could be due\nto several things, including:\n- Technical failures of a cellular provider or Microsoft related service such as MFA.\n- The last remaining Global Administrator account is inaccessible.\nEnsure two Emergency Access accounts have been defined.\nNote: Microsoft provides several recommendations for these accounts and how to\nconfigure them. For more information on this, please refer to the references section.\nThe CIS Benchmark outlines the more critical things to consider.", "Impact": "Failure to properly implement emergency access accounts can weaken the security\nposture. Microsoft recommends excluding at least one of the two emergency access\naccounts from all conditional access rules, necessitating passwords with sufficient\nentropy and length to protect against random guesses. For a secure passwordless\nsolution, FIDO2 security keys may be used instead of passwords.", "Audit": "Step 1 - Ensure a policy and procedure is in place at the organization:\n- In order for accounts to be effectively used in a break-glass situation the proper\npolicies and procedures must be authorized and distributed by senior\nmanagement.\n- FIDO2 Security Keys should be locked in a secure separate fireproof location.\n- Passwords should be at least 16 characters, randomly generated and MAY be\nseparated in multiple pieces to be joined on emergency.\nStep 2 - Ensure two emergency access accounts are defined:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com\n2. Expand Users > Active Users\n3. Inspect the designated emergency access accounts and ensure the following:\no The accounts are named correctly, and do NOT identify with a particular\nperson.\no The accounts use the default .onmicrosoft.com domain and not the\norganization's.\no The accounts are cloud-only.\no The accounts are unlicensed.\no The accounts are assigned the Global Administrator directory role.\nStep 3 - Ensure at least one account is excluded from all conditional access\nrules:\n1. Navigate Microsoft Entra admin center https://entra.microsoft.com/\n2. Expand Protection > Conditional Access.\n3. Inspect the conditional access rules.\n4. Ensure one of the emergency access accounts is excluded from all rules.\nWarning: As of 10/15/2024 MFA is required for all users including Break Glass\nAccounts. It is recommended to update these accounts to use passkey\n(FIDO2) or configure certificate-based authentication for MFA. Both methods satisfy the\nMFA requirement.", "Remediation": "Step 1 - Create two emergency access accounts:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com\n2. Expand Users > Active Users\n3. Click Add user and create a new user with this criteria:\no Name the account in a way that does NOT identify it with a particular\nperson.\no Assign the account to the default .onmicrosoft.com domain and not the\norganization's.\no The password must be at least 16 characters and generated randomly.\no Do not assign a license.\no Assign the user the Global Administrator role.\n4. Repeat the above steps for the second account.\nStep 2 - Exclude at least one account from conditional access policies:\n1. Navigate Microsoft Entra admin center https://entra.microsoft.com/\n2. Expand Protection > Conditional Access.\n3. Inspect the conditional access policies.\n4. For each rule add an exclusion for at least one of the emergency access\naccounts.\n5. Users > Exclude > Users and groups and select one emergency access\naccount.\nStep 3 - Ensure the necessary procedures and policies are in place:\n- In order for accounts to be effectively used in a break glass situation the proper\npolicies and procedures must be authorized and distributed by senior\nmanagement.\n- FIDO2 Security Keys should be locked in a secure separate fireproof location.\n- Passwords should be at least 16 characters, randomly generated and MAY be\nseparated in multiple pieces to be joined on emergency.\nWarning: As of 10/15/2024 MFA is required for all users including Break Glass\nAccounts. It is recommended to update these accounts to use passkey\n(FIDO2) or configure certificate-based authentication for MFA. Both methods satisfy the\nMFA requirement.\nAdditional suggestions for emergency account management:\n- Create access reviews for these users.\n- Exclude users from conditional access rules.\n- Add the account to a restricted management administrative unit.\nWarning: If CA (conditional access) exclusion is managed by a group, this group should\nbe added to PIM for groups (licensing required) or be created as a role-assignable\ngroup. If it is a regular security group, then users with the Group Administrators role are\nable to bypass CA entirely.", "Title": "Ensure two emergency access accounts have been defined", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "1.1 Users", "DefaultValue": "Not defined.", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"5.1\", \"title\": \"Establish and Maintain an Inventory of Accounts\", \"description\": \"Establish and maintain an inventory of all accounts managed in the enterprise. v8 The inventory must include both user and administrator accounts. The inventory, at - - - a minimum, should contain the person's name, username, start/stop dates, and department. Validate that all active accounts are authorized, on a recurring schedule at a minimum quarterly, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/security-planning#stage-1-critical-items-to-do-right-now\n2. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/security-emergency-access\n3. https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/admin-\nunits-restricted-management\n4. https://learn.microsoft.com/en-us/entra/identity/authentication/concept-\nmandatory-multifactor-authentication#accounts", "Rationale": "In various situations, an organization may require the use of a break glass account to\ngain emergency access. In the event of losing access to administrative functions, an\norganization may experience a significant loss in its ability to provide support, lose\ninsight into its security posture, and potentially suffer financial losses.", "Section": "1 Microsoft 365 admin center", "RecommendationId": "1.1.2"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve all users
    $users = Get-MgBetaUser -All

    # Filter for emergency access accounts
    $emergencyAccounts = $users | Where-Object {
        $_.UserPrincipalName -like "*.onmicrosoft.com" -and
        $_.AssignedLicenses.Count -eq 0 -and
        $_.UserType -eq "Member" -and
        $_.DisplayName -notmatch ".*@.*" -and
        $_.DirectoryRoles -contains "Global Administrator"
    }

    # Check if at least two emergency accounts are defined
    $isCompliant = $emergencyAccounts.Count -ge 2

    # Collect results for each emergency account
    foreach ($account in $emergencyAccounts) {
        $resourceResults += @{
            ResourceName = $account.DisplayName
            UserPrincipalName = $account.UserPrincipalName
            IsCompliant = $isCompliant
        }
    }

    # Determine overall status
    $overallStatus = if ($isCompliant) { 'Pass' } else { 'Fail' }
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
