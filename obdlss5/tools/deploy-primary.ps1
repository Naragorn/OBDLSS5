[CmdletBinding()]
param(
    [string]$GamePath = 'D:\SteamLibrary\steamapps\common\Oblivion',
    [string]$ProcurementRoot = '',
    [string]$Python = 'C:\Users\Nadi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [switch]$ValidateOnly,
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$cliPath = Join-Path $repoRoot 'obdlss5/tools/obdlss5.py'
if (-not $ProcurementRoot) {
    $ProcurementRoot = Join-Path $repoRoot 'obdlss5/results/procurement/20260918-flat-d3d11'
}
$lumeniteRoot = Join-Path $ProcurementRoot 'lumenite/LumeniteFX-f8cbbb4eccfcb7adf0d74bb358ba349272e3c1e9'
$outputPath = if ($Output) { $Output } else { Join-Path $repoRoot 'obdlss5/results/deploy-primary.json' }
$journalPath = Join-Path $GamePath 'obdlss5-primary-install-journal.json'

$stageArguments = [System.Collections.Generic.List[string]]::new()
foreach ($value in @($cliPath, 'stage', '--profile', 'flat-d3d11-primary')) {
    [void]$stageArguments.Add([string]$value)
}
if (-not $ValidateOnly) { [void]$stageArguments.Add('--apply') }
foreach ($value in @('--destination', $GamePath, '--backup-and-replace', '--journal', $journalPath, '--output', $outputPath)) {
    [void]$stageArguments.Add([string]$value)
}

function Add-Artifact([string]$Role, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing procurement artifact for ${Role}: $Path"
    }
    [void]$stageArguments.Add("--artifact=$Role=$Path")
}

Add-Artifact 'dgvoodoo_d3d9_x86' (Join-Path $ProcurementRoot 'dgvoodoo/MS/x86/D3D9.dll')
Add-Artifact 'reshade_x86' (Join-Path $ProcurementRoot 'reshade-extracted/ReShade32.dll')
Add-Artifact 'feeder_addon32' (Join-Path $ProcurementRoot 'feeder/dlss5-feed.addon32')
Add-Artifact 'feeder_shader' (Join-Path $ProcurementRoot 'feeder/reshade-shaders/Shaders/DLSS5_Feed.fx')
Add-Artifact 'reshade_header_core' (Join-Path $ProcurementRoot 'reshade-shader-headers/ReShade.fxh')
Add-Artifact 'reshade_header_ui' (Join-Path $ProcurementRoot 'reshade-shader-headers/ReShadeUI.fxh')
Add-Artifact 'reshade_header_text' (Join-Path $ProcurementRoot 'reshade-shader-headers/DrawText.fxh')

$shaderFiles = [ordered]@{
    lumenite_anamorphic_bloom = 'lumenite_AnamorphicBloom.fx'
    lumenite_kernel = 'lumenite_Kernel.fx'
    lumenite_lsao = 'lumenite_LSAO.fx'
    lumenite_quant_ao = 'lumenite_QuantAO.fx'
    lumenite_quant_motion = 'lumenite_QuantMotion.fx'
    lumenite_rtao = 'lumenite_RTAO.fx'
    lumenite_sssr = 'lumenite_SSSR.fx'
    lumenite_traa = 'lumenite_TRAA.fx'
}
foreach ($roleName in $shaderFiles.Keys) {
    Add-Artifact $roleName (Join-Path $lumeniteRoot ('Shaders/' + $shaderFiles[$roleName]))
}
$includeFiles = [ordered]@{
    lumenite_color_management = 'lumenite_ColorManagement.fxh'
    lumenite_compute = 'lumenite_Compute.fxh'
    lumenite_helpers = 'lumenite_Helpers.fxh'
    lumenite_projections = 'lumenite_Projections.fxh'
}
foreach ($roleName in $includeFiles.Keys) {
    Add-Artifact $roleName (Join-Path $lumeniteRoot ('Shaders/include/' + $includeFiles[$roleName]))
}
Add-Artifact 'lumenite_bluenoise' (Join-Path $lumeniteRoot 'Textures/lumenite_bluenoise256.png')
Add-Artifact 'feeder_host64' (Join-Path $ProcurementRoot 'feeder/host64/dlss5-feed-host64.exe')
Add-Artifact 'reshade_x64' (Join-Path $ProcurementRoot 'reshade-extracted/ReShade64.dll')
Add-Artifact 'dfc_addon64' (Join-Path $ProcurementRoot 'dfc/deep-fried-chicken.addon64')
Add-Artifact 'dfc_bridge64' (Join-Path $ProcurementRoot 'dfc/deep-fried-chicken-nvngx.dll')
Add-Artifact 'dfc_config' (Join-Path $ProcurementRoot 'dfc/deep-fried-chicken.cfg')
Add-Artifact 'nvidia_nr64' (Join-Path $ProcurementRoot 'nvidia/nvngx_dlssnr.dll')
Add-Artifact 'nvidia_dlss64' (Join-Path $ProcurementRoot 'nvidia/nvngx_dlss.dll')

& $Python @stageArguments
exit $LASTEXITCODE




