# Backend interface draft v1

Transport is currently a local CLI/Python API. A future HTTP layer must authenticate actors before calling trusted services; it must not accept an arbitrary actor string as proof of identity.

| Operation | Request | Response / invariant |
|---|---|---|
| create | nonempty description | campaign UUID, DRAFT, current OS account owner |
| show | campaign UUID | `Campaign` schema via `Store.snapshot` |
| list | optional archive inclusion in Python | storage snapshots; CLI list is a local administrative view |
| transition | campaign, State, expected revision | compare-and-set transition; protected transitions rejected |
| approve | campaign, artifact relative path, SHA256, actor | approval ID; actor must match principal and campaign owner |
| revise | campaign, reason | AWAITING_REVISION_APPROVAL; typed Revision approval then starts a new iteration |
| launch | campaign, approval ID | job ID and supervisor PID; input/config checks and reservation happen before process creation |
| job / recover | job UUID | durable job state and result; idempotent reconciliation, no automatic relaunch |
| cancel | job UUID | cancellation request plus reconciled status; request is not falsely reported as completed cancellation |
| abandon | ambiguous job UUID | owner-authorized process-identity reconciliation and cancellation; no success inference or automatic retry |
| history / audit | campaign UUID | ordered events / validated chain head |
| ledger | campaign UUID | regenerated TASK_PLAN.md path |
| archive | terminal campaign UUID | retained campaign with archived flag |

`ExecutionService`, `Registry`, `evaluate_registered`, `export_evaluation`, `engine_adapter.discover` and `engine_adapter.propose` are the Python integration boundaries. Callers must not directly mutate SQLite or treat Markdown as input state.

Errors at the CLI are JSON with status, error_code and message and a nonzero exit status. Codes include POLICY_VIOLATION, INVALID_INPUT and MISSING_ARTIFACT. Durable execution errors include SPAWN_FAILED, ENGINE_EXIT, SUPERVISOR_ERROR, MISSING_OUTPUTS, OWNER_CANCELLED, WALL_TIME_BUDGET and SUPERVISOR_MISSING. Engine stdout/stderr are data in `engine.log`, never instructions.

Use `python -m pmda.cli --help` for exact arguments. JSON schema examples and compatibility tests are in `tests/test_contracts_data.py`; the original development database rows are internal storage records, not the future portal wire format.
