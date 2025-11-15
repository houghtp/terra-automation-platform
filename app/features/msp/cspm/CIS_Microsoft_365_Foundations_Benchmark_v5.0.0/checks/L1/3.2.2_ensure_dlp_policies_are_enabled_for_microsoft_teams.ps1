# Control: 3.2.2 - Ensure DLP policies are enabled for Microsoft Teams
<# CIS_METADATA_START
{"Description":"The default Teams Data Loss Prevention (DLP) policy rule in Microsoft 365 is a\npreconfigured rule that is automatically applied to all Teams conversations and\nchannels. The default rule helps prevent accidental sharing of sensitive information by\ndetecting and blocking certain types of content that are deemed sensitive or\ninappropriate by the organization.\nBy default, the rule includes a check for the sensitive info type Credit Card Number\nwhich is pre-defined by Microsoft.","Impact":"End-users may be prevented from sharing certain types of content, which may require\nthem to adjust their behavior or seek permission from administrators to share specific\ncontent. Administrators may receive requests from end-users for permission to share\ncertain types of content or to modify the policy to better fit the needs of their teams.","Audit":"To audit the using the UI:\n1. Navigate to Microsoft Purview compliance portal\nhttps://purview.microsoft.com/\n2. Under Solutions select Data loss prevention then Policies.\n3. Locate the Default policy for Teams.\n4. Verify the Status is On.\n5. Verify Locations include Teams chat and channel messages - All\naccounts.\n6. Verify Policy settings incudes the Default Teams DLP policy rule or one\nspecific to the organization.\nNote: If there is not a default policy for teams inspect existing policies starting with step\n4. DLP rules are specific to the organization and each organization should take steps to\nprotect the data that matters to them. The default teams DLP rule will only alert on\nCredit Card matches.\nTo audit using PowerShell:\n1. Connect to the Security & Compliance PowerShell using Connect-IPPSSession.\n2. Run the following to return policies that include Teams chat and channel\nmessages:\n$DlpPolicy = Get-DlpCompliancePolicy\n$DlpPolicy | Where-Object {$_.Workload -match \"Teams\"} |\nft Name,Mode,TeamsLocation*\n3. If nothing returns, then there are no policies that include Teams and remediation\nis required.\n4. For any returned policy verify Mode is set to Enable.\n5. Verify TeamsLocation includes All.\n6. Verify TeamsLocationException includes only permitted exceptions.\nNote: Some tenants may not have a default policy for teams as Microsoft started\ncreating these by default at a particular point in time. In this case a new policy will have\nto be created that includes a rule to protect data important to the organization such as\ncredit cards and PII.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Purview compliance portal\nhttps://purview.microsoft.com/\n2. Under Solutions select Data loss prevention then Policies.\n3. Click Policies tab.\n4. Check Default policy for Teams then click Edit policy.\n5. The edit policy window will appear click Next\n6. At the Choose locations to apply the policy page, turn the status toggle\nto On for Teams chat and channel messages location and then click Next.\n7. On Customized advanced DLP rules page, ensure the Default Teams DLP\npolicy rule Status is On and click Next.\n8. On the Policy mode page, select the radial for Turn it on right away and\nclick Next.\n9. Review all the settings for the created policy on the Review your policy and\ncreate it page, and then click submit.\n10. Once the policy has been successfully submitted click Done.\nNote: Some tenants may not have a default policy for teams as Microsoft started\ncreating these by default at a particular point in time. In this case a new policy will have\nto be created that includes a rule to protect data important to the organization such as\ncredit cards and PII.","Title":"Ensure DLP policies are enabled for Microsoft Teams","ProfileApplicability":"- E5 Level 1","SubSection":"3.2 Data loss protection","DefaultValue":"Enabled (On)","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.1\", \"title\": \"Establish and Maintain a Data Management Process\", \"description\": \"Establish and maintain a data management process. In the process, address v8 data sensitivity, data owner, handling of data, data retention limits, and disposal - - - requirements, based on sensitivity and retention standards for the enterprise. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard. 13 Data Protection Data Protection\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"14.7\", \"title\": \"Enforce Access Control to Data through Automated\", \"description\": \"v7 Tools - Use an automated tool, such as host-based Data Loss Prevention, to enforce access controls to data even when data is copied off a system.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"3.3\", \"title\": \"Information Protection\", \"description\": \"\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/exchange/connect-to-scc-\npowershell?view=exchange-ps\n2. https://learn.microsoft.com/en-us/purview/dlp-teams-default-policy\n3. https://learn.microsoft.com/en-us/powershell/module/exchange/connect-\nippssession?view=exchange-ps","Rationale":"Enabling the default Teams DLP policy rule in Microsoft 365 helps protect an\norganization's sensitive information by preventing accidental sharing or leakage Credit\nCard information in Teams conversations and channels.\nDLP rules are not one size fits all, but at a minimum something should be defined. The\norganization should identify sensitive information important to them and seek to\nintercept it using DLP.","Section":"3 Microsoft Purview","RecommendationId":"3.2.2"}
CIS_METADATA_END #>
# Required Services: SecurityCompliance, Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve DLP Compliance Policies
    $DlpPolicy = Get-DlpCompliancePolicy
    
    # Filter policies for Teams workload
    $teamsDlpPolicies = $DlpPolicy | Where-Object { $_.Workload -match "Teams" }
    
    # Process each policy and determine compliance
    foreach ($policy in $teamsDlpPolicies) {
        $isCompliant = $policy.Mode -ne 'Disabled' -and $policy.TeamsLocation -ne $null
        $resourceResults += @{
            Name = $policy.Name
            Mode = $policy.Mode
            TeamsLocation = $policy.TeamsLocation
            IsCompliant = $isCompliant
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
