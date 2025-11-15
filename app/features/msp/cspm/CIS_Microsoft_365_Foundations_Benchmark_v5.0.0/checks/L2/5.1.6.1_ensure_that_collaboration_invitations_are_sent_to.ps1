# Control: 5.1.6.1 - Ensure that collaboration invitations are sent to
<# CIS_METADATA_START
{"RecommendationId":"5.1.6.1","Level":"L2","Title":"Ensure that collaboration invitations are sent to allowed domains only","Section":"5 Microsoft Entra admin center","SubSection":"5.1 Identity","ProfileApplicability":"- E3 Level 2\n- E5 Level 2","Description":"B2B collaboration is a feature within Microsoft Entra External ID that allows for guest\ninvitations to an organization.\nEnsure users can only send invitations to specified domains.\nNote: This list works independently from OneDrive for Business and SharePoint Online\nallow/block lists. To restrict individual file sharing in SharePoint Online, set up an allow\nor blocklist for OneDrive for Business and SharePoint Online. For instance, in\nSharePoint or OneDrive users can still share with external users from prohibited\ndomains by using Anyone links if they haven't been disabled.","Rationale":"By specifying allowed domains for collaborations, external user's companies are\nexplicitly identified. Also, this prevents internal users from inviting unknown external\nusers such as personal accounts and granting them access to resources.","Impact":"This could make collaboration more difficult if the setting is not quickly updated when a\nnew domain is identified as \"allowed\".","Audit":"To audit using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > External Identities select External\ncollaboration settings.\n3. Under Collaboration restrictions, verify that Allow invitations only to\nthe specified domains (most restrictive) is selected. Then verify\nallowed domains are specified under Target domains.","Remediation":"To remediate using the UI:\n1. Navigate to Microsoft Entra admin center https://entra.microsoft.com/.\n2. Click to expand Identity > External Identities select External\ncollaboration settings.\n3. Under Collaboration restrictions, select Allow invitations only to the\nspecified domains (most restrictive) is selected. Then specify the\nallowed domains under Target domains.","DefaultValue":"Allow invitations to be sent to any domain (most inclusive)","References":"1. https://learn.microsoft.com/en-us/entra/external-id/allow-deny-list\n2. https://learn.microsoft.com/en-us/entra/external-id/what-is-b2b","CISControls":"[{\"version\": \"\", \"id\": \"6.1\", \"title\": \"Establish an Access Granting Process\", \"description\": \"Establish and follow a process, preferably automated, for granting access to - - - enterprise assets upon new hire, rights grant, or role change of a user.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"v8\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]"}
CIS_METADATA_END #>
# Required Services: MgGraph
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    
    # Retrieve the external collaboration settings
    $externalCollaborationSettings = Get-MgPolicyIdentitySecurityDefaultEnforcementPolicy

    # Check if the collaboration restrictions are set to allow invitations only to specified domains
    $isCompliant = $false
    $allowedDomains = @()
    
    if ($externalCollaborationSettings) {
        $isCompliant = $externalCollaborationSettings.AllowInvitationsOnlyToSpecifiedDomains -eq $true
        $allowedDomains = $externalCollaborationSettings.AllowedDomains
    }

    # Add the result to the resource results
    $resourceResults += @{
        ResourceName = "External Collaboration Settings"
        CurrentValue = @{
            AllowInvitationsOnlyToSpecifiedDomains = $externalCollaborationSettings.AllowInvitationsOnlyToSpecifiedDomains
            AllowedDomains = $allowedDomains
        }
        IsCompliant = $isCompliant
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
