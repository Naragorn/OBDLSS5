# OBDLSS5

Experimental DLSS 5-style neural-rendering integration for classic 32-bit
The Elder Scrolls IV: Oblivion.

The public install kit is in
[`release/OBDLSS5-Oblivion-v0.1.0/`](release/OBDLSS5-Oblivion-v0.1.0/).
Start with its [English installation guide](release/OBDLSS5-Oblivion-v0.1.0/INSTALL.md).

This is not an official NVIDIA product. NVIDIA's official DLSS 5 3D-Guided
Neural Rendering support is documented for GeForce RTX 50 Series GPUs. The
experimental Oblivion route was measured on an RTX 4090 with a separately
sourced SF-v2 NR runtime; that result must not be read as official RTX 4090
support.

The implementation report and complete specification remain available in
[`IMPLEMENTATION_REPORT.md`](IMPLEMENTATION_REPORT.md) and
[`OBDLSS5_SPEC.md`](OBDLSS5_SPEC.md). The full specification gate is currently
partial, so this repository is an experimental release and not a production
compatibility promise.
