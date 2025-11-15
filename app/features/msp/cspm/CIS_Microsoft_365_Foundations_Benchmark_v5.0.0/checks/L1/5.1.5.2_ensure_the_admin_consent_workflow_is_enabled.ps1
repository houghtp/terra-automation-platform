# Control: 5.1.5.2 - Ensure the admin consent workflow is enabled
<# CIS_METADATA_START
{"RecommendationId":"5.1.5.2","Level":"L1","Title":"Ensure the admin consent workflow is enabled","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"The admin consent workflow gives admins a secure way to grant access to applications\nthat require admin approval. When a user tries to access an application but is unable to\nprovide consent, they can send a request for admin approval. The request is sent via\nemail to admins who have been designated as reviewers. A reviewer takes action on\nthe request, and the user is notified of the action.","Rationale":"The admin consent workflow (Preview) gives admins a secure way to grant access to\napplications that require admin approval. When a user tries to access an application but\nis unable to provide consent, they can send a request for admin approval. The request\nis sent via email to admins who have been designated as reviewers. A reviewer acts on\nthe request, and the user is notified of the action.","Impact":"To approve requests, a reviewer must be a global administrator, cloud application\nadministrator, or application administrator. The reviewer must already have one of these\nadmin roles assigned; simply designating them as a reviewer doesn't elevate their\nprivileges.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Applications select Enterprise applications.\n3. Under Security select Consent and permissions.\n4. Under Manage select Admin consent settings.\n5. Verify that Users can request admin consent to apps they are unable\nto consent to is set to Yes.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Policy.Read.All\"\n2. Run the following command:\nGet-MgPolicyAdminConsentRequestPolicy |\nfl IsEnabled,NotifyReviewers,RemindersEnabled\n3. Ensure IsEnabled is set to True.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Applications select Enterprise applications.\n3. Under Security select Consent and permissions.\n4. Under Manage select Admin consent settings.\n5. Set Users can request admin consent to apps they are unable to\nconsent to to Yes under Admin consent requests.\n6. Under the Reviewers choose the Roles and Groups that will review user\ngenerated app consent requests.\n7. Set Selected users will receive email notifications for requests to\nYes\n8. Select Save at the top of the window.","DefaultValue":"- Users can request admin consent to apps they are unable to\nconsent to: No\n- Selected users to review admin consent requests: None\n- Selected users will receive email notifications for requests: Yes\n- Selected users will receive request expiration reminders: Yes\n- Consent request expires after (days): 30","References":"1. https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-admin-\nconsent-workflow","CISControls":"[{\"version\": \"\", \"id\": \"2.5\", \"title\": \"Allowlist Authorized Software\", \"description\": \"v8 Use technical controls, such as application allowlisting, to ensure that only - - authorized software can execute or be accessed. Reassess bi-annually, or more frequently.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"18.3\", \"title\": \"Verify That Acquired Software is Still Supported\", \"description\": \"v7 Verify that the version of all software acquired from outside your organization - - is still supported by the developer or appropriately hardened based on developer security recommendations. 5.1.6 External Identities\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the admin consent request policy
    $adminConsentPolicy = Get-MgBetaPolicyAdminConsentRequestPolicy

    # Check if the admin consent workflow is enabled
    $isEnabled = $adminConsentPolicy.IsEnabled
    $notifyReviewers = $adminConsentPolicy.NotifyReviewers
    $remindersEnabled = $adminConsentPolicy.RemindersEnabled

    # Add the result to the results array
    $resourceResults += @{
        PolicyName = "Admin Consent Request Policy"
        IsEnabled = $isEnabled
        NotifyReviewers = $notifyReviewers
        RemindersEnabled = $remindersEnabled
        IsCompliant = $isEnabled -eq $true
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
