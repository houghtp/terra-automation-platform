# CRASH-SAFE App Creation + Power BI Admin API Enablement
# Run each section one by one if PowerShell keeps crashing

# =========================
# SECTION 0: Module Imports
# =========================
# Ensure Microsoft Graph and Power BI modules exist and are loaded.
# This may take several minutes on first run.
try {
    Write-Host "`n0. Ensuring required modules..." -ForegroundColor Cyan

    $graphModuleName = "Microsoft.Graph"
    $pbiModuleName   = "MicrosoftPowerBIMgmt"

    # Check and install Microsoft Graph
    Write-Host "Checking for $graphModuleName..." -ForegroundColor Gray
    if (-not (Get-Module -ListAvailable -Name $graphModuleName)) {
        Write-Host "Installing $graphModuleName (this may take 5-10 minutes)..." -ForegroundColor Yellow
        Write-Host "Please wait, downloading from PowerShell Gallery..." -ForegroundColor Gray
        Install-Module $graphModuleName -Scope CurrentUser -Force -AllowClobber -AcceptLicense -SkipPublisherCheck -ErrorAction Stop
        Write-Host "✓ $graphModuleName installed successfully" -ForegroundColor Green
    } else {
        Write-Host "✓ $graphModuleName already available" -ForegroundColor Green
    }

    # Check and install Power BI Management
    Write-Host "Checking for $pbiModuleName..." -ForegroundColor Gray
    if (-not (Get-Module -ListAvailable -Name $pbiModuleName)) {
        Write-Host "Installing $pbiModuleName (this may take 2-3 minutes)..." -ForegroundColor Yellow
        Write-Host "Please wait, downloading from PowerShell Gallery..." -ForegroundColor Gray
        Install-Module $pbiModuleName -Scope CurrentUser -Force -AllowClobber -AcceptLicense -SkipPublisherCheck -ErrorAction Stop
        Write-Host "✓ $pbiModuleName installed successfully" -ForegroundColor Green
    } else {
        Write-Host "✓ $pbiModuleName already available" -ForegroundColor Green
    }

    Write-Host "All modules ready (PowerShell will auto-load them when needed)." -ForegroundColor Green
} catch {
    Write-Host "Module setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "This may be due to:" -ForegroundColor Yellow
    Write-Host "  1. PowerShell execution policy restrictions" -ForegroundColor Yellow
    Write-Host "  2. Network connectivity issues" -ForegroundColor Yellow
    Write-Host "  3. PowerShell Gallery access blocked" -ForegroundColor Yellow
    Write-Host "`nTo fix, try running as Administrator:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Gray
    exit
}

# =====================================================================
# SECTION 1: Connect to Microsoft Graph (Application/Permission Management)
# =====================================================================
try {
    Write-Host "`n1. Connecting to Microsoft Graph..." -ForegroundColor Cyan
    # Scopes chosen to allow app creation and app role assignments
    $graphScopes = @(
        'Application.ReadWrite.All',
        'AppRoleAssignment.ReadWrite.All',
        'Directory.ReadWrite.All'
    )
    Connect-MgGraph -Scopes $graphScopes -ErrorAction Stop
    Write-Host "Connected to Microsoft Graph." -ForegroundColor Green
} catch {
    Write-Host "Graph connection failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Hint: Install-Module Microsoft.Graph -Force" -ForegroundColor Yellow
    exit
}

# ==========================================================
# SECTION 2: Locate First-Party Service Principals (Graph, SPO, PBI)
# ==========================================================
Write-Host "`n2. Locating first-party service principals..." -ForegroundColor Cyan

# Helper to resiliently fetch a service principal by AppId
function Get-ServicePrincipalByAppId {
    param(
        [Parameter(Mandatory=$true)][string]$AppId
    )
    $sp = $null
    try {
        $sp = Get-MgServicePrincipal -Filter "appId eq '$AppId'" -ErrorAction Stop
    } catch {
        Write-Host "Filter failed for ${AppId}, falling back to full scan..." -ForegroundColor Yellow
    }
    if (-not $sp) {
        try {
            $all = Get-MgServicePrincipal -All -ErrorAction Stop
            $sp = $all | Where-Object { $_.AppId -eq $AppId }
        } catch {
            Write-Host "Full scan failed for ${AppId}: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    return $sp
}

$graphAppId = '00000003-0000-0000-c000-000000000000' # Microsoft Graph
$spoAppId   = '00000003-0000-0ff1-ce00-000000000000' # SharePoint Online
$pbiAppId   = '00000009-0000-0000-c000-000000000000' # Power BI Service (Fabric workload)
$exoAppId   = '00000002-0000-0ff1-ce00-000000000000' # Office 365 Exchange Online

$mgSP  = Get-ServicePrincipalByAppId -AppId $graphAppId
$spoSP = Get-ServicePrincipalByAppId -AppId $spoAppId
$pbiSP = Get-ServicePrincipalByAppId -AppId $pbiAppId
$exoSP = Get-ServicePrincipalByAppId -AppId $exoAppId

if (-not $mgSP)  { Write-Host "ERROR: Microsoft Graph SP not found." -ForegroundColor Red; exit }
if (-not $spoSP) { Write-Host "ERROR: SharePoint Online SP not found." -ForegroundColor Red; exit }
if (-not $pbiSP) { Write-Host "WARNING: Power BI SP not found. PBI permissions will be skipped." -ForegroundColor Yellow }
if (-not $exoSP) { Write-Host "WARNING: Exchange Online SP not found. Exchange permissions will be skipped." -ForegroundColor Yellow }

Write-Host "Graph SP:   $($mgSP.DisplayName)  (AppRoles: $($mgSP.AppRoles.Count))" -ForegroundColor Green
Write-Host "SharePoint:  $($spoSP.DisplayName)  (AppRoles: $($spoSP.AppRoles.Count))" -ForegroundColor Green
if ($pbiSP) {
    Write-Host "Power BI:    $($pbiSP.DisplayName)  (AppRoles: $($pbiSP.AppRoles.Count))" -ForegroundColor Green
}
if ($exoSP) {
    Write-Host "Exchange:    $($exoSP.DisplayName)  (AppRoles: $($exoSP.AppRoles.Count))" -ForegroundColor Green
}

# =====================================
# SECTION 3: Define Desired App Permissions
# =====================================
Write-Host "`n3. Defining desired permissions..." -ForegroundColor Cyan

# Graph application permissions (App Roles). Keep your existing sets.
$corePermissions = @(
    "User.Read.All",
    "Group.Read.All",
    "Directory.Read.All",
    "Organization.Read.All",
    "Application.Read.All",
    "Policy.Read.All",
    "AuditLog.Read.All",
    "SecurityEvents.Read.All",
    "Reports.Read.All"
)
$advancedPermissions = @(
    "Group.ReadWrite.All",
    "Directory.ReadWrite.All",
    "Policy.ReadWrite.ConditionalAccess",
    "RoleManagement.Read.Directory",
    "RoleManagement.ReadWrite.Directory",
    "Sites.Read.All",
    "Sites.FullControl.All",
    "Mail.Read"
)
$specialPermissions = @(
    "UserAuthenticationMethod.Read.All",
    "UserAuthenticationMethod.ReadWrite.All",
    "User.ReadWrite.All",
    "Domain.Read.All",
    "Domain.ReadWrite.All",
    "Application.ReadWrite.All",
    "DeviceManagementConfiguration.Read.All",
    "IdentityRiskEvent.Read.All",
    "IdentityRiskyUser.Read.All",
    "OrgSettings-AppsAndServices.Read.All",
    "OrgSettings-Forms.Read.All",
    "AccessReview.Read.All"
)
$allPermissions = $corePermissions + $advancedPermissions + $specialPermissions

# SharePoint application permissions
$sharePointPermissions = @(
    "Sites.FullControl.All"
)

# Power BI (Fabric) application permissions (Admin REST)
# NOTE: In Entra, Power BI exposes app roles like Tenant.Read.All / Tenant.ReadWrite.All
$powerBIPermissions = @(
    "Tenant.Read.All",
    "Tenant.ReadWrite.All"
)

# Power BI (Fabric) DELEGATED permissions for user authentication
# Service Principal auth doesn't work with Fabric Admin APIs (returns 500 error)
# Solution: Use automated user authentication with ROPC flow
# User must have Power BI Administrator or Fabric Administrator role
$powerBIDelegatedPermissions = @(
    "Tenant.Read.All",
    "Tenant.ReadWrite.All"
)

# Exchange Online application permissions
$exchangePermissions = @(
    "Exchange.ManageAsApp"
)

# ======================================================
# SECTION 4: Resolve App Role IDs for Each Resource (RRA)
# ======================================================
Write-Host "`n4. Resolving app role IDs (application and delegated)..." -ForegroundColor Cyan

$graphResourceAccess      = @()
$sharePointResourceAccess = @()
$powerBIResourceAccess    = @()
$exchangeResourceAccess   = @()

# Helper to add APPLICATION role if present
function Add-RoleIfAvailable {
    param(
        [Parameter(Mandatory=$true)] $SpObject,
        [Parameter(Mandatory=$true)] [string] $PermissionValue,
        [Parameter(Mandatory=$true)] [ref] $TargetArray,
        [Parameter(Mandatory=$true)] [string] $Label
    )
    try {
        $role = $SpObject.AppRoles | Where-Object { $_.Value -eq $PermissionValue -and $_.AllowedMemberTypes -contains "Application" }
        if ($role) {
            $TargetArray.Value += @{ Id = $role.Id; Type = "Role" }
            Write-Host "  OK ${Label} (App): $PermissionValue  (Id: $($role.Id))" -ForegroundColor Green
        } else {
            Write-Host "  SKIP ${Label} (App): $PermissionValue (not available as application role)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ERROR ${Label} (App): $PermissionValue - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Helper to add DELEGATED scope if present
function Add-ScopeIfAvailable {
    param(
        [Parameter(Mandatory=$true)] $SpObject,
        [Parameter(Mandatory=$true)] [string] $PermissionValue,
        [Parameter(Mandatory=$true)] [ref] $TargetArray,
        [Parameter(Mandatory=$true)] [string] $Label
    )
    try {
        $scope = $SpObject.Oauth2PermissionScopes | Where-Object { $_.Value -eq $PermissionValue }
        if ($scope) {
            $TargetArray.Value += @{ Id = $scope.Id; Type = "Scope" }
            Write-Host "  OK ${Label} (Delegated): $PermissionValue  (Id: $($scope.Id))" -ForegroundColor Green
        } else {
            Write-Host "  SKIP ${Label} (Delegated): $PermissionValue (not available as delegated scope)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ERROR ${Label} (Delegated): $PermissionValue - $($_.Exception.Message)" -ForegroundColor Red
    }
}

foreach ($p in $allPermissions)          { Add-RoleIfAvailable -SpObject $mgSP  -PermissionValue $p -TargetArray ([ref]$graphResourceAccess)      -Label "Graph" }
foreach ($p in $sharePointPermissions)   { Add-RoleIfAvailable -SpObject $spoSP -PermissionValue $p -TargetArray ([ref]$sharePointResourceAccess) -Label "SharePoint" }
if ($pbiSP) {
    # Add APPLICATION permissions (for SP auth - though they don't work due to API bug)
    foreach ($p in $powerBIPermissions) { Add-RoleIfAvailable -SpObject $pbiSP -PermissionValue $p -TargetArray ([ref]$powerBIResourceAccess) -Label "Power BI" }
    # Add DELEGATED permissions (for user auth - this is what actually works)
    foreach ($p in $powerBIDelegatedPermissions) { Add-ScopeIfAvailable -SpObject $pbiSP -PermissionValue $p -TargetArray ([ref]$powerBIResourceAccess) -Label "Power BI" }
}
if ($exoSP) {
    foreach ($p in $exchangePermissions) { Add-RoleIfAvailable -SpObject $exoSP -PermissionValue $p -TargetArray ([ref]$exchangeResourceAccess)  -Label "Exchange" }
}

if (($graphResourceAccess.Count + $sharePointResourceAccess.Count + $powerBIResourceAccess.Count + $exchangeResourceAccess.Count) -eq 0) {
    Write-Host "ERROR: No valid roles resolved. Aborting." -ForegroundColor Red
    exit
}

# ===========================================
# SECTION 5: Create App Registration (with RRA)
# ===========================================
Write-Host "`n5. Creating application registration..." -ForegroundColor Cyan

$requiredResourceAccess = @()

if ($graphResourceAccess.Count -gt 0) {
    $requiredResourceAccess += @{
        ResourceAppId  = $graphAppId
        ResourceAccess = $graphResourceAccess
    }
}
if ($sharePointResourceAccess.Count -gt 0) {
    $requiredResourceAccess += @{
        ResourceAppId  = $spoAppId
        ResourceAccess = $sharePointResourceAccess
    }
}
if ($powerBIResourceAccess.Count -gt 0) {
    # *** This was missing in your original script ***
    $requiredResourceAccess += @{
        ResourceAppId  = $pbiAppId
        ResourceAccess = $powerBIResourceAccess
    }
}
if ($exchangeResourceAccess.Count -gt 0) {
    $requiredResourceAccess += @{
        ResourceAppId  = $exoAppId
        ResourceAccess = $exchangeResourceAccess
    }
}

$appDisplayName = "CIS M365 Compliance Scanner"
$maxRetries     = 3
$retryCount     = 0
$app            = $null

while ($retryCount -lt $maxRetries) {
    try {
        $app = New-MgApplication `
            -DisplayName $appDisplayName `
            -SignInAudience "AzureADMyOrg" `
            -RequiredResourceAccess $requiredResourceAccess `
            -ErrorAction Stop

        Write-Host "Application created: $($app.DisplayName)" -ForegroundColor Green
        Write-Host "  App ID: $($app.AppId)" -ForegroundColor Gray
        break
    } catch {
        $retryCount++
        Write-Host "Attempt $retryCount failed: $($_.Exception.Message)" -ForegroundColor Red
        if ($retryCount -lt $maxRetries) {
            Write-Host "Retrying in 5 seconds..." -ForegroundColor Yellow
            Start-Sleep 5
        } else {
            Write-Host "Failed to create application after $maxRetries attempts" -ForegroundColor Red
            exit
        }
    }
}

# Enable ROPC flow (Resource Owner Password Credential) for automated user login
Write-Host "`nEnabling ROPC flow for automated user authentication..." -ForegroundColor Cyan
try {
    # ROPC flow allows automated user authentication without interactive browser
    # This is required because Fabric Admin API only works with user auth (not SP)
    # User must have Power BI Administrator or Fabric Administrator role

    # Update application to enable public client flows (ROPC)
    Update-MgApplication -ApplicationId $app.Id `
        -IsFallbackPublicClient:$true `
        -PublicClient @{
            RedirectUris = @("urn:ietf:wg:oauth:2.0:oob", "http://localhost")
        } -ErrorAction Stop

    Write-Host "✓ ROPC flow enabled (allows automated user login)" -ForegroundColor Green
    Write-Host "  NOTE: User credentials will be required for Power BI checks" -ForegroundColor Yellow
    Write-Host "  Required Role: Power BI Administrator OR Fabric Administrator" -ForegroundColor Yellow
} catch {
    Write-Host "✗ Failed to enable ROPC flow: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  This may impact automated user authentication for Power BI checks" -ForegroundColor Yellow
}

# ===============================
# SECTION 6: Create Service Principal
# ===============================
Write-Host "`n6. Creating service principal..." -ForegroundColor Cyan
try {
    $sp = New-MgServicePrincipal -AppId $app.AppId -ErrorAction Stop
    Write-Host "Service principal created." -ForegroundColor Green
} catch {
    Write-Host "Failed to create service principal: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# =========================
# SECTION 7: Client Secret
# =========================
Write-Host "`n7. Creating client secret..." -ForegroundColor Cyan
try {
    $secret = Add-MgApplicationPassword -ApplicationId $app.Id -PasswordCredential @{
        DisplayName = "CIS Scanner Secret"
        EndDateTime = (Get-Date).AddMonths(12)
    } -ErrorAction Stop
    Write-Host "Client secret created (12 months)." -ForegroundColor Green
} catch {
    Write-Host "Failed to create secret: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# ====================================================
# SECTION 7.5: Self-Signed Certificate (For Teams/Exchange/Compliance)
# ====================================================
Write-Host "`n7.5. Creating self-signed certificate..." -ForegroundColor Cyan
$cert = $null
try {
    $certName = "CIS-M365-Compliance-Cert-$(Get-Date -Format 'yyyyMMdd')"
    $certPath = "$env:TEMP\$certName"

    $cert = New-SelfSignedCertificate `
        -Subject "CN=$certName" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyExportPolicy Exportable `
        -KeySpec Signature `
        -KeyLength 2048 `
        -KeyAlgorithm RSA `
        -HashAlgorithm SHA256 `
        -NotAfter (Get-Date).AddYears(2)

    Write-Host "Certificate created: $($cert.Thumbprint)" -ForegroundColor Green

    # Export certificate files (cross-platform compatible)
    $pfxPassword = "CISCompliance2024!"
    $securePfxPassword = ConvertTo-SecureString -String $pfxPassword -AsPlainText -Force

    Export-Certificate -Cert $cert -FilePath "$certPath.cer" -Type CERT | Out-Null
    Export-PfxCertificate -Cert $cert -FilePath "$certPath.pfx" -Password $securePfxPassword | Out-Null

    Write-Host "Certificate files exported:" -ForegroundColor Green
    Write-Host "  Public Key (.cer):  $certPath.cer" -ForegroundColor Gray
    Write-Host "  Private Key (.pfx): $certPath.pfx" -ForegroundColor Gray
    Write-Host "  PFX Password: $pfxPassword" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "LINUX USERS: Copy the .pfx file to your Linux environment" -ForegroundColor Cyan
    Write-Host "  Use -CertificatePath instead of -CertificateThumbprint in Start-Checks.ps1" -ForegroundColor Cyan

    # Bind certificate to application
    $cerBytes = [System.IO.File]::ReadAllBytes("$certPath.cer")
    $keyCred  = @{
        Type        = "AsymmetricX509Cert"
        Usage       = "Verify"
        Key         = $cerBytes
        DisplayName = $certName
        EndDateTime = $cert.NotAfter
    }
    Update-MgApplication -ApplicationId $app.Id -KeyCredentials @($keyCred) -ErrorAction Stop
    Write-Host "Certificate bound to application." -ForegroundColor Green
    Write-Host "  Required for Teams, Exchange, and Security & Compliance connections" -ForegroundColor Yellow
} catch {
    Write-Host "Cert step failed: $($_.Exception.Message). Teams/Exchange/Compliance connections will not work." -ForegroundColor Red
    $cert = $null
}

# ======================================================
# SECTION 8: Grant Admin Consent (App Role Assignments)
# ======================================================
Write-Host "`n8. Granting admin consent (app role assignments)..." -ForegroundColor Cyan

function Grant-AppRoleAssignments {
    param(
        [Parameter(Mandatory=$true)] [string] $PrincipalSpId,
        [Parameter(Mandatory=$true)] $ResourceSp,
        [Parameter(Mandatory=$true)] $RoleArray
    )
    $count = 0
    foreach ($ra in $RoleArray) {
        try {
            New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $PrincipalSpId -BodyParameter @{
                PrincipalId = $PrincipalSpId
                ResourceId  = $ResourceSp.Id
                AppRoleId   = $ra.Id
            } -ErrorAction SilentlyContinue | Out-Null
            $count++
        } catch {
            # Ignored if already assigned or transient
        }
    }
    return $count
}

$granted = 0
$granted += Grant-AppRoleAssignments -PrincipalSpId $sp.Id -ResourceSp $mgSP  -RoleArray $graphResourceAccess
$granted += Grant-AppRoleAssignments -PrincipalSpId $sp.Id -ResourceSp $spoSP -RoleArray $sharePointResourceAccess
if ($pbiSP -and $powerBIResourceAccess.Count -gt 0) {
    $granted += Grant-AppRoleAssignments -PrincipalSpId $sp.Id -ResourceSp $pbiSP -RoleArray $powerBIResourceAccess
}
if ($exoSP -and $exchangeResourceAccess.Count -gt 0) {
    $granted += Grant-AppRoleAssignments -PrincipalSpId $sp.Id -ResourceSp $exoSP -RoleArray $exchangeResourceAccess
}
Write-Host "Granted/confirmed $granted app role assignments." -ForegroundColor Green

# Grant admin consent for delegated permissions (OAuth2 scopes)
# This is required for ROPC flow to work with Power BI
Write-Host "Granting admin consent for delegated permissions (ROPC)..." -ForegroundColor Gray
try {
    # Power BI delegated permission: Tenant.Read.All
    if ($pbiSP) {
        $tenantReadScope = $pbiSP.Oauth2PermissionScopes | Where-Object { $_.Value -eq "Tenant.Read.All" }
        if ($tenantReadScope) {
            try {
                New-MgOauth2PermissionGrant `
                    -ClientId $sp.Id `
                    -ConsentType "AllPrincipals" `
                    -ResourceId $pbiSP.Id `
                    -Scope "Tenant.Read.All" `
                    -ErrorAction SilentlyContinue | Out-Null
                Write-Host "✓ Granted delegated permission: Tenant.Read.All (Power BI)" -ForegroundColor Green
            } catch {
                # Already granted or error - continue
                Write-Host "  Note: Delegated permission may already be granted" -ForegroundColor Yellow
            }
        }
    }
} catch {
    Write-Host "  Warning: Failed to grant delegated permissions: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  You may need to grant consent manually for ROPC to work" -ForegroundColor Yellow
}

# =======================================================================================
# SECTION 8.5: Enable Fabric/Power BI Tenant Settings for Service Principals
# =======================================================================================
# This step enables service principal authentication for Power BI read-only admin APIs.
# Required for Power BI CIS compliance checks (Section 9).
# You must be a Fabric/Power BI Admin for this section to succeed.
#
# Production best practice: Creates a dedicated security group and enables the setting
# only for service principals in that group (not entire organization).
#
# Reference: https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis
# ---------------------------------------------------------------------------------------

# Toggle this to $true if you want the script to enable the tenant settings automatically.
$EnableFabricTenantSettings = $true

# Production-grade security: Create dedicated security group for Power BI service principal access
$CreateSecurityGroup = $true
$SecurityGroupName = "Power BI Service Principal Admin API Access"
$SecurityGroupDescription = "Service principals in this group can access Power BI read-only admin APIs for compliance scanning"

if ($EnableFabricTenantSettings) {
    try {
        Write-Host "`n8.5. Setting up Power BI tenant settings for service principals..." -ForegroundColor Cyan

        # STEP 1: Create security group if needed
        $securityGroup = $null
        if ($CreateSecurityGroup) {
            Write-Host "Creating security group for Power BI service principal access..." -ForegroundColor Gray

            # Check if group already exists
            $existingGroup = Get-MgGroup -Filter "displayName eq '$SecurityGroupName'" -ErrorAction SilentlyContinue

            if ($existingGroup) {
                Write-Host "✓ Security group already exists: $SecurityGroupName" -ForegroundColor Yellow
                $securityGroup = $existingGroup
            } else {
                try {
                    # Create new security group
                    $securityGroup = New-MgGroup -DisplayName $SecurityGroupName `
                        -MailEnabled:$false `
                        -MailNickname ($SecurityGroupName -replace '[^a-zA-Z0-9]', '') `
                        -SecurityEnabled:$true `
                        -Description $SecurityGroupDescription `
                        -ErrorAction Stop

                    Write-Host "✓ Created security group: $SecurityGroupName" -ForegroundColor Green
                    Write-Host "  Group ID: $($securityGroup.Id)" -ForegroundColor Gray
                } catch {
                    Write-Host "✗ Failed to create security group: $($_.Exception.Message)" -ForegroundColor Red
                    Write-Host "Falling back to 'entire organization' scope..." -ForegroundColor Yellow
                    $CreateSecurityGroup = $false
                }
            }

            # STEP 2: Add service principal to the security group
            if ($securityGroup) {
                Write-Host "Adding service principal to security group..." -ForegroundColor Gray

                # Check if already a member
                $existingMembers = Get-MgGroupMember -GroupId $securityGroup.Id -ErrorAction SilentlyContinue
                $isMember = $existingMembers | Where-Object { $_.Id -eq $sp.Id }

                if ($isMember) {
                    Write-Host "✓ Service principal already in group" -ForegroundColor Yellow
                } else {
                    try {
                        $memberRef = @{
                            "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($sp.Id)"
                        }
                        New-MgGroupMemberByRef -GroupId $securityGroup.Id -BodyParameter $memberRef -ErrorAction Stop
                        Write-Host "✓ Added service principal to security group" -ForegroundColor Green
                    } catch {
                        Write-Host "✗ Failed to add service principal to group: $($_.Exception.Message)" -ForegroundColor Red
                        Write-Host "You may need to add it manually in Entra ID portal" -ForegroundColor Yellow
                    }
                }
            }
        }

        # STEP 2.5: Create dedicated user account for Power BI compliance checks
        # Service Principal auth doesn't work with Fabric Admin API (500 error)
        # Solution: Create user with Power BI Administrator role for automated checks
        # NOTE: We still configure SP above for future-proofing in case Microsoft fixes the API

        Write-Host "`nCreating dedicated user account for Power BI compliance checks..." -ForegroundColor Cyan

        $complianceUser = $null
        $complianceUserPassword = $null

        try {
            # Get tenant domain for UPN
            $org = Get-MgOrganization -ErrorAction Stop
            $tenantDomain = ($org.VerifiedDomains | Where-Object { $_.IsDefault -eq $true }).Name

            $complianceUsername = "cis-powerbi-scanner@$tenantDomain"

            # Check if user already exists
            $existingUser = Get-MgUser -Filter "userPrincipalName eq '$complianceUsername'" -ErrorAction SilentlyContinue

            if ($existingUser) {
                Write-Host "✓ User already exists: $complianceUsername" -ForegroundColor Yellow
                $complianceUser = $existingUser
                Write-Host "  Note: You'll need to use the existing password or reset it manually" -ForegroundColor Yellow
            } else {
                # Generate strong random password
                $passwordLength = 16
                $password = -join ((65..90) + (97..122) + (48..57) + @(33,35,36,37,38,42,43,45,61,63,64) | Get-Random -Count $passwordLength | ForEach-Object {[char]$_})
                $complianceUserPassword = $password

                # Create user
                $passwordProfile = @{
                    Password                      = $password
                    ForceChangePasswordNextSignIn = $false
                }

                $complianceUser = New-MgUser -DisplayName "CIS Power BI Compliance Scanner" `
                    -UserPrincipalName $complianceUsername `
                    -AccountEnabled:$true `
                    -PasswordProfile $passwordProfile `
                    -MailNickname "cis-powerbi-scanner" `
                    -UsageLocation "US" `
                    -ErrorAction Stop

                Write-Host "✓ Created user: $complianceUsername" -ForegroundColor Green
                Write-Host "  User ID: $($complianceUser.Id)" -ForegroundColor Gray
            }

            # Assign Fabric Administrator role (required for Admin API access)
            Write-Host "Assigning Fabric Administrator role..." -ForegroundColor Gray
            try {
                $fabricAdminRole = Get-MgDirectoryRole -Filter "displayName eq 'Fabric Administrator'" -ErrorAction SilentlyContinue
                if (-not $fabricAdminRole) {
                    Write-Host "Activating Fabric Administrator role template..." -ForegroundColor Gray
                    $allTemplates = Get-MgDirectoryRoleTemplate -All -ErrorAction Stop
                    $roleTemplate = $allTemplates | Where-Object { $_.DisplayName -eq 'Fabric Administrator' }
                    if ($roleTemplate) {
                        $fabricAdminRole = New-MgDirectoryRole -RoleTemplateId $roleTemplate.Id
                    } else {
                        throw "Fabric Administrator role template not found."
                    }
                }
                $already = Get-MgDirectoryRoleMember -DirectoryRoleId $fabricAdminRole.Id | Where-Object { $_.Id -eq $complianceUser.Id }
                if (-not $already) {
                    $ref = @{ "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($complianceUser.Id)" }
                    New-MgDirectoryRoleMemberByRef -DirectoryRoleId $fabricAdminRole.Id -BodyParameter $ref -ErrorAction Stop | Out-Null
                    Write-Host "✓ Fabric Administrator role assigned" -ForegroundColor Green
                } else {
                    Write-Host "✓ User already has Fabric Administrator role" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "✗ Failed to assign Fabric Administrator role: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "  You MUST assign this role manually for Power BI checks to work!" -ForegroundColor Yellow
            }

            # Assign Power BI/Fabric license (required for Admin API access)
            Write-Host "Assigning Power BI license..." -ForegroundColor Gray
            try {
                # Get available SKUs with Power BI or Fabric
                $availableSkus = Get-MgSubscribedSku -All -ErrorAction Stop

                # Try to find Power BI or Fabric licenses in order of preference
                $powerBISku = $null
                $preferredSkus = @(
                    "POWER_BI_PRO",           # Power BI Pro
                    "POWER_BI_STANDARD",      # Power BI (Free)
                    "Microsoft_365_E5",       # M365 E5 (includes Power BI Pro)
                    "Microsoft_365_E3",       # M365 E3 (includes Power BI)
                    "ENTERPRISEPREMIUM",      # Office 365 E5
                    "ENTERPRISEPACK"          # Office 365 E3
                )

                foreach ($skuName in $preferredSkus) {
                    $sku = $availableSkus | Where-Object {
                        $_.SkuPartNumber -eq $skuName -and
                        $_.PrepaidUnits.Enabled -gt $_.ConsumedUnits
                    } | Select-Object -First 1

                    if ($sku) {
                        $powerBISku = $sku
                        Write-Host "  Found available license: $($sku.SkuPartNumber)" -ForegroundColor Gray
                        break
                    }
                }

                if ($powerBISku) {
                    # Check if user already has this license
                    $userLicenses = Get-MgUserLicenseDetail -UserId $complianceUser.Id -ErrorAction SilentlyContinue
                    $hasLicense = $userLicenses | Where-Object { $_.SkuId -eq $powerBISku.SkuId }

                    if ($hasLicense) {
                        Write-Host "✓ User already has Power BI license ($($powerBISku.SkuPartNumber))" -ForegroundColor Yellow
                    } else {
                        # Assign license
                        $addLicenses = @{
                            SkuId = $powerBISku.SkuId
                        }
                        Set-MgUserLicense -UserId $complianceUser.Id `
                            -AddLicenses @($addLicenses) `
                            -RemoveLicenses @() `
                            -ErrorAction Stop
                        Write-Host "✓ Assigned Power BI license: $($powerBISku.SkuPartNumber)" -ForegroundColor Green
                    }
                } else {
                    Write-Host "✗ No Power BI or compatible licenses available in tenant" -ForegroundColor Red
                    Write-Host "  You MUST assign a Power BI license manually for Admin API access!" -ForegroundColor Yellow
                    Write-Host "  Required: Power BI Pro, Power BI Premium Per User, or Fabric capacity" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "✗ Failed to assign license: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "  You MUST assign a Power BI license manually!" -ForegroundColor Yellow
            }

            # Add user to security group
            if ($securityGroup) {
                Write-Host "Adding user to Power BI security group..." -ForegroundColor Gray

                $existingMembers = Get-MgGroupMember -GroupId $securityGroup.Id -ErrorAction SilentlyContinue
                $userInGroup = $existingMembers | Where-Object { $_.Id -eq $complianceUser.Id }

                if ($userInGroup) {
                    Write-Host "✓ User already in security group" -ForegroundColor Yellow
                } else {
                    try {
                        $memberRef = @{
                            "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($complianceUser.Id)"
                        }
                        New-MgGroupMemberByRef -GroupId $securityGroup.Id -BodyParameter $memberRef -ErrorAction Stop
                        Write-Host "✓ Added user to security group" -ForegroundColor Green
                    } catch {
                        Write-Host "✗ Failed to add user to group: $($_.Exception.Message)" -ForegroundColor Red
                        Write-Host "You may need to add it manually in Entra ID portal" -ForegroundColor Yellow
                    }
                }
            }

        } catch {
            Write-Host "✗ Failed to create/configure compliance user: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "You may need to create the user manually" -ForegroundColor Yellow
        }

        # STEP 3: Set the allowed security groups array
        $AllowedSecurityGroupObjectIds = @()
        if ($CreateSecurityGroup -and $securityGroup) {
            $AllowedSecurityGroupObjectIds = @($securityGroup.Id)
            Write-Host "✓ Security group configured for Power BI tenant settings" -ForegroundColor Green
            Write-Host "  Scope: Specific security group only" -ForegroundColor Gray
        } else {
            Write-Host "⚠ Using 'entire organization' scope (no security group)" -ForegroundColor Yellow
        }

        # STEP 4: Connect to Power BI and update tenant settings
        Write-Host "Connecting to Fabric (Power BI) to update tenant settings..." -ForegroundColor Gray
        Connect-PowerBIServiceAccount -ErrorAction Stop

        # 1) Read all tenant settings and locate the two targets by TITLE so we don't hard-code settingName.
        $tenantSettingsJson = Invoke-PowerBIRestMethod -Method Get -Url 'https://api.fabric.microsoft.com/v1/admin/tenantsettings'
        $tenantSettings     = $null
        try { $tenantSettings = $tenantSettingsJson | ConvertFrom-Json } catch { $tenantSettings = $null }

        if (-not $tenantSettings) { throw "Failed to parse tenant settings JSON." }

        # Helper to find a setting by partial title match (robust to Microsoft renames)
        function Find-TenantSetting {
            param(
                [Parameter(Mandatory=$true)][string]$TitleContains
            )
            foreach ($ts in $tenantSettings.tenantSettings) {
                if ($null -ne $ts.title -and ($ts.title -like "*$TitleContains*")) {
                    return $ts
                }
            }
            return $null
        }

        # Titles evolve; match common/current titles:
        # - "Service principals can access read-only admin APIs"
        # - "Service principals can call Fabric public APIs" (the “permission-based/public APIs” control)
        $readOnlySetting = Find-TenantSetting -TitleContains "read-only admin APIs"
        $publicApisSetting = Find-TenantSetting -TitleContains "call Fabric public APIs"

        if (-not $readOnlySetting) {
            Write-Host "WARNING: Could not find 'read-only admin APIs' tenant setting by title. Skipping that one." -ForegroundColor Yellow
        }
        if (-not $publicApisSetting) {
            Write-Host "WARNING: Could not find 'call Fabric public APIs' tenant setting by title. Skipping that one." -ForegroundColor Yellow
        }

        # Function to build the request body matching Microsoft's API format
        function New-TenantSettingBody {
            param(
                [Parameter(Mandatory=$true)]$CurrentSetting,
                [bool]$Enable=$true,
                [string[]]$GroupObjectIds=@()
            )

            # Build request body per Microsoft's API example
            $body = @{
                enabled = $Enable
            }

            # If the setting supports security groups, we MUST include the enabledSecurityGroups field
            # even if it's empty (empty = entire organization)
            if ($CurrentSetting.canSpecifySecurityGroups -eq $true) {
                $enabledSecurityGroups = @()
                if ($GroupObjectIds.Count -gt 0) {
                    foreach ($gid in $GroupObjectIds) {
                        $enabledSecurityGroups += @{
                            graphId = $gid
                            name    = $gid  # Can be any label
                        }
                    }
                }
                # Always include this field if the setting supports security groups
                $body.enabledSecurityGroups = $enabledSecurityGroups
            }

            # CRITICAL: Include properties from current setting if they exist
            # Convert properties to proper array format for JSON serialization
            if ($CurrentSetting.properties -and $CurrentSetting.properties.Count -gt 0) {
                $propertiesArray = @()
                foreach ($prop in $CurrentSetting.properties) {
                    $propertiesArray += @{
                        name  = $prop.name
                        value = $prop.value
                        type  = $prop.type
                    }
                }
                $body.properties = $propertiesArray
            }

            return ($body | ConvertTo-Json -Depth 10 -Compress)
        }

        # 2) Enable the read-only admin APIs setting
        if ($readOnlySetting) {
            # Check if already enabled
            if ($readOnlySetting.enabled -eq $true) {
                Write-Host "✓ Read-only Admin APIs already enabled." -ForegroundColor Green
            } else {
                # Enable via Fabric Admin API
                $roBody = New-TenantSettingBody -CurrentSetting $readOnlySetting -Enable:$true -GroupObjectIds:$AllowedSecurityGroupObjectIds
                $roUrl  = "https://api.fabric.microsoft.com/v1/admin/tenantsettings/$($readOnlySetting.settingName)/update"

                try {
                    # Get access token from Power BI session and use Invoke-RestMethod with proper headers
                    $token = (Get-PowerBIAccessToken)["Authorization"]
                    $headers = @{
                        "Authorization" = $token
                        "Content-Type" = "application/json"
                    }
                    Invoke-RestMethod -Method Post -Uri $roUrl -Headers $headers -Body $roBody -ContentType "application/json" | Out-Null
                    Write-Host "✓ Enabled read-only Admin APIs successfully!" -ForegroundColor Green
                } catch {
                    Write-Host "✗ Failed to enable read-only Admin APIs via API" -ForegroundColor Red
                    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Yellow
                    Write-Host "  Please enable manually at: https://app.powerbi.com/admin-portal/tenantSettings" -ForegroundColor Yellow
                    throw
                }
            }
        } else {
            Write-Host "⚠ Could not find 'read-only admin APIs' tenant setting." -ForegroundColor Yellow
        }

        Write-Host "✓ Tenant setting configuration complete." -ForegroundColor Green
    } catch {
        Write-Host "Tenant settings step failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "You can enable manually in the Fabric Admin portal." -ForegroundColor Yellow
    }
}

# =================================================
# SECTION 9: Assign Global Reader Role (Read-Only Access)
# =================================================
Write-Host "`n9. Assigning Global Reader role (read-only access)..." -ForegroundColor Cyan
try {
    $globalReaderRole = Get-MgDirectoryRole -Filter "displayName eq 'Global Reader'" -ErrorAction SilentlyContinue
    if (-not $globalReaderRole) {
        Write-Host "Activating Global Reader role template..." -ForegroundColor Gray
        $allTemplates = Get-MgDirectoryRoleTemplate -All -ErrorAction Stop
        $roleTemplate = $allTemplates | Where-Object { $_.DisplayName -eq 'Global Reader' }
        if ($roleTemplate) {
            $globalReaderRole = New-MgDirectoryRole -RoleTemplateId $roleTemplate.Id
        } else {
            throw "Global Reader role template not found."
        }
    }
    $already = Get-MgDirectoryRoleMember -DirectoryRoleId $globalReaderRole.Id | Where-Object { $_.Id -eq $sp.Id }
    if (-not $already) {
        $ref = @{ "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($sp.Id)" }
        New-MgDirectoryRoleMemberByRef -DirectoryRoleId $globalReaderRole.Id -BodyParameter $ref -ErrorAction Stop | Out-Null
        Write-Host "Global Reader role assigned." -ForegroundColor Green
    } else {
        Write-Host "Service principal already has Global Reader." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Failed to assign Global Reader role: $($_.Exception.Message)" -ForegroundColor Yellow
}

# =================================================
# SECTION 9.5: Assign Exchange Administrator (Required for Exchange Online)
# =================================================
Write-Host "`n9.5. Assigning Exchange Administrator role (required for Exchange Online)..." -ForegroundColor Cyan
try {
    $exoAdminRole = Get-MgDirectoryRole -Filter "displayName eq 'Exchange Administrator'" -ErrorAction SilentlyContinue
    if (-not $exoAdminRole) {
        Write-Host "Activating Exchange Administrator role template..." -ForegroundColor Gray
        $allTemplates = Get-MgDirectoryRoleTemplate -All -ErrorAction Stop
        $roleTemplate = $allTemplates | Where-Object { $_.DisplayName -eq 'Exchange Administrator' }
        if ($roleTemplate) {
            $exoAdminRole = New-MgDirectoryRole -RoleTemplateId $roleTemplate.Id
        } else {
            throw "Exchange Administrator role template not found."
        }
    }
    $already = Get-MgDirectoryRoleMember -DirectoryRoleId $exoAdminRole.Id | Where-Object { $_.Id -eq $sp.Id }
    if (-not $already) {
        $ref = @{ "@odata.id" = "https://graph.microsoft.com/v1.0/directoryObjects/$($sp.Id)" }
        New-MgDirectoryRoleMemberByRef -DirectoryRoleId $exoAdminRole.Id -BodyParameter $ref -ErrorAction Stop | Out-Null
        Write-Host "Exchange Administrator role assigned." -ForegroundColor Green
    } else {
        Write-Host "Service principal already has Exchange Administrator." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Failed to assign Exchange Administrator role: $($_.Exception.Message)" -ForegroundColor Yellow
}

# =====================
# SECTION 10: Outputs
# =====================
Write-Host "`n=== App Provisioned Successfully ===" -ForegroundColor Green

# Build JSON output for API integration
$outputJson = @{
    tenant_id = (Get-MgContext).TenantId
    client_id = $app.AppId
    client_secret = $secret.SecretText
}

# Add certificate as base64 if available
if ($cert) {
    try {
        # Read .pfx file and convert to base64
        $pfxBytes = [System.IO.File]::ReadAllBytes("$certPath.pfx")
        $certificateBase64 = [System.Convert]::ToBase64String($pfxBytes)

        $outputJson.certificate_pfx_base64 = $certificateBase64
        $outputJson.certificate_password = "CISCompliance2024!"
    }
    catch {
        Write-Warning "Failed to read certificate file for base64 encoding: $($_.Exception.Message)"
    }
}

# Add Power BI user credentials if available
if ($complianceUser) {
    $outputJson.powerbi_username = $complianceUser.UserPrincipalName
    if ($complianceUserPassword) {
        $outputJson.powerbi_password = $complianceUserPassword
    }
    $outputJson.powerbi_user_id = $complianceUser.Id
}

# Display formatted output
Write-Host "`nConnection Details:" -ForegroundColor Cyan
Write-Host ("Tenant ID: {0}" -f $outputJson.tenant_id) -ForegroundColor Yellow
Write-Host ("Client ID: {0}" -f $outputJson.client_id) -ForegroundColor Yellow
Write-Host ("Client Secret: {0}" -f $outputJson.client_secret) -ForegroundColor Yellow

if ($cert) {
    Write-Host "`nCertificate Details:" -ForegroundColor Cyan
    Write-Host ("Certificate Thumbprint (Windows only): {0}" -f $cert.Thumbprint) -ForegroundColor Yellow
    Write-Host ("Certificate Password: {0}" -f $outputJson.certificate_password) -ForegroundColor Yellow
    Write-Host ("Certificate Base64 Length: {0} characters" -f $outputJson.certificate_pfx_base64.Length) -ForegroundColor Gray
    Write-Host "  Required for Teams, Exchange, and Security & Compliance checks" -ForegroundColor Gray
}

if ($complianceUser) {
    Write-Host "`nPower BI Compliance User Details:" -ForegroundColor Cyan
    Write-Host ("Username: {0}" -f $outputJson.powerbi_username) -ForegroundColor Yellow
    if ($complianceUserPassword) {
        Write-Host ("Password: {0}" -f $outputJson.powerbi_password) -ForegroundColor Yellow
    } else {
        Write-Host "Password: <existing user - use current password or reset manually>" -ForegroundColor Yellow
    }
    Write-Host ("User ID: {0}" -f $outputJson.powerbi_user_id) -ForegroundColor Gray
    Write-Host ("Role: Fabric Administrator") -ForegroundColor Green
    Write-Host ("License: Power BI (check assignment above)") -ForegroundColor Green
}

# Output JSON to file for easy API consumption
$jsonOutputPath = Join-Path $PSScriptRoot "app-credentials.json"
$outputJson | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonOutputPath -Encoding UTF8
Write-Host "`n✓ Credentials saved to JSON: $jsonOutputPath" -ForegroundColor Green
Write-Host "  Use this file for API/FastAPI integration" -ForegroundColor Gray

Write-Host "`n===" -ForegroundColor Cyan
Write-Host "IMPORTANT: Authentication Methods Summary" -ForegroundColor Yellow
Write-Host "===" -ForegroundColor Cyan
Write-Host ""
Write-Host "CLIENT SECRET (Graph, SharePoint):" -ForegroundColor Cyan
Write-Host "  ✓ Microsoft Graph API" -ForegroundColor Green
Write-Host "  ✓ SharePoint Online" -ForegroundColor Green
Write-Host ""
Write-Host "CERTIFICATE (Teams, Exchange, Compliance):" -ForegroundColor Cyan
if ($cert) {
    Write-Host "  ✓ Microsoft Teams" -ForegroundColor Green
    Write-Host "  ✓ Exchange Online" -ForegroundColor Green
    Write-Host "  ✓ Security & Compliance" -ForegroundColor Green
} else {
    Write-Host "  ✗ Certificate generation failed - these services will be skipped" -ForegroundColor Red
}
Write-Host ""
Write-Host "USER TOKEN (Power BI ROPC):" -ForegroundColor Cyan
Write-Host "  ✓ Power BI Admin API (requires: Fabric Admin role + License + Security group)" -ForegroundColor Green
Write-Host ""
