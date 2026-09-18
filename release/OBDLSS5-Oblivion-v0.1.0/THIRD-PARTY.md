# Third-party components and provenance

This public kit contains no third-party binary payloads. Download them from
the upstream locations below and retain the listed versions. The hashes are
the hashes recorded during the author's local validation; they are not a
substitute for checking the upstream release and its license.

| Component | Required version | Upstream | Recorded archive/deployed hash | Distribution note |
|---|---|---|---|---|
| DLSS5-Feeder | v1.16.0-beta.4, commit `53f88d4be93ae48e7e1ba5ef7a4f7d87618843ff` | [GitHub release](https://github.com/jlrouzies-fr/DLSS5-Feeder/releases/tag/v1.16.0-beta.4) | archive `d16f8b527f76ff1f531682a576d699cb5634838c0e2899585e3671814eda2745` | Obtain from upstream; do not use lookalike downloads. |
| dgVoodoo2 | v2.87.5 | [GitHub release](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.87.5) | archive `5ffde6927f7355ca3fdd5d785b581256a8e6539fa13e395a891ade6ba1040850` | License/provenance must be accepted from upstream. |
| ReShade | 6.8.0, x86 and x64 add-on builds | [reshade.me](https://reshade.me/) | installer `afe4c8f13048306307983b8b3d41d5bf00a86820440b0e57dea10950e1176445` | Obtain and install from the official site. |
| LumeniteFX | commit `f8cbbb4eccfcb7adf0d74bb358ba349272e3c1e9` | [Pinned source tree](https://github.com/umar-afzaal/LumeniteFX/tree/f8cbbb4eccfcb7adf0d74bb358ba349272e3c1e9) | archive `43220f99fc0ffa0216e01ebd657180f8c9d043c939f760283b896ea257f1b6a2` | AGNYA license requires official-link distribution; it is not mirrored here. |
| Deep Fried Chicken | 2.0.0-CP184-Performance-Matched-Residual | Author distribution channel recorded in the lock | files recorded in `obdlss5/dependencies.lock.json` | User must obtain the original package and follow its terms. |
| NVIDIA DLSS runtime | `nvngx_dlss.dll` 310.9.1 candidate | [Pinned archive](https://github.com/RankFTW/rhi-repo/releases/download/dlss-310.9.1/nvngx_dlss_310.9.1.zip) | archive `aaba83b288bd145c3808e8d7a0ba03cc8c8676d18ad984b1bfa6563046a3ba37` | NVIDIA runtime; not redistributed by OBDLSS5. |
| NVIDIA DLSSNR runtime | SF-v2 experimental candidate | [Pinned archive](https://github.com/RankFTW/rhi-repo/releases/download/dlssnr-310.8.SF-v2/nvngx_dlssnr_310.8.SF-v2.zip) | archive `1da35941894994eb087e017577829e492454e9bae3a6a9397027069ceb74955c` | Experimental/unreviewed; no official NVIDIA support claim. |

The full machine-local lock is included in `obdlss5/dependencies.lock.json`.
The SF-v2 runtime is the measured reason the RTX 4090 test passed; the normal
310.8.0 candidate rejected Feature 18 in the same isolated test. This is a
compatibility observation, not a guarantee for other GPUs, drivers or games.

