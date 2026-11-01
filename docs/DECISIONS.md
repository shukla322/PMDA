# Architecture decisions

## ADR-001: authoritative campaign state

SQLite transactions store states, events, approvals, and launch reservations. Markdown is a regenerable view. Local trusted operators are the current security boundary; an actor string is attribution, not authentication. A portal must add authenticated identity before multi-user use.

## ADR-002: existing environment is usable

On 2026-10-27 Python 3.12.3 and the existing Solitarius virtual environment ran successfully under current permissions. `pip check` passed. PyTorch 2.12.0+cpu reported CUDA unavailable. Prior claims of missing Python were based on restricted access and are superseded by these checks. Do not rebuild or delete working environments based on those claims.

The current development runtime is borrowed read-only from `../solitarius/.venv`; this is not a standalone locked deployment. A fresh BTP environment remains a release prerequisite.

## ADR-003: research gate status

Target/dataset/predictor selection remains unresolved. Generic infrastructure and descriptor evaluation can be implemented and tested independently, but no stage is claimed complete while its scientific prerequisites remain open. This is an explicit parallel-work exception to the roadmap's strict stage order.

## ADR-004: exact configuration execution

The public sampling MCP tool regenerates TOML when launched. Baseline tests compare parsed preview and executed configurations. Production launch will require an adapter that executes the exact approved bytes and verifies referenced input/model hashes. That production path is not enabled by the baseline script.

## ADR-005: no fabricated potency

All current molecule records mark activity unavailable. Predictor contracts and qualification logic can be tested with fixtures, but fixtures are not scientific models or scientific validation.
