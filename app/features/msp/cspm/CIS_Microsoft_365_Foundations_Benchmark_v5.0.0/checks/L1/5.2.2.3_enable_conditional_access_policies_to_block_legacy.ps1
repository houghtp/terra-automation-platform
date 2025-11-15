# Control: 5.2.2.3 - Enable Conditional Access policies to block legacy
<# CIS_METADATA_START
{"RecommendationId":"5.2.2.3","Level":"L1","Title":"Enable Conditional Access policies to block legacy authentication","Section":"5 Microsoft Entra admin center","SubSection":"5.2 Protection","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Entra ID supports the most widely used authentication and authorization protocols\nincluding legacy authentication. This authentication pattern includes basic\nauthentication, a widely used industry-standard method for collecting username and\npassword information.\nThe following messaging protocols support legacy authentication:\n- Authenticated SMTP - Used to send authenticated email messages.\n- Autodiscover - Used by Outlook and EAS clients to find and connect to\nmailboxes in Exchange Online.\n- Exchange ActiveSync (EAS) - Used to connect to mailboxes in Exchange Online.\n- Exchange Online PowerShell - Used to connect to Exchange Online with remote\nPowerShell. If you block Basic authentication for Exchange Online PowerShell,\nyou need to use the Exchange Online PowerShell Module to connect. For\ninstructions, see Connect to Exchange Online PowerShell using multifactor\nauthentication.\n- Exchange Web Services (EWS) - A programming interface that's used by\nOutlook, Outlook for Mac, and third-party apps.\n- IMAP4 - Used by IMAP email clients.\n- MAPI over HTTP (MAPI/HTTP) - Primary mailbox access protocol used by\nOutlook 2010 SP2 and later.\n- Offline Address Book (OAB) - A copy of address list collections that are\ndownloaded and used by Outlook.\n- Outlook Anywhere (RPC over HTTP) - Legacy mailbox access protocol\nsupported by all current Outlook versions.\n- POP3 - Used by POP email clients.\n- Reporting Web Services - Used to retrieve report data in Exchange Online.\n- Universal Outlook - Used by the Mail and Calendar app for Windows 10.\n- Other clients - Other protocols identified as utilizing legacy authentication.","Rationale":"Legacy authentication protocols do not support multi-factor authentication. These\nprotocols are often used by attackers because of this deficiency. Blocking legacy\nauthentication makes it harder for attackers to gain access.\nNote: Basic authentication is now disabled in all tenants. Before December 31 2022,\nyou could re-enable the affected protocols if users and apps in your tenant couldn't\nconnect. Now no one (you or Microsoft support) can re-enable Basic authentication in\nyour tenant.","Impact":"Enabling this setting will prevent users from connecting with older versions of Office,\nActiveSync or using protocols like IMAP, POP or SMTP and may require upgrades to\nolder versions of Office, and use of mobile mail clients that support modern\nauthentication.\nThis will also cause multifunction devices such as printers from using scan to e-mail\nfunction if they are using a legacy authentication method. Microsoft has mail flow best\npractices in the link below which can be used to configure a MFP to work with modern\nauthentication:\nhttps://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/how-to-set-up-a-\nmultifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365","Audit":"To audit using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Ensure that a policy exists with the following criteria and is set to On:\no Under Users verify All users is included.\no Ensure that only documented user exclusions exist and that they are\nreviewed annually.\no Under Target resources verify All resources (formerly 'All\ncloud apps') is selected.\no Ensure that only documented resource exclusions exist and that they are\nreviewed annually.\no Under Conditions select Client apps then verify Exchange\nActiveSync clients and Other clients is checked.\no Under Grant verify Block access is selected.\n4. Ensure Enable policy is set to On.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","Remediation":"To remediate using the UI:\n1. Navigate to the Microsoft Entra admin center https://entra.microsoft.com.\n2. Click expand Protection > Conditional Access select Policies.\n3. Create a new policy by selecting New policy.\no Under Users include All users.\no Under Target resources include All resources (formerly 'All\ncloud apps').\no Under Conditions select Client apps and check the boxes for\nExchange ActiveSync clients and Other clients.\no Under Grant select Block Access.\no Click Select.\n4. Set the policy On and click Create.\nNote: Break-glass accounts should be excluded from all Conditional Access policies.","DefaultValue":"Basic authentication is disabled by default as of January 2023.","References":"1. https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-\nonline/disable-basic-authentication-in-exchange-online\n2. https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/how-to-set-\nup-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-\noffice-365\n3. https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-\nonline/deprecation-of-basic-authentication-exchange-online","CISControls":"[{\"version\": \"\", \"id\": \"4.8\", \"title\": \"Uninstall or Disable Unnecessary Services on\", \"description\": \"Enterprise Assets and Software Uninstall or disable unnecessary services on enterprise assets and software, - - such as an unused file sharing service, web application module, or service function.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"9.2\", \"title\": \"Ensure Only Approved Ports, Protocols and Services\", \"description\": \"v7 Are Running - - Ensure that only network ports, protocols, and services listening on a system with validated business needs, are running on each system.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Conditional Access policies
    $conditionalAccessPolicies = Get-MgIdentityConditionalAccessPolicy -All

    # Check for a policy that blocks legacy authentication
    foreach ($policy in $conditionalAccessPolicies) {
        $isCompliant = $false
        $policyDetails = @{
            PolicyName = $policy.DisplayName
            IsEnabled = $policy.State -eq 'Enabled'
            IncludesAllUsers = $false
            IncludesAllResources = $false
            BlocksLegacyAuth = $false
            ExclusionsReviewed = $false
        }

        # Check if policy is enabled
        if ($policyDetails.IsEnabled) {
            # Check if all users are included
            $policyDetails.IncludesAllUsers = $policy.Conditions.Users.Include -contains 'All'
            
            # Check if all resources are included
            $policyDetails.IncludesAllResources = $policy.Conditions.Applications.Include -contains 'All'
            
            # Check if legacy authentication is blocked
            $legacyClients = @('ExchangeActiveSync', 'Other')
            $policyDetails.BlocksLegacyAuth = ($policy.Conditions.ClientAppTypes -contains $legacyClients)
            
            # Check if exclusions are documented and reviewed
            $policyDetails.ExclusionsReviewed = ($policy.Conditions.Users.Exclude -eq $null) -or ($policy.Conditions.Applications.Exclude -eq $null)
            
            # Determine compliance
            $isCompliant = $policyDetails.IsEnabled -and $policyDetails.IncludesAllUsers -and $policyDetails.IncludesAllResources -and $policyDetails.BlocksLegacyAuth -and $policyDetails.ExclusionsReviewed
        }

        $policyDetails.IsCompliant = $isCompliant
        $resourceResults += $policyDetails
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
