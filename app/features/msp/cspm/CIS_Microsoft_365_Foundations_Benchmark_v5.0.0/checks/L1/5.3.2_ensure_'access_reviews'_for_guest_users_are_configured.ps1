# Control: 5.3.2 - Ensure 'Access reviews' for Guest Users are configured
<# CIS_METADATA_START
{"Description":"Access reviews enable administrators to establish an efficient automated process for\nreviewing group memberships, access to enterprise applications, and role assignments.\nThese reviews can be scheduled to recur regularly, with flexible options for delegating\nthe task of reviewing membership to different members of the organization.\nEnsure Access reviews for Guest Users are configured to be performed no less\nfrequently than monthly.","Impact":"Access reviews that are ignored may cause guest users to lose access to resources\ntemporarily.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity Governance and select Access reviews\n3. Inspect the access reviews, and ensure an access review is created with the\nfollowing criteria:\no Overview: Scope is set to Guest users only and status is Active\no Reviewers: Ensure appropriate reviewer(s) are designated.\no Settings > General: Mail notifications and Reminders are set to\nEnable\no Reviewers: Require reason on approval is set to Enable\no Scheduling: Frequency is Monthly or more frequent.\no When completed: Auto apply results to resource is set to Enable\no When completed: If reviewers don't respond is set to Remove\naccess\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scope\nAccessReview.Read.All\n2. Run the following script to output a list of Access Reviews that target only Guest\nUsers.\n$Uri =\n'https://graph.microsoft.com/v1.0/identityGovernance/accessReviews/definition\ns'\n$AccessReviews = Invoke-MgGraphRequest -Uri $Uri -Method Get |\nSelect-Object -ExpandProperty Value\n$AccessReviewReport = [System.Collections.Generic.List[Object]]::new()\n$GuestReviews = $AccessReviews |\nWhere-Object { $_.scope.query -match \"userType eq 'Guest'\" -or\n$_.scope.principalscopes.query -match \"userType eq 'Guest'\" }\nforeach ($review in $GuestReviews) {\n$value = $review.settings\n$obj = [PSCustomObject]@{\nName = $review.DisplayName\nStatus = $review.Status\nmailNotificationsEnabled = $value.mailNotificationsEnabled\nReminders = $value.reminderNotificationsEnabled\njustificationRequiredOnApproval =\n$value.justificationRequiredOnApproval\nFrequency = $value.recurrence.pattern.type\nautoApplyDecisionsEnabled = $value.autoApplyDecisionsEnabled\ndefaultDecision = $value.defaultDecision\n}\n$AccessReviewReport.Add($obj)\n}\n$AccessReviewReport\n3. Review the output, if nothing returns then the audit fails.\n4. Only one access review meeting all parameters is required for an overall pass. A\npassing access review will meet the below parameters:\nName : Review guest access across Microsoft 365\ngroups\nStatus : InProgress\nmailNotificationsEnabled : True\nReminders : True\njustificationRequiredOnApproval : True\nFrequency : absoluteMonthly or weekly\nautoApplyDecisionsEnabled : True\ndefaultDecision : Deny\nNote: Frequency can be absoluteMonthly or weekly.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/\n2. Click to expand Identity Governance and select Access reviews\n3. Click New access review.\n4. Select what to review choose Teams + Groups.\n5. Review Scope set to All Microsoft 365 groups with guest users, do not\nexclude groups.\n6. Scope set to Guest users only then click Next: Reviews.\n7. Select reviewers an appropriate user that is NOT the guest user themselves.\n8. Duration (in days) at most 3.\n9. Review recurrence is Monthly or more frequent.\n10. End is set to Never, then click Next: Settings.\n11. Check Auto apply results to resource.\n12. Set If reviewers don't respond to Remove access.\n13. Check the following: Justification required, E-mail notifications,\nReminders.\n14. Click Next: Review + Create and finally click Create.","Title":"Ensure 'Access reviews' for Guest Users are configured","ProfileApplicability":"- E5 Level 1","SubSection":"5.3 Identity Governance","DefaultValue":"By default access reviews are not configured.","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"5.1\", \"title\": \"Establish and Maintain an Inventory of Accounts\", \"description\": \"Establish and maintain an inventory of all accounts managed in the enterprise. v8 The inventory must include both user and administrator accounts. The inventory, at - - - a minimum, should contain the person's name, username, start/stop dates, and department. Validate that all active accounts are authorized, on a recurring schedule at a minimum quarterly, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"5.3\", \"title\": \"Disable Dormant Accounts\", \"description\": \"Delete or disable any dormant accounts after a period of 45 days of inactivity, - - - where supported.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview\n2. https://learn.microsoft.com/en-us/entra/id-governance/create-access-review","Rationale":"Access to groups and applications for guests can change over time. If a guest user's\naccess to a particular folder goes unnoticed, they may unintentionally gain access to\nsensitive data if a member adds new files or data to the folder or application. Access\nreviews can help reduce the risks associated with outdated assignments by requiring a\nmember of the organization to conduct the reviews. Furthermore, these reviews can\nenable a fail-closed mechanism to remove access to the subject if the reviewer does not\nrespond to the review.","Section":"5 Microsoft Entra admin center","RecommendationId":"5.3.2"}
CIS_METADATA_END #>
# Required Services: SharePoint, MgGraph, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Adapted script logic from the original script
    # Note: This requires Entra ID P2 or Entra ID Governance license
    $Uri = 'https://graph.microsoft.com/v1.0/identityGovernance/accessReviews/definitions'

    try {
        $AccessReviews = Invoke-MgGraphRequest -Uri $Uri -Method Get -ErrorAction Stop | Select-Object -ExpandProperty Value
    }
    catch {
        # Check if this is a license requirement error
        if ($_.Exception.Message -like "*AadPremiumLicenseRequired*" -or $_.Exception.Message -like "*Entra ID P2*" -or $_.Exception.Message -like "*Governance*" -or $_.Exception.Message -like "*403*" -or $_.Exception.Message -like "*Forbidden*") {
            $resourceResults += @{
                Name = "Guest User Access Reviews"
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

    $GuestReviews = $AccessReviews | Where-Object {
        $_.scope.query -match "userType eq 'Guest'" -or
        $_.scope.principalscopes.query -match "userType eq 'Guest'"
    }

    foreach ($review in $GuestReviews) {
        $value = $review.settings
        $obj = [PSCustomObject]@{
            Name = $review.DisplayName
            mailNotificationsEnabled = $value.mailNotificationsEnabled
            justificationRequiredOnApproval = $value.justificationRequiredOnApproval
            autoApplyDecisionsEnabled = $value.autoApplyDecisionsEnabled
            defaultDecision = $value.defaultDecision
            IsCompliant = ($value.mailNotificationsEnabled -eq $true) -and
                          ($value.justificationRequiredOnApproval -eq $true) -and
                          ($value.autoApplyDecisionsEnabled -eq $true) -and
                          ($value.defaultDecision -eq 'Deny')
        }
        $resourceResults += $obj
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
