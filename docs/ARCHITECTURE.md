# Local research backend architecture, contracts v1

## Boundaries

`Store` owns SQLite state, revisions, budgets, approvals and the append-only event ledger. `ExecutionService` reserves and reconciles jobs. A separate `pmda.worker` process owns the engine subprocess, timeout and cancellation. `engine_adapter` consumes MCP tool schemas and requests dry-run TOML; MCP does not own authoritative campaign state. `dataset`, `predictor`, `evaluation` and `Registry` provide deterministic scientific services. No LLM controls state transitions. LLM specialists are Stage 6 and the authenticated network portal is Stage 9.

Everything is rooted inside BTP. Inputs supplied to the engine must already be copied into their campaign, with absolute paths and size/SHA256 entries in `inputs.json`. Outputs are confined by validated configuration to that campaign's `outputs` directory. A generated subprocess command has a fixed executable and module and uses an argument array without a shell.

## Storage and migration

The authoritative database is `campaigns.sqlite3` in a caller-selected BTP runtime directory. Tables are campaigns, events, approvals and jobs. SQLite `BEGIN IMMEDIATE` serializes writes; expected revisions reject stale state transitions. Connections close after each transaction. `PRAGMA user_version` controls additive migrations through version 5. Unknown future versions fail closed. Legacy campaigns without an authenticated owner remain readable but cannot obtain new approvals. Migration hashes the pre-existing ledger as observed; it cannot retroactively authenticate historical records. New approvals record actor, acting scientist/operator role, request/decision times, decision, comments and reviewed hashes. Old approvals retain an explicit legacy-unrecorded role instead of fabricated attribution. One local owner may hold multiple roles; launch approval uses the operator role and scientific approvals use the scientist role.

Events include per-campaign previous/event SHA256 values. SQLite triggers reject event updates and deletes. `verify_history` detects alterations; this is tamper evidence against accidental or application-level modification, not protection from an OS administrator who can replace the entire database. Keep backups or externally anchored hashes for later deployment. Markdown is a generated view and can be deleted/rebuilt.

Campaign removal is archival of terminal records, preserving provenance. Hard deletion is not an MVP operation. Revision approval increments an iteration and requires fresh plan/score/launch approvals. Earlier iterations remain in history. Job and candidate reservations consume campaign budgets even if execution fails; ambiguous work is never retried automatically.

## State entry and exit conditions

| State | Entry / exit |
|---|---|
| DRAFT | Created by local principal; enter PLANNING or terminate |
| PLANNING | Construct typed plan; request plan approval |
| AWAITING_PLAN_APPROVAL | Owner approves exact Plan bytes/hash; research target must exist; enter FORMULATING |
| FORMULATING | Construct typed Score; request score approval |
| AWAITING_SCORE_APPROVAL | Owner approves Score; activity components require eligible registered predictor; enter CONFIGURING |
| CONFIGURING | Stage trusted inputs and complete TOML; request launch approval |
| AWAITING_LAUNCH_APPROVAL | Validate per-run engine schema, allowlist, paths, model/plan agreement and budget; bind config and input-manifest hashes; enter QUEUED |
| QUEUED | One atomic reservation rechecks all current approved artifacts, model/data checksums and cumulative budgets; enter RUNNING |
| RUNNING | Only supervisor/reconciliation controls exit; success enters EVALUATING, error/timeout FAILED, cancellation CANCELLED; ambiguity remains observable and blocks duplicate launch |
| EVALUATING | Build deterministic evidence; enter ANALYSING |
| ANALYSING | Complete only with typed evidence, matching analysis hash, successful job and verified result artifacts; otherwise request revision |
| AWAITING_REVISION_APPROVAL | Owner approves typed change rationale; increment iteration and return to PLANNING |
| COMPLETED / FAILED / CANCELLED | No further state transitions; may archive |

Non-running, nonterminal states permit owner-requested failure/cancellation. `request_revision` permits explicit invalidation and reapproval from nonterminal, non-running states. Owner identity is enforced at the CLI using the local OS account; internal Python services are trusted, not an authentication boundary against arbitrary code running as that same account.

## Scientific records

`schemas/v1/` contains 19 exported JSON schemas, generated from `pmda.schemas`. Unknown fields, invalid versions, non-finite numbers, invalid bounds and missing required relationships are rejected. JSON is the machine contract; no workflow parses prose. Major schema changes require a new version and explicit migration. Existing metadata versions are immutable: registration uses exclusive creation and reads recheck referenced artifacts.

The raw EGFR download is immutable evidence, not a training table. Curation emits per-activity decisions, molecule-level aggregated values, provenance, and a report. Split assignments are explicit and scaffold-disjoint. Training and calibration are separated from the test set. The random forest is exported as inert JSON tree arrays; inference does not unpickle arbitrary Python objects. The exported model's predictions are checked against scikit-learn before publication. Only successful report thresholds permit the registry's optimization lookup; campaign approval remains a separate decision.

Evaluator evidence distinguishes invalid structures, computed descriptors, configured gate checks and qualified predictions. PAINS/Brenk matches are review flags, not toxicity findings. Missing inference stays unavailable/error. JSON preserves the full evidence; Parquet contains versioned candidate rows, descriptors and alert fields. A hash manifest binds the export files.

## Supported execution scope

CPU sampling (Reinvent/Mol2Mol), bounded Reinvent transfer learning, and bounded QED-only reinforcement learning are supported by the strict execution allowlist. Arbitrary score plugins, remote responders, external config includes and generated executable code are rejected. This deliberately limits the current real engine integration; registry qualification of an EGFR predictor does not yet imply that it is wired into the engine's RL reward. Full target-specific optimization is a later integration requirement, not established by the QED smoke test.

The supervisor survives an initiating CLI exit. Result files are atomically published, include configuration identity and artifact hashes, and can be reconciled repeatedly without duplicate transitions. Missing supervisors produce `ambiguous`; missing or corrupt artifacts block acceptance. A host reboot or supervisor crash between external launch and process registration cannot be inferred as nonexecution. Do not automatically restart such work. Live supervised jobs support cancellation and elapsed-time enforcement. The owner can explicitly abandon an ambiguous job: the service verifies recorded PID/creation time and the exact job-specific command, also checks for a spawn-before-marker process by exact argv, stops matching processes, and records cancellation. It never interprets an abandoned job as scientific success or refunds its reserved budget. A simulated orphan process is exercised by the regression suite; real host power-loss testing remains a deployment-hardening exercise.
