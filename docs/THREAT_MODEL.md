# Local MVP threat model

Assets: approval provenance, campaign state, molecular data, model weights, reproducible scientific outputs, local compute/storage. Trust boundary: the local OS account and installed BTP package are trusted; dataset strings, model metadata, tool replies, logs and future agent proposals are untrusted data.

| Threat | Current control | Residual / later requirement |
|---|---|---|
| Prose or agent bypasses approval | Typed artifacts, owner check, revision and hash verification, one launch reservation | A malicious OS owner can edit Python/SQLite; network authentication belongs to portal work |
| Changed objective/model/config | Recheck current approved artifacts, config/manifest hashes and input files before launch | OS-level adversarial races are not an isolation guarantee; deploy with restricted service account/container |
| Path traversal or shell injection | UUID validation, resolved containment, strict config allowlist, fixed argv, no shell | Filesystem reparse-point replacement by trusted OS owner is out of scope |
| Generated/plugin code execution | Custom plugins, responders and external scoring includes rejected by execution adapter | Third-party engine and public model loaders remain trusted dependencies; no arbitrary uploads |
| Duplicate launch after crash | Atomic reservation, supervisor claim, conservative ambiguous state, no automatic retry | Host-level crash between spawn and PID record needs operator reconciliation |
| Runaway compute | CPU-only, epoch/step/candidate/job limits, timeout and cancellation | No kernel-enforced RAM/disk quota; current smoke workload only |
| Tampered audit history | Hash chain and append-only SQL triggers | No external signing or immutable backup; same OS account can replace database |
| Dataset leakage and overclaiming | Scaffold splits, source IDs, calibration/test separation, overlap report, explicit qualification | Shared publications and unknown generator training overlap remain limitations |
| Model deserialization | Predictor uses JSON arrays, NPZ never loads pickle | REINVENT priors still require trusted upstream source plus checksum; checksum alone does not prove safety |
| Secret exposure | No keys needed, ignored .env, redacted pattern scan, no copied external chat.py | Pattern scan is bounded; historical VECTOR credential status remains unverified |

Network inventory: ChEMBL public HTTPS target/activity/assay/status endpoints for dataset acquisition; Zenodo public HTTPS model metadata/weights; no network needed for normal local execution or bundle recreation. MCP uses local stdio. No paid API, cloud job or telemetry endpoint is configured by PMDA. Vendored examples are reference material, not authorization to execute them.
