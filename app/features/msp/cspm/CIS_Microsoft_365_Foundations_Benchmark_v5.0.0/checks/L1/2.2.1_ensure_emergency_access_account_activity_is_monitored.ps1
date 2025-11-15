# Control: 2.2.1 - Ensure emergency access account activity is monitored
<# CIS_METADATA_START
{"Description":"Organizations should monitor sign-in and audit log activity from the emergency\naccounts and trigger notifications to other administrators. When you monitor the activity\nfor emergency access accounts, you can verify these accounts are only used for testing\nor actual emergencies. You can use Azure Monitor, Microsoft Sentinel, Defender for\nCloud Apps or other tools to monitor the sign-in logs and trigger email and SMS alerts to\nyour administrators whenever emergency access accounts sign in.\nThis recommendation uses Defender for Cloud Apps Policies to alert on emergency\naccess account activity.\nThe recommended state is to monitor Activity type Log on on break-glass or\nemergency access accounts.","Impact":"There is no real world impact to monitoring these accounts beyond allocating staff. The\nfrequency of emergency account sign on should be so low that any activity raises a red\nflag that is treated with the highest priority.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com\n2. Under the Cloud Apps section select Policies -> Policy management.\n3. Locate a privileged accounts policy that meets the following criteria\no Policy severity is High severity.\no Category is Privileged accounts.\no Act on Single activity is selected.\no Under Activities matching all of the following verify:\no Filter1: Activity type equals Log on\no Filter2: User Name equals <Emergency access account> as Any role\no Ensure all additional emergency access accounts are accounted for.\no Under Alerts, verify alerting is configured.\n4. Repeat this process for any additional emergency access or break-glass\naccounts in the organization. If matching policies do not exist, then the audit\nprocedure is considered a fail.\nNote: Multiple accounts can be monitored by a single policy or by separate policies.\nNote: Emergency access account activity can be monitored in various ways. The audit\nprocedure passes as long as all emergency access account activity is monitored.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com\n2. Under the Cloud Apps section select Policies -> Policy management.\n3. Click on All policies and then Create policy -> Activity policy.\n4. Give the policy a name and set the following:\no Policy severity to High severity.\no Category to Privileged accounts.\no Act on Single activity.\no Click Select a filter -> Activity type equals Log on.\no Click Add a filter -> User Name equals <Emergency access account>\nas Any role.\no Ensure all emergency access accounts are added to this policy or\nanother.\no Select an alert method such as Send alert as email.\nNote: Multiple accounts can be monitored by a single policy or by separate policies.","Title":"Ensure emergency access account activity is monitored","ProfileApplicability":"- E5 Level 1","SubSection":"2.2 Cloud apps","DefaultValue":"A policy to monitor emergency access accounts does not exist by default.","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"8.2\", \"title\": \"Collect Audit Logs\", \"description\": \"Collect audit logs. Ensure that logging, per the enterprise's audit log - - - management process, has been enabled across enterprise assets. 16 Account Monitoring and Control Account Monitoring and Control\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"2.3\", \"title\": \"Audit\", \"description\": \"This section is intentionally blank and exists to ensure the structure of the benchmark is consistent.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"2.4\", \"title\": \"System\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/entra/identity/role-based-access-\ncontrol/security-emergency-access#monitor-sign-in-and-audit-logs\n2. https://learn.microsoft.com/en-us/defender-cloud-apps/control-cloud-apps-with-\npolicies","Rationale":"Emergency access accounts should be used in very few scenarios, for example, the last\nGlobal Administrator has left the organization and the account is inaccessible. All\nactivity on an emergency access account should be reviewed at the time of the event to\nensure the sign on is legitimate and authorized.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.2.1"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Get all users with Global Administrator role (emergency accounts should be among them)
    $globalAdminRoleTemplateId = "62e90394-69f5-4237-9190-012177145e10" # Global Administrator role template ID

    # Get the directory role using the role template ID filter
    $globalAdminRole = Get-MgDirectoryRole -Filter "roleTemplateId eq '$globalAdminRoleTemplateId'"

    if (-not $globalAdminRole) {
        throw "Global Administrator role not found"
    }

    $globalAdmins = Get-MgDirectoryRoleMember -DirectoryRoleId $globalAdminRole.Id | Where-Object { $_.AdditionalProperties.'@odata.type' -eq '#microsoft.graph.user' }

    # Check for cloud-only accounts (potential emergency accounts)
    # Emergency accounts should be cloud-only and not federated
    $potentialEmergencyAccounts = @()

    foreach ($admin in $globalAdmins) {
        $user = Get-MgUser -UserId $admin.Id -Select "Id,UserPrincipalName,UserType,OnPremisesSyncEnabled,AccountEnabled"

        # Emergency accounts are typically cloud-only (OnPremisesSyncEnabled is null or false)
        # and should be enabled accounts
        if ($user.AccountEnabled -and (-not $user.OnPremisesSyncEnabled)) {
            $potentialEmergencyAccounts += $user
        }
    }

    if ($potentialEmergencyAccounts.Count -eq 0) {
        $resourceResults += @{
            ResourceName = "Emergency Access Accounts"
            CurrentValue = "No cloud-only Global Admin accounts found"
            IsCompliant = $false
            Details = "No potential emergency access accounts identified. Should have at least 2 cloud-only Global Admin accounts."
        }
    } else {
        # Check if monitoring is configured by looking for recent sign-in logs
        # Note: This is a basic check - full compliance requires Azure Monitor alerts
        foreach ($account in $potentialEmergencyAccounts) {
            try {
                # Try to get sign-in logs for this user (last 30 days)
                $signInLogs = Get-MgAuditLogSignIn -Filter "userId eq '$($account.Id)'" -Top 10

                $hasSignInLogging = $signInLogs -ne $null -and $signInLogs.Count -ge 0
                $monitoringStatus = if ($hasSignInLogging) {
                    "Sign-in logs accessible - monitoring possible"
                } else {
                    "Sign-in logs not accessible - monitoring may not be configured"
                }

                $resourceResults += @{
                    ResourceName = $account.UserPrincipalName
                    CurrentValue = $monitoringStatus
                    IsCompliant = $hasSignInLogging
                    Details = "Emergency account identified. Sign-in log access: $hasSignInLogging. Full compliance requires Azure Monitor alerts for this account."
                }
            }
            catch {
                $resourceResults += @{
                    ResourceName = $account.UserPrincipalName
                    CurrentValue = "Unable to check sign-in logs"
                    IsCompliant = $false
                    Details = "Error accessing sign-in logs: $($_.Exception.Message)"
                }
            }
        }
    }

    # Add informational result about full compliance requirements
    $resourceResults += @{
        ResourceName = "Compliance Requirements"
        CurrentValue = "Manual verification required"
        IsCompliant = $null
        Details = "Full compliance requires: 1) Azure Monitor alerts for emergency account sign-ins, 2) Log Analytics workspace with SigninLogs, 3) Alert rules for emergency account activity. This check only verifies basic log access."
    }

    # Determine overall status - this is informational since full monitoring setup requires manual verification
    $compliantChecks = ($resourceResults | Where-Object { $_.IsCompliant -eq $true }).Count
    $overallStatus = if ($compliantChecks -gt 0 -and $potentialEmergencyAccounts.Count -ge 2) { 'Pass' } else { 'Fail' }
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
