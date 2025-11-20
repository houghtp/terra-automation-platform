# Control: 6.5.1 - Ensure modern authentication for Exchange Online is
<# CIS_METADATA_START
{"Description": "Modern authentication in Microsoft 365 enables authentication features like multifactor\nauthentication (MFA) using smart cards, certificate-based authentication (CBA), and\nthird-party SAML identity providers. When you enable modern authentication in\nExchange Online, Outlook 2016 and Outlook 2013 use modern authentication to log in\nto Microsoft 365 mailboxes. When you disable modern authentication in Exchange\nOnline, Outlook 2016 and Outlook 2013 use basic authentication to log in to Microsoft\n365 mailboxes.\nWhen users initially configure certain email clients, like Outlook 2013 and Outlook 2016,\nthey may be required to authenticate using enhanced authentication mechanisms, such\nas multifactor authentication. Other Outlook clients that are available in Microsoft 365\n(for example, Outlook Mobile and Outlook for Mac 2016) always use modern\nauthentication to log in to Microsoft 365 mailboxes.", "Impact": "Users of older email clients, such as Outlook 2013 and Outlook 2016, will no longer be\nable to authenticate to Exchange using Basic Authentication, which will necessitate\nmigration to modern authentication practices.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings select Org Settings.\n3. Select Modern authentication.\n4. Verify Turn on modern authentication for Outlook 2013 for Windows\nand later (recommended) is checked.\nTo audit using PowerShell:\n1. Run the Microsoft Exchange Online PowerShell Module.\n2. Connect to Exchange Online using Connect-ExchangeOnline.\n3. Run the following PowerShell command:\nGet-OrganizationConfig | Format-Table -Auto Name, OAuth*\n4. Verify OAuth2ClientProfileEnabled is True.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Settings select Org Settings.\n3. Select Modern authentication.\n4. Check Turn on modern authentication for Outlook 2013 for Windows\nand later (recommended) to enable modern authentication.\nTo remediate using PowerShell:\n1. Run the Microsoft Exchange Online PowerShell Module.\n2. Connect to Exchange Online using Connect-ExchangeOnline.\n3. Run the following PowerShell command:\nSet-OrganizationConfig -OAuth2ClientProfileEnabled $True", "Title": "Ensure modern authentication for Exchange Online is enabled", "ProfileApplicability": "- E3 Level 1\n- E5 Level 1", "SubSection": "6.5 Settings", "DefaultValue": "True", "Level": "L1", "CISControls": "[{\"version\": \"\", \"id\": \"3.10\", \"title\": \"Encrypt Sensitive Data in Transit\", \"description\": \"Encrypt sensitive data in transit. Example implementations can include: - - Transport Layer Security (TLS) and Open Secure Shell (OpenSSH).\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"16.3\", \"title\": \"Require Multi-factor Authentication\", \"description\": \"Require multi-factor authentication for all user accounts, on all systems, - - whether managed onsite or by a third-party provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"16.5\", \"title\": \"Encrypt Transmittal of Username and\", \"description\": \"v7 Authentication Credentials - - Ensure that all account usernames and authentication credentials are transmitted across networks using encrypted channels.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-\nonline/enable-or-disable-modern-authentication-in-exchange-online", "Rationale": "Strong authentication controls, such as the use of multifactor authentication, may be\ncircumvented if basic authentication is used by Exchange Online email clients such as\nOutlook 2016 and Outlook 2013. Enabling modern authentication for Exchange Online\nensures strong authentication mechanisms are used when establishing sessions\nbetween email clients and Exchange Online.", "Section": "6 Exchange admin center", "RecommendationId": "6.5.1"}
CIS_METADATA_END #>
# Required Services: ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original cmdlet to get organization configuration
    $orgConfig = Get-OrganizationConfig
    
    # Process the results and convert to standard format
    foreach ($config in $orgConfig) {
        $isCompliant = $true
        
        # Check if OAuth is enabled (example logic, adjust as needed)
        if ($config.OAuth2ClientProfileEnabled -ne $true) {
            $isCompliant = $false
        }
        
        # Add result to the results array
        $resourceResults += @{
            Name = $config.Name
            OAuth2ClientProfileEnabled = $config.OAuth2ClientProfileEnabled
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
