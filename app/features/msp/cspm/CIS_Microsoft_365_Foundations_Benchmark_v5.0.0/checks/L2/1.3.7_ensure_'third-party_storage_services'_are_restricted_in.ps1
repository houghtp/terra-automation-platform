# Control: 1.3.7 - Ensure 'third-party storage services' are restricted in
<# CIS_METADATA_START
{"Description": "Third-party storage can be enabled for users in Microsoft 365, allowing them to store\nand share documents using services such as Dropbox, alongside OneDrive and team\nsites.\nEnsure Microsoft 365 on the web third-party storage services are restricted.", "Impact": "Impact associated with this change is highly dependent upon current practices in the\ntenant. If users do not use other storage providers, then minimal impact is likely.\nHowever, if users do regularly utilize providers outside of the tenant this will affect their\nability to continue to do so.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com\n2. Go to Settings > Org Settings > Services > Microsoft 365 on the web\n3. Ensure Let users open files stored in third-party storage services\nin Microsoft 365 on the web is not checked.\nTo audit using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Application.Read.All\".\n2. Run the following script:\n$SP = Get-MgServicePrincipal -Filter \"appId eq 'c1f33bc0-bdb4-4248-ba9b-\n096807ddb43e'\"\nif ((-not $SP) -or $SP.AccountEnabled) {\nWrite-Host \"Audit Result: ** FAIL **\"\n} else {\nWrite-Host \"Audit Result: ** PASS **\"\n}\n3. To pass AccountEnabled must be False.\nNote: The check will also fail if the Service Principal does not exist as users will still be\nable to open files stored in third-party storage services in Microsoft 365 on the web.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com\n2. Go to Settings > Org Settings > Services > Microsoft 365 on the web\n3. Uncheck Let users open files stored in third-party storage\nservices in Microsoft 365 on the web\nTo remediate using PowerShell:\n1. Connect to Microsoft Graph using Connect-MgGraph -Scopes\n\"Application.ReadWrite.All\"\n2. Run the following script:\n$SP = Get-MgServicePrincipal -Filter \"appId eq 'c1f33bc0-bdb4-4248-ba9b-\n096807ddb43e'\"\n# If the service principal doesn't exist then create it first.\nif (-not $SP) {\n$SP = New-MgServicePrincipal -AppId \"c1f33bc0-bdb4-4248-ba9b-\n096807ddb43e\"\n}\nUpdate-MgServicePrincipal -ServicePrincipalId $SP.Id -AccountEnabled:$false", "Title": "Ensure 'third-party storage services' are restricted in 'Microsoft 365 on the web'", "ProfileApplicability": "- E3 Level 2\n- E5 Level 2", "SubSection": "1.3 Settings", "DefaultValue": "Enabled - Users are able to open files stored in third-party storage services", "Level": "L2", "CISControls": "[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.4\", \"title\": \"Only Allow Access to Authorized Cloud Storage or\", \"description\": \"v7 Email Providers - - Only allow access to authorized cloud storage or email providers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/microsoft-365/admin/setup/set-up-file-storage-\nand-sharing?view=o365-worldwide#enable-or-disable-third-party-storage-\nservices", "Rationale": "By using external storage services an organization may increase the risk of data\nbreaches and unauthorized access to confidential information. Additionally, third-party\nservices may not adhere to the same security standards as the organization, making it\ndifficult to maintain data privacy and security.", "Section": "1 Microsoft 365 admin center", "RecommendationId": "1.3.7"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve the Service Principal
    $SP = Get-MgBetaServicePrincipal -Filter "appId eq 'c1f33bc0-bdb4-4248-ba9b-096807ddb43e'"
    
    # Check compliance
    $isCompliant = $false
    if ($SP -and -not $SP.AccountEnabled) {
        $isCompliant = $true
    }
    
    # Add result to the results array
    $resourceResults += @{
        ResourceName = "Service Principal"
        IsCompliant = $isCompliant
        Details = if ($isCompliant) { "PASS" } else { "FAIL" }
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
