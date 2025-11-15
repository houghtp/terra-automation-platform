# Control: 7.3.2 - Ensure OneDrive sync is restricted for unmanaged
<# CIS_METADATA_START
{"Description":"Microsoft OneDrive allows users to sign in their cloud tenant account and begin syncing\nselect folders or the entire contents of OneDrive to a local computer. By default, this\nincludes any computer with OneDrive already installed, whether it is Entra Joined ,\nEntra Hybrid Joined or Active Directory Domain joined.\nThe recommended state for this setting is Allow syncing only on computers\njoined to specific domains Enabled: Specify the AD domain GUID(s)","Impact":"Enabling this feature will prevent users from using the OneDrive for Business Sync\nclient on devices that are not joined to the domains that were defined.","Audit":"To audit using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click Settings followed by OneDrive - Sync\n3. Verify that Allow syncing only on computers joined to specific\ndomains is checked.\n4. Verify that the Active Directory domain GUIDS are listed in the box.\no Use the Get-ADDomain PowerShell command on the on-premises server\nto obtain the GUID for each on-premises domain.\nTo audit using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService -Url\nhttps://tenant-admin.sharepoint.com, replacing \"tenant\" with the\nappropriate value.\n2. Run the following PowerShell command:\nGet-SPOTenantSyncClientRestriction | fl\nTenantRestrictionEnabled,AllowedDomainList\n3. Ensure TenantRestrictionEnabled is set to True and AllowedDomainList\ncontains the trusted domains GUIDs from the on premises environment.","Remediation":"To remediate using the UI:\n1. Navigate to SharePoint admin center https://admin.microsoft.com/sharepoint\n2. Click Settings then select OneDrive - Sync.\n3. Check the Allow syncing only on computers joined to specific\ndomains.\n4. Use the Get-ADDomain PowerShell command on the on-premises server to\nobtain the GUID for each on-premises domain.\n5. Click Save.\nTo remediate using PowerShell:\n1. Connect to SharePoint Online using Connect-SPOService\n2. Run the following PowerShell command and provide the DomainGuids from the\nGet-AADomain command:\nSet-SPOTenantSyncClientRestriction -Enable -DomainGuids \"786548DD-877B-4760-\nA749-6B1EFBC1190A; 877564FF-877B-4760-A749-6B1EFBC1190A\"\nNote: Utilize the -BlockMacSync:$true parameter if you are not using conditional\naccess to ensure Macs cannot sync.","Title":"Ensure OneDrive sync is restricted for unmanaged","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","SubSection":"7.3 Settings","DefaultValue":"By default there are no restrictions applied to the syncing of OneDrive.\nTenantRestrictionEnabled : False\nAllowedDomainList : {}","Level":"L2","CISControls":"[{\"version\": \"v8\", \"id\": \"0.0\", \"title\": \"Explicitly Not Mapped\", \"description\": \"Explicitly Not Mapped\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]","References":"1. https://learn.microsoft.com/en-us/sharepoint/allow-syncing-only-on-specific-\ndomains\n2. https://learn.microsoft.com/en-us/powershell/module/sharepoint-online/set-\nspotenantsyncclientrestriction?view=sharepoint-ps","Rationale":"Unmanaged devices pose a risk, since their security cannot be verified through existing\nsecurity policies, brokers or endpoint protection. Allowing users to sync data to these\ndevices takes that data out of the control of the organization. This increases the risk of\nthe data either being intentionally or accidentally leaked.\nNote: This setting is only applicable to Active Directory domains when operating in a\nhybrid configuration. It does not apply to Entra domains. If there are devices which are\nonly Entra ID joined, consider using a Conditional Access Policy instead.","Section":"7 SharePoint admin center","RecommendationId":"7.3.2"}
CIS_METADATA_END #>
# Required Services: SharePoint, MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()# Use the Get-ADDomain PowerShell command on the on-premises server
    # to obtain the GUID for each on-premises domain.
    $domains = Get-ADDomain | Select-Object -ExpandProperty ObjectGuid

    # Get the SharePoint Online Tenant Sync Client Restriction settings
    $tenantSyncClientRestriction = Get-PnPTenantSyncClientRestriction

    # Check if the trusted domains GUIDs from the on-premises environment are present
    $isCompliant = $true
    foreach ($domainGuid in $domains) {
        if (-not ($tenantSyncClientRestriction.TrustedDomainGuids -contains $domainGuid)) {
            $isCompliant = $false
            $resourceResults += @{
                DomainGuid = $domainGuid
                IsCompliant = $false
                Message = "Domain GUID $domainGuid is not trusted in SharePoint Online."
            }
        } else {
            $resourceResults += @{
                DomainGuid = $domainGuid
                IsCompliant = $true
                Message = "Domain GUID $domainGuid is trusted in SharePoint Online."
            }
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
