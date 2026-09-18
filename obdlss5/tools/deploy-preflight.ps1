[CmdletBinding()]
param(
    [string]$GamePath = 'D:\SteamLibrary\steamapps\common\Oblivion',
    [string]$ProcurementRoot = '',
    [string]$Python = 'python',
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$cli = Join-Path $repoRoot 'obdlss5/tools/obdlss5.py'
if (-not $ProcurementRoot) {
    $ProcurementRoot = Join-Path $repoRoot 'obdlss5/results/procurement/20260918-flat-d3d11'
}
$lumeniteRoot = Join-Path $ProcurementRoot 'lumenite/LumeniteFX-f8cbbb4eccfcb7adf0d74bb358ba349272e3c1e9'
$output = Join-Path $repoRoot 'obdlss5/results/deploy-preflight.json'
$journal = Join-Path $GamePath 'obdlss5-preflight-install-journal.json'

$cliArgs = [System.Collections.Generic.List[string]]::new()
foreach ($value in @($cli, 'stage', '--profile', 'flat-d3d11-preflight')) {
    [void]$cliArgs.Add([string]$value)
}
if (-not $ValidateOnly) { [void]$cliArgs.Add('--apply') }
foreach ($value in @('--destination', $GamePath, '--backup-and-replace', '--journal', $journal, '--output', $output)) {
    [void]$cliArgs.Add([string]$value)
}

function Add-Artifact([string]$Role, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing procurement artifact for ${Role}: $Path"
    }
    [void]$cliArgs.Add("--artifact=$Role=$Path")
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
foreach ($role in $shaderFiles.Keys) {
    Add-Artifact $role (Join-Path $lumeniteRoot ('Shaders/' + $shaderFiles[$role]))
}
$includeFiles = [ordered]@{
    lumenite_color_management = 'lumenite_ColorManagement.fxh'
    lumenite_compute = 'lumenite_Compute.fxh'
    lumenite_helpers = 'lumenite_Helpers.fxh'
    lumenite_projections = 'lumenite_Projections.fxh'
}
foreach ($role in $includeFiles.Keys) {
    Add-Artifact $role (Join-Path $lumeniteRoot ('Shaders/include/' + $includeFiles[$role]))
}
Add-Artifact 'lumenite_bluenoise' (Join-Path $lumeniteRoot 'Textures/lumenite_bluenoise256.png')
Add-Artifact 'feeder_host64' (Join-Path $ProcurementRoot 'feeder/host64/dlss5-feed-host64.exe')
Add-Artifact 'reshade_x64' (Join-Path $ProcurementRoot 'reshade-extracted/ReShade64.dll')

& $Python @cliArgs
exit $LASTEXITCODE
