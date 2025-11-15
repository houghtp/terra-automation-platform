# Control: 2.1.1 - Ensure Safe Links for Office Applications is Enabled
<# CIS_METADATA_START
{"Description":"Enabling Safe Links policy for Office applications allows URL's that exist inside of Office\ndocuments and email applications opened by Office, Office Online and Office mobile to\nbe processed against Defender for Office time-of-click verification and rewritten if\nrequired.\nNote: E5 Licensing includes a number of Built-in Protection policies. When auditing\npolicies note which policy you are viewing, and keep in mind CIS recommendations\noften extend the Default or Build-in Policies provided by MS. In order to Pass the\nhighest priority policy must match all settings recommended.","Impact":"User impact associated with this change is minor - users may experience a very short\ndelay when clicking on URLs in Office documents before being directed to the\nrequested site. Users should be informed of the change as, in the event a link is unsafe\nand blocked, they will receive a message that it has been blocked.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com\n2. Under Email & collaboration select Policies & rules\n3. Select Threat policies then Safe Links\n4. Inspect each policy and attempt to identify one that matches the parameters\noutlined below.\n5. Scroll down the pane and click on Edit Protection settings (Global Readers\nwill look for on or off values)\n6. Ensure the following protection settings are set as outlined:\nEmail\no Checked On: Safe Links checks a list of known, malicious\nlinks when users click links in email. URLs are rewritten by\ndefault\no Checked Apply Safe Links to email messages sent within the\norganization\no Checked Apply real-time URL scanning for suspicious links\nand links that point to files\no Checked Wait for URL scanning to complete before delivering\nthe message\no Unchecked Do not rewrite URLs, do checks via Safe Links API\nonly.\nTeams\no Checked On: Safe Links checks a list of known, malicious\nlinks when users click links in Microsoft Teams. URLs are\nnot rewritten\nOffice 365 Apps\no Checked On: Safe Links checks a list of known, malicious\nlinks when users click links in Microsoft Office apps. URLs\nare not rewritten\nClick protection settings\no Checked Track user clicks\no Unchecked Let users click through the original URL\n7. There is no recommendation for organization branding.\n8. Click close\nTo audit using PowerShell:\n1. Connect using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-SafeLinksPolicy | Format-Table Name\n3. Once this returns the list of policies run the following command to view the\npolicies.\nGet-SafeLinksPolicy -Identity \"Policy Name\"\n4. Verify the value for the following.\no EnableSafeLinksForEmail: True\no EnableSafeLinksForTeams: True\no EnableSafeLinksForOffice: True\no TrackClicks: True\no AllowClickThrough: False\no ScanUrls: True\no EnableForInternalSenders: True\no DeliverMessageAfterScan: True\no DisableUrlRewrite: False","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com\n2. Under Email & collaboration select Policies & rules\n3. Select Threat policies then Safe Links\n4. Click on +Create\n5. Name the policy then click Next\n6. In Domains select all valid domains for the organization and Next\n7. Ensure the following URL & click protection settings are defined:\nEmail\no Checked On: Safe Links checks a list of known, malicious\nlinks when users click links in email. URLs are rewritten by\ndefault\no Checked Apply Safe Links to email messages sent within the\norganization\no Checked Apply real-time URL scanning for suspicious links\nand links that point to files\no Checked Wait for URL scanning to complete before delivering\nthe message\no Unchecked Do not rewrite URLs, do checks via Safe Links API\nonly.\nTeams\no Checked On: Safe Links checks a list of known, malicious\nlinks when users click links in Microsoft Teams. URLs are\nnot rewritten\nOffice 365 Apps\no Checked On: Safe Links checks a list of known, malicious\nlinks when users click links in Microsoft Office apps. URLs\nare not rewritten\nClick protection settings\no Checked Track user clicks\no Unchecked Let users click through the original URL\no There is no recommendation for organization branding.\n8. Click Next twice and finally Submit\nTo remediate using PowerShell:\n1. Connect using Connect-ExchangeOnline.\n2. Run the following PowerShell script to create a policy at highest priority that will\napply to all valid domains on the tenant:\n# Create the Policy\n$params = @{\nName = \"CIS SafeLinks Policy\"\nEnableSafeLinksForEmail = $true\nEnableSafeLinksForTeams = $true\nEnableSafeLinksForOffice = $true\nTrackClicks = $true\nAllowClickThrough = $false\nScanUrls = $true\nEnableForInternalSenders = $true\nDeliverMessageAfterScan = $true\nDisableUrlRewrite = $false\n}\nNew-SafeLinksPolicy @params\n# Create the rule for all users in all valid domains and associate with\nPolicy\nNew-SafeLinksRule -Name \"CIS SafeLinks\" -SafeLinksPolicy \"CIS SafeLinks\nPolicy\" -RecipientDomainIs (Get-AcceptedDomain).Name -Priority 0","Title":"Ensure Safe Links for Office Applications is Enabled","ProfileApplicability":"- E5 Level 2","SubSection":"2.1 Email & collaboration","DefaultValue":"","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"10.1\", \"title\": \"Deploy and Maintain Anti-Malware Software\", \"description\": \"v8 - - - Deploy and maintain anti-malware software on all enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.4\", \"title\": \"Maintain and Enforce Network-Based URL Filters\", \"description\": \"Enforce network-based URL filters that limit a system's ability to connect to websites not approved by the organization. This filtering shall be enforced for each - - of the organization's systems, whether they are physically at an organization's facilities or not.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/safe-links-policies-\nconfigure?view=o365-worldwide\n2. https://learn.microsoft.com/en-us/powershell/module/exchange/set-\nsafelinkspolicy?view=exchange-ps\n3. https://learn.microsoft.com/en-us/defender-office-365/preset-security-\npolicies?view=o365-worldwide","Rationale":"Safe Links for Office applications extends phishing protection to documents and emails\nthat contain hyperlinks, even after they have been delivered to a user.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.1"}
CIS_METADATA_END #>
# Required Services: Teams, SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve Safe Links Policies
    $safeLinksPolicies = Get-SafeLinksPolicy

    # Iterate over each policy to check compliance
    foreach ($policy in $safeLinksPolicies) {
        $policyDetails = Get-SafeLinksPolicy -Identity $policy.Name

        # Check compliance for each policy
        $isCompliant = $true
        if (-not $policyDetails.EnableSafeLinksForEmail) { $isCompliant = $false }
        if (-not $policyDetails.EnableSafeLinksForTeams) { $isCompliant = $false }
        if (-not $policyDetails.EnableSafeLinksForOffice) { $isCompliant = $false }
        if (-not $policyDetails.TrackClicks) { $isCompliant = $false }
        if ($policyDetails.AllowClickThrough) { $isCompliant = $false }
        if (-not $policyDetails.ScanUrls) { $isCompliant = $false }
        if (-not $policyDetails.EnableForInternalSenders) { $isCompliant = $false }
        if (-not $policyDetails.DeliverMessageAfterScan) { $isCompliant = $false }
        if ($policyDetails.DisableUrlRewrite) { $isCompliant = $false }

        # Add policy result to the results array
        $resourceResults += @{
            PolicyName = $policy.Name
            IsCompliant = $isCompliant
            Details = $policyDetails
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
