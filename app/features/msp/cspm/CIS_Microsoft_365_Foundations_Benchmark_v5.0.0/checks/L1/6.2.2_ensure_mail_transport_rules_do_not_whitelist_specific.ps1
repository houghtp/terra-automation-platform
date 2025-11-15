# Control: 6.2.2 - Ensure mail transport rules do not whitelist specific
<# CIS_METADATA_START
{"Description":"Mail flow rules (transport rules) in Exchange Online are used to identify and take action\non messages that flow through the organization.","Impact":"Care should be taken before implementation to ensure there is no business need for\ncase-by-case whitelisting. Removing all whitelisted domains could affect incoming mail\nflow to an organization although modern systems sending legitimate mail should have\nno issue with this.","Audit":"To audit using the UI:\n1. Navigate to Exchange admin center https://admin.exchange.microsoft.com..\n2. Click to expand Mail Flow and then select Rules.\n3. Review each rule and ensure that a single rule does not contain both of these\nproperties together:\no Under Apply this rule if: Sender's address domain portion belongs\nto any of these domains: '<domain>'\no Under Do the following: Set the spam confidence level (SCL) to\n'-1'\nNote: Setting the spam confidence level to -1 indicates the message is from a trusted\nsender, so the message bypasses spam filtering. The recommendation fails if any\nexternal domain has a SCL of -1.\nTo audit using PowerShell:\n1. Connect to Exchange online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-TransportRule | Where-Object { $_.setscl -eq -1 -and $_.SenderDomainIs -\nne $null } | ft Name,SenderDomainIs,SetSCL","Remediation":"To remediate using the UI:\n1. Navigate to Exchange admin center https://admin.exchange.microsoft.com..\n2. Click to expand Mail Flow and then select Rules.\n3. For each rule that sets the spam confidence level to -1 for a specific domain,\nselect the rule and click Delete.\nTo remediate using PowerShell:\n1. Connect to Exchange online using Connect-ExchangeOnline.\n2. To modify the rule:\nRemove-TransportRule {RuleName}\n3. Verify the rules no longer exists by re-running the audit procedure.","Title":"Ensure mail transport rules do not whitelist specific","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","SubSection":"6.2 Mail flow","DefaultValue":"","Level":"L1","CISControls":"[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/exchange/security-and-compliance/mail-flow-\nrules/configuration-best-practices\n2. https://learn.microsoft.com/en-us/exchange/security-and-compliance/mail-flow-\nrules/mail-flow-rules","Rationale":"Whitelisting domains in transport rules bypasses regular malware and phishing\nscanning, which can enable an attacker to launch attacks against your users from a\nsafe haven domain.\nNote: If an organization identifies a business need for an exception, the domain should\nonly be whitelisted if inbound emails from that domain originate from a specific IP\naddress. These exceptions should be documented and regularly reviewed.","Section":"6 Exchange admin center","RecommendationId":"6.2.2"}
CIS_METADATA_END #>
# Required Services: SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve transport rules and filter based on criteria
    $transportRules = Get-TransportRule | Where-Object { $_.setscl -eq -1 -and $_.SenderDomainIs -ne $null }
    
    # Process each transport rule and determine compliance
    foreach ($rule in $transportRules) {
        $isCompliant = $false
        $ruleDetails = @{
            Name = $rule.Name
            SenderDomainIs = $rule.SenderDomainIs
            SetSCL = $rule.SetSCL
            IsCompliant = $isCompliant
        }
        $resourceResults += $ruleDetails
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
