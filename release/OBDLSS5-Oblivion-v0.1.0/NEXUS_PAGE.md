# Nexus Mods page text

## Title

OBDLSS5 - Experimental Neural Rendering for Classic Oblivion

## Summary

Experimental flat-screen neural-rendering integration for the 2006 32-bit
release of The Elder Scrolls IV: Oblivion. Includes a transactional installer,
verification/uninstall scripts, a controlled OFF/ON validation pair and exact
third-party dependency instructions.

## Description

OBDLSS5 routes classic Oblivion through dgVoodoo2 D3D11, ReShade, the pinned
DLSS5 Feeder transport and a 64-bit neural host. The tested pipeline reached
standalone DFC neural evaluation on an RTX 4090 with an experimental SF-v2
DLSSNR runtime.

This is an experimental community integration, not an official NVIDIA DLSS 5
port. NVIDIA officially documents DLSS 5 3D-Guided Neural Rendering for
GeForce RTX 50 Series hardware. The RTX 4090 result is a measured local
compatibility result and is not a support guarantee.

## Requirements

- Classic The Elder Scrolls IV: Oblivion (2006, 32-bit), not Oblivion Remastered.
- Windows 10/11 x64.
- NVIDIA RTX GPU and current driver; official DLSS 5 hardware support is RTX 50 Series.
- The exact third-party files listed in `THIRD-PARTY.md`.
- Windowed 1920x1080 SDR baseline for the first test.

## Installation

1. Download the archive and read `INSTALL.md`.
2. Obtain each dependency from its upstream link in `THIRD-PARTY.md`.
3. Arrange the files under the `Dependencies` layout in `INSTALL.md`.
4. Run `Install-OBDLSS5.ps1` against the user's Oblivion directory.
5. Launch windowed and use the ReShade Home overlay to confirm feed delivery
   and neural-consumer activity.

The installer makes a backup and writes an install journal. Use
`Uninstall-OBDLSS5.ps1` to restore it. Do not use this package with
anti-cheat-protected online games.

## Known limits

- The public package does not redistribute NVIDIA, DFC, dgVoodoo2, ReShade or
  AGNYA-licensed LumeniteFX binaries.
- Separate clean launches were used for the static OFF/ON pair; no same-process
  motion capture is claimed.
- The complete OBDLSS5 A01-A12 release gate remains partial.

## File upload

- File name: `OBDLSS5-Oblivion-v0.1.0.zip`
- Version: `0.1.0`
- Category: Main file
- SHA-256: see the release asset and `SHA256SUMS.txt`.

