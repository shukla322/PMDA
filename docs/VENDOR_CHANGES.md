# Local adaptations to copied upstream source

On 28 October 2026, BTP added `vendor/REINVENT4/reinvent_plugins/components/comp_pmda_activity.py`. This is a BTP-authored registration shim for the independently implemented `pmda.reward` module, not upstream REINVENT science code. It exposes one hash-pinned EGFR model/recipe endpoint. PMDA's config and approval checks reject other custom code, unmanifested inputs and score-contract mismatches. The original upstream license and source provenance remain intact.

Upstream origin/commit records remain in `references/sources.json`. These directories are copied source with licenses, not original PMDA implementations.

The imported MCP source already included the Windows sampling change preserved in `references/windows-sampling.patch` and a compatibility adjustment omitting the removed REINVENT `unique_sequences` RL parameter from emitted TOML.

On 27 October 2026, BTP additionally changed `vendor/solitarius-mcp/config_builders/tl_config.py` and `rl_config.py` to serialize filesystem strings with JSON-compatible double-quoted escapes instead of directly interpolating Windows backslashes into TOML. The concrete failure was `TOMLDecodeError: Invalid hex value` for a path beginning `C:\Users`. File paths remain the same; emitted TOML now round-trips them correctly. No engine logic or scientific scoring model was changed by this fix.

PMDA's adapter always requests dry_run and disables upstream launch. Its own allowlist and the installed engine's run-specific schema validate the resulting complete configuration before approval and launch. Future changes to vendored files should be documented here and their hashes captured by the dependency audit.
