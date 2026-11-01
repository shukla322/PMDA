# Stages 1–5 completion tracker

Authority: `DEVELOPMENT_ROADMAP.md` exit gates, supported by actual test and run artifacts. Created 27 October 2026. The work packages below are now implemented for the trusted local CPU research MVP; current evidence and remaining boundaries are in `DELIVERY_REPORT.md` and `runtime/verification/acceptance.json`. This is not a blanket assertion that every possible roadmap test, optional hardware path or production control has been verified.

## Project-owner decisions and remaining external uncertainty

1. Target/data selection delegated to the implementer. Human EGFR/ChEMBL is selected for feasibility assessment; see `TARGET_SELECTION.md`. No target-specific model may be claimed validated before curation, split design, evaluation and intended use are documented.
2. Free resources only. Use local CPU, no paid cloud or API services, bounded runs, and document download sizes/storage requirements before large acquisitions.
3. The owner does not know the historically reported credential. Its current status is unverified; see `CREDENTIAL_STATUS.md`. This does not block independent BTP engineering or require a new API key.

Engineering work on contracts, control, evaluation infrastructure and execution can proceed independently of the target decision. Target selection and data suitability block the curated target dataset and predictor deliverables. Human scientific review must be recorded honestly, not invented by software.

## Work packages and required evidence

| Order | Stage | Remaining work | Completion evidence |
|---|---|---|---|
| 1 | 1 | Pin dependencies, document CPU/GPU and external network prerequisites, baseline/model manifest, secret scanning and remediation report | Recreated environment passes package checks and baseline; capability matrix explicitly records verified/failed/blocked operations |
| 2 | 2 | Version all MVP schemas, candidate tables, registries, interface contracts, errors, state entry/exit conditions, migration/backward-compatibility policy and threat model | Valid/invalid fixtures, migration tests, complete schema inventory and architecture documentation |
| 3 | 3 | Roles/permissions, artifact revision and reapproval, budgets, idempotency, recovery, evidence-enforced completion, mock adapters and audit integrity | Mock campaign completes with authorized actions; transition matrix, crash/restart, corruption and duplicate-launch tests pass |
| 4 | 4 | Approved immutable configuration and input manifests, supervised engine execution, MCP compatibility map, PID/job reconciliation, timeout/cancellation and artifact collection | Approved real sampling traverses state machine; exact config checks; fake-server tests; disconnect, cancellation, missing-output and restart evidence |
| 5 | 1/4 | Mol2Mol, TL and RL bounded runs | Actual logs, configs, model/input hashes and outputs; any blocked capability has an explicit cause rather than a success label |
| 6 | 5 | Standardization policy, alert catalogs, neighbors/clustering, dataset/predictor registries, traceable JSON/Parquet evidence | Golden chemistry fixtures, edge-case handling, deterministic output and missing-inference rejection tests |
| 7 | 5 | Curate selected target dataset; train and evaluate first predictor; calibrate uncertainty/domain; document suitability for optimization | Provenance and curation report, leakage-aware splits, held-out metrics, uncertainty/domain evaluation, predictor contract and documented qualification decision |
| 8 | 1–5 | Reconcile every roadmap gate with implementation and evidence | Final acceptance matrix links each requirement to code, tests and run artifacts; unresolved gates remain open |

## Completion boundaries

- Stage 1 permits explicit blocked capability statuses, but this must not be described as all scientific capabilities working.
- Stage 5 requires a real target-specific predictor report; placeholders and synthetic test fixtures do not fulfill it.
- Completion means research software validated for its documented intended use, not clinically validated drugs or demonstrated efficacy.
- LLM specialist agents begin at Stage 6; the web portal begins at Stage 9; the Strategist is Stage 11. None is silently added to the Stage 1–5 scope.
- Existing verification: 17 foundation tests, BTP-local dependency audit, package consistency check, and real 100-molecule CPU sampling. These remain baseline evidence only.
