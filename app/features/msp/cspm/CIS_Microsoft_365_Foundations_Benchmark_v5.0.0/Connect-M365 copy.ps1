# M365 Authentication Script
# Generic authentication for Microsoft 365 services
# Called by SimpleMainScript.ps1

# Global variable to store Power BI user token (for hybrid authentication)
# Must be global so check scripts can access it
$global:PowerBIUserToken = $null

function Connect-M365Services {
    param(
        [string]$TenantId,
        [string]$ClientId = $null,
        [string]$ClientSecret = $null,
        [string]$CertificateThumbprint = $null,
        [string]$CertificatePath = $null,        # Path to .pfx file (file-based)
        [string]$CertificateBase64 = $null,      # Base64 encoded .pfx content (API-based)
        [string]$CertificatePassword = $null,    # Password for .pfx file/content
        [string]$Username = $null,
        [string]$Password = $null
    )

    Write-Host "Starting M365 authentication..." -ForegroundColor Cyan
    Write-Host "TenantId: $TenantId" -ForegroundColor Yellow
    if (-not [string]::IsNullOrEmpty($ClientId)) {
        Write-Host "Client ID: $($ClientId.Substring(0,8))..." -ForegroundColor Yellow
    }

    try {
        # Determine authentication method
        $useServicePrincipal = (-not [string]::IsNullOrEmpty($ClientId) -and (-not [string]::IsNullOrEmpty($ClientSecret) -or -not [string]::IsNullOrEmpty($CertificateThumbprint) -or -not [string]::IsNullOrEmpty($CertificatePath) -or -not [string]::IsNullOrEmpty($CertificateBase64)))
        $useCertificateAuth = (-not [string]::IsNullOrEmpty($CertificateThumbprint) -or -not [string]::IsNullOrEmpty($CertificatePath) -or -not [string]::IsNullOrEmpty($CertificateBase64))

        # Load certificate from base64 string (API/FastAPI compatible - no file storage needed)
        $certificate = $null
        if (-not [string]::IsNullOrEmpty($CertificateBase64)) {
            Write-Host "Loading certificate from base64 string (in-memory, no file storage)..." -ForegroundColor Yellow
            try {
                # Decode base64 to byte array
                $certBytes = [System.Convert]::FromBase64String($CertificateBase64)

                if (-not [string]::IsNullOrEmpty($CertificatePassword)) {
                    $secureCertPassword = ConvertTo-SecureString $CertificatePassword -AsPlainText -Force
                    $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certBytes, $secureCertPassword)
                } else {
                    $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certBytes)
                }
                Write-Host "✓ Certificate loaded from base64 (Thumbprint: $($certificate.Thumbprint))" -ForegroundColor Green
                # Override thumbprint with loaded certificate's thumbprint
                $CertificateThumbprint = $certificate.Thumbprint
            }
            catch {
                Write-Warning "Failed to load certificate from base64: $($_.Exception.Message)"
                throw "Certificate loading failed. Ensure the base64 string is valid .pfx content and password is correct."
            }
        }
        # Load certificate from file if path provided (file-based fallback)
        elseif (-not [string]::IsNullOrEmpty($CertificatePath)) {
            Write-Host "Loading certificate from file: $CertificatePath" -ForegroundColor Yellow
            try {
                if (-not [string]::IsNullOrEmpty($CertificatePassword)) {
                    $secureCertPassword = ConvertTo-SecureString $CertificatePassword -AsPlainText -Force
                    $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath, $secureCertPassword)
                } else {
                    $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath)
                }
                Write-Host "✓ Certificate loaded successfully (Thumbprint: $($certificate.Thumbprint))" -ForegroundColor Green
                # Override thumbprint with loaded certificate's thumbprint
                $CertificateThumbprint = $certificate.Thumbprint
            }
            catch {
                Write-Warning "Failed to load certificate from file: $($_.Exception.Message)"
                throw "Certificate loading failed. Ensure the .pfx file exists and password is correct."
            }
        }

        if ($useServicePrincipal) {
            if ($useCertificateAuth) {
                if (-not [string]::IsNullOrEmpty($CertificateBase64)) {
                    Write-Host "Using Service Principal with Certificate Base64 authentication (API/FastAPI compatible)" -ForegroundColor Green
                } elseif (-not [string]::IsNullOrEmpty($CertificatePath)) {
                    Write-Host "Using Service Principal with Certificate File authentication (Linux-compatible)" -ForegroundColor Green
                } else {
                    Write-Host "Using Service Principal with Certificate Thumbprint authentication (Windows Certificate Store)" -ForegroundColor Green
                }
            } else {
                Write-Host "Using Service Principal with Client Secret authentication" -ForegroundColor Green
                $secureSecret = ConvertTo-SecureString $ClientSecret -AsPlainText -Force
                $credential = New-Object System.Management.Automation.PSCredential($ClientId, $secureSecret)
            }
        } else {
            Write-Host "Using Interactive User authentication" -ForegroundColor Green
        }        # Hybrid Authentication: Get user token via ROPC if Username/Password provided
        # This is needed because Service Principal auth doesn't work with Fabric Admin API
        if (-not [string]::IsNullOrEmpty($Username) -and -not [string]::IsNullOrEmpty($Password)) {
            Write-Host "Obtaining Power BI user token via ROPC flow..." -ForegroundColor Yellow
            try {
                $tokenEndpoint = "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
                $tokenBody = @{
                    client_id     = $ClientId
                    client_secret = $ClientSecret
                    scope         = "https://analysis.windows.net/powerbi/api/.default"
                    username      = $Username
                    password      = $Password
                    grant_type    = "password"
                }

                $tokenResponse = Invoke-RestMethod -Method Post -Uri $tokenEndpoint -ContentType "application/x-www-form-urlencoded" -Body $tokenBody -ErrorAction Stop
                $global:PowerBIUserToken = $tokenResponse.access_token

                Write-Host "✓ Power BI user token obtained (valid for $($tokenResponse.expires_in) seconds)" -ForegroundColor Green
                Write-Host "  This token will be used for Power BI compliance checks (9.1.x)" -ForegroundColor Gray
            }
            catch {
                $errorDetails = $_.ErrorDetails.Message
                if ($errorDetails) {
                    try {
                        $errorJson = $errorDetails | ConvertFrom-Json
                        Write-Warning "Failed to obtain Power BI user token:"
                        Write-Warning "  Error: $($errorJson.error)"
                        Write-Warning "  Description: $($errorJson.error_description)"
                    }
                    catch {
                        Write-Warning "Failed to obtain Power BI user token: $($_.Exception.Message)"
                    }
                }
                else {
                    Write-Warning "Failed to obtain Power BI user token: $($_.Exception.Message)"
                }
                Write-Warning "Power BI checks may fail. Ensure user has correct permissions and ROPC is enabled."
                $global:PowerBIUserToken = $null
            }
        }

        # Connect to Microsoft Graph
        Write-Host "Connecting to Microsoft Graph..." -ForegroundColor Yellow
        try {
            if ($useServicePrincipal) {
                if ($useCertificateAuth) {
                    if ($certificate) {
                        # Use certificate object (Linux-compatible)
                        Connect-MgGraph -ClientId $ClientId -Certificate $certificate -TenantId $TenantId -NoWelcome -ErrorAction Stop
                    } else {
                        # Use thumbprint (Windows Certificate Store)
                        Connect-MgGraph -ClientId $ClientId -CertificateThumbprint $CertificateThumbprint -TenantId $TenantId -NoWelcome -ErrorAction Stop
                    }
                } else {
                    Connect-MgGraph -ClientSecretCredential $credential -TenantId $TenantId -NoWelcome -ErrorAction Stop
                }
            } else {
                Connect-MgGraph -TenantId $TenantId -Scopes @(
                    "User.Read.All",
                    "Group.Read.All",
                    "Group.ReadWrite.All",
                    "Directory.Read.All",
                    "Directory.ReadWrite.All",
                    "Organization.Read.All",
                    "Application.Read.All",
                    "Policy.Read.All",
                    "Policy.ReadWrite.Authorization",
                    "Policy.ReadWrite.AuthenticationMethod",
                    "Policy.ReadWrite.ConditionalAccess",
                    "AuditLog.Read.All",
                    "RoleManagement.Read.Directory",
                    "RoleManagement.ReadWrite.Directory",
                    "Sites.Read.All",
                    "Reports.Read.All",
                    "Mail.Read",
                    "UserAuthenticationMethod.Read.All",
                    "UserAuthenticationMethod.ReadWrite.All",
                    "User.ReadWrite.All",
                    "Domain.Read.All",
                    "Domain.ReadWrite.All",
                    "OrgSettings-AppsAndServices.Read.All",
                    "OrgSettings-Forms.Read.All",
                    "Application.ReadWrite.All",
                    "DeviceManagementConfiguration.Read.All",
                    "DeviceManagementConfiguration.ReadWrite.All",
                    "IdentityRiskEvent.Read.All",
                    "IdentityRiskyUser.Read.All",
                    "SecurityEvents.Read.All",
                    "Tennant.Read.All"
                ) -NoWelcome -ErrorAction Stop
            }
            Write-Host "✓ Microsoft Graph connected" -ForegroundColor Green
        }
        catch {
            Write-Warning "Graph connection failed: $($_.Exception.Message)"
        }

        # Connect to Teams
        Write-Host "Connecting to Microsoft Teams..." -ForegroundColor Yellow
        try {
            if ($useServicePrincipal) {
                if ($useCertificateAuth) {
                    if ($certificate) {
                        # Teams doesn't support certificate object directly, must use thumbprint
                        # So we need to temporarily install cert to user store on Linux
                        Write-Host "Note: Teams requires certificate in store, using thumbprint: $CertificateThumbprint" -ForegroundColor Yellow

                        # For Linux: Import certificate to user store temporarily
                        if ($PSVersionTable.Platform -eq 'Unix') {
                            try {
                                $certStore = New-Object System.Security.Cryptography.X509Certificates.X509Store('My', 'CurrentUser')
                                $certStore.Open('ReadWrite')
                                $certStore.Add($certificate)
                                $certStore.Close()
                                Write-Host "✓ Certificate temporarily installed to user store for Teams" -ForegroundColor Green
                            }
                            catch {
                                Write-Warning "Failed to install certificate to user store: $($_.Exception.Message)"
                            }
                        }
                    }
                    Connect-MicrosoftTeams -TenantId $TenantId -CertificateThumbprint $CertificateThumbprint -ApplicationId $ClientId -ErrorAction Stop
                    Write-Host "✓ Microsoft Teams connected" -ForegroundColor Green
                } else {
                    # Teams requires certificate for Service Principal auth
                    Write-Host "⊘ Teams skipped (requires certificate for Service Principal auth)" -ForegroundColor Yellow
                }
            } else {
                Connect-MicrosoftTeams -TenantId $TenantId -ErrorAction Stop
                Write-Host "✓ Microsoft Teams connected" -ForegroundColor Green
            }
        }
        catch {
            Write-Warning "Teams connection failed: $($_.Exception.Message)"
        }

        # Connect to Exchange Online
        Write-Host "Connecting to Exchange Online..." -ForegroundColor Yellow
        try {
            if ($useServicePrincipal) {
                # Get tenant domain name for Exchange/Compliance (they don't accept GUID)
                $org = Get-MgOrganization -ErrorAction Stop
                $tenantDomain = ($org.VerifiedDomains | Where-Object { $_.Name -like "*.onmicrosoft.com" }).Name

                if ($useCertificateAuth) {
                    if ($certificate) {
                        # Exchange doesn't support certificate object, must use thumbprint
                        # Certificate already installed to store in Teams section above
                        Write-Host "Using certificate thumbprint for Exchange: $CertificateThumbprint" -ForegroundColor Yellow
                    }
                    Connect-ExchangeOnline -CertificateThumbprint $CertificateThumbprint -AppId $ClientId -Organization $tenantDomain -ShowBanner:$false -ErrorAction Stop
                    Write-Host "✓ Exchange Online connected" -ForegroundColor Green
                } else {
                    # Exchange requires certificate for Service Principal auth
                    Write-Host "⊘ Exchange Online skipped (requires certificate for Service Principal auth)" -ForegroundColor Yellow
                }
            } else {
                Connect-ExchangeOnline -ShowBanner:$false -ErrorAction Stop
                Write-Host "✓ Exchange Online connected" -ForegroundColor Green
            }
        }
        catch {
            Write-Warning "Exchange Online connection failed: $($_.Exception.Message)"
        }

        # Connect to Security & Compliance Center
        Write-Host "Connecting to Security & Compliance..." -ForegroundColor Yellow
        try {
            if ($useServicePrincipal) {
                # Get tenant domain name for Exchange/Compliance (they don't accept GUID)
                $org = Get-MgOrganization -ErrorAction Stop
                $tenantDomain = ($org.VerifiedDomains | Where-Object { $_.Name -like "*.onmicrosoft.com" }).Name

                if ($useCertificateAuth) {
                    Connect-IPPSSession -CertificateThumbprint $CertificateThumbprint -AppId $ClientId -Organization $tenantDomain -ShowBanner:$false -ErrorAction Stop
                    Write-Host "✓ Security & Compliance connected" -ForegroundColor Green
                } else {
                    # Security & Compliance requires certificate for Service Principal auth
                    Write-Host "⊘ Security & Compliance skipped (requires certificate for Service Principal auth)" -ForegroundColor Yellow
                }
            } else {
                Connect-IPPSSession -ShowBanner:$false -ErrorAction Stop
                Write-Host "✓ Security & Compliance connected" -ForegroundColor Green
            }
        }
        catch {
            Write-Warning "Security & Compliance connection failed: $($_.Exception.Message)"
        }

        # Connect to SharePoint
        Write-Host "Connecting to SharePoint Online..." -ForegroundColor Yellow
        try {
            # Get tenant domain for SharePoint URL
            $org = Get-MgOrganization -ErrorAction Stop
            $domain = ($org.VerifiedDomains | Where-Object { $_.Name -like "*.onmicrosoft.com" }).Name -replace '\.onmicrosoft\.com$', ''
            $sharePointUrl = "https://$domain-admin.sharepoint.com"

            if ($useServicePrincipal) {
                if ($useCertificateAuth) {
                    Connect-PnPOnline -Url $sharePointUrl -ClientId $ClientId -Thumbprint $CertificateThumbprint -Tenant $TenantId -WarningAction SilentlyContinue -ErrorAction Stop
                } else {
                    Connect-PnPOnline -Url $sharePointUrl -ClientId $ClientId -ClientSecret $ClientSecret -WarningAction SilentlyContinue -ErrorAction Stop
                }
            } else {
                Connect-PnPOnline -Url $sharePointUrl -Interactive -WarningAction SilentlyContinue -ErrorAction Stop
            }
            Write-Host "✓ SharePoint Online connected" -ForegroundColor Green
        }
        catch {
            Write-Warning "SharePoint connection failed: $($_.Exception.Message)"
        }

        # Connect to Power BI
        # Note: If we obtained a user token via ROPC, we skip Power BI connection
        # because the checks will use $global:PowerBIUserToken directly
        if ($global:PowerBIUserToken) {
            Write-Host "✓ Power BI user token available - skipping Connect-PowerBIServiceAccount" -ForegroundColor Green
            Write-Host "  Power BI checks will use user token directly" -ForegroundColor Gray
        }
        else {
            Write-Host "Connecting to Power BI..." -ForegroundColor Yellow
            try {
                # Disconnect any existing Power BI sessions to avoid cached credentials
                try { Disconnect-PowerBIServiceAccount -ErrorAction SilentlyContinue } catch { }

                if ($useServicePrincipal) {
                    if ($useCertificateAuth) {
                        # For certificate-based authentication with Power BI
                        Connect-PowerBIServiceAccount -ServicePrincipal -ApplicationId $ClientId -CertificateThumbprint $CertificateThumbprint -TenantId $TenantId -ErrorAction Stop
                    } else {
                        # For service principal authentication with Power BI
                        Connect-PowerBIServiceAccount -ServicePrincipal -Credential $credential -TenantId $TenantId -ErrorAction Stop
                    }
                } else {
                    # For interactive authentication
                    Connect-PowerBIServiceAccount -ErrorAction Stop
                }
                Write-Host "✓ Power BI connected" -ForegroundColor Green
            }
            catch {
                Write-Warning "Power BI connection failed: $($_.Exception.Message)"
            }
        }

        Write-Host "✓ M365 authentication completed!" -ForegroundColor Cyan

        return @{
            TechType = "M365"
            Status = "Success"
        }
    }
    catch {
        Write-Error "M365 authentication failed: $($_.Exception.Message)"
        return @{
            TechType = "M365"
            Status = "Failed"
            Error = $_.Exception.Message
        }
    }
}