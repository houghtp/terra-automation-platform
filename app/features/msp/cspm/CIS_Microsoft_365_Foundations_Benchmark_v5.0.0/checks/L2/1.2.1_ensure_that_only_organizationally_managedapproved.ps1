# Control: 1.2.1 - Ensure that only organizationally managed/approved
<# CIS_METADATA_START
{"Description": "Microsoft 365 Groups is the foundational membership service that drives all teamwork\nacross Microsoft 365. With Microsoft 365 Groups, you can give a group of people\naccess to a collection of shared resources. While there are several different group types\nthis recommendation concerns Microsoft 365 Groups.\nIn the Administration panel, when a group is created, the default privacy value is\n\"Public\".", "Impact": "If the recommendation is applied, group owners could receive more access requests\nthan usual, especially regarding groups originally meant to be public.", "Audit": "To audit using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Teams & groups select Active teams & groups.\n3. On the Active teams and groups page, check that no groups have the status\n'Public' in the privacy column.\nTo audit using PowerShell:\n1. Connect to the Microsoft Graph service using Connect-MgGraph -Scopes\n\"Group.Read.All\".\n2. Run the following Microsoft Graph PowerShell command:\nGet-MgGroup -All | where {$_.Visibility -eq \"Public\"} | select\nDisplayName,Visibility\n3. Ensure Visibility is Private for each group.", "Remediation": "To remediate using the UI:\n1. Navigate to Microsoft 365 admin center https://admin.microsoft.com.\n2. Click to expand Teams & groups select Active teams & groups..\n3. On the Active teams and groups page, select the group's name that is public.\n4. On the popup groups name page, Select Settings.\n5. Under Privacy, select Private.", "Title": "Ensure that only organizationally managed/approved public groups exist", "ProfileApplicability": "- E3 Level 2\n- E5 Level 2", "SubSection": "1.2 Teams & groups", "DefaultValue": "Public when created from the Administration portal; private otherwise.", "Level": "L2", "CISControls": "[{\"version\": \"\", \"id\": \"3.3\", \"title\": \"Configure Data Access Control Lists\", \"description\": \"v8 Configure data access control lists based on a user's need to know. Apply - - - data access control lists, also known as access permissions, to local and remote file systems, databases, and applications.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}, {\"version\": \"\", \"id\": \"13.1\", \"title\": \"Maintain an Inventory Sensitive Information\", \"description\": \"v7 Maintain an inventory of all sensitive information stored, processed, or - - - transmitted by the organization's technology systems, including those located onsite or at a remote service provider.\", \"ig1\": false, \"ig2\": false, \"ig3\": false}]", "References": "1. https://learn.microsoft.com/en-us/entra/identity/users/groups-self-service-\nmanagement\n2. https://learn.microsoft.com/en-us/microsoft-365/admin/create-groups/compare-\ngroups?view=o365-worldwide", "Rationale": "Ensure that only organizationally managed and approved public groups exist. When a\ngroup has a \"public\" privacy, users may access data related to this group (e.g.\nSharePoint), through three methods:\n- By using the Azure portal, and adding themselves into the public group\n- By requesting access to the group from the Group application of the Access\nPanel\n- By accessing the SharePoint URL\nAdministrators are notified when a user uses the Azure Portal. Requesting access to the\ngroup forces users to send a message to the group owner, but they still have immediate\naccess to the group. The SharePoint URL is usually guessable and can be found from\nthe Group application of the Access Panel. If group privacy is not controlled, any user\nmay access sensitive information, according to the group they try to access.\nNote: Public in this case means public to the identities within the organization.", "Section": "1 Microsoft 365 admin center", "RecommendationId": "1.2.1"}
CIS_METADATA_END #>
# Required Services: MgGraph, Teams
# Note: Authentication is handled centrally - do not add Connect-* commands

$ErrorActionPreference = 'Stop'

try {
    # Initialize results array
    $resourceResults = @()
    # Retrieve all groups with visibility set to "Public"
    $publicGroups = Get-MgBetaGroup -All | Where-Object { $_.Visibility -eq "Public" }

    # Process each public group and determine compliance
    foreach ($group in $publicGroups) {
        $resourceResults += @{
            GroupId = $group.Id
            DisplayName = $group.DisplayName
            Visibility = $group.Visibility
            IsCompliant = $false  # Assuming public groups are non-compliant
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
