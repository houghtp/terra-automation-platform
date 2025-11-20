# Control: 5.3.1 - Ensure 'Privileged Identity Management' is used to
<# CIS_METADATA_START
{"Description": "Microsoft Entra Privileged Identity Management can be used to audit roles, allow just in\ntime activation of roles and allow for periodic role attestation. Organizations should\nremove permanent members from privileged Office 365 roles and instead make them\neligible, through a JIT activation workflow.", "Impact": "The implementation of Just in Time privileged access is likely to necessitate changes to\nadministrator routine. Administrators will only be granted access to administrative roles\nwhen required. When administrators request role activation, they will need to document\nthe reason for requiring role access, anticipated time required to have the access, and\nto reauthenticate to enable role access.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity Governance select Privileged Identity\nManagement.\n3. Under Manage select Microsoft Entra Roles.\n4. Under Manage select Roles.\n5. Inspect at a minimum the following sensitive roles to ensure the members are\nEligible and not Permanent:\n- Application Administrator\n- Authentication Administrator\n- Azure Information Protection Administrator\n- Billing Administrator\n- Cloud Application Administrator\n- Cloud Device Administrator\n- Compliance Administrator\n- Customer LockBox Access Approver\n- Exchange Administrator\n- Fabric Administrator\n- Global Administrator\n- HelpDesk Administrator\n- Intune Administrator\n- Kaizala Administrator\n- License Administrator\n- Microsoft Entra Joined Device Local Administrator\n- Password Administrator\n- Privileged Authentication Administrator\n- Privileged Role Administrator\n- Security Administrator\n- SharePoint Administrator\n- Skype for Business Administrator\n- Teams Administrator\n- User Administrator", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity Governance select Privileged Identity\nManagement.\n3. Under Manage select Microsoft Entra Roles.\n4. Under Manage select Roles.\n5. Inspect at a minimum the following sensitive roles. For each of the members that\nhave an ASSIGNMENT TYPE of Permanent, click on the ... and choose Make\neligible:\n- Application Administrator\n- Authentication Administrator\n- Azure Information Protection Administrator\n- Billing Administrator\n- Cloud Application Administrator\n- Cloud Device Administrator\n- Compliance Administrator\n- Customer LockBox Access Approver\n- Exchange Administrator\n- Fabric Administrator\n- Global Administrator\n- HelpDesk Administrator\n- Intune Administrator\n- Kaizala Administrator\n- License Administrator\n- Microsoft Entra Joined Device Local Administrator\n- Password Administrator\n- Privileged Authentication Administrator\n- Privileged Role Administrator\n- Security Administrator\n- SharePoint Administrator\n- Skype for Business Administrator\n- Teams Administrator\n- User Administrator", "Title": "Ensure 'Privileged Identity Management' is used to manage roles", "ProfileApplicability": "- E5 Level 2", "SubSection": "5.3 Identity Governance", "DefaultValue": "", "Level": "L2", "CISControls": "[{\"version\": \"\", \"id\": \"6.1\", \"title\": \"Establish an Access Granting Process\", \"description\": \"Establish and follow a process, preferably automated, for granting access to - - - enterprise assets upon new hire, rights grant, or role change of a user.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"6.2\", \"title\": \"Establish an Access Revoking Process\", \"description\": \"Establish and follow a process, preferably automated, for revoking access to enterprise assets, through disabling accounts immediately upon termination, rights - - - revocation, or role change of a user. Disabling accounts, instead of deleting accounts, may be necessary to preserve audit trails.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"4.1\", \"title\": \"Maintain Inventory of Administrative Accounts\", \"description\": \"v7 Use automated tools to inventory all administrative accounts, including domain - - and local accounts, to ensure that only authorized individuals have elevated privileges.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/pim-configure", "Rationale": "Organizations want to minimize the number of people who have access to secure\ninformation or resources, because that reduces the chance of a malicious actor getting\nthat access, or an authorized user inadvertently impacting a sensitive resource.\nHowever, users still need to carry out privileged operations in Entra ID. Organizations\ncan give users just-in-time (JIT) privileged access to roles. There is a need for oversight\nfor what those users are doing with their administrator privileges. PIM helps to mitigate\nthe risk of excessive, unnecessary, or misused access rights.", "Section": "5 Microsoft Entra admin center", "RecommendationId": "5.3.1"}
CIS_METADATA_END #>
# Required Services: SharePoint, Teams, ExchangeOnline, MgGraph, SecurityCompliance
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Define the sensitive roles to check
    $sensitiveRoles = @(
        "Application Administrator",
        "Authentication Administrator",
        "Azure Information Protection Administrator",
        "Billing Administrator",
        "Cloud Application Administrator",
        "Cloud Device Administrator",
        "Compliance Administrator",
        "Customer LockBox Access Approver",
        "Exchange Administrator",
        "Fabric Administrator",
        "Global Administrator",
        "HelpDesk Administrator",
        "Intune Administrator",
        "Kaizala Administrator",
        "License Administrator",
        "Microsoft Entra Joined Device Local Administrator",
        "Password Administrator",
        "Privileged Authentication Administrator",
        "Privileged Role Administrator",
        "Security Administrator",
        "SharePoint Administrator",
        "Skype for Business Administrator",
        "Teams Administrator",
        "User Administrator"
    )

    # Retrieve all role assignments
    $roleAssignments = Get-MgBetaRoleManagementDirectoryRoleAssignment -All

    # Check each role assignment
    foreach ($assignment in $roleAssignments) {
        $roleName = $assignment.RoleDefinition.DisplayName
        $assignmentType = $assignment.AssignmentType

        # Check if the role is in the list of sensitive roles
        if ($sensitiveRoles -contains $roleName) {
            $isCompliant = $assignmentType -eq "Eligible"

            $resourceResults += @{
                ResourceName = $roleName
                CurrentValue = $assignmentType
                IsCompliant = $isCompliant
            }
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
