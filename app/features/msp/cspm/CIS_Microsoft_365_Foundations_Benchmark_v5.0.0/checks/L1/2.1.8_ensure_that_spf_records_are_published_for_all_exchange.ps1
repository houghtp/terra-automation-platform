# Control: 2.1.8 - Ensure that SPF records are published for all Exchange
<# CIS_METADATA_START
{"Description":"For each domain that is configured in Exchange, a corresponding Sender Policy\nFramework (SPF) record should be created.","Impact":"There should be minimal impact of setting up SPF records however, organizations\nshould ensure proper SPF record setup as email could be flagged as spam if SPF is not\nsetup appropriately.","Audit":"To audit using PowerShell:\n1. Open a command prompt.\n2. Type the following command in PowerShell:\nResolve-DnsName [domain1.com] txt | fl\n3. Ensure that a value exists and that it includes v=spf1\ninclude:spf.protection.outlook.com. This designates Exchange Online as\na designated sender.\nTo verify the SPF records are published, use the REST API for each domain:\nhttps://graph.microsoft.com/v1.0/domains/[DOMAIN.COM]/serviceConfigurationRec\nords\n1. Ensure that a value exists that includes v=spf1\ninclude:spf.protection.outlook.com. This designates Exchange Online as\na designated sender.\nNote: Resolve-DnsName is not available on older versions of Windows prior to\nWindows 8 and Server 2012.","Remediation":"To remediate using a DNS Provider:\n1. If all email in your domain is sent from and received by Exchange Online, add the\nfollowing TXT record for each Accepted Domain:\nv=spf1 include:spf.protection.outlook.com -all\n2. If there are other systems that send email in the environment, refer to this article\nfor the proper SPF configuration: https://docs.microsoft.com/en-\nus/office365/SecurityCompliance/set-up-spf-in-office-365-to-help-prevent-\nspoofing.","Title":"Ensure that SPF records are published for all Exchange","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"2.1 Email & collaboration","DefaultValue":"","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"9.5\", \"title\": \"Implement DMARC\", \"description\": \"v8 To lower the chance of spoofed or modified emails from valid domains, - - implement DMARC policy and verification, starting with implementing the Sender Policy Framework (SPF) and the DomainKeys Identified Mail (DKIM) standards.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.8\", \"title\": \"Implement DMARC and Enable Receiver-Side\", \"description\": \"Verification v7 To lower the chance of spoofed or modified emails from valid domains, - - implement Domain-based Message Authentication, Reporting and Conformance (DMARC) policy and verification, starting by implementing the Sender Policy Framework (SPF) and the DomainKeys Identified Mail(DKIM) standards.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/microsoft-365/security/office-365-\nsecurity/email-authentication-spf-configure?view=o365-worldwide","Rationale":"SPF records allow Exchange Online Protection and other mail systems to know where\nmessages from domains are allowed to originate. This information can be used by that\nsystem to determine how to treat the message based on if it is being spoofed or is valid.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.8"}
CIS_METADATA_END #>
# Required Services: MgGraph, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()

    # Get verified domains from the tenant
    $verifiedDomains = Get-MgDomain | Where-Object { $_.IsVerified -eq $true }

    if (-not $verifiedDomains) {
        $resourceResults += @{
            Domain = "N/A"
            IsCompliant = $false
            Details = "No verified domains found in tenant"
        }
    } else {
        foreach ($domain in $verifiedDomains) {
            try {
                # Skip .onmicrosoft.com domains as they don't need SPF records
                if ($domain.Id -like "*.onmicrosoft.com") {
                    $resourceResults += @{
                        Domain = $domain.Id
                        IsCompliant = $true
                        Details = "Skipped - .onmicrosoft.com domain does not require SPF record"
                    }
                    continue
                }

                # Check SPF record for the domain
                $spfRecord = Resolve-DnsName -Name $domain.Id -Type TXT -ErrorAction SilentlyContinue |
                    Where-Object { $_.Strings -match "v=spf1" -and $_.Strings -match "include:spf\.protection\.outlook\.com" }

                $isCompliant = $null -ne $spfRecord

                $resourceResults += @{
                    Domain = $domain.Id
                    IsCompliant = $isCompliant
                    Details = if ($isCompliant) {
                        "SPF record found with spf.protection.outlook.com"
                    } else {
                        "SPF record missing or does not include spf.protection.outlook.com"
                    }
                }
            }
            catch {
                $resourceResults += @{
                    Domain = $domain.Id
                    IsCompliant = $false
                    Details = "Error checking SPF record: $($_.Exception.Message)"
                }
            }
        }
    }

    # Determine overall status - only fail if custom domains (non-.onmicrosoft.com) don't have proper SPF
    $customDomainResults = $resourceResults | Where-Object { $_.Domain -notlike "*.onmicrosoft.com" }
    $overallStatus = if (($customDomainResults | Where-Object { -not $_.IsCompliant })) { 'Fail' } else { 'Pass' }
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
