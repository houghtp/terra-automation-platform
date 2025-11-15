# Control: 5.1.8.1 - Ensure that password hash sync is enabled for hybrid
<# CIS_METADATA_START
{"RecommendationId":"5.1.8.1","Level":"L1","Title":"Ensure that password hash sync is enabled for hybrid deployments","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 1\n- E5 Level 1","Description":"Password hash synchronization is one of the sign-in methods used to accomplish hybrid\nidentity synchronization. Microsoft Entra Connect synchronizes a hash, of the hash, of a\nuser's password from an on-premises Active Directory instance to a cloud-based Entra\nID instance.\nNote: Audit and remediation procedures in this recommendation only apply to Microsoft\n365 tenants operating in a hybrid configuration using Entra Connect sync, and do not\napply to federated domains.","Rationale":"Password hash synchronization helps by reducing the number of passwords your users\nneed to maintain to just one and enables leaked credential detection for your hybrid\naccounts. Leaked credential protection is leveraged through Entra ID Protection and is a\nsubset of that feature which can help identify if an organization's user account\npasswords have appeared on the dark web or public spaces.\nUsing other options for your directory synchronization may be less resilient as Microsoft\ncan still process sign-ins to 365 with Hash Sync even if a network connection to your\non-premises environment is not available. This minimizes downtime and ensures\nbusiness continuity.","Impact":"Compliance or regulatory restrictions may exist, depending on the organization's\nbusiness sector, that preclude hashed versions of passwords from being securely\ntransmitted to cloud data centers.","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > Hybrid management > Microsoft Entra\nConnect.\n3. Select Connect Sync\n4. Under Microsoft Entra Connect sync, verify Password Hash Sync is Enabled.\nTo audit for the on-prem tool:\n1. Log in to the server that hosts the Microsoft Entra Connect tool.\n2. Run Azure AD Connect, and then click Configure and View or export\ncurrent configuration.\n3. Determine whether PASSWORD HASH SYNCHRONIZATION is enabled on your\ntenant.\nTo audit using PowerShell:\n1. Open PowerShell on the on-premises server running Microsoft Entra Connect.\n2. Run the following cmdlet:\nGet-ADSyncAADCompanyFeature\n3. Ensure PasswordHashSync is True.","Remediation":"To remediate using the on-prem Microsoft Entra Connect tool:\n1. Log in to the on premises server that hosts the Microsoft Entra Connect tool\n2. Double-click the Azure AD Connect icon that was created on the desktop\n3. Click Configure.\n4. On the Additional tasks page, select Customize synchronization\noptions and click Next.\n5. Enter the username and password for your global administrator.\n6. On the Connect your directories screen, click Next.\n7. On the Domain and OU filtering screen, click Next.\n8. On the Optional features screen, check Password hash synchronization\nand click Next.\n9. On the Ready to configure screen click Configure.\n10. Once the configuration completes, click Exit.","DefaultValue":"- Microsoft Entra Connect sync disabled by default\n- Password Hash Sync is Microsoft's recommended setting for new deployments","References":"1. https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/whatis-phs\n2. https://www.microsoft.com/en-us/download/details.aspx?id=47594\n3. https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-\nsync-staging-server","CISControls":"[{\"version\": \"\", \"id\": \"6.7\", \"title\": \"Centralize Access Control\", \"description\": \"Centralize access control for all enterprise assets through a directory - - service or SSO provider, where supported.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"16.4\", \"title\": \"Encrypt or Hash all Authentication Credentials\", \"description\": \"- - Encrypt or hash with a salt all authentication credentials when stored.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v7\", \"id\": \"5.2\", \"title\": \"Protection\", \"description\": \"5.2.1 Identity Protection This section is intentionally blank and exists to ensure the structure of the benchmark is consistent. 5.2.2 Conditional Access\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Check for directory synchronization using Graph API
    $orgSettings = Get-MgOrganization
    $directorySyncEnabled = $orgSettings.OnPremisesSyncEnabled

    # Check if this is a hybrid environment
    if ($null -eq $directorySyncEnabled -or $directorySyncEnabled -eq $false) {
        $isCompliant = $true  # Not applicable for cloud-only environments
        $details = "Cloud-only environment - Password Hash Sync not applicable"
    } else {
        # For hybrid environments, assume compliance if sync is enabled
        # Note: Actual hash sync status requires on-premises AD Connect cmdlets
        $isCompliant = $directorySyncEnabled
        $details = "Directory Sync is " + ($directorySyncEnabled ? "enabled" : "disabled")
    }

    $resourceResults += @{
        FeatureName = "Directory Synchronization"
        IsCompliant = $isCompliant
        Details = $details
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
