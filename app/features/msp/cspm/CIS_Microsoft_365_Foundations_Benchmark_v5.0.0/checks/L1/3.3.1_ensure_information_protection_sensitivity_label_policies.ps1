# Control: 3.3.1 - Ensure Information Protection sensitivity label policies
<# CIS_METADATA_START
{"Description":"Sensitivity labels enable organizations to classify and label content across Microsoft 365\nbased on its sensitivity and business impact. These labels can be applied manually by\nusers or automatically based on the content. When applied, labels can automatically\nencrypt content, provide \"Confidential\" watermarks, restrict access, and offer various\ndata protection features.\nLabels can be scoped to data assets and containers:\n- Files & other data assets in Microsoft 365, Fabric, Azure, AWS and other\nplatforms\n- Email messages sent from all versions of Outlook\n- Meeting calendar events and schedules in Outlook and Teams\n- Teams, Microsoft 365 Groups and SharePoint sites","Impact":"Encryption configurations (control access, DKE, BYOK) in the individual labels may\nimpact users' ability to access site documents and information. Careful consideration of\nthe individual sensitivity label configurations should be exercised prior to applying an\nauto labeling policy, publishing policy, sensitivity label configuration, or PowerShell\nbased label settings to SharePoint sites.\nAdditionally, when updating or deleting Sensitivity Labels, an assessment of the\npotential impacts should be conducted to avoid unintended consequences. If tenants\nare configured for sharing with guests or external domains and Sensitivity Labels have\nencryption applied, this can affect the ability to share documents via email stored in\nSharePoint. Some recipients may be unable to open the document depending on their\nemail client, which could trigger Purview Advanced Encryptions and OME flows based\non the recipient type and the cloud license from which the email is sent (e.g.,\ngovernment clouds vs. commercial clouds).","Audit":"To audit using the UI:\n1. Navigate to Microsoft Purview compliance portal\nhttps://purview.microsoft.com/\n2. Select Information protection > Policies > Label publishing policies.\n3. Ensure that a Label policy exists and is published according to the organization's\ninformation protection needs.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Purview compliance portal\nhttps://purview.microsoft.com/\n2. Select Information protection > Sensitivity labels.\n3. Click Create a label to create a label.\n4. Click Publish labels and select any newly created labels to publish according\nto the organization's information protection needs.","Title":"Ensure Information Protection sensitivity label policies","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"3.3 Information Protection","DefaultValue":"The \"Global sensitivity label policy\" exists by default.","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"3.7\", \"title\": \"Establish and Maintain a Data Classification Scheme\", \"description\": \"Establish and maintain an overall data classification scheme for the enterprise. v8 Enterprises may use labels, such as \\\"Sensitive,\\\" \\\"Confidential,\\\" and \\\"Public,\\\" and - - classify their data according to those labels. Review and update the classification scheme annually, or when significant enterprise changes occur that could impact this Safeguard.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"14.6\", \"title\": \"Protect Information through Access Control Lists\", \"description\": \"Protect all information stored on systems with file system, network share, claims, application, or database specific access control lists. These controls will enforce the - - - principle that only authorized individuals should have access to the information based on their need to access the information as a part of their responsibilities. 4 Microsoft Intune admin center This section includes settings specific to hardening the Microsoft 365 tenant itself through Intune settings. CIS has other platform specific benchmarks for Intune which are intended to harden endpoints through Endpoint Manager (Microsoft Intune admin center). Those are developed in the following WorkBench communities: CIS Microsoft Intune for Windows: https://workbench.cisecurity.org/communities/116 CIS Intune Apple iOS and iPadOS Benchmarks: https://workbench.cisecurity.org/communities/179\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/purview/sensitivity-labels\n2. https://learn.microsoft.com/en-us/purview/create-sensitivity-labels","Rationale":"Consistent usage of sensitivity labels can help reduce the risk of data loss or exposure\nand enable more effective incident response if a breach does occur. They can also help\norganizations comply with regulatory requirements and provide visibility and control over\nsensitive information.","Section":"3 Microsoft Purview","RecommendationId":"3.3.1"}
CIS_METADATA_END #>
# Required Services: SecurityCompliance
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve sensitivity label policies
    $labelPolicies = Get-LabelPolicy

    foreach ($policy in $labelPolicies) {
        # Check if the policy is published
        $isPublished = $policy.Published -eq $true
        
        $resourceResults += @{
            PolicyName   = $policy.DisplayName
            IsPublished  = $isPublished
            IsCompliant  = $isPublished
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
