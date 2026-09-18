# OBDLSS5 implementation report

Date: 2026-09-18  
Specification: OBDLSS5_SPEC.md, version 1.1  
Overall state: PARTIAL

## Current result

The requested classic Oblivion installation is D:/SteamLibrary/steamapps/common/Oblivion. Oblivion.exe is verified as PE32/I386 with SHA-256 a8f313845c1545e9a60e1e995961eef4c033115da9443f6d756341df3c2b7dc6.

The mode=2 primary build is deployed with user-supplied Deep Fried Chicken 2.0.0 CP184, NVIDIA DLSS 310.9.1 and the hash-locked experimental NVIDIA DLSSNR SF-v2 runtime. The existing d3d9.dll.dxvk was inspected and preserved; it was not overwritten or renamed.

## Deployed files

- dgVoodoo x86 D3D9.dll
- ReShade Add-on x86 dxgi.dll
- Feeder dlss5-feed.addon32 and host64/dlss5-feed-host64.exe
- ReShade shader headers, DLSS5_Feed.fx and the pinned LumeniteFX shaders/includes/texture
- ReShade Add-on x64 at host64/dxgi.dll
- DFC 2.0.0 CP184: host64/deep-fried-chicken.addon64, host64/deep-fried-chicken-nvngx.dll, host64/deep-fried-chicken.cfg
- NVIDIA DLSS host64/nvngx_dlss.dll 310.9.1
- Experimental NVIDIA DLSSNR host64/nvngx_dlssnr.dll 310.8.SF-v2 / stated file version 310.8.SF.0
- dgVoodoo.conf, ReShadePreset.ini, both ReShade.ini files and dlss5-feed.cfg

Placement and SHA-256 verification passed for all 28 primary profile roles and the five profile configuration files. The current reports are [deploy-primary.json](/D:/Modding/OBDLSS5/obdlss5/results/deploy-primary.json) and [verify-primary.json](/D:/Modding/OBDLSS5/obdlss5/results/verify-primary.json). Rollback ownership is recorded in D:/SteamLibrary/steamapps/common/Oblivion/obdlss5-primary-install-journal.json; the prior normal NR DLL is in backup D:/SteamLibrary/steamapps/common/Oblivion/.obdlss5-backups/20260918T090330Z-62a20c5b.

## H0 result

The isolated candidate test and the actual deployed host both used the host64/dlss5-feed-host64.exe --test --hide command.

Measured on the actual machine:

- NVIDIA GeForce RTX 4090, driver 616.92
- exit code 0
- DFC 2.0.0 reached ARMED / consuming the synthetic contract
- SF-v2 loaded as nvngx_dlssnr.dll 310.8.2.0, stated file version 310.8.SF.0
- NVIDIA DLSS loaded as 310.9.1.0
- Feature 18 was created through the DFC bridge
- neural evaluation returned Success; the log records standalone neural frame succeeded
- 300/300 synthetic feeder evaluations succeeded
- DFC reports pipeline=ENABLED

This resolves the earlier stock-runtime block on Ada: the normal 310.8.0 runtime rejected Feature 18, while the separately published experimental SF-v2 runtime passed the same H0 on this RTX 4090. The SF-v2 binary is external and unreviewed; this is a measured compatibility result, not a redistribution or safety claim.

Evidence: [H0 collect record](/D:/Modding/OBDLSS5/obdlss5/results/h0-sf-v2-live-20260918T0905Z-collect.json), [host log](/D:/Modding/OBDLSS5/obdlss5/results/runs/h0-sf-v2-live-20260918T0905Z/host-log/dlss5-feed-host.log) and [DFC log](/D:/Modding/OBDLSS5/obdlss5/results/runs/h0-sf-v2-live-20260918T0905Z/dfc-log/deep-fried-chicken.log).

## Tests and acceptance boundary

- Direct unittest discovery: 20 tests PASS.
- Primary PE32 and placement/hash verify: zero failures.
- A02 H0: PASS.
- A02 H0: PASS.
- Real-game primary run: Feed delivery, x64 host evaluation, GPU timing, DFC standalone DLSSNR activity and screenshots: VERIFIED for the captured run.
- A03-A05, A07-A10 lifecycle/gameplay and A12 full performance matrix: PARTIAL or not complete.
- A06 controlled static OFF/ON pair: recorded. OFF uses enabled=0 with an explicit no-frames-fed log; ON uses enabled=1 with NR_ACTIVE suite evidence and a screenshot. Motion capture and same-process toggle evidence remain incomplete.
- Release gate remains fail-closed; this is PARTIAL, not POC_VERIFIED or FLAT_CORE_VERIFIED.

## Dependency and source policy

DFC was supplied locally by the user and recorded as 2.0.0-CP184-Performance-Matched-Residual. The normal NVIDIA NR runtime was replaced only after an isolated test of the separately sourced SF-v2 archive. The archive SHA-256 is 1da35941894994eb087e017577829e492454e9bae3a6a9397027069ceb74955c; the deployed DLL SHA-256 is 6eb209e764f39872625debd6abaf45e2bb6322f6f270f781f70c059ae30b3927. Both are recorded in obdlss5/dependencies.lock.json. OptiScaler was not silently substituted for DFC.

## Next technical step

Complete the remaining release-gate work: a baseline run, matched NR OFF/ON captures with a recorded visual verdict, lifecycle/host-loss tests and the full performance matrix. The captured real-game NR run is now evidence-backed, but it is not the full Flat PoC gate.

obdlss5/core/ remains intentionally absent because the specification gates shared-core extraction on a passing Flat PoC.
