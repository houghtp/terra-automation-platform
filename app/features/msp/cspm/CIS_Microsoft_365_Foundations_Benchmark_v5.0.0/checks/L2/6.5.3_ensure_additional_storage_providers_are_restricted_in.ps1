# Control: 6.5.3 - Ensure additional storage providers are restricted in
<# CIS_METADATA_START
{"Description":"This setting allows users to open certain external files while working in Outlook on the\nweb. If allowed, keep in mind that Microsoft doesn't control the use terms or privacy\npolicies of those third-party services.\nEnsure AdditionalStorageProvidersAvailable are restricted.","Impact":"The impact associated with this change is highly dependent upon current practices in\nthe tenant. If users do not use other storage providers, then minimal impact is likely.\nHowever, if users do regularly utilize providers outside of the tenant this will affect their\nability to continue to do so.","Audit":"To audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-OwaMailboxPolicy | Format-Table Name, AdditionalStorageProvidersAvailable\n3. Verify that the value returned is False.","Remediation":"To remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-OwaMailboxPolicy -Identity OwaMailboxPolicy-Default -\nAdditionalStorageProvidersAvailable $false","Title":"Ensure additional storage providers are restricted in","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"6.5 Settings","DefaultValue":"Additional Storage Providers - True","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.4\", \"title\": \"Only Allow Access to Authorized Cloud Storage or\", \"description\": \"v7 Email Providers - - Only allow access to authorized cloud storage or email providers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/powershell/module/exchange/set-\nowamailboxpolicy?view=exchange-ps\n2. https://support.microsoft.com/en-us/topic/3rd-party-cloud-storage-services-\nsupported-by-office-apps-fce12782-eccc-4cf5-8f4b-d1ebec513f72","Rationale":"By default, additional storage providers are allowed in Office on the Web (such as Box,\nDropbox, Facebook, Google Drive, OneDrive Personal, etc.). This could lead to\ninformation leakage and additional risk of infection from organizational non-trusted\nstorage providers. Restricting this will inherently reduce risk as it will narrow\nopportunities for infection and data leakage.","Section":"6 Exchange admin center","RecommendationId":"6.5.3"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve OWA Mailbox Policies
    $owaMailboxPolicies = Get-OwaMailboxPolicy | Select-Object Name, AdditionalStorageProvidersAvailable
    
    # Process each policy and determine compliance
    foreach ($policy in $owaMailboxPolicies) {
        $isCompliant = -not $policy.AdditionalStorageProvidersAvailable
        $resourceResults += @{
            Name = $policy.Name
            IsCompliant = $isCompliant
            AdditionalStorageProvidersAvailable = $policy.AdditionalStorageProvidersAvailable
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
