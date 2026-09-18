# Installation

## 1. Requirements

- Windows 10/11 x64.
- A legitimate, working installation of classic 32-bit Oblivion.
- A current NVIDIA driver appropriate for the installed GPU.
- PowerShell 5.1 or newer.
- Oblivion configured for a controlled baseline: 1920x1080, windowed, SDR,
  no MSAA/SSAA, no frame generation and no Smooth Motion.
- All dependency files listed below. The package does not redistribute
  proprietary or author-restricted binaries.

## 2. Prepare dependencies

Create a folder named `Dependencies` next to `Install-OBDLSS5.ps1` and arrange
the upstream files exactly like this:

```text
Dependencies\
  dgVoodoo\D3D9.dll                         # x86 build
  ReShade\ReShade32.dll
  ReShade\ReShade64.dll
  ReShadeShaders\Shaders\ReShade.fxh
  ReShadeShaders\Shaders\ReShadeUI.fxh
  ReShadeShaders\Shaders\DrawText.fxh
  Feeder\dlss5-feed.addon32
  Feeder\host64\dlss5-feed-host64.exe
  Feeder\reshade-shaders\Shaders\DLSS5_Feed.fx
  Lumenite\Shaders\lumenite_AnamorphicBloom.fx
  Lumenite\Shaders\lumenite_Kernel.fx
  Lumenite\Shaders\lumenite_LSAO.fx
  Lumenite\Shaders\lumenite_QuantAO.fx
  Lumenite\Shaders\lumenite_QuantMotion.fx
  Lumenite\Shaders\lumenite_RTAO.fx
  Lumenite\Shaders\lumenite_SSSR.fx
  Lumenite\Shaders\lumenite_TRAA.fx
  Lumenite\Shaders\include\lumenite_ColorManagement.fxh
  Lumenite\Shaders\include\lumenite_Compute.fxh
  Lumenite\Shaders\include\lumenite_Helpers.fxh
  Lumenite\Shaders\include\lumenite_Projections.fxh
  Lumenite\Textures\lumenite_bluenoise256.png
  DFC\deep-fried-chicken.addon64
  DFC\deep-fried-chicken-nvngx.dll
  DFC\deep-fried-chicken.cfg
  NVIDIA\nvngx_dlss.dll
  NVIDIA\nvngx_dlssnr.dll
```

Use the exact versions and source links in [THIRD-PARTY.md](THIRD-PARTY.md).
Do not rename `deep-fried-chicken-nvngx.dll`. Do not replace it with
`nvngx.dll`.

## 3. Install

Close the game and run PowerShell in this directory:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Install-OBDLSS5.ps1 -GamePath "C:\Path\To\Oblivion"
```

For another installation path, replace `-GamePath`. The command stops before
writing if a required dependency or `Oblivion.exe` is missing.

## 4. First launch

1. Start Oblivion windowed.
2. Press `Home` to open ReShade.
3. Confirm the `DLSS5_Feed` technique is loaded.
4. Confirm the Feeder overlay reports a built feed and delivered frames.
5. In the Deep Fried Chicken tab, confirm the neural consumer is active.
6. If the display is black or frozen, exit the game and run
   `Uninstall-OBDLSS5.ps1`, then inspect the generated journal/log files.

The default `dlss5-feed.cfg` uses `enabled=1`, `mode=2`, `host_window=2` and
`async_home=0`. To disable the feed for a clean comparison, edit only:

```text
enabled=0
```

Restore `enabled=1` before the neural ON run.

## 5. Verify

```powershell
.\Verify-OBDLSS5.ps1 -GamePath "C:\Path\To\Oblivion"
```

The verifier reports missing files, unexpected hashes and the install journal
path. It does not claim that a GPU performed a neural evaluation; that requires
an in-game log/evidence run.

