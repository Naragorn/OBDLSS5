[CmdletBinding()]
param([Parameter(Mandatory = $true)][string] $GamePath)
$ErrorActionPreference = 'Stop'
$GamePath = (Resolve-Path -LiteralPath $GamePath).Path
$journalPath = Join-Path $GamePath 'obdlss5-install-journal.json'
if (-not (Test-Path -LiteralPath $journalPath -PathType Leaf)) { throw "Install journal not found: $journalPath" }
if (Get-Process -Name Oblivion -ErrorAction SilentlyContinue) { throw 'Oblivion.exe is running. Close the game before uninstalling.' }
$journal = Get-Content -Raw -LiteralPath $journalPath | ConvertFrom-Json
foreach ($record in $journal.files) {
    $destination = Join-Path $GamePath $record.Path
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) { continue }
    $current = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($current -ne $record.InstalledSha256) { Write-Warning "Leaving modified file in place: $($record.Path)"; continue }
    if ($record.BackupPath -and (Test-Path -LiteralPath $record.BackupPath -PathType Leaf)) {
        Copy-Item -LiteralPath $record.BackupPath -Destination $destination -Force
    } else {
        Remove-Item -LiteralPath $destination -Force
    }
}
Write-Output "OBDLSS5 files restored or removed. Journal retained at $journalPath"
