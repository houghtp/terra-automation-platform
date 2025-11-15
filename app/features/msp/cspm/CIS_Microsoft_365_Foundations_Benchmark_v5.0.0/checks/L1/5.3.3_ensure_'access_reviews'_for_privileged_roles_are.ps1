# Control: 5.3.3 - Ensure 'Access reviews' for privileged roles are
<# CIS_METADATA_START
{"Description":"Access reviews enable administrators to establish an efficient automated process for\nreviewing group memberships, access to enterprise applications, and role assignments.\nThese reviews can be scheduled to recur regularly, with flexible options for delegating\nthe task of reviewing membership to different members of the organization.\nEnsure Access reviews for high privileged Entra ID roles are done monthly or more\nfrequently. These reviews should include at a minimum the roles listed below:\n- Global Administrator\n- Exchange Administrator\n- SharePoint Administrator\n- Teams Administrator\n- Security Administrator\nNote: An access review is created for each role selected after completing the process.","Impact":"In order to avoid disruption reviewers who have the authority to revoke roles should be\ntrusted individuals who understand the significance of access reviews. Additionally, the\nprinciple of separation of duties should be applied to ensure that no administrator is\nresponsible for reviewing their own access levels. This will cause additional\nadministrative overhead.\nIf the reviews are configured to automatically revoke highly privileged roles like the\nGlobal Administrator role, then this could result in removing all Global Administrators\nfrom the organization. Care should be taken when configuring this setting especially in\nthe case of break-glass accounts which would be included by association.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity Governance and select Privileged Identity\nManagement\n3. Select Microsoft Entra Roles under Manage\n4. Select Access reviews\n5. Ensure there are access reviews configured for each high privileged roles and\neach meets the criteria laid out below:\no Scope - Everyone\no Status - Active\no Reviewers - Role reviewers should be designated personnel. Preferably\nnot a self-review.\no Mail notifications - Enable\no Reminders - Enable\no Require reason on approval - Enable\no Frequency - Monthly or more frequently.\no Duration (in days) - 4 at most\no Auto apply results to resource - Enable\no If reviewers don't respond - No change\nAny remaining settings are discretionary\n.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity Governance and select Privileged Identity\nManagement\n3. Select Microsoft Entra Roles under Manage\n4. Select Access reviews and click New access review.\no Provide a name and description.\no Set Frequency to Monthly or more frequently.\no Set Duration (in days) to at most 4.\no Set End to Never.\no Set Users scope to All users and groups.\no In Role select these roles: Global Administrator,Exchange\nAdministrator,SharePoint Administrator,Teams\nAdministrator,Security Administrator\no Set Assignment type to All active and eligible assignments.\no Set Reviewers member(s) responsible for this type of review, other than\nself.\n5. Upon completion settings:\no Set Auto apply results to resource to Enable.\no Set If reviewers don't respond to No change.\n6. Advanced settings:\no Set Show recommendations to Enable\no Set Require reason on approval to Enable\no Set Mail notifications to Enable\no Set Reminders to Enable\n7. Click Start to save the review.\nWarning: Care should be taken when configuring the If reviewers don't\nrespond setting for Global Administrator reviews, if misconfigured break-glass\naccounts could automatically have roles revoked. Additionally, reviewers should be\neducated on the purpose of break-glass accounts to prevent accidental manual\nremoval of roles.","Title":"Ensure 'Access reviews' for privileged roles are","ProfileApplicability":"- E5 Level 1","SubSection":"5.3 Identity Governance","DefaultValue":"By default access reviews are not configured.","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"5.1\", \"title\": \"Establish and Maintain an Inventory of Accounts\", \"description\": \"Establish and maintain an inventory of all accounts managed in the enterprise. v8 The inventory must include both user and administrator accounts. The inventory, at - - - a minimum, should contain the person's name, username, start/stop dates, and department. Validate that all active accounts are authorized, on a recurring schedule at a minimum quarterly, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"5.3\", \"title\": \"Disable Dormant Accounts\", \"description\": \"Delete or disable any dormant accounts after a period of 45 days of inactivity, - - - where supported.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-\nmanagement/pim-create-roles-and-resource-roles-review\n2. https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview","Rationale":"Regular review of critical high privileged roles in Entra ID will help identify role drift, or\npotential malicious activity. This will enable the practice and application of \"separation of\nduties\" where even non-privileged users like security auditors can be assigned to review\nassigned roles in an organization. Furthermore, if configured these reviews can enable\na fail-closed mechanism to remove access to the subject if the reviewer does not\nrespond to the review.","Section":"5 Microsoft Entra admin center","RecommendationId":"5.3.3"}
CIS_METADATA_END #>
# Required Services: SharePoint, MgGraph, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Define the roles to check
    $rolesToCheck = @(
        "Global Administrator",
        "Exchange Administrator",
        "SharePoint Administrator",
        "Teams Administrator",
        "Security Administrator"
    )

    # Retrieve access reviews for the specified roles
    # Note: This requires Entra ID P2 or Entra ID Governance license
    try {
        $accessReviews = Get-MgBetaIdentityGovernanceAccessReviewDefinition -All -ErrorAction Stop
    }
    catch {
        # Check if this is a license requirement error
        if ($_.Exception.Message -like "*AadPremiumLicenseRequired*" -or $_.Exception.Message -like "*Entra ID P2*" -or $_.Exception.Message -like "*Governance*" -or $_.Exception.Message -like "*403*" -or $_.Exception.Message -like "*Forbidden*") {
            $resourceResults += @{
                RoleName = "Privileged Roles Access Reviews"
                CurrentValue = "Entra ID P2 or Governance license required"
                IsCompliant = $null
                Details = "This check requires Microsoft Entra ID P2 or Microsoft Entra ID Governance license. Cannot evaluate without Identity Governance access."
            }

            return @{
                status = "Manual"
                status_id = 2
                Details = $resourceResults
                Note = "Requires Entra ID P2 or Governance license for Access Reviews"
            }
        }
        else {
            throw
        }
    }

    foreach ($role in $rolesToCheck) {
        # Filter access reviews for the current role
        $roleReviews = $accessReviews | Where-Object { $_.Role -eq $role }

        # Check compliance for each review
        foreach ($review in $roleReviews) {
            $isCompliant = ($review.Scope -eq "Everyone") -and
                           ($review.Status -eq "Active") -and
                           ($review.Reviewers -ne "Self") -and
                           ($review.MailNotifications -eq $true) -and
                           ($review.Reminders -eq $true) -and
                           ($review.RequireReasonOnApproval -eq $true) -and
                           ($review.Frequency -le 30) -and
                           ($review.DurationInDays -le 4) -and
                           ($review.AutoApplyResults -eq $true) -and
                           ($review.IfReviewersDontRespond -eq "No change")

            $resourceResults += @{
                RoleName = $role
                ReviewId = $review.Id
                CurrentValue = @{
                    Scope = $review.Scope
                    Status = $review.Status
                    Reviewers = $review.Reviewers
                    MailNotifications = $review.MailNotifications
                    Reminders = $review.Reminders
                    RequireReasonOnApproval = $review.RequireReasonOnApproval
                    Frequency = $review.Frequency
                    DurationInDays = $review.DurationInDays
                    AutoApplyResults = $review.AutoApplyResults
                    IfReviewersDontRespond = $review.IfReviewersDontRespond
                }
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
