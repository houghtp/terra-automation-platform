# Control: 3.2.1 - Ensure DLP policies are enabled
<# CIS_METADATA_START
{"Description":"Data Loss Prevention (DLP) policies allow Exchange Online and SharePoint Online\ncontent to be scanned for specific types of data like social security numbers, credit card\nnumbers, or passwords.","Impact":"Enabling a Teams DLP policy will allow sensitive data in Exchange Online and\nSharePoint Online to be detected or blocked. Always ensure to follow appropriate\nprocedures during testing and implementation of DLP policies based on organizational\nstandards.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Purview https://purview.microsoft.com/\n2. Click Solutions > Data loss prevention and then Policies.\n3. Verify that the organization is using policies applicable to the types data that is in\ntheir interest to protect.\n4. Verify the policies are On.\nNote: The types of policies an organization should implement to protect information are\nspecific to their industry. However, certain types of information, such as credit card\nnumbers, social security numbers, and certain personally identifiable information (PII),\nare universally important to safeguard across all industries.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Purview https://purview.microsoft.com/\n2. Click Solutions > Data loss prevention then Policies.\n3. Click Create policy.\n4. Create a policy that is specific to the types of data the organization wishes to\nprotect.","Title":"Ensure DLP policies are enabled","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"3.2 Data loss protection","DefaultValue":"","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.1\", \"title\": \"Establish and Maintain a Data Management Process\", \"description\": \"Establish and maintain a data management process. In the process, address v8 data sensitivity, data owner, handling of data, data retention limits, and disposal - - - requirements, based on sensitivity and retention standards for the enterprise. Review and update documentation annually, or when significant enterprise changes occur that could impact this Safeguard. 13 Data Protection Data Protection\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"14.7\", \"title\": \"Enforce Access Control to Data through Automated\", \"description\": \"v7 Tools - Use an automated tool, such as host-based Data Loss Prevention, to enforce access controls to data even when data is copied off a system.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp?view=o365-\nworldwide","Rationale":"Enabling DLP policies alerts users and administrators that specific types of data should\nnot be exposed, helping to protect the data from accidental exposure.","Section":"3 Microsoft Purview","RecommendationId":"3.2.1"}
CIS_METADATA_END #>
# Required Services: SecurityCompliance
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve DLP policies
    $dlpPolicies = Get-DlpCompliancePolicy

    foreach ($policy in $dlpPolicies) {
        $isCompliant = $policy.Mode -eq "Enforce"
        
        $resourceResults += @{
            PolicyName   = $policy.DisplayName
            CurrentValue = $policy.Mode
            IsCompliant  = $isCompliant
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
