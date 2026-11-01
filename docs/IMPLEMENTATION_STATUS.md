# Implementation status — 29 October 2026

The local portal and Stage 8–10 research-release evidence are documented in [LOCAL_RELEASE.md](LOCAL_RELEASE.md). Use `QUICKSTART.md` at the BTP root for the professor-demo walkthrough. Current full regression: 69 passing tests. A real HTTP campaign journey and an original-location backup/restore drill passed. The redesigned browser interface still needs visual signoff because the computer/browser connector became unavailable. Production deployment and scientific effectiveness are not claimed.

The Stage 6–7 CPU MVP has run successfully: see [STAGE_7_DELIVERY.md](STAGE_7_DELIVERY.md) for observed results and [STAGES_6_7.md](STAGES_6_7.md) for operating instructions. The 27 October acceptance report below is historical and predates the new agent/reward source; do not treat it as a current-source test result.

## Current delivery

The initial foundation below has been substantially extended. Read [DELIVERY_REPORT.md](DELIVERY_REPORT.md) for current Stage 1–5 capabilities and the precise acceptance boundary. `runtime/verification/acceptance.json` verifies 57 passing tests, 19 schemas, offline environment recreation, real MCP-to-controller sampling/Mol2Mol/TL/RL with byte-identical configurations, cancellation/timeout checks, and the registered EGFR scientific baseline. CUDA execution remains unverified even though an RTX 3060 Laptop GPU is present.

## Historical initial-foundation snapshot

The remainder records the earlier implementation state and is retained for provenance; its unfinished-work table is superseded by the delivery report.

The owner has delegated target/dataset selection and authorized free resources only. Human EGFR/ChEMBL is the initial benchmark under feasibility assessment (`TARGET_SELECTION.md`). The historical external credential concern remains unverified (`CREDENTIAL_STATUS.md`); no new API key is required for this foundation work.

## Verification evidence

- BTP-local migration verified on 2026-10-27: all 17 tests passed using `.venv/Scripts/python.exe`; `pip check` found no broken requirements, and the active dependency-origin audit passed for 101 installed distributions. No filesystem links were found in the copied environment, vendor, model, or reference directories.
- New BTP-only CPU sampling passed in `runtime/baseline-20261027T133115176071Z/`: 100 raw samples, 97 valid and unique, 84 scaffold categories, internal diversity 0.89576650 across 4,656 pairs. Parsed preview/executed configurations matched. This demonstrates infrastructure operation, not potency or drug suitability.
- The following earlier results are retained as historical evidence from before dependency migration.

- 17 automated regression tests passed on 2026-10-27 using Python 3.12.3 from the existing Solitarius environment.
- Windows sandbox blocked atomic ledger replacement; the same tests passed outside the sandbox. SQLite connections are now explicitly closed after each transaction.
- Real MCP CPU sampling completed in `runtime/baseline-20261027T131903571499Z/`.
- Requested/raw molecules: 100; independently valid: 96; unique valid: 96; scaffold categories including acyclic: 89; mean fingerprint distance: 0.89321956 across 4,560 unique pairs.
- Parsed preview and executed TOML matched. This comparison is post-execution evidence, not a substitute for a production pre-launch approval boundary.
- The sampling API does not expose a seed in this path; repeated runs can differ. The observed 96% result is a smoke-test observation, not a benchmark claim.
- `environment.json`, `environment-observed.txt`, `tools.json`, `preview.toml`, raw CSV, MCP response, and independent `evaluation.json` preserve the evidence.

| Roadmap stage | Implemented evidence | Remaining gate |
|---|---|---|
| 0 Initiation | Package layout, original implementation, architecture decisions, documented attribution | Target/dataset choice, budgets and named scientific owner |
| 1 Foundation | Dedicated BTP environment, vendored engine/server, local prior and references; pip check and import-origin audit clean | Portable reproducible installation bundle; Mol2Mol model and TL/RL smoke runs; credential revocation confirmation |
| 2 Contracts | Campaign states, approval routes, target and predictor metadata, typed uncertainty/domain gates | Full versioned schema inventory, migrations, assay/dataset/score contracts |
| 3 Control | Transactional SQLite, history, optimistic revision check, approval hash checks, single launch reservation, restart persistence, ledger | Authenticated actors, revision flow, budgets, external-process reconciliation and automated recovery |
| 4 Engine | Real MCP client, discovery and bounded sampling baseline, preview/actual comparison | Approved-config execution adapter, TL/RL job supervision, cancel/reconnect/process reconciliation |
| 5 Evaluation | RDKit descriptors, SA heuristic, SMARTS gates, exact novelty, similarity, scaffolds, diversity, honest missing-model status | Curated dataset, calibrated activity model, real domain/uncertainty estimators, alert catalogs, complete evidence schema |

## Known boundaries

- Tests of state policy run against a trusted local caller. They do not establish network or multi-user security.
- Predictor fixtures test qualification logic only. No target-specific predictor has been trained or registered.
- The baseline script is developer-authorized infrastructure sampling, not a campaign with simulated human approval.
- The CLI can request generic analysis/completion transitions; evidence-enforced completion is still required before agent integration.
- Approval validation currently detects changes at launch; automatic invalidation/reapproval workflows remain pending.
- All active source, package installations, scientific assets, and references now reside in BTP. Neighboring folders are no longer runtime dependencies. System Python and Windows remain prerequisites; see `LOCAL_DEPENDENCIES.md`.
- No credential was revoked: revocation needs access to the issuing service. Existing external `chat.py` has not been copied or executed.

## Next implementation slice

1. Add complete JSON schemas and objective/score artifact type validation.
2. Add job reconciliation and exact-approved-config execution.
3. Build a reproducible installation bundle from the now-local BTP scientific environment and expand model/input manifests.
4. Run bounded TL/RL tests after config compatibility verification.
5. Select the first target and curate a scientifically valid dataset before predictor optimization.
