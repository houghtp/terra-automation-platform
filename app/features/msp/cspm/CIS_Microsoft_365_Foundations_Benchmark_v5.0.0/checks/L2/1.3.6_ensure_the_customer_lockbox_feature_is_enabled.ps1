# Control: 1.3.6 - Ensure the customer lockbox feature is enabled
<# CIS_METADATA_START
{"Description":"Customer Lockbox is a security feature that provides an additional layer of control and\ntransparency to customer data in Microsoft 365. It offers an approval process for\nMicrosoft support personnel to access organization data and creates an audited trail to\nmeet compliance requirements.","Impact":"Administrators will need to grant Microsoft access to the tenant environment prior to a\nMicrosoft engineer accessing the environment for support or troubleshooting.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings then select Org settings.\n3. Select Security & privacy tab.\n4. Click Customer lockbox.\n5. Ensure the box labeled Require approval for all data access requests\nis checked.\nTo audit using SecureScore:\n1. Navigate to the Microsoft 365 SecureScore portal.\nhttps://securescore.microsoft.com\n2. Search for Turn on customer lockbox feature under Improvement\nactions.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-OrganizationConfig | Select-Object CustomerLockBoxEnabled\n3. Verify the value is set to True.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings then select Org settings.\n3. Select Security & privacy tab.\n4. Click Customer lockbox.\n5. Check the box Require approval for all data access requests.\n6. Click Save.\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-OrganizationConfig -CustomerLockBoxEnabled $true","Title":"Ensure the customer lockbox feature is enabled","ProfileApplicability":"- E5 Level 2","SubSection":"1.3 Settings","DefaultValue":"Require approval for all data access requests - Unchecked\nCustomerLockboxEnabled - False","Level":"L2","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/azure/security/fundamentals/customer-lockbox-\noverview","Rationale":"Enabling this feature protects organizational data against data spillage and exfiltration.","Section":"1 Microsoft 365 admin center","RecommendationId":"1.3.6"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    $orgConfig = Get-OrganizationConfig | Select-Object CustomerLockBoxEnabled
    $isCompliant = $orgConfig.CustomerLockBoxEnabled -eq $true
    $resourceResults += @{
        Name = "Customer Lockbox"
        IsCompliant = $isCompliant
        Details = "Customer Lockbox is " + ($orgConfig.CustomerLockBoxEnabled ? "enabled" : "disabled")
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
