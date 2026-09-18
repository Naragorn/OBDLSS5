# OBDLSS5 for The Elder Scrolls IV: Oblivion

Experimental flat-screen neural-rendering integration for the 2006 32-bit
release of *The Elder Scrolls IV: Oblivion*.

This release is a deployment kit, not an official NVIDIA DLSS 5 port. It uses
the following measured route:

```text
Oblivion.exe (x86/D3D9)
  -> dgVoodoo2 D3D11
  -> ReShade x86 / Lumenite Kernel / DLSS5 Feeder
  -> x86 feeder add-on and x64 host
  -> Deep Fried Chicken / NVIDIA NR runtime
  -> flat-screen present
```

The tested machine was an RTX 4090. The successful neural run used an
experimental SF-v2 `nvngx_dlssnr.dll`; this is not an NVIDIA-supported RTX 4090
DLSS 5 configuration. NVIDIA's official DLSS 5 3D-Guided Neural Rendering
hardware table currently lists GeForce RTX 50 Series GPUs.

## Status

- Real-game feed, host evaluation, GPU timing and standalone NR activity: verified on the author's test machine.
- Controlled static OFF/ON comparison: recorded.
- Full A01-A12 specification/release gate: not complete; this is experimental.
- Supported game scope: classic 2006 Oblivion only. Oblivion Remastered is out of scope.
- Online/anti-cheat protected games: not supported.

Read [INSTALL.md](INSTALL.md) before copying anything. The installer refuses
to run while Oblivion is open, creates a backup, validates the required local
dependency files, and records an install journal.

## Included

- `Install-OBDLSS5.ps1` — transactional PowerShell installer.
- `Uninstall-OBDLSS5.ps1` — restores the install backup where available.
- `Verify-OBDLSS5.ps1` — checks the installed file set and hashes.
- `payload/` — OBDLSS5 configuration owned by this package.
- Dependency provenance, exact versions and hashes in [THIRD-PARTY.md](THIRD-PARTY.md).

Third-party binaries are intentionally not mirrored in this public kit. Obtain
each dependency from its upstream source and place it in the layout described
in [INSTALL.md](INSTALL.md).

