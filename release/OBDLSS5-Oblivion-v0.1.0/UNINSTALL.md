# Uninstall

Close Oblivion, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Uninstall-OBDLSS5.ps1 -GamePath "C:\Path\To\Oblivion"
```

The installer records the files it changed in
`obdlss5-install-journal.json` and stores overwritten files in an
`obdlss5-backups\<timestamp>` directory. The uninstaller restores that backup
when present. It removes an installed file only when its current SHA-256 still
matches the recorded installed hash; locally modified files are left in place
and reported.

