[CmdletBinding()]
param([Parameter(Mandatory = $true)][string] $GamePath)
$ErrorActionPreference = 'Stop'
$GamePath = (Resolve-Path -LiteralPath $GamePath).Path
$journalPath = Join-Path $GamePath 'obdlss5-install-journal.json'
if (-not (Test-Path -LiteralPath $journalPath -PathType Leaf)) { throw "Install journal not found: $journalPath" }
$journal = Get-Content -Raw -LiteralPath $journalPath | ConvertFrom-Json
$failures = 0
foreach ($record in $journal.files) {
    $path = Join-Path $GamePath $record.Path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { Write-Output "MISSING $($record.Path)"; $failures++; continue }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $record.InstalledSha256) { Write-Output "MISMATCH $($record.Path) $actual"; $failures++ } else { Write-Output "OK      $($record.Path)" }
}
if ($failures -gt 0) { throw "Verification failed with $failures problem(s)." }
Write-Output 'Verification passed.'
