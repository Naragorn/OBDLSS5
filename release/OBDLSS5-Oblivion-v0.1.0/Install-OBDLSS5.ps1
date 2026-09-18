[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [string] $GamePath,
    [string] $DependencyRoot = (Join-Path $PSScriptRoot 'Dependencies')
)

$ErrorActionPreference = 'Stop'
$GamePath = (Resolve-Path -LiteralPath $GamePath).Path
$Oblivion = Join-Path $GamePath 'Oblivion.exe'
if (-not (Test-Path -LiteralPath $Oblivion -PathType Leaf)) {
    throw "Oblivion.exe was not found below $GamePath"
}
if (Get-Process -Name Oblivion -ErrorAction SilentlyContinue) {
    throw 'Oblivion.exe is running. Close the game before installing.'
}

function Require-File([string] $RelativePath) {
    $path = Join-Path $DependencyRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing dependency: $RelativePath (expected at $path)"
    }
    return $path
}

$files = @(
    @{ Source = 'dgVoodoo\D3D9.dll'; Destination = 'D3D9.dll' },
    @{ Source = 'ReShade\ReShade32.dll'; Destination = 'dxgi.dll' },
    @{ Source = 'Feeder\dlss5-feed.addon32'; Destination = 'dlss5-feed.addon32' },
    @{ Source = 'Feeder\reshade-shaders\Shaders\DLSS5_Feed.fx'; Destination = 'reshade-shaders\Shaders\DLSS5_Feed.fx' },
    @{ Source = 'ReShadeShaders\Shaders\ReShade.fxh'; Destination = 'reshade-shaders\Shaders\ReShade.fxh' },
    @{ Source = 'ReShadeShaders\Shaders\ReShadeUI.fxh'; Destination = 'reshade-shaders\Shaders\ReShadeUI.fxh' },
    @{ Source = 'ReShadeShaders\Shaders\DrawText.fxh'; Destination = 'reshade-shaders\Shaders\DrawText.fxh' },
    @{ Source = 'Lumenite\Shaders\lumenite_AnamorphicBloom.fx'; Destination = 'reshade-shaders\Shaders\lumenite_AnamorphicBloom.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_Kernel.fx'; Destination = 'reshade-shaders\Shaders\lumenite_Kernel.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_LSAO.fx'; Destination = 'reshade-shaders\Shaders\lumenite_LSAO.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_QuantAO.fx'; Destination = 'reshade-shaders\Shaders\lumenite_QuantAO.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_QuantMotion.fx'; Destination = 'reshade-shaders\Shaders\lumenite_QuantMotion.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_RTAO.fx'; Destination = 'reshade-shaders\Shaders\lumenite_RTAO.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_SSSR.fx'; Destination = 'reshade-shaders\Shaders\lumenite_SSSR.fx' },
    @{ Source = 'Lumenite\Shaders\lumenite_TRAA.fx'; Destination = 'reshade-shaders\Shaders\lumenite_TRAA.fx' },
    @{ Source = 'Lumenite\Shaders\include\lumenite_ColorManagement.fxh'; Destination = 'reshade-shaders\Shaders\include\lumenite_ColorManagement.fxh' },
    @{ Source = 'Lumenite\Shaders\include\lumenite_Compute.fxh'; Destination = 'reshade-shaders\Shaders\include\lumenite_Compute.fxh' },
    @{ Source = 'Lumenite\Shaders\include\lumenite_Helpers.fxh'; Destination = 'reshade-shaders\Shaders\include\lumenite_Helpers.fxh' },
    @{ Source = 'Lumenite\Shaders\include\lumenite_Projections.fxh'; Destination = 'reshade-shaders\Shaders\include\lumenite_Projections.fxh' },
    @{ Source = 'Lumenite\Textures\lumenite_bluenoise256.png'; Destination = 'reshade-shaders\Textures\lumenite_bluenoise256.png' },
    @{ Source = 'Feeder\host64\dlss5-feed-host64.exe'; Destination = 'host64\dlss5-feed-host64.exe' },
    @{ Source = 'ReShade\ReShade64.dll'; Destination = 'host64\dxgi.dll' },
    @{ Source = 'DFC\deep-fried-chicken.addon64'; Destination = 'host64\deep-fried-chicken.addon64' },
    @{ Source = 'DFC\deep-fried-chicken-nvngx.dll'; Destination = 'host64\deep-fried-chicken-nvngx.dll' },
    @{ Source = 'DFC\deep-fried-chicken.cfg'; Destination = 'host64\deep-fried-chicken.cfg' },
    @{ Source = 'NVIDIA\nvngx_dlss.dll'; Destination = 'host64\nvngx_dlss.dll' },
    @{ Source = 'NVIDIA\nvngx_dlssnr.dll'; Destination = 'host64\nvngx_dlssnr.dll' }
)

$resolved = foreach ($file in $files) {
    [void](Require-File $file.Source)
    [pscustomobject]@{ Source = Join-Path $DependencyRoot $file.Source; Destination = Join-Path $GamePath $file.Destination }
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$backup = Join-Path $GamePath "obdlss5-backups\$stamp"
$journalPath = Join-Path $GamePath 'obdlss5-install-journal.json'
$records = @()

foreach ($file in $resolved) {
    $destinationDir = Split-Path -Parent $file.Destination
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    if (Test-Path -LiteralPath $file.Destination -PathType Leaf) {
        $relative = $file.Destination.Substring($GamePath.Length).TrimStart('\')
        $backupPath = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupPath) | Out-Null
        Copy-Item -LiteralPath $file.Destination -Destination $backupPath -Force
    } else {
        $backupPath = $null
    }
    Copy-Item -LiteralPath $file.Source -Destination $file.Destination -Force
    $records += [pscustomobject]@{
        Path = $file.Destination.Substring($GamePath.Length).TrimStart('\')
        InstalledSha256 = (Get-FileHash -LiteralPath $file.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
        BackupPath = $backupPath
    }
}

$generated = @{
    'dlss5-feed.cfg' = Get-Content -Raw (Join-Path $PSScriptRoot 'payload\dlss5-feed.cfg')
    'dgVoodoo.conf' = Get-Content -Raw (Join-Path $PSScriptRoot 'payload\dgVoodoo.conf')
    'ReShadePreset.ini' = Get-Content -Raw (Join-Path $PSScriptRoot 'payload\ReShadePreset.ini')
    'ReShade.ini' = "[GENERAL]`r`nEffectSearchPaths=.\reshade-shaders\Shaders`r`nTextureSearchPaths=.\reshade-shaders\Textures`r`nPresetPath=.\ReShadePreset.ini`r`n[INPUT]`r`nKeyOverlay=36,0,0,0`r`n"
    'host64\ReShade.ini' = "[DLSS5Host]`r`nWindowHeight=0`r`nWindowWidth=900`r`n[GENERAL]`r`nEffectSearchPaths=.\`r`nTextureSearchPaths=.\`r`nPresetPath=.\ReShadePreset.ini`r`n[INPUT]`r`nKeyOverlay=36,0,0,0`r`n"
}
foreach ($entry in $generated.GetEnumerator()) {
    $destination = Join-Path $GamePath $entry.Key
    $destinationDir = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $relative = $destination.Substring($GamePath.Length).TrimStart('\')
        $backupPath = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupPath) | Out-Null
        Copy-Item -LiteralPath $destination -Destination $backupPath -Force
    } else { $backupPath = $null }
    [IO.File]::WriteAllText($destination, [string]$entry.Value, [Text.UTF8Encoding]::new($false))
    $records += [pscustomobject]@{ Path=$entry.Key; InstalledSha256=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant(); BackupPath=$backupPath }
}

$journal = [pscustomobject]@{
    schema = 1
    installedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    gamePath = $GamePath
    backupRoot = $backup
    files = $records
}
$journal | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $journalPath -Encoding UTF8
Write-Output "OBDLSS5 installed. Backup: $backup"
Write-Output "Journal: $journalPath"
