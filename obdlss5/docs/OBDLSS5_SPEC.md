# OBDLSS5 — Flat Neural Rendering implementation specification

Version: 1.1 · Research date: 2026-09-18 · Status: ready for implementation; runtime validation pending.

This specification is written for implementation agents, especially Luna, and for Claude's subsequent review. It supersedes the earlier conversational plan. Statements labelled **source finding** describe inspected upstream material; **decision** denotes our engineering choice; **runtime gate** requires measurements on the target machine. Neither upstream reports nor this document establish that Oblivion or an RTX 4090 already works.

## 1. Product and scope

**OBDLSS5** is a standalone, flat-screen Neural Rendering mod/integration for **classic The Elder Scrolls IV: Oblivion (2006)**. Oblivion Remastered is excluded. The first milestone is a reproducible, toggleable PoC, followed by a small reusable implementation and a reviewable experimental release package.

OBDLSS5 will be the engineering starting point for later **OBVR** integration. Proven transport, neural-host, frame-contract and diagnostic code should become a shared internal component. OBVR must eventually consume that component without requiring users to install the flat OBDLSS5 package. This task implements **only OBDLSS5**. It implements no OpenXR, stereo, eye tracking, shared-eye reprojection, foveation, auto-quality policy or VR menu changes.

Sequence is mandatory: unchanged upstream Flat PoC → measured proof → minimal extraction of working code → Flat regression tests. Do not begin with a new renderer or an invented NVIDIA DLSS5 SDK interface.

Other exclusions: engine-native motion vectors, projection jitter injection, DLSS Super Resolution as a product feature, Frame Generation, Ray Reconstruction, HDR-display support, ENB compatibility, broad mod compatibility, automatic driver changes, and publication to Nexus/GitHub. Oblivion's internal HDR/bloom setting is distinct from HDR display output; record it rather than conflating the two.

## 2. What the research establishes

| Finding | Evidence and implication |
| --- | --- |
| Official DLSS 3D-Guided Neural Rendering hardware table lists RTX 50, not RTX 40 | [NVIDIA compatibility](https://www.nvidia.com/en-us/geforce/technologies/dlss/#compatibility). RTX 4090 is an experimental target, with no support promise. |
| DLSS5-Feeder constructs a DLAA input path; a separate consumer performs NR | [Feeder README](https://github.com/jlrouzies-fr/DLSS5-Feeder). Loaded DLLs, successful DLAA and successful NR are different states. |
| The project supports an x86 client and x64 host | The pinned [IPC source](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/src/feed_ipc.h) defines version 9 and cross-process resource/fence transfer. Reuse it. |
| A D3D9-to-D3D11 route exists | [dgVoodoo documentation](https://dege.freeweb.hu/dgVoodoo2/) describes translation; [Feeder deployment runbook](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/DEPLOY-DEV.md) gives x86 deployment and reports Fable tests. This is not an Oblivion test. |
| Fallout 3 has a community DXVK reference | [Classic-games repository](https://github.com/perseval-BLR/dlss5-classic-games) reports x86 D3D9 → DXVK → Vulkan → Feeder/host. It reports dgVoodoo problems for Fallout 3. Treat this as fallback evidence, not proof that Oblivion fails on dgVoodoo. |
| Estimated motion is optical flow | [LumeniteFX](https://github.com/umar-afzaal/LumeniteFX) and the pinned shader describe image-based motion estimation, not Gamebryo geometry velocities. NPC motion is not automatically absent; illumination changes and occlusion can make estimates wrong. |
| Current integration is community engineering | [OptiScaler NR release](https://github.com/Dagherbou/OptiScaler_DLSSNR/releases/tag/v0.2.0-dlssnr) explicitly describes an unofficial integration and a modified model runtime for pre-Blackwell hardware. It does not establish our exact 4090 configuration. |

**Corrections to the previous plan:** do not promise 4090 compatibility, do not treat `300/300` DLAA evaluations as sufficient NR proof, do not assume that an x86 trust mask reaches the host, and do not assume the default transport presents the same frame it just submitted.

No OBVR repository was supplied or inspected while authoring this spec. Consequently, no OBVR hook addresses, current renderer internals, or existing build targets are asserted. Luna's initial local inspection maps this plan onto the actual checkout; it is not a request to repeat broad web research.

## 3. Fixed implementation decisions

| ID | Decision |
| --- | --- |
| D01 | Windows x64 execution environment; actual Oblivion executable must be PE32/I386. Windows 11 is the preferred test machine, not an asserted minimum OS requirement. |
| D02 | Start at 1920×1080, windowed, SDR display output, native work resolution, one neural pass. Disable MSAA/SSAA, frame generation and Smooth Motion for controlled comparisons. |
| D03 | Primary route: dgVoodoo D3D11 + ReShade x86 + Feeder addon32 + x64 host + Deep Fried Chicken (DFC). |
| D04 | Use the same pinned Feeder release for client, host and shader. No mixed builds and no floating latest dependency. |
| D05 | Use Lumenite Kernel only, before the feed technique. Do not enable its other artistic effects. |
| D06 | Use synchronous return (`async_home=0`) for correctness baselines. Measure the pipelined option later as a separate Flat experiment, not as VR-ready behavior. |
| D07 | No new OBSE plug-in or D3D9 proxy for the first PoC. Existing OBVR graphics hooks are disabled in the isolated Flat test setup. |
| D08 | First deliverable can be profiles, staging/checking tools and upstream binaries supplied separately. New C++ is justified only by a demonstrated gap or the post-PoC extraction. |
| D09 | Keep upstream executable/add-on filenames during PoC and extraction; consumer recognition can depend on the process identity. OBDLSS5 is the package/product name. |
| D10 | Reuse upstream IPC and GPU synchronization; do not replace them with CPU readback, socket frame streaming or a new protocol. |

Primary pipeline: `Oblivion.exe (x86/D3D9) → dgVoodoo (D3D11) → ReShade x86 / Kernel / Feed → addon32 → host64 D3D12 / DFC NR → output returned → Flat present`.

## 4. Dependency baseline and procurement gate

These are **selected candidates**, not a tested OBDLSS5 compatibility bundle. An upstream-tested combination and an OBDLSS5-tested combination are recorded separately.

| Component | Selected starting version | Provenance / lock rule |
| --- | --- | --- |
| Feeder | `v1.16.0-beta.4` | Commit `53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff`; [release](https://github.com/jlrouzies-fr/DLSS5-Feeder/releases/tag/v1.16.0-beta.4). ZIP SHA-256 `d16f8b527f76ff1f531682a576d699cb5634838c0e2899585e3671814eda2745`. |
| dgVoodoo2 | `v2.87.5` | [Maintainer release](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.87.5); regular ZIP `dgVoodoo2_87_5.zip`, SHA-256 `5ffde6927f7355ca3fdd5d785b581256a8e6539fa13e395a891ade6ba1040850`. GitHub API reports 2026-09-15. This new version has not been tested here. |
| ReShade | `6.8.0`, full add-on support | [Official download](https://reshade.me/); obtain both x86 and x64 DLLs from that installer. Hash installer and extracted DLLs locally. |
| LumeniteFX | `f8cbbb4eccfcb7adf0d74bb358ba349272e3c1e9` | [Pinned tree](https://github.com/umar-afzaal/LumeniteFX/tree/f8cbbb4eccfcb7adf0d74bb358ba349272e3c1e9), from `mainline`. Include required shader includes and texture dependencies; hash deployed files. |
| DFC | `1.4.8-alpha` | Selected because pinned Feeder includes ABI evidence and upstream reports host testing. Obtain the original package from the author's [distribution channel](https://discord.gg/g2v2XGqvR), or a provenance-recorded local copy. No publicly verified package hash was obtained in this research. |
| NVIDIA NR model | Candidate file version `310.8.0` | User-supplied `nvngx_dlssnr.dll`; candidate comes from the [classic-games reference](https://github.com/perseval-BLR/dlss5-classic-games). Actual exact binary/hash must be recorded and pass H0. |
| NVIDIA DLSS runtime | Candidate file version `310.9.0` | User-supplied `nvngx_dlss.dll`; same reference. Record actual file version and SHA-256. No need to add DLSSG/DLSSD simply because another reference includes them. |
| Driver | Record installed version; `616.64` is the DFC reference candidate | Do not change the driver automatically. Pinned upstream reports DFC host success on one RTX 5090 with this driver; other configurations remain unverified. |
| Optional fallback | DXVK `3.0.2` x86 | [Official releases](https://github.com/doitsujin/dxvk/releases); use only under §9. |

**Procurement boundary:** the DFC package and NVIDIA runtime binaries were not downloaded, executed or authenticated during authoring. Some depend on user access to distribution channels. These are concrete missing inputs, not permission for Luna to search for random replacements. If absent, complete the offline implementation work and report the exact missing files. Do not invent hashes or claim the runtime gate passed.

If the exact DFC version cannot be obtained, the bounded alternative is OptiScaler DLSSNR `v0.2.0-dlssnr` (§9). Do not silently replace DFC with another alpha. A replacement creates a new named profile and a new H0 result.

For RTX 4090, a compatible user-supplied experimental NR runtime may be necessary. Stock runtime failure on Ada is a hardware/runtime blocker, not evidence that the Oblivion capture code is wrong. No binary patching task is included. Continue build/tooling work, but never count a DLAA-only 4090 run as an NR PoC.

Implement `dependencies.lock.json`: schema version; component name; source URL; release/tag; full commit where available; expected upstream digest where published; actual archive and deployed-file SHA-256; PE architecture; file version; acquisition date; license identifier or `unreviewed`; configuration-profile ID. Preserve expected and observed hashes as separate fields. Null is allowed for missing local input; staging must refuse required null/mismatched artifacts. No update checks during game startup. For implementation questions, use the evidence and MCP workflow in §17; dependency upgrades still require a documented reason and a new locked profile.

## 5. Work layout and owned deliverables

Within the supplied checkout create an isolated `obdlss5/` subtree, unless it is already an OBDLSS5-only repo. Do not move unrelated OBVR files. Suggested paths are requirements for a new subtree, with a documented mapping if existing equivalents exist:

- `docs/OBDLSS5_SPEC.md`: this specification, kept intact except explicit errata.
- `obdlss5/README.md`: setup, scope, toggle behavior, rollback, tested hardware.
- `obdlss5/dependencies.lock.json` and `profiles/flat-d3d11/`: manifests and text profiles.
- `obdlss5/tools/obdlss5.py`: Python 3.11+ standard-library CLI for inventory, staging, validation, evidence collection and rollback. Python is a development/deployment dependency, not a per-frame runtime dependency.
- `obdlss5/tests/`: meaningful CLI fixtures and later C++ contract tests.
- `obdlss5/third_party/DLSS5-Feeder/`: pinned source checkout/submodule, added only when needed for build or patch work. Do not vendor downloaded proprietary binaries.
- `obdlss5/patches/`: minimal documented upstream changes if required.
- `obdlss5/core/`: only created after P5 succeeds; actual extracted C++ and headers.
- `obdlss5/results/`: human-readable results and compact machine-readable index; large local captures and dumps remain ignored.

Implement CLI subcommands `inventory`, `stage`, `verify`, `collect`, `rollback`, `test`, and `release-check`. The last two implement the automated harness and shipping gate in §17. All accept explicit paths, including spaces and Unicode. Default operation is read-only inventory or staging into a dedicated directory. Applying files to a game directory requires the explicit `stage --apply` argument; the command is authorized as part of implementing/testing this task on the selected test installation.

`inventory`: read executable PE machine, module candidate names, file versions/hashes and writable paths; record OS/GPU/driver where available. Reject PE32+ or a Remastered executable. Do not assume launcher bitness equals game bitness. Without a validated executable signature, identify the game as user-selected/unverified rather than trusting only a filename.

`stage`: validate all inputs first; no partial installation on missing prerequisites. Copy only manifest-owned files. Refuse an existing conflicting proxy DLL unless an explicit backup-and-replace option is supplied. Back up overwritten files with hashes in an installation journal. Edit INIs by section/key, preserving unrelated sections. Never regex-replace every `Enabled=` key. Do not install Vulkan globally for the primary path.

`verify`: report architecture/placement, exact hashes, dependency pairing, active provider/order, consumer conflicts, compiler failures, and the evidence states in §10. Offline verification must say `NOT_RUN` for live behavior. Return nonzero for failed requirements.

`collect`: copy explicitly selected run logs/configs, inventory and captures into a unique run directory; create a JSON index. Do not include saves, credentials or unrelated files. Config collection is from both game and host directories.

`rollback`: restore only journal-owned paths. If a file has changed since installation, preserve it and report a conflict. Do not remove unrelated mods, global ReShade installs or game saves.

## 6. Primary installation contract

Only the game-root `D3D9.dll` belongs to dgVoodoo. Game-root `dxgi.dll` is ReShade x86. `host64/dxgi.dll` is ReShade x64; these two files must not be interchangeable.

| Destination relative to actual Oblivion.exe | Contents |
| --- | --- |
| `D3D9.dll` | dgVoodoo `MS/x86/D3D9.dll` |
| `dgVoodoo.conf`, optional `dgVoodooCpl.exe` | dgVoodoo config/control panel |
| `dxgi.dll` | ReShade 6.8.0 full-add-on x86 DLL |
| `dlss5-feed.addon32` | Pinned release client |
| `ReShade.ini`, `ReShadePreset.ini` | Game-side settings |
| `reshade-shaders/Shaders/DLSS5_Feed.fx` | Matching Feeder shader |
| `reshade-shaders/Shaders/` | Lumenite shaders/includes and required ReShade framework headers |
| `reshade-shaders/Textures/` | Required Lumenite texture assets |
| `host64/dlss5-feed-host64.exe` | Same-release host |
| `host64/dxgi.dll` | ReShade 6.8.0 full-add-on x64 DLL |
| `host64/deep-fried-chicken.addon64` | DFC add-on |
| `host64/deep-fried-chicken-nvngx.dll` | DFC bridge, not NVIDIA model |
| `host64/deep-fried-chicken.cfg` | Original DFC 1.4.8-alpha defaults |
| `host64/nvngx_dlssnr.dll`, `host64/nvngx_dlss.dll` | User-supplied x64 NVIDIA files |
| `host64/ReShade.ini` | Host settings; do not point its AddonPath at the game root |

This placement is based on the pinned [deployment runbook](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/DEPLOY-DEV.md). No x64 consumer belongs beside Oblivion.exe. Keep other neural consumers out of `host64`.

### 6.1 Configuration fragments

These fragments contain selected keys, not complete replacements for upstream configuration files. Merge them while the game and host are closed.

`dgVoodoo.conf`:

```ini
[General]
OutputAPI = d3d11_fl11_0
[DirectX]
DisableAndPassThru = false
VideoCard = internal3D
VRAM = 1GB
dgVoodooWatermark = true
```

The virtual VRAM value is an initial compatibility setting, not the actual GPU's VRAM. Remove the watermark after wrapper proof and before measurements. These values are a starting profile derived from the Feeder runbook, not verified Oblivion tuning.

Game `ReShadePreset.ini`:

```ini
Techniques=Lumenite_Kernel@lumenite_Kernel.fx,DLSS5_Feed@DLSS5_Feed.fx
TechniqueSorting=Lumenite_Kernel@lumenite_Kernel.fx,DLSS5_Feed@DLSS5_Feed.fx

[DLSS5_Feed.fx]
PreprocessorDefinitions=DLSS5_MV_PROVIDER=3
```

Select this preset in game-side ReShade. Put the provider definition in the effect's preset section; do not rely on adding it to `ReShade.ini`'s GENERAL section. Preserve any other explicitly required per-effect definitions. The internal technique identifier and display label are different; use the identifiers above in files. [Pinned runbook](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/DEPLOY-DEV.md).

Game-root `dlss5-feed.cfg` is a **flat key/value file**, not our own `[NeuralRendering]` INI:

```ini
enabled=1
mode=2
hdr=-1
depth_inverted=-1
flags=-1
reset_every=0
host_window=1
host_gpu_priority=0
work_resolution=100
work_upscale=0
async_home=0
mv_scale_x=1.0
mv_scale_y=1.0
```

These keys and meanings were checked in pinned `src/dlss5-feed32.cpp`, `Cfg` and `CfgReload`. `mode=1` is transport-only; `mode=0` is inert; `mode=2` runs the DLSS path. The neural consumer has its own enable state. Never use `mode=1` and report NR success.

Leave DFC at one pass/native work scale with extras disabled for the first comparison. Do not copy settings from a newer DFC alpha into 1.4.8. The pinned runbook mentions `safe_neutral_start` for **1.4.13-alpha**, not the selected package; it is not an OBDLSS5 baseline setting.

## 7. Frame contract and ownership

This section defines the invariants any OBDLSS5 code must preserve. It is not a claim of a public NVIDIA NR API.

### 7.1 Input semantics

The pinned [Feed shader](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/shaders/DLSS5_Feed.fx) supplies:

| Input | Contract |
| --- | --- |
| Color | Current Flat frame at the feed technique; in the PoC this can already contain HUD. Record format and color interpretation. Do not double-apply sRGB conversion. |
| Depth | `DLSS5_Depth`, R32F, raw hardware depth with sampling/orientation adjustments. Do not substitute linearized DisplayDepth output. |
| Motion | `DLSS5_MV`, RG16F, current-to-previous pixel displacement. `previousUV = currentUV + mvPixels / dimensions`. |
| Provider flow | Kernel estimates delta UV at 1/8 dimensions; Feeder converts/resamples it. Do not multiply it by dimensions a second time in new code. |
| Mask | Shader emits a trust mask, but the selected x86 IPC has only Color, Output, Depth and MV slots. Mask availability to the neural host is false. |
| Resolution/jitter | Equal input/output dimensions; no game projection jitter. Host jitter values remain zero in this native-size DLAA profile. |
| History | One Flat history. Reset on newly built resources or discontinuity handling; never reset every frame as a supposed quality fix. |

Depth reversal, upside-down orientation and clear selection must be measured in Oblivion. Initial `-1` settings mean automatic inference, not proof of correctness. Do not copy Fable's depth-clear profile merely because both games are D3D9.

### 7.2 Cross-process invariants

Pinned [feed_ipc.h](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/src/feed_ipc.h) defines packed, fixed-width IPC with protocol 9. D3D11 normally exports resource handles to the host; the host creates shared fences. Vulkan uses host-created resources. Preserve duplication direction and actual negotiated output format. Never send C++ pointers or COM interface addresses through IPC. Handle numeric values are process-scoped.

For `async_home=0`, frame N waits for N's output before presenting. For `async_home=1`, output belongs to the previous submitted frame. Do not report the latter as zero-latency or silently combine it with current-frame HUD/camera metadata. It is not a future VR solution by itself.

Keep GPU ownership, barriers, completion checks and release order intact. A frame/resource generation changes on resize or device recreation; old-generation outputs must not be adopted. Input resources must stay alive through GPU consumption; output cannot be reused until its reader is finished. A host failure must not cause indefinite waiting or copying uninitialized/stale output as if it were valid. Preserve and test upstream recovery before changing it.

Do not generalize a single numeric result code across APIs. The IPC source describes NGX success as `0x1`; another log may report an HRESULT-style zero. Interpret results using the producing API and upstream helpers, not a blanket `code == 0` parser.

### 7.3 DFC integration

Pinned [feed_dfc.h](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/src/feed_dfc.h) publishes ABI-1 feeder markers before feature creation and every evaluation. Preserve the marker tuple, host mode and evaluation cadence. Do not acquire DFC's ownership mutex or write its exported state.

`ARMED` means interception is ready; it does not prove output. Upstream re-creates the feature after DFC becomes armed when necessary, because an earlier DLAA feature can otherwise remain unadopted. Keep that behavior. Re-creating on every frame is prohibited. Do not rewrite interop based only on DLL filename detection.

## 8. Implementation phases and gates

Each phase produces a small reviewable commit. Run the next phase automatically when its gate passes. Hardware-dependent gates may be `BLOCKED_ENVIRONMENT`; finish independent CLI/build work without falsely marking later runtime phases complete.

### P0 — Local mapping, inventory and lock

Read local AGENTS instructions, README, handoff and relevant renderer/build history if an OBVR checkout is supplied. Record the starting commit and uncommitted changes. Map the new subtree without altering working VR behavior. Implement inventory and dependency locking; prepare an isolated minimal Oblivion setup. Use the chosen executable's normal launch method and record OBSE/mod state.

**H0, early runtime viability:** prepare `host64` alone and run:

```powershell
.\host64\dlss5-feed-host64.exe --test --hide
```

Capture exit code and all host/consumer/ReShade logs. The pinned host tests 300 evaluations on a synthetic 640×360 contract. Require evaluation success **and** independent evidence that DFC created and evaluated its neural feature. Repeat with NR off as a control. This test does not exercise game capture, full-resolution memory pressure or normal game startup timing. It is an early runtime gate, not PoC acceptance.

If H0 fails on RTX 4090 with the supplied runtime, report `BLOCKED_RUNTIME` and the exact GPU/driver/consumer/model tuple. Do not start reverse-engineering Oblivion to repair an isolated host failure.

### P1 — Game and wrapper baseline

Run untouched Flat Oblivion and record the setup. Add dgVoodoo only; verify its watermark, correct world rendering, menus and save/load. Check interior/exterior, first/third person, water and effects. Record actual D3D11 activation, not just DLL presence. Remove the watermark for timing.

**Gate:** game playable without ReShade or NR, no reproducible corruption. On a reproducible wrapper-only failure follow §9; do not stack wrappers.

### P2 — ReShade and guides

Add ReShade only, then Kernel and the feed shader with the feed add-on disabled. Confirm x86 full-add-on build and no shader compile errors. Visualize depth and motion. Capture:

1. Still camera/still scene.
2. Camera yaw and pitch separately.
3. Walking forward and sideways.
4. Moving NPC while the camera is still.
5. First-person weapon/spell, vegetation, water and particles.
6. Enter/exit menus and load another cell/save.

Use near/far geometry to establish raw depth orientation. Reject empty, UI-only or wrong-surface depth. Nonzero motion during a pan is necessary but not sufficient; inspect direction and alignment. Record failures of estimated object motion. Do not introduce camera-only analytic vectors as if they solved animated objects.

**Gate:** correct scene depth, coherent pan/translation flow, documented limitations. No hard-coded guessed depth constant is accepted as verified.

### P3 — Transport and DLAA control

Enable addon32/host with `mode=1` and `async_home=0`. Verify round-trip color, dimensions, format, shared-fence progress and no channel swap/flip. Then use `mode=2` with the neural consumer disabled to establish the DLAA-only control. Keep the same resolution and guide settings.

**Gate:** successful transport, correct output, no unresolved initialization failures. Failure must preserve the original image or disable the effect; a frozen last output is not success.

### P4 — Neural Rendering Flat proof

Enable exactly DFC and run the real game startup sequence. Permit its documented one-time restart. Verify DFC arming and subsequent neural work; H0 success alone does not prove the real startup path adopted the feature.

Capture matched NR OFF/ON frames with identical camera/settings. Use a quiet static scene and a short motion clip; retain original captures. Confirm consumer neural work in the same run. The visible comparison must switch only NR, keeping wrapper/ReShade/Feeder/DLAA enabled. Separately compare native game output to the full stack.

**Gate:** sustained actual neural evaluations, visible effect, live toggle and original output when disabled. A screenshot changed only by sharpening, a debug tint or DLAA is not NR proof.

### P5 — Reproducibility and failure tests

Finish staging, verification, collection and rollback. Run the acceptance matrix (§11), save evidence, and reinstall the exact locked profile from a clean baseline. Failure-inject by stopping the helper, using mismatched client/host copies in an isolated test, and removing a required runtime file. These tests must not modify the main play installation. Execute the game scenarios through the automated harness in §17, retaining screenshots and machine-readable assertions.

**Gate:** all PoC-required rows pass, or the result is explicitly PARTIAL. Only a passing Flat PoC unlocks P6.

### P6 — Minimal reusable implementation

Keep OBDLSS5 functioning while extracting real code (§12). Re-run H0, transport, NR toggle, resize and host-loss tests after extraction. Deliver build instructions, dependency notices and an experimental package manifest containing only permitted files.

**Gate:** the extracted component is called by the working Flat path, not an unused interface. Stop at OBDLSS5 completion; do not add OBVR features.

## 9. Bounded fallback rules

### 9.1 Renderer fallback

After one reproducible primary-path failure, capture logs, isolate the first failing layer and investigate its root cause. Correct a concrete configuration/bitness/code error and rerun the failing test before considering a fallback. If the wrapper alone still fails and evidence identifies an upstream/platform limitation outside the present implementation boundary, select the **DXVK Flat profile**, recording the cause, evidence and unresolved limitation. A fallback does not count as fixing the primary profile. Do not spend unlimited iterations varying unrelated switches.

Remove/back up dgVoodoo and the game-root ReShade dxgi proxy through the installation journal. Install DXVK `x86/d3d9.dll` and ReShade's x86 full-add-on **Vulkan layer**; retain the x64 host. Use `dxvk.allowFse = False`, native work size, and Smooth Motion disabled. Global layer installation affects other Vulkan games; record that dependency and use the official installer rather than inventing registry edits. [Feeder README](https://github.com/jlrouzies-fr/DLSS5-Feeder).

Run wrapper and guides gates again. Use the same consumer first to isolate the renderer variable. If DFC specifically fails on this path, use §9.2 as a new profile. The pinned DFC runbook does not establish in-game x86 Vulkan validation.

The Fallout 3 reference warns about early `LoadFromDllMain` registration and contains `NRStyle=2`; current Feeder documentation warns that this style can crash with newer RenoDX. Do not transplant the reference configuration wholesale. Keep any host-side DFC startup setting separate from game-side Vulkan registration. [Classic-games reference](https://github.com/perseval-BLR/dlss5-classic-games), [Feeder README](https://github.com/jlrouzies-fr/DLSS5-Feeder).

If both renderer profiles fail their wrapper/guide gates, stop renderer work with concrete evidence and continue independent deliverables. A new engine hook needs a spec amendment, not an improvised third architecture.

### 9.2 Consumer fallback

Selected alternative: **OptiScaler DLSSNR v0.2.0-dlssnr**, not stock OptiScaler. This is also an option when the DFC package cannot be sourced. Keep it in a separate profile with fresh H0 evidence; never silently downgrade or combine consumers.

In `host64`, replace the complete DFC set with the fork's package. Rename `OptiScaler.dll` to `winmm.dll`; keep ReShade as `dxgi.dll`. Keep the fork's runtime directory and `nvngx.dll_dlssnr.dll` forwarder. The forwarder is not the NVIDIA model; supply the two NVIDIA DLLs separately.

Use section-aware settings:

```ini
[DlssNr]
Enabled=true
ScanExposure=false
[Upscalers]
Dx12Upscaler=dlss
[Log]
LogToFile=true
LogLevel=2
[Spoofing]
Dxgi=false
StreamlineSpoofing=false
[Hotfix]
CheckForUpdate=false
```

Do not run its generic installer if that would take over `dxgi.dll`. Require routing evidence and actual NR evaluations from its log. Merely seeing its DLL or `nvngx_dlss.dll` loaded is insufficient; upstream documents automatic fallback to another upscaler if DLSS is missing. [Pinned deployment §9b](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/DEPLOY-DEV.md).

This spec does not select RenoDX as a third fallback. That would multiply driver/version combinations without resolving a defined blocker.

## 10. Diagnostics and evidence model

Expose separate states in `verify`/reports:

`NOT_RUN → INVENTORIED → WRAPPER_OK → GUIDES_OK → TRANSPORT_OK → DLAA_OK → NR_ACTIVE → POC_VERIFIED`.

A component may instead be `BLOCKED_ENVIRONMENT`, `BLOCKED_DEPENDENCY`, `BLOCKED_RUNTIME`, `FAILED` or `UNKNOWN`. Do not infer a higher state from a lower one. Diagnostics track both feed evaluation and neural-consumer evaluation; when a consumer provides no readable counter, use its documented runtime evidence and report uncertainty rather than manufacturing a count.

Per run record: run ID/time; repository commit and patch hash; profile/lock digest; executable hash/version; OS; GPU name and adapter identity where available; driver; resolution/window mode; refresh/cap/VSync; mod/OBSE inventory; settings; host/client versions; actual loaded DLL paths/versions; guide status; transport protocol; consumer identity; evaluation/reset/failure counts where available; captures and timing data.

Read `ReShade.log` and `dlss5-feed.log` at game root, plus host-side `ReShade.log`, `dlss5-feed-host.log`, and `deep-fried-chicken.log` or `OptiScaler.log`. Associate logs with one process session, not stale earlier runs. Preserve raw values and API domain for errors. Log transitions and summaries, not a line for every frame.

Special diagnostics to retain:

- Separate DFC ready state from observed neural frames.
- Effective `async_home`, work resolution, image format and depth reversal.
- Cross-adapter mismatch or failed shared-fence import.
- Shader compile errors even when a technique appears selected.
- Old `d3dcompiler_47.dll` compilation failures in the host directory. Back up a conflicting application-local copy only after confirming the compile error; never delete a system DLL.
- Missing trust mask on the x86 host is a documented limitation, not proof of broken transport.

## 11. Acceptance and performance

`POC_VERIFIED` requires all mandatory rows. This specification defines the thresholds; it does not assert measured results.

| ID | Mandatory test | Pass condition / required evidence |
| --- | --- | --- |
| A01 | Baseline | Correct classic executable, recorded configuration, playable native run. |
| A02 | Host H0 | Synthetic evaluation succeeds and consumer NR evidence exists; off control recorded. |
| A03 | Wrapper | Correct interior/exterior output and menus; no reproducible corruption. |
| A04 | Guides | Depth and motion captures demonstrate alignment; known artifacts recorded. |
| A05 | Transport | Correct orientation/channels/dimensions; protocol matches; no stale output presented as current in synchronous mode. |
| A06 | Neural proof | Actual consumer NR activity plus matched NR OFF/ON captures and motion video. |
| A07 | Toggle | Ten OFF/ON cycles without crash/hang; document any history warm-up. |
| A08 | Gameplay | Thirty continuous minutes including exterior, interior, combat, conversation, inventory, water and first/third-person views. No reproducible crash or indefinite freeze. |
| A09 | Lifecycle | Five save/load transitions, five alt-tabs, resolution change and return. Recovery or an explicit safe disabled state; no invalid texture reuse. |
| A10 | Host failure | Stop helper during play; Flat rendering continues or effect cleanly disables within five seconds. No indefinite wait; restart does not reuse stale handles. If upstream cannot meet this, fix before POC_VERIFIED. |
| A11 | Reinstall/rollback | Clean reinstall reproduces hashes/profile; rollback restores owned originals and preserves unrelated files. |
| A12 | Performance | All stages below measured, or unavailable metrics explicitly marked. |

UI can remain inside the processed frame for the first PoC, but document every visible HUD/menu artifact. An experimental PoC may carry that limitation; a general release must not be advertised as UI-safe until text, cursor, dialogue and inventory are verified. Creating a reliable pre-HUD hook is a later scope amendment if the PoC shows it is necessary; do not guess draw-call indices now.

Performance stages: native; wrapper; ReShade plus guides; transport-only; DLAA with NR disabled; NR enabled. For each, run the same two scenes (one exterior, one interior), 30-second warm-up plus 60-second capture, three repetitions. Keep cap/VSync and camera path equal. Record average FPS (1000 divided by mean frame time in milliseconds), median of run means, p95/p99 frame time, VRAM, and GPU timing when available. State measurement tool/version. If reporting a “1% low”, define its calculation; do not equate it silently with a percentile. CPU wait time is not GPU execution time.

Do not extrapolate the 640×360 host test to 1080p/4K. Do not claim FPS improvements: NR is extra work. There is no invented minimum FPS acceptance promise. Report the cost and leave quality/performance approval to the user. Measure `async_home=1` only after the correctness baseline, separately report its additional frame age, and never silently change the default.

## 12. Shared component: actual extraction after proof

The shared part is an outcome of OBDLSS5, not a parallel OBVR implementation. We need a functioning Flat caller and a narrow internal seam.

Inspected pinned source anchors:

| Responsibility | Current upstream anchors |
| --- | --- |
| Game integration | `src/dlss5-feed32.cpp`: `OnRenderTechnique`, `ResolveHandles`, `FeedFrameDispatch`, `OnDestroyEffectRuntime`, `OnReloadedEffects` |
| D3D11 resource path | Same file: `BuildShared`, `CopyOrResampleInputs`, `BlitOutputToBackbuffer`, `ReleaseShared` |
| Host connection/lifetime | Same file: `HostLink`, `HostClose`, `HostLost`, `HostDrain` |
| Wire contract | `src/feed_ipc.h`: `FeedHello`, `FeedBuild`, `FeedBuildAck`, `FeedFrameMsg` |
| Host neural work | `host/dlss5-feed-host64.cpp`: `CreateFeature`, `Evaluate`, `Serve`, `RunTest` |
| Consumer readiness | `src/feed_dfc.h`; host `ChickenPoll`, `PublishDfcInterop` |

**Extraction target:** isolate frame metadata/validation and the already-working host evaluation lifecycle into internal modules called from the existing Flat execution path. Move code without changing evaluation order, feature flags, interop markers, synchronization or color conversion. Retain ReShade callbacks and overlay in the Flat adapter. Retain Windows/GPU types in the appropriate transport/backend layer; do not force a platform-independent abstraction over everything.

A minimal internal request contract must carry: frame ID; resource generation; input/output dimensions; actual formats/color encoding; raw-depth convention; MV direction/units; jitter; reset reason; resource references with owner/lifetime; readiness/completion mechanism. Result must distinguish unavailable, pass-through, successful DLAA, observed NR, and failure. It must identify the source frame/generation. Do not invent an NR-success flag merely because `Evaluate` returns DLAA success.

Only one view/context is implemented. Future OBVR will need independent histories and per-eye scheduling; document that the present code is **single-view only**. No second-eye enum, unused mode setting or mock stereo implementation is required.

Do not serialize this C++ internal request directly into the existing pipe. The transport adapter maps it to the unchanged version-9 structures. Adding masks or more views would require a separately designed protocol change later.

Concrete done condition: the production Flat path calls the extracted validation/evaluation code, the synthetic host test exercises that same code, and post-extraction A05–A10 remain passing. A document saying “shared core” or an unused interface does not satisfy P6. If global-state coupling makes a larger extraction risky, extract the smallest working host lifecycle seam and document the remaining dependencies instead of rewriting all client backends.

Build with the upstream scripts initially:

```bat
build-addon32.bat
host\build-host.bat
```

Outputs are `build\dlss5-feed.addon32` and `host\dlss5-feed-host64.exe`. These scripts use MSVC and `tools\vcvars.bat`; the client uses C++20. Install the x86/x64 C++ build tools and Windows SDK. Honor an existing `VCVARSALL` path; do not assume the upstream author's fallback Visual Studio directory exists locally. Preserve separate x86/x64 object output directories. A clean build must use the pinned external headers/libraries in the source checkout, not arbitrary machine-global SDK replacements.

Relevant source build references: [client script](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/build-addon32.bat), [host script](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff/host/build-host.bat).

## 13. Tests Luna must implement

Tests must protect actual risks, not duplicate every setter:

1. Stage refuses wrong-architecture host/client DLLs, mismatched hashes and missing dependencies before changing the destination.
2. INI editing changes only the specified section and preserves unrelated keys; paths with spaces/Unicode work.
3. Install/rollback round trip restores originals; a subsequently user-modified file is preserved and reported.
4. Log fixtures distinguish DLAA-only, DFC armed-but-idle, actual NR evidence, API-specific success codes, stale logs and initialization failure.
5. After extraction: reject stale resource generation, missing required input and incompatible dimensions; reset history after rebuilding. Use the production validation path.
6. Live host-loss/resize behavior from the acceptance table; mocks cannot replace these GPU tests.

Build/test success on Linux or a machine without the target GPU is `BUILD_OR_OFFLINE_ONLY`, never `POC_VERIFIED`.

## 14. Licenses and package boundary

Ship our text profiles, tooling, documentation and own permitted build outputs with notices. Default experimental package excludes all downloaded third-party runtime binaries and Lumenite files; users provide them through the manifest inputs.

[Feeder license](https://github.com/jlrouzies-fr/DLSS5-Feeder/blob/main/LICENSE) is MIT and names upstream bridge-derived portions. Preserve notices when deriving/extracting code. [ReShade](https://reshade.me/) identifies BSD-3-Clause and asks users to obtain its distribution from the official site. [Lumenite license](https://github.com/umar-afzaal/LumeniteFX/blob/mainline/LICENSE.md) is **AGNYA**, not MIT; do not fold its implementation into the shared core. [OptiScaler fork](https://github.com/Dagherbou/OptiScaler_DLSSNR) is GPL-3.0; it remains an optional external runtime, not code copied into the core under assumed MIT terms. DFC and NVIDIA binary redistribution permission was not established.

Record each dependency's license file and provenance. Do not disable antivirus, system security, driver signature checks or global OS protections to make installation work. A hash matches a specific download; it does not independently prove that an experimental binary is safe or authorized for redistribution.

## 15. Review packet and completion report

Produce `IMPLEMENTATION_REPORT.md` containing:

- Overall state: BLOCKED / PARTIAL / POC_VERIFIED / FLAT_CORE_VERIFIED.
- Exact pipeline and actual dependency lock; distinguish selected candidates from tested versions.
- Acceptance table with PASS/FAIL/NOT_RUN and evidence paths.
- Measured performance and visual limitations, including UI and optical-flow artifacts.
- Patches with reason and source anchor; no unexplained upstream rewrites.
- Extracted component boundaries and remaining OBVR work, without implementing it.
- Known missing inputs and exactly one next technical step if blocked.

Claude review checklist:

- Does any success claim confuse loading, DLAA, feature creation, NR evaluation or visual proof?
- Are all architectures, proxy filenames and consumer identities correct?
- Are frame age, format, MV units and raw-depth conventions preserved?
- Can host death or resource recreation leave a deadlock, stale output or use-after-free?
- Is extraction exercised by the real Flat path and its tests?
- Are any 4090, UI-safety or VR-support claims unsupported?
- Are version/hash locks, rollback and third-party notices complete?

Do not claim Claude has reviewed anything until an actual review is supplied.

## 16. Research coverage and unresolved runtime facts

Research included live NVIDIA compatibility/research pages; Feeder README/releases/issue #54; pinned GitHub API source retrieval of deployment instructions, IPC, shader, DFC interop header, x86 client, x64 host and build scripts; Lumenite source tree/Kernel/license; ReShade official docs; dgVoodoo maintainer docs/release metadata; OptiScaler NR release and classic-game reports.

Some GitHub HTML/raw links failed to render during research. Pinned Feeder files were successfully retrieved via the GitHub Git Trees/Blobs API and inspected. The API resolved the release to the full commit in §4. The dgVoodoo hash was obtained from its GitHub release asset metadata, not from a downloaded archive. Neither archive was executed here.

Further primary references: [NVIDIA research](https://research.nvidia.com/labs/adlr/DLSS5/), [ReShade source](https://github.com/crosire/reshade), [Feeder issue #54](https://github.com/jlrouzies-fr/DLSS5-Feeder/issues/54), [Microsoft D3D11 resource sharing](https://learn.microsoft.com/en-us/windows/win32/direct3d11/direct3d-11-1-features#sharing-direct3d-11-resources).

Unresolved facts are target-specific: Oblivion depth selection, renderer compatibility, exact local binaries, full-resolution NR behavior on the user's GPU, UI artifacts and performance. They have explicit tests above. Luna should implement this plan and run those tests, not restart an open-ended technology survey or conceal the remaining experimental nature of the integration.


## 17. Mandatory engineering, evidence and autonomous testing policy

This section is normative. It strengthens all earlier phases and gates. Implementing the harness is part of OBDLSS5 delivery, not optional follow-up work. Existing runtime gates still apply; automation never turns an unavailable environment into a passing result.

### 17.1 Fix root causes; make assumptions explicit

Prefer fixing the root cause over working around symptoms. Reproduce the failure, localize the first failing layer, form an explicit hypothesis, gather discriminating evidence, fix the underlying defect and retain a regression test. Do not hide errors by disabling the feature, suppressing logs, resetting history every frame, adding arbitrary delays, repeatedly restarting the helper, weakening assertions or loosening image thresholds until tests pass.

A safe pass-through after an error protects the game; it does not mean the requested NR feature passed. A workaround is permitted only when the root cause or precisely bounded limitation is recorded and a direct fix is outside this task's control. Label it as a workaround, document trade-offs and removal conditions, and retain a test exposing the original failure. The bounded fallback profiles in §9 remain available under this rule; they are not permission to bypass diagnosis.

Require hard proof. Maintain an evidence ledger linking each requirement and material technical claim to a pinned source, inspected code, reproducible test or captured runtime result. Distinguish VERIFIED, HYPOTHESIS, UNKNOWN and BLOCKED. Every hypothesis must state how it will be tested. Do not silently assume ABI behavior, file ownership, GPU support, successful NR, scene readiness or visual correctness. A source claim is not proof that our build works; a screenshot is not proof of which neural path executed.

### 17.2 Use Context7, Exa and DeepWiki MCP

For implementation-time API, dependency and architecture questions, prefer **Context7 MCP**, **Exa MCP** and **DeepWiki MCP** over recall from training data:

- Context7: resolve the actual library/project identity and retrieve version-relevant API documentation when indexed.
- Exa: locate current primary documentation, release notes, issue discussions and maintainer sources; open and evaluate the underlying source instead of treating a search summary as proof.
- DeepWiki: locate relevant repository components and understand call paths; verify consequential claims against the pinned source files and commit.

Discover the available MCP tools first. Use the tools appropriate to the question rather than mechanically querying all three for every change. Record source URL, applicable version/commit, retrieval date and the decision supported. Prefer exact pinned implementation behavior over generic or mismatched-version summaries. Existing research in this spec remains the baseline; use targeted lookup to resolve concrete questions, not a new open-ended survey.

If a named MCP is unavailable, record that limitation. Use accessible primary documentation and pinned local source as a disclosed fallback. If authoritative evidence cannot be obtained, leave the claim UNKNOWN and block dependent acceptance. Never pretend to have called an unavailable tool or fill gaps with remembered signatures, invented configuration keys or assumed behavior.

### 17.3 English throughout the project

All newly written or modified code identifiers, code comments, docstrings, Git commit messages, test names/descriptions, diagnostics, generated reports, documentation and developer-facing configuration explanations must be in **English**. Preserve third-party notices and exact external API identifiers. Do not translate unrelated upstream files merely to satisfy this rule. The implementation prompt is also in English.

### 17.4 Test suites and live game harness are required

Maintain automated unit/contract tests, integration tests and a Windows live-game acceptance harness. Tests must exercise our actual built/deployed code and selected profile. A fixture-only suite, mock renderer, upstream binary without our changes, or synthetic host test alone cannot satisfy live acceptance.

Implement `obdlss5.py test --suite unit|integration|game|all --profile <id>` and `obdlss5.py release-check --profile <id>`. These are required CLI interfaces to be developed, not claims that commands already exist. Tests return nonzero on any failed or blocked required case and write machine-readable results plus an English summary. Use the same production validators from the CLI/core rather than a second test-only implementation.

The live harness must:

1. Validate the dependency lock, build identity, selected installation and target GPU; deploy the exact candidate build to the isolated test installation.
2. Open the real game through its recorded launch method and track the actual game process, helper and loaded build identity. A launcher window alone is not game readiness.
3. Load controlled test saves or reproducible scene fixtures, drive camera/input and execute the applicable A01–A12 scenarios, including NR toggling, menus, save/load, lifecycle and helper failure. Keep fixture prerequisites explicit and preserve the user's personal saves. Store hashes and scene setup metadata; do not distribute game assets without rights.
4. Wait for observed readiness and render progress with bounded timeouts. Do not use a fixed sleep as sole readiness proof. Detect crashes, hung processes, missing windows, frozen frame progress and incorrect focus/input routing.
5. Capture lossless screenshots at named checkpoints and on failures; capture short motion sequences where temporal artifacts matter. Record camera/scene state, settings, timestamp, frame/run ID and build/profile identity. For NR comparison, keep the input scene matched and retain both OFF and ON evidence.
6. Collect game, host and consumer logs/counters from the same run and correlate them with screenshots. Confirm actual NR execution and evaluate visual quality separately. UI text/cursors, depth/motion alignment, channel order, black frames, stale output and temporal artifacts are explicit checks.
7. Inspect the captured images, through image-capable agent/tool review as well as suitable automated assertions. Pixel difference alone is not a visual-quality oracle. Calibrate tolerances against controlled nondeterminism, define the expected result before accepting a candidate, and retain the review verdict and reasons. If image inspection cannot run, visual acceptance stays BLOCKED.
8. Clean up only test-owned processes/resources, preserve diagnostics and restore the isolated setup as necessary. Do not repeatedly kill unrelated processes or change global machine settings to force a pass.

Each scenario must define preconditions, actions, timeout, expected behavior, executable assertions and evidence paths before its acceptance result is judged. Golden/reference images require documented provenance and review; the current failed output must never automatically become the golden image. For generative NR, compare stable invariants and controlled captures rather than requiring bit-identical neural pixels across different hardware. Any required human-only visual check remains pending until performed; do not silently replace it with a weaker automatic metric.

### 17.5 Autonomous development → test → inspect → fix loop

Operate automatically through: implement a scoped change → build → run targeted tests → launch the game harness where relevant → inspect screenshots and logs → diagnose the cause → fix → rerun. Continue until the intended features meet their explicit expectations and all applicable gates are green. Do not hand routine game launching, screenshot collection or regression reruns to the user when the agent has the required execution capabilities.

Run the full required suite on the final exact build and profile after targeted failures are resolved. In particular, repeat the live regression suite after shared-core extraction. Associate results with the commit/build hash and dependency/configuration hashes; results from an older build cannot approve a newer one.

Automation must make progress rather than retry blindly. Repeated identical failures without new evidence require a fresh diagnosis. An unavailable game, GPU, credentialed dependency, MCP source or interactive desktop is an explicit blocker, not an endless restart loop. Complete independent work and report the exact missing input when blocked. Do not waive or skip the gate to appear finished.

### 17.6 Green-before-ship gate

**Test suites and the live harness must exist and all required tests must be green before shipping.** For the selected release profile, A01–A12 and the post-extraction requirements must pass on the exact release candidate. Shipping includes marking a package ready for users, uploading a release or making a supported-compatibility claim. A diagnostic/WIP artifact may be retained, but must be labelled NOT FOR RELEASE.

`release-check` must fail closed if a required test fails, is skipped, quarantined, UNKNOWN, NOT_RUN or BLOCKED, if screenshots/visual verdicts are missing, if evidence belongs to another build/profile, or if the evidence index is incomplete. Require at least two consecutive passing full live-suite runs from clean game launches on the final candidate to expose startup/recovery flakiness. Disclose the tested hardware/profile scope; green RTX 50 tests do not establish RTX 4090 support. A failing required 4090 target remains blocked rather than being silently removed from the release requirements.

Record every failure and retry in the run history; do not report only the successful attempt. Do not lower acceptance criteria, delete failing cases, replace integration tests with mocks or grant yourself an exception to make the badge green. Any scope/acceptance change requires an explicit documented decision from the user. Publication still requires a user request; green tests do not themselves authorize publishing.

Add to Claude's review packet: evidence ledger; automated harness entry points; scenario definitions and assertions; final build/profile hashes; full suite results; two consecutive final live-run IDs; screenshots/motion captures and their verdicts; failure history; diagnosed root causes; any explicitly labelled workarounds; MCP/source lookup records. Claimed completion is invalid without these artifacts.
