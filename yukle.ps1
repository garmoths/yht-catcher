$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Write-Info([string]$Message) {
    Write-Host "`n[YHT] $Message" -ForegroundColor Cyan
}

function Stop-Install([string]$Message) {
    Write-Host "`n[HATA] $Message" -ForegroundColor Red
    exit 1
}

function Find-Python {
    $Candidates = @(
        @{ Command = "py"; Arguments = @("-3") },
        @{ Command = "python"; Arguments = @() },
        @{ Command = "python3"; Arguments = @() }
    )

    foreach ($Candidate in $Candidates) {
        if (Get-Command $Candidate.Command -ErrorAction SilentlyContinue) {
            $VersionCheck = @($Candidate.Arguments) + @(
                "-c",
                "import sys; raise SystemExit(sys.version_info < (3, 9))"
            )
            & $Candidate.Command @VersionCheck 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $Candidate
            }
        }
    }
    return $null
}

$Python = Find-Python
if ($null -eq $Python) {
    Stop-Install "Python 3.9 veya daha yenisi bulunamadı. https://www.python.org/downloads/ adresinden kurun."
}

$VersionArguments = @($Python.Arguments) + @("--version")
$PythonVersion = (& $Python.Command @VersionArguments 2>&1 | Out-String).Trim()
Write-Info "Python bulundu: $PythonVersion"

if (-not (Test-Path $VenvPython)) {
    Write-Info "Sanal ortam oluşturuluyor..."
    $VenvArguments = @($Python.Arguments) + @("-m", "venv", $VenvDir)
    & $Python.Command @VenvArguments
    if ($LASTEXITCODE -ne 0) {
        Stop-Install "Sanal ortam oluşturulamadı."
    }
} else {
    Write-Info "Mevcut sanal ortam kullanılacak."
}

Write-Info "Python paketleri yükleniyor..."
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Stop-Install "pip güncellenemedi." }

& $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { Stop-Install "Proje paketleri yüklenemedi." }

& $VenvPython -m pip check
if ($LASTEXITCODE -ne 0) { Stop-Install "Paket doğrulaması başarısız." }

$EnvPath = Join-Path $ScriptDir ".env"
if (-not (Test-Path $EnvPath)) {
    Copy-Item (Join-Path $ScriptDir ".env.example") $EnvPath
    Write-Info ".env dosyası örnek ayarlardan oluşturuldu. Twilio bilgilerini girmeniz gerekiyor."
} else {
    Write-Info "Mevcut .env dosyası korundu."
}

$ChromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Chromium\Application\chrome.exe"
)
$ChromeFound = $false
foreach ($ChromePath in $ChromeCandidates) {
    if ($ChromePath -and (Test-Path $ChromePath)) {
        $ChromeFound = $true
        break
    }
}

if ($ChromeFound) {
    Write-Info "Chrome/Chromium bulundu."
} else {
    Write-Host "`n[UYARI] Chrome veya Chromium bulunamadı. Botu çalıştırmadan önce kurun." -ForegroundColor Yellow
}

Write-Host "`nKurulum tamamlandı. Botu başlatmak için:`n"
Write-Host "  cd `"$ScriptDir`""
Write-Host "  .venv\Scripts\python.exe main.py`n"
