# Stage 1–5 delivery and acceptance evidence

27 October 2026. All implementation, dependencies, inputs and outputs are inside BTP. No paid service was used. The delivered scope is a trusted, single-user Windows CPU research backend. Machine-readable verification: `runtime/verification/acceptance.json`; regression details: `runtime/verification/tests.json` and `tests.log`.

## What is complete and verified

| Stage | Delivered | Evidence |
|---|---|---|
| 1 Foundation | Dedicated runtime, pinned packages, offline binary bundle, model checksums/source records, references, secret-pattern scan, capability inventory; sampling, Mol2Mol, TL and RL CPU smoke runs | Fresh `runtime/recreated-py312` passes checks and 100-molecule baseline; both prior checksums verified; no secret-pattern findings in the scanned scope |
| 2 Contracts | 19 versioned schemas; architecture, API draft, state conditions, registry interfaces, error boundaries, database migrations and threat model | `schemas/v1/`, `docs/ARCHITECTURE.md`, `API_CONTRACT.md`, `THREAT_MODEL.md`; valid/invalid contract tests and old/future schema tests |
| 3 Control | Owner/role checks, exact-hash approvals and input manifests, revisions, iteration isolation of approvals, cumulative budgets, launch reservations, append-only hash-chained history, supervision/recovery, ledger regeneration and terminal archival | Mock campaign completion; illegal-transition matrix; every-state reopen; transaction/launch rollback; concurrency, mutation, ownership, corruption/missing-input and orphan-process tests |
| 4 Engine | MCP schema discovery and dry-run adapter, installed-engine validation, supervised exact-config execution, job/PID/log/checkpoint/artifact collection, cancellation/timeout, derived learning plot and molecule analysis | Actual MCP-to-controller sampling, Mol2Mol, one-epoch TL and two-step QED RL all pass; each records byte-identical preview/execution TOML; cancellation and timeout pass |
| 5 Evaluation | Structure policy, descriptors, QED/SA, SMARTS constraints, PAINS/Brenk flags, rule summaries, fingerprints/neighbors, novelty, scaffolds/diversity/clustering, data curation, registries, first predictor, uncertainty/domain gating and JSON/Parquet evidence | 777 curated EGFR molecules; scaffold-held-out test; deterministic evaluator checks; model reproduction; valid/invalid structures, stereoisomers, salts, out-of-domain and missing inference tests |

The regression suite passes **57 tests with no skips**. The acceptance script checks that the source hashes still match that test run. Tested source code and actual data are the evidence; test counts alone are not the acceptance criterion.

## Actual run evidence

- Fresh-environment 100-molecule MCP baseline: `runtime/baseline-20261027T141908586203Z/`; 100 valid and unique in this run. This stochastic observation is not a general quality guarantee.
- MCP/controller exact-config sampling: `runtime/controlled-sampling-20261027T143019Z/`.
- Latest direct sampling with primary-output and log collection checks: `runtime/controlled-sampling-20261027T144325Z/`.
- Exact-config MCP Mol2Mol: `runtime/controlled-mol2mol-20261027T150106Z/`.
- Exact-config MCP transfer learning: `runtime/controlled-transfer_learning-20261027T145615Z/`.
- Exact-config MCP reinforcement learning: `runtime/controlled-staged_learning-20261027T145729Z/`.
- Cancellation: `runtime/controlled-sampling-20261027T142103Z/`.
- Timeout: `runtime/controlled-sampling-20261027T142613Z/`.
- Derived RL plot and independent molecule analysis: `runtime/rl-report-20261027T145146Z/`. The two-step reward decreased; this is an infrastructure check, not a successful optimization claim.
- Failed attempts are retained, including schema mismatches, OpenBLAS resource failure and Windows TOML path escaping. Their causes and fixes are documented rather than erased. `VENDOR_CHANGES.md` attributes the local builder adaptations.

Smoke campaigns record explicitly automated test approvals under the user's development authorization. They do not impersonate scientist review of an actual pharmaceutical campaign. The normal CLI enforces the local OS principal and acting role; trusted Python code is not an adversarial authentication boundary.

## Scientific baseline

Target: assay-described wild-type human EGFR, CHEMBL203/P00533. Of 18,381 downloaded exact IC50 binding records, conservative curation produced 777 molecules and 354 scaffold categories. Train/calibration/test rows: 518/88/171. The CPU fingerprint forest obtains held-out MAE 0.5573 pIC50, RMSE 0.7647, R-squared 0.6432 and Spearman 0.8294, exceeding the mean and nearest-neighbor baselines on this split.

The calibrated interval is approximately ±1.3983 pIC50, with 93.57% empirical coverage at nominal 90%. Domain coverage is 79.53%. Thirty-eight publications overlap across scaffold partitions. Only five held-out examples meet pIC50 <= 5. Tautomerization limits, source-assay variability and stereochemical caveats remain. Read `EGFR_MODEL_CARD.md`; these are preliminary research results, not an independent external validation or clinical claim.

Training repetition reproduced the exported JSON model exactly and metrics within 1e-10. Registries enforce artifact hashes, dataset/target linkage and consistent qualification metadata. An activity score must name the correct qualified predictor and its model hash. The predictor is eligible under its declared internal research gates; that does not constitute human approval of a real experiment.

## Why this is not an unrestricted “100% finished” claim

The local MVP checks above pass. The full roadmap has broader tests and later-stage controls; they must not be silently treated as completed:

- **CUDA remains unverified.** Hardware inspection found an RTX 3060 Laptop GPU, but the pinned environment is CPU-only. No GPU-capable environment or driver change was made. Stage 1's capability status is explicit; no GPU result is invented.
- **Recovery evidence is simulated/local.** Transaction failures, reserved jobs, missing supervisors, a real dummy orphan process, persistence, cancellation and timeout are tested. A real machine power failure at every execution boundary and cross-machine restoration were not tested.
- **Local identity only.** A single owner may hold scientist/operator/model-owner/reviewer responsibilities. Multi-user network authentication, service-account/container isolation, kernel RAM/disk quotas and deployment hardening belong to the portal/deployment stages.
- **Engine reward scope is bounded.** QED RL is working. The registered EGFR predictor is not yet wired into REINVENT's RL reward. Target-specific end-to-end optimization and LLM specialists remain subsequent integration stages.
- **Scientific review is not fabricated.** No external supervisor/medicinal-chemist signoff, experimental assay validation, multi-seed dissertation benchmark or prospective validation is claimed.
- **Historical external credential concern remains unverified.** BTP does not use that external source or require an API key. The bounded BTP scan found no matching secrets; it cannot establish provider-side revocation.

Thus: the substantial Stage 1–5 local backend and scientific foundation is implemented and verified; a blanket claim that every roadmap item and validation scenario is 100% closed would overstate the evidence.

## Next development boundary

Update, 28 October 2026: the subsequent CPU agent/reward integration and actual Stage 7 campaign are recorded in `STAGE_7_DELIVERY.md`. The evidence and test counts above remain the historical Stage 1–5 record rather than a current-source regression claim.

Use these stable contracts and execution services for Stage 6 specialists. Before promoting the first real target-specific campaign, add the tested predictor reward adapter, explicit scientific campaign acceptance criteria, appropriate reviewer signoff and the Stage 7/8 equal-budget evaluations. Keep Strategist/VECTOR+ extensions in Phase 2 rather than conflating them with this foundation delivery.
