# Control: 2.1.5 - Ensure Safe Attachments for SharePoint, OneDrive,
<# CIS_METADATA_START
{"Description":"Safe Attachments for SharePoint, OneDrive, and Microsoft Teams scans these services\nfor malicious files.","Impact":"Impact associated with Safe Attachments is minimal, and equivalent to impact\nassociated with anti-virus scanners in an environment.","Audit":"To audit using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com\n2. Under Email & collaboration select Policies & rules\n3. Select Threat policies then Safe Attachments.\n4. Click on Global settings\n5. Ensure the toggle is Enabled to Turn on Defender for Office 365 for\nSharePoint, OneDrive, and Microsoft Teams.\n6. Ensure the toggle is Enabled to Turn on Safe Documents for Office\nclients.\n7. Ensure the toggle is Deselected/Disabled to Allow people to click\nthrough Protected View even if Safe Documents identified the file\nas malicious.\nTo audit using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nGet-AtpPolicyForO365 | fl\nName,EnableATPForSPOTeamsODB,EnableSafeDocs,AllowSafeDocsOpen\nVerify the values for each parameter as below:\nEnableATPForSPOTeamsODB : True\nEnableSafeDocs : True\nAllowSafeDocsOpen : False","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft 365 Defender https://security.microsoft.com\n2. Under Email & collaboration select Policies & rules\n3. Select Threat policies then Safe Attachments.\n4. Click on Global settings\n5. Click to Enable Turn on Defender for Office 365 for SharePoint,\nOneDrive, and Microsoft Teams\n6. Click to Enable Turn on Safe Documents for Office clients\n7. Click to Disable Allow people to click through Protected View even\nif Safe Documents identified the file as malicious.\n8. Click Save\nTo remediate using PowerShell:\n1. Connect to Exchange Online using Connect-ExchangeOnline.\n2. Run the following PowerShell command:\nSet-AtpPolicyForO365 -EnableATPForSPOTeamsODB $true -EnableSafeDocs $true -\nAllowSafeDocsOpen $false","Title":"Ensure Safe Attachments for SharePoint, OneDrive,","ProfileApplicability":"- E5 Level 2","SubSection":"2.1 Email & collaboration","DefaultValue":"","Level":"L2","CISControls":"[{\"version\": \"\", \"id\": \"9.7\", \"title\": \"Deploy and Maintain Email Server Anti-Malware\", \"description\": \"v8 Protections - Deploy and maintain email server anti-malware protections, such as attachment scanning and/or sandboxing.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"10.1\", \"title\": \"Deploy and Maintain Anti-Malware Software\", \"description\": \"v8 - - - Deploy and maintain anti-malware software on all enterprise assets.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"7.10\", \"title\": \"Sandbox All Email Attachments\", \"description\": \"Use sandboxing to analyze and block inbound email attachments with - malicious behavior.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"8.1\", \"title\": \"Utilize Centrally Managed Anti-malware Software\", \"description\": \"Utilize centrally managed anti-malware software to continuously monitor and - - defend each of the organization's workstations and servers.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/defender-office-365/safe-attachments-for-spo-\nodfb-teams-about","Rationale":"Safe Attachments for SharePoint, OneDrive, and Microsoft Teams protect organizations\nfrom inadvertently sharing malicious files. When a malicious file is detected that file is\nblocked so that no one can open, copy, move, or share it until further actions are taken\nby the organization's security team.","Section":"2 Microsoft 365 Defender","RecommendationId":"2.1.5"}
CIS_METADATA_END #>
# Required Services: Teams, SharePoint, ExchangeOnline
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Execute the original cmdlet to get ATP policy for Office 365
    $atpPolicy = Get-AtpPolicyForO365
    
    # Process the results and convert to standard format
    foreach ($policy in $atpPolicy) {
        $isCompliant = $true # Assume compliance unless specific checks fail
        
        # Example compliance check (customize based on actual policy requirements)
        if ($policy.SomeProperty -ne 'ExpectedValue') {
            $isCompliant = $false
        }
        
        # Add the result to the resource results array
        $resourceResults += @{
            PolicyName = $policy.Name
            IsCompliant = $isCompliant
            Details = $policy | Select-Object -Property *
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
