# OBDLSS5 implementation prompt for Luna

Place `OBDLSS5_SPEC.md` beside this prompt in the project. Give Luna the following assignment.

---

Implement **OBDLSS5** according to the complete accompanying `OBDLSS5_SPEC.md`, version **1.1**, researched on 2026-09-18. Read the entire specification before changing code. It supersedes earlier conversational plans, and its mandatory engineering/testing policy in §17 applies throughout.

Implement only the Flat version for classic Oblivion (2006). This project will later be the foundation for OBVR through a genuinely shared internal component. Do not implement VR, OpenXR, stereo, eye tracking or additional VR quality modes now.

## Evidence and engineering rules

- Prefer fixing the **root cause** over working around symptoms. Reproduce, isolate, gather evidence, fix the underlying defect and add a regression test. Never hide a failure by disabling the intended feature, suppressing diagnostics, adding arbitrary delays or weakening assertions. Use the bounded fallbacks only with a documented cause and limitation; a workaround is not a fixed primary path.
- Require **hard proof and no silent assumptions**. Maintain the evidence ledger from §17. Separate VERIFIED, HYPOTHESIS, UNKNOWN and BLOCKED. Source claims, successful compilation, a loaded DLL, DLAA success, consumer readiness, actual NR execution and visual correctness are different evidence levels.
- Prefer **Context7 MCP + Exa MCP + DeepWiki MCP** for concrete documentation and repository questions over training-data recall. Discover available tools, use the appropriate service, retrieve primary sources and verify consequential claims against the pinned code/version. Record provenance. Do not restart broad research or replace locked versions with latest. If a service is unavailable, disclose that and use primary docs/local source; never fabricate tool use or unsupported API details.
- Write all code identifiers, comments, docstrings, Git messages, test descriptions, diagnostics, reports and documentation in **English**, preserving external API names and third-party notices.

## Execution order

1. Read local project instructions, README, handoff and relevant build/renderer history. Record the initial commit and working-tree changes. Map the specification's paths to the actual checkout and preserve unrelated work.
2. Implement P0 and the offline tools: inventory, dependency locking, staging, verification, evidence collection and rollback. Implement the required `test` and `release-check` interfaces and test-suite structure early. Keep existing OBVR behavior untouched.
3. Run host gate H0 early. Record exact missing DFC/NVIDIA files or runtime limitations. RTX 4090 NR is experimental. DLAA-only success is never DLSS5-NR success.
4. Execute P1–P5 in order: game → wrapper → ReShade/guides → transport/DLAA → actual NR → reproducible Flat PoC. Begin with the selected D3D11 profile and `async_home=0`. Use §9 fallbacks only when their evidence conditions are met and record separate profiles.
5. Build and use the **live Windows game harness**. It must launch the actual game with our candidate code, load controlled scenarios, drive input, toggle NR, collect logs and screenshots, exercise lifecycle/failure cases, inspect visual results and produce machine-readable verdicts. A synthetic host run or mock renderer cannot replace it.
6. After the Flat PoC passes, execute P6: extract the smallest useful shared implementation from the proven path. The real Flat caller and synthetic host tests must exercise it. No unused interfaces and no wholesale Feeder rewrite. Repeat live regressions after extraction.
7. Prepare the implementation report and Claude review packet specified in §§15 and 17. Follow dependency/licensing limits. Do not publish automatically.

## Autonomous development and testing loop

Work automatically through **develop → build → test → launch game → inspect screenshots/logs → diagnose → fix → retest** until the requested features behave as specified and all required gates are green. Do not stop at code that merely compiles or hand routine test execution to the user when you can perform it yourself.

Define each scenario's expected result and assertions before judging its output. Preserve matched NR OFF/ON captures and temporal evidence. Inspect the actual screenshots with image-capable tools; do not treat any pixel difference as proof of correct NR. Record build/profile/run identity with every result. Never approve a new build using an older build's evidence or automatically turn failed output into a golden reference.

Maintain meaningful unit/contract, integration and live acceptance suites. Run targeted tests while fixing defects, then the full required suite on the final exact candidate. Require **two consecutive passing full live-suite runs from clean launches**, including the specified screenshot/visual checks. Retain failure history and root-cause explanations.

**Before shipping, the test suites and live harness must exist and all required tests must be green.** `release-check` must fail for required failures, skips, quarantines, UNKNOWN, NOT_RUN, BLOCKED, missing visual evidence or mismatched build/profile hashes. Do not remove tests, weaken thresholds, replace real tests with mocks or silently drop a required GPU target to manufacture green results. Green tests do not authorize publication.

If Windows, the game, GPU, interactive desktop or required runtime files are unavailable, complete all independent implementation/offline work. Mark live gates truthfully and identify the exact missing input. Do not claim completion or bypass the PoC gate to deliver a supposedly working shared core. Repeated identical failures require new diagnosis rather than blind retries.

Make small, coherent commits without asking before each reversible implementation step. Preserve existing changes and record backups for replaced proxy DLLs. If the specification is demonstrably wrong, document evidence and the smallest correction. Implement supported local corrections; document major architecture or acceptance changes for a user decision while continuing independent work. Do not silently change scope or acceptance standards.

Finish with a concise status and `IMPLEMENTATION_REPORT.md`: changed components, exact tested pipeline, suite results, evidence paths, measured performance, remaining defects, root causes/workarounds and one concrete next step if blocked. Include the evidence ledger, source/MCP records, final build/profile hashes, final live-run IDs and screenshot verdicts for Claude. Do not claim Claude has reviewed anything before an actual review occurs.

Start by reading the specification and inspecting the local project, then implement the plan.
