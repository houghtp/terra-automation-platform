# Simple M365 Connection Script - Batch-Aware Version
# Supports selective service connections based on batch requirements
# No logic, no DLL loading, just direct connections

$global:PowerBIUserToken = $null

function Connect-M365 {

    param(
        [string]$TenantId,
        [string]$TenantDomain,
        [string]$SharePointAdminUrl,
        [string]$ClientId,
        [string]$ClientSecret,
        [string]$CertificateThumbprint,
        [string]$CertificatePath,
        [string]$CertificateBase64,
        [string]$CertificatePassword,
        [string]$Username,
        [string]$Password,

        # Batch control parameters (optional)
        [switch]$SkipGraph,
        [switch]$SkipTeams,
        [switch]$SkipExchange
    )

    try {
        Write-Output "=== CONNECT-M365 DEBUG START ==="
        Write-Output "TenantId: $TenantId"
        Write-Output "TenantDomain: $TenantDomain"
        Write-Output "ClientId: $ClientId"
        Write-Output "Has ClientSecret: $(-not [string]::IsNullOrEmpty($ClientSecret))"
        Write-Output "Has CertificateBase64: $(-not [string]::IsNullOrEmpty($CertificateBase64))"
        Write-Output "Has CertificatePath: $(-not [string]::IsNullOrEmpty($CertificatePath))"
        Write-Output "Has CertificatePassword: $(-not [string]::IsNullOrEmpty($CertificatePassword))"
        Write-Output "Has Username: $(-not [string]::IsNullOrEmpty($Username))"
        Write-Output "Has Password: $(-not [string]::IsNullOrEmpty($Password))"
        Write-Output "SkipGraph: $SkipGraph"
        Write-Output "SkipTeams: $SkipTeams"
        Write-Output "SkipExchange: $SkipExchange"
        Write-Output "================================"

        # Set PowerShell HTTP client timeout to 5 minutes (default is sometimes too short)
        Write-Output "Setting HTTP timeout to 300 seconds..."
        $PSDefaultParameterValues = @{
            'Invoke-RestMethod:TimeoutSec' = 300
            'Invoke-WebRequest:TimeoutSec' = 300
        }

        # CRITICAL: Set .NET HttpClient timeout to 5 minutes (default is 100 seconds)
        # This affects the internal HTTP clients used by Exchange/Graph/Teams modules
        Write-Output "Setting .NET HttpClient timeout to 300 seconds..."

        # Set environment variable that some modules respect
        $env:POWERSHELL_HTTPCLIENT_TIMEOUT_SEC = "300"

        # Configure ServicePointManager for older .NET HTTP handling
        [System.Net.ServicePointManager]::MaxServicePointIdleTime = 300000
        [System.Net.ServicePointManager]::Expect100Continue = $false
        [System.Net.ServicePointManager]::DefaultConnectionLimit = 100

        Write-Output "✓ .NET HTTP settings configured (timeout: 300s)"

        # Determine authentication method
        Write-Output "Determining authentication method..."
        $hasCertificate = (-not [string]::IsNullOrEmpty($CertificatePath) -or -not [string]::IsNullOrEmpty($CertificateBase64))
        $hasClientSecret = (-not [string]::IsNullOrEmpty($ClientId) -and -not [string]::IsNullOrEmpty($ClientSecret))
        Write-Output "hasCertificate: $hasCertificate"
        Write-Output "hasClientSecret: $hasClientSecret"

        if (-not $hasCertificate -and -not $hasClientSecret) {
            throw "Authentication credentials missing: provide either (CertificatePath/CertificateBase64 + CertificatePassword) OR (ClientId + ClientSecret)"
        }

        # Certificate authentication (preferred)
        if ($hasCertificate) {
            if (-not $CertificatePassword) {
                throw "Certificate password is required when using certificate authentication"
            }

            # Load certificate
            Write-Output "Loading certificate..."
            if ($CertificatePath) {
                if (-not (Test-Path $CertificatePath)) {
                    throw "Certificate file not found at path: $CertificatePath"
                }
                # PowerShell Core 6+ uses -AsByteStream instead of -Encoding Byte
                $certBytes = Get-Content -Path $CertificatePath -AsByteStream -Raw
            } else {
                Write-Output "Decoding certificate from Base64..."
                $certBytes = [System.Convert]::FromBase64String($CertificateBase64)
                Write-Output "Certificate bytes: $($certBytes.Length) bytes"
            }

            Write-Output "Creating X509Certificate2 object..."
            $secureCertPassword = ConvertTo-SecureString $CertificatePassword -AsPlainText -Force
            $certificate = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certBytes, $secureCertPassword)
            $CertificateThumbprint = $certificate.Thumbprint
            Write-Output "Certificate Thumbprint: $CertificateThumbprint"

            # Install to user store for Teams/Graph certificate auth
            Write-Output "Installing certificate to CurrentUser\My store..."
            $certStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("My", "CurrentUser")
            $certStore.Open('ReadWrite')
            $certStore.Add($certificate)
            $certStore.Close()

            Write-Output "✓ Certificate loaded successfully"
        }
        elseif ($hasClientSecret) {
            Write-Output "Using client secret authentication (limited service support)"
            # Client secret auth - some services may not be available
        }

        # Get Power BI token if Username/Password provided (always needed for Power BI checks, no conflicts)
        if (-not [string]::IsNullOrEmpty($Username) -and -not [string]::IsNullOrEmpty($Password)) {
            Write-Output "Authenticating Power BI..."
            $body = @{
                grant_type = "password"
                client_id  = $ClientId
                username   = $Username
                password   = $Password
                resource   = "https://analysis.windows.net/powerbi/api"
                scope      = "openid"
            }
            try {
                $tokenResponse = Invoke-RestMethod -Uri "https://login.microsoftonline.com/$TenantId/oauth2/token" -Method POST -Body $body -ErrorAction Stop
                $global:PowerBIUserToken = $tokenResponse.access_token
                Write-Output "✓ Power BI token obtained"
            }
            catch {
                Write-Output "WARNING: Power BI token acquisition failed: $($_.Exception.Message)"
                Write-Output "WARNING: Power BI checks (9.1.x) may fail"
            }
        }
        else {
            Write-Output "WARNING: Power BI credentials not provided - Power BI checks (9.1.x) will be skipped"
        }

        # BATCH-SPECIFIC CONNECTIONS
        # Different batches connect to different services to avoid assembly conflicts

        if (-not $SkipExchange) {
            # EXCHANGE BATCH: Connect to Exchange, Compliance, SharePoint
            # These services require certificate authentication
            Write-Output "=== EXCHANGE BATCH CONNECTIONS ==="
            if ($hasCertificate) {
                Write-Output "Authenticating Exchange Online..."
                Write-Output "  Using Certificate object, AppId=$ClientId, Org=$TenantDomain"
                $exoStart = Get-Date
                try {
                    Connect-ExchangeOnline -Certificate $certificate -AppId $ClientId -Organization $TenantDomain -ShowBanner:$false
                    $exoDuration = (Get-Date) - $exoStart
                    Write-Output "  ✓ Exchange connected in $($exoDuration.TotalSeconds)s"
                } catch {
                    Write-Output "  ✗ Exchange FAILED: $($_.Exception.Message)"
                    throw
                }

                Write-Output "Authenticating Security & Compliance..."
                Write-Output "  Using Certificate object, AppId=$ClientId, Org=$TenantDomain"
                $complianceStart = Get-Date
                try {
                    Connect-IPPSSession -Certificate $certificate -AppId $ClientId -Organization $TenantDomain -ShowBanner:$false
                    $complianceDuration = (Get-Date) - $complianceStart
                    Write-Output "  ✓ Compliance connected in $($complianceDuration.TotalSeconds)s"
                } catch {
                    Write-Output "  ✗ Compliance FAILED: $($_.Exception.Message)"
                    throw
                }

                Write-Output "Authenticating SharePoint Online..."
                Write-Output "  Using Thumbprint=$CertificateThumbprint, ClientId=$ClientId"
                $spStart = Get-Date
                try {
                    Connect-PnPOnline -Url $SharePointAdminUrl -ClientId $ClientId -Thumbprint $CertificateThumbprint -Tenant $TenantId
                    $spDuration = (Get-Date) - $spStart
                    Write-Output "  ✓ SharePoint connected in $($spDuration.TotalSeconds)s"
                } catch {
                    Write-Output "  ✗ SharePoint FAILED: $($_.Exception.Message)"
                    throw
                }
            }
            elseif ($hasClientSecret) {
                Write-Output "Authenticating SharePoint Online (client secret)..."
                Connect-PnPOnline -Url $SharePointAdminUrl -ClientId $ClientId -ClientSecret $ClientSecret

                Write-Output "WARNING: Exchange/Compliance require certificate authentication - skipping"
            }
        }

        if (-not $SkipGraph) {
            # GRAPH BATCH: Connect to Graph only (isolated from Exchange/Teams)
            Write-Output "=== GRAPH BATCH CONNECTIONS ==="
            Write-Output "Authenticating Microsoft Graph..."
            $graphStart = Get-Date
            try {
                if ($hasCertificate) {
                    Write-Output "  Using CertificateThumbprint=$CertificateThumbprint, ClientId=$ClientId"
                    Connect-MgGraph -ClientId $ClientId -TenantId $TenantId -CertificateThumbprint $CertificateThumbprint -NoWelcome
                }
                elseif ($hasClientSecret) {
                    Write-Output "  Using ClientSecret, ClientId=$ClientId"
                    $secureSecret = ConvertTo-SecureString $ClientSecret -AsPlainText -Force
                    $credential = New-Object System.Management.Automation.PSCredential($ClientId, $secureSecret)
                    Connect-MgGraph -ClientSecretCredential $credential -TenantId $TenantId -NoWelcome
                }
                $graphDuration = (Get-Date) - $graphStart
                Write-Output "  ✓ Graph connected in $($graphDuration.TotalSeconds)s"
            } catch {
                Write-Output "  ✗ Graph FAILED: $($_.Exception.Message)"
                throw
            }
        }

        if (-not $SkipTeams) {
            # TEAMS BATCH: Connect to Teams only (requires certificate)
            Write-Output "=== TEAMS BATCH CONNECTIONS ==="
            if ($hasCertificate) {
                Write-Output "Authenticating Microsoft Teams..."
                Write-Output "  Using Certificate object, ApplicationId=$ClientId"
                $teamsStart = Get-Date
                try {
                    Import-Module MicrosoftTeams -Force -ErrorAction Stop
                    Connect-MicrosoftTeams -TenantId $TenantId -Certificate $certificate -ApplicationId $ClientId
                    $teamsDuration = (Get-Date) - $teamsStart
                    Write-Output "  ✓ Teams connected in $($teamsDuration.TotalSeconds)s"
                } catch {
                    Write-Output "  ✗ Teams FAILED: $($_.Exception.Message)"
                    throw
                }
            }
            else {
                Write-Output "WARNING: Teams requires certificate authentication - skipping"
            }
        }

        Write-Output "✓ Batch services connected"

        return @{
            Status = "Success"
            TechType = "M365"
            Error = $null
        }
    }
    catch {
        return @{
            Status = "Failed"
            TechType = "M365"
            Error = $_.Exception.Message
        }
    }
}
