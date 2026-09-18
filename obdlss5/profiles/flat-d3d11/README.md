# Flat D3D11 profile

This is the selected primary profile for classic Oblivion (2006). It is a locked staging contract, not a compatibility claim. Users supply the third-party artifacts through explicit `--artifact ROLE=PATH` assignments; the tool refuses required components whose deployed hashes are not recorded in the lock.

The profile keeps `async_home=0`, native work resolution, one view, SDR output and the dgVoodoo -> ReShade x86 -> Feeder -> host64 layout from `OBDLSS5_SPEC.md`. The dgVoodoo watermark is enabled only for wrapper proof and must be removed before performance measurements.

