# Control: 5.3.4 - Ensure approval is required for Global Administrator
<# CIS_METADATA_START
{"Description":"Microsoft Entra Privileged Identity Management can be used to audit roles, allow just in\ntime activation of roles and allow for periodic role attestation. Requiring approval before\nactivation allows one of the selected approvers to first review and then approve the\nactivation prior to PIM granted the role. The approver doesn't have to be a group\nmember or owner.\nThe recommended state is Require approval to activate for the Global\nAdministrator role.","Impact":"Approvers do not need to be assigned the same role or be members of the same group.\nIt's important to have at least two approvers and an emergency access (break-glass)\naccount to prevent a scenario where no Global Administrators are available. For\nexample, if the last active Global Administrator leaves the organization, and only eligible\nbut inactive Global Administrators remain, a trusted approver without the Global\nAdministrator role or an emergency access account would be essential to avoid delays\nin critical administrative tasks.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity Governance select Privileged Identity\nManagement.\n3. Under Manage select Microsoft Entra Roles.\n4. Under Manage select Roles.\n5. Select Global Administrator in the list.\n6. Select Role settings..\n7. Verify Require approval to activate is set to Yes.\n8. Verify there are at least two approvers in the list.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity Governance select Privileged Identity\nManagement.\n3. Under Manage select Microsoft Entra Roles.\n4. Under Manage select Roles.\n5. Select Global Administrator in the list.\n6. Select Role settings and click Edit.\n7. Check the Require approval to activate box.\n8. Add at least two approvers.\n9. Click Update.","Title":"Ensure approval is required for Global Administrator","ProfileApplicability":"- E5 Level 1","SubSection":"5.3 Identity Governance","DefaultValue":"Require approval to activate : No.","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"6.1\", \"title\": \"Establish an Access Granting Process\", \"description\": \"Establish and follow a process, preferably automated, for granting access to - - - enterprise assets upon new hire, rights grant, or role change of a user.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Establish an Access Revoking Process\", \"description\": \"Establish and follow a process, preferably automated, for revoking access to enterprise assets, through disabling accounts immediately upon termination, rights - - - revocation, or role change of a user. Disabling accounts, instead of deleting accounts, may be necessary to preserve audit trails.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"4.1\", \"title\": \"Maintain Inventory of Administrative Accounts\", \"description\": \"v7 Use automated tools to inventory all administrative accounts, including domain - - and local accounts, to ensure that only authorized individuals have elevated privileges.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/pim-configure\n2. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/groups-role-settings#require-approval-to-activate","Rationale":"Requiring approval for Global Administrator role activation enhances visibility and\naccountability every time this highly privileged role is used. This process reduces the\nrisk of an attacker elevating a compromised account to the highest privilege level, as\nany activation must first be reviewed and approved by a trusted party.\nNote: This only acts as protection for eligible users that are activating a role. Directly\nassigning a role does require an approval workflow so therefore it is important to\nimplement and use PIM correctly.","Section":"5 Microsoft Entra admin center","RecommendationId":"5.3.4"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Retrieve the role settings for Global Administrator
    $globalAdminRole = Get-MgBetaRoleManagementDirectoryRoleAssignment -Filter "RoleDefinitionId eq '62e90394-69f5-4237-9190-012177145e10'" -All

    # Check if approval is required for activation
    $approvalRequired = $false
    $approversCount = 0

    if ($globalAdminRole) {
        # Get the first role assignment to get the role definition ID
        $roleDefinitionId = $globalAdminRole[0].RoleDefinitionId
        $roleSettings = Get-MgBetaRoleManagementDirectoryRoleDefinition -UnifiedRoleDefinitionId $roleDefinitionId

        if ($roleSettings) {
            $approvalRequired = $roleSettings.ApprovalRequiredForActivation
            $approversCount = ($roleSettings.ApproverIds).Count
        }
    }

    # Determine compliance
    $isCompliant = $approvalRequired -eq $true -and $approversCount -ge 2

    # Add result to the results array
    $resourceResults += @{
        ResourceName = "Global Administrator"
        ApprovalRequired = $approvalRequired
        ApproversCount = $approversCount
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
