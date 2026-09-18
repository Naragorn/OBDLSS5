# OBDLSS5

OBDLSS5 is the flat-screen experimental integration for classic The Elder Scrolls IV: Oblivion (2006). The implementation is fail-closed: an installed wrapper or a DLAA-like host result is never reported as neural rendering without independent consumer evidence.

## Current machine state

The selected game is D:/SteamLibrary/steamapps/common/Oblivion. Its Oblivion.exe is verified PE32/I386. The x64 host observed an NVIDIA GeForce RTX 4090 with driver 616.92.

The flat-d3d11-primary profile is deployed with mode=2, DFC 2.0.0 CP184, NVIDIA DLSS 310.9.1 and the experimental NVIDIA DLSSNR 310.8.SF-v2 runtime. Placement and hashes pass. H0 proves DFC ARMED, successful Feature-18 neural creation/evaluation and synthetic feeder evaluations on this RTX 4090. A real Oblivion run also recorded Feed -> x64 host -> standalone DLSSNR success with screenshots. host_window=2 is the measured compatibility setting for this installation. The existing d3d9.dll.dxvk remains preserved.

## Deployment

The local procurement workspace contains the hash-locked build inputs. The primary install journal is:

D:/SteamLibrary/steamapps/common/Oblivion/obdlss5-primary-install-journal.json

The CLI supports inventory, stage, verify, collect, rollback, test and release-check. The evidence records are [evidence-ledger.json](/D:/Modding/OBDLSS5/obdlss5/results/evidence-ledger.json), [evidence-index.json](/D:/Modding/OBDLSS5/obdlss5/results/evidence-index.json), [deploy-primary.json](/D:/Modding/OBDLSS5/obdlss5/results/deploy-primary.json) and [verify-primary.json](/D:/Modding/OBDLSS5/obdlss5/results/verify-primary.json).

Rollback is owned-only and conflict-preserving.

## Evidence boundary

The current result is PARTIAL, not POC_VERIFIED. The real game launch and same-run neural execution are now verified for the captured primary run: the screen shows the DLSS 5 Feed status and DFC consumer, while the logs record DLSSNR initialization, Feature 18 creation and repeated successful neural frames. A matched NR OFF/ON capture pair, visual verdict artifact, lifecycle scenarios and the full performance matrix remain incomplete. Do not advertise the current state as a complete Oblivion NR PoC yet.

No VR, OpenXR, stereo, eye tracking, frame generation or shared core is included. obdlss5/core/ remains intentionally absent until a measured Flat PoC exists.
