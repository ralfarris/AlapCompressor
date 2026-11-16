$ErrorActionPreference = 'Stop'
# Build AlapCompressor pakai compiler C# bawaan Windows (.NET Framework 4.x) — tanpa install SDK tambahan.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path $csc)) { throw 'csc.exe (.NET Framework 4) tidak ditemukan.' }

$dist = Join-Path $root 'dist'
New-Item -ItemType Directory -Force $dist | Out-Null
$sources = Get-ChildItem (Join-Path $root 'src') -Filter *.cs | ForEach-Object { $_.FullName }

$ico = Join-Path $root 'assets\alapcompressor.ico'
$icoParam = if (Test-Path $ico) { "/win32icon:$ico" } else { "" }

$resParams = @(
    "/resource:$root\static\index.html,AlapCompressor.Web.index.html",
    "/resource:$root\static\css\style.css,AlapCompressor.Web.style.css",
    "/resource:$root\static\js\app.js,AlapCompressor.Web.app.js"
)

& $csc /nologo /target:winexe /optimize+ /platform:anycpu /codepage:65001 `
    "/out:$dist\AlapCompressor.exe" "/win32manifest:$root\src\app.manifest" $icoParam $resParams `
    /r:System.dll /r:System.Core.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll `
    /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll /r:System.Web.Extensions.dll `
    $sources
if ($LASTEXITCODE -ne 0) { throw "Build gagal ($LASTEXITCODE)" }
$size = [math]::Round((Get-Item "$dist\AlapCompressor.exe").Length / 1KB)
Write-Host "Build OK -> dist\AlapCompressor.exe ($size KB)"
