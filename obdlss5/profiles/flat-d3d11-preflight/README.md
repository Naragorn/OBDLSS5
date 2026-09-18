# flat-d3d11-preflight

This is the real-install preparation profile for classic 32-bit Oblivion. It deploys only the verified wrapper, ReShade, Feeder, LumeniteFX and 64-bit helper files that are available in the local procurement workspace.

`dlss5-feed.cfg` is deliberately set to `mode=1`. This proves no neural feature; it is a transport-only preparation step. The primary `flat-d3d11` profile remains blocked until the exact DFC and NVIDIA runtime files are supplied and independently hashed.

The deployment keeps the dgVoodoo watermark enabled until wrapper activation is observed. Existing unrelated files, including an existing `d3d9.dll.dxvk`, are not selected by this profile.
