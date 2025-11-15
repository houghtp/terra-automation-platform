# Control: 5.3.5 - Ensure approval is required for Privileged Role
<# CIS_METADATA_START
{"Description":"Microsoft Entra Privileged Identity Management can be used to audit roles, allow just in\ntime activation of roles and allow for periodic role attestation. Requiring approval before\nactivation allows one of the selected approvers to first review and then approve the\nactivation prior to PIM granted the role. The approver doesn't have to be a group\nmember or owner.\nThe recommended state is Require approval to activate for the Privileged\nRole Administrator role.","Impact":"Requiring approvers for automatic role assignment can slightly increase administrative\noverhead and add delays to tasks.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity Governance select Privileged Identity\nManagement.\n3. Under Manage select Microsoft Entra Roles.\n4. Under Manage select Roles.\n5. Select Privileged Role Administrator in the list.\n6. Select Role settings.\n7. Verify Require approval to activate is set to Yes.\n8. Verify there are at least two approvers in the list.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity Governance select Privileged Identity\nManagement.\n3. Under Manage select Microsoft Entra Roles.\n4. Under Manage select Roles.\n5. Select Privileged Role Administrator in the list.\n6. Select Role settings and click Edit.\n7. Check the Require approval to activate box.\n8. Add at least two approvers.\n9. Click Update.","Title":"Ensure approval is required for Privileged Role","ProfileApplicability":"- E5 Level 1","SubSection":"5.3 Identity Governance","DefaultValue":"Require approval to activate : No.","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"6.1\", \"title\": \"Establish an Access Granting Process\", \"description\": \"Establish and follow a process, preferably automated, for granting access to - - - enterprise assets upon new hire, rights grant, or role change of a user.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Establish an Access Revoking Process\", \"description\": \"Establish and follow a process, preferably automated, for revoking access to enterprise assets, through disabling accounts immediately upon termination, rights - - - revocation, or role change of a user. Disabling accounts, instead of deleting accounts, may be necessary to preserve audit trails.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"4.1\", \"title\": \"Maintain Inventory of Administrative Accounts\", \"description\": \"v7 Use automated tools to inventory all administrative accounts, including domain - - and local accounts, to ensure that only authorized individuals have elevated privileges. 6 Exchange admin center The Exchange admin center contains settings related to everything Exchange Online. Direct link: https://admin.exchange.microsoft.com/ The PowerShell module most used in this section is ExchangeOnlineManagement and uses Connect-ExchangeOnline as the connection cmdlet. The latest version of the module can be downloaded here: https://www.powershellgallery.com/packages/ExchangeOnlineManagement/\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.1\", \"title\": \"Audit\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/pim-configure\n2. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/groups-role-settings#require-approval-to-activate","Rationale":"This role grants the ability to manage assignments for all Microsoft Entra roles including\nthe Global Administrator role. This role does not include any other privileged abilities in\nMicrosoft Entra ID like creating or updating users. However, users assigned to this role\ncan grant themselves or others additional privilege by assigning additional roles.\nRequiring approval for activation enhances visibility and accountability every time this\nhighly privileged role is used. This process reduces the risk of an attacker elevating a\ncompromised account to the highest privilege level, as any activation must first be\nreviewed and approved by a trusted party.\nNote: This only acts as protection for eligible users that are activating a role. Directly\nassigning a role does require an approval workflow so therefore it is important to\nimplement and use PIM correctly.","Section":"5 Microsoft Entra admin center","RecommendationId":"5.3.5"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Get the Privileged Role Administrator role definition
    $allRoles = Get-MgBetaRoleManagementDirectoryRoleDefinition -All
    $privilegedRoleAdminRole = $allRoles | Where-Object { $_.DisplayName -eq 'Privileged Role Administrator' }

    if (-not $privilegedRoleAdminRole) {
        throw "Privileged Role Administrator role definition not found"
    }

    # Get the role assignment policy for this role
    # Note: This requires Entra ID P2 or Entra ID Governance license
    try {
        $rolePolicy = Get-MgBetaPolicyRoleManagementPolicy -Filter "scopeId eq '/' and scopeType eq 'Directory'" -ExpandProperty "rules" -All -ErrorAction Stop |
                      Where-Object { $_.Id -match $privilegedRoleAdminRole.Id }
    }
    catch {
        # Check if this is a license requirement error
        if ($_.Exception.Message -like "*AadPremiumLicenseRequired*" -or $_.Exception.Message -like "*Entra ID P2*" -or $_.Exception.Message -like "*Governance license*") {
            $resourceResults += @{
                ResourceName = "Privileged Role Administrator PIM Policy"
                CurrentValue = "Entra ID P2 or Governance license required"
                IsCompliant = $null
                Details = "This check requires Microsoft Entra ID P2 or Microsoft Entra ID Governance license. Cannot evaluate without Privileged Identity Management (PIM) access."
            }

            return @{
                status = "Manual"
                status_id = 2
                Details = $resourceResults
                Note = "Requires Entra ID P2 or Governance license for PIM role management policies"
            }
        }
        else {
            throw
        }
    }

    if ($rolePolicy) {
        # Check the activation rules for approval requirement
        $activationRules = $rolePolicy.Rules | Where-Object { $_.Id -like '*Activation_Approval*' -or $_.'@odata.type' -eq '#microsoft.graph.unifiedRoleManagementPolicyApprovalRule' }

        $requireApproval = $false
        $approversCount = 0

        if ($activationRules) {
            foreach ($rule in $activationRules) {
                if ($rule.Setting.IsApprovalRequired) {
                    $requireApproval = $true
                    $approversCount = ($rule.Setting.ApprovalStages.PrimaryApprovers | Measure-Object).Count
                }
            }
        }

        # Determine compliance - requires approval with at least 1 approver
        $isCompliant = $requireApproval -eq $true -and $approversCount -ge 1

        $resourceResults += @{
            ResourceName = "Privileged Role Administrator"
            CurrentValue = "Approval Required: $requireApproval, Approvers: $approversCount"
            IsCompliant = $isCompliant
            Details = "PIM policy evaluated for role activation approval requirements"
        }
    } else {
        $resourceResults += @{
            ResourceName = "Privileged Role Administrator"
            CurrentValue = "No PIM policy found"
            IsCompliant = $false
            Details = "No role management policy configured for Privileged Role Administrator"
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
