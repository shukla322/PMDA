# Local research release — 29 October 2026

## Release scope

This is the Stage 9 portal plus the **local portion of Stage 10**, intended for running and demonstrating PMDA on the existing Windows computer. It is not a public production deployment or a completed clinical/scientific validation. Start with `QUICKSTART.md` and `START_PORTAL.cmd` in BTP.

The UI includes a project overview, interactive role explanations, actual agent context/response inspection, step-by-step review guidance, authenticated campaign creation, separate plan/score/launch approvals, live status/logs, candidate filtering/pagination, RDKit structure rendering, a descriptor-space plot, scaffold counts, final-portfolio cards and artifact exports. The reference campaign is read-only. Every model statement remains labelled as computational evidence.

## Local architecture and boundaries

- FastAPI versioned REST API with generated OpenAPI, static HTML/CSS/JavaScript, and server-sent state events.
- SQLite for users, sessions, project-scoped permissions, operation status and access events. Campaign state and immutable approval evidence remain in the existing controller databases.
- Passwords use salted PBKDF2; sessions use random tokens stored as hashes, HttpOnly/SameSite cookies, expiry and CSRF checks. Initial credentials are written only to the local ignored access file. HTTP is supported only on loopback; HTTPS and Secure cookies are required before remote deployment.
- Viewer, scientist, operator and administrator roles. API authorization is enforced independently of UI buttons. The local execution principal owns the filesystem campaigns; portal user identity is recorded in access events and approval comments. This is a shared-project local service, not isolated operating-system accounts.
- Single background preparation queue. Restarted preparation is marked interrupted; explicit resume preserves failed evidence. Existing engine workers retain the established timeout/cancellation/reconciliation behavior. No automatic engine relaunch.
- Uploads and arbitrary generated scoring code are not enabled. Downloads are authenticated, campaign-contained and limited to enumerated artifacts.

## Evidence

- Current full regression: **69 passed, zero failures/errors/skips**, recorded in `runtime/verification/tests.json` on 29 October. The test log includes intentional invalid-SMILES fixtures.
- Seven portal boundary tests cover authentication, CSRF, role enforcement, project isolation, approval bypass, download traversal and filtering/pagination of 10,000 synthetic rows.
- Real HTTP workflow: `runtime/portal-journey-20261029T042822Z/result.json`. A four-candidate campaign traversed all three approval gates, ran local agents and REINVENT, evaluated all rows and exported the report and SVG. The pipeline verification passed; the small campaign's scientific criteria did not. No browser-test pass is inferred from this API evidence.
- Live agent diagnostics: `runtime/agent-diagnostics-20261029T042616Z/results.json`. Seven cases passed the final validator; **two passed on their first attempt and five needed a retry with controller guidance**. This is narrow diagnostic evidence, not broad independent agent reasoning.
- Scientific strata: `runtime/science-stage8-20261029T042609Z/report.json`. Held-out MAE 0.5573 overall, 0.4547 in-domain and 0.9561 out-of-domain. Five weak-activity examples had MAE 2.1756 and zero empirical interval coverage. Negative discrimination is not adequately established.
- Comparative pilot: `runtime/benchmark-stage8-20261028T052759Z`. Ten runs, 480 generated rows, five approaches and two seeds. Candidate ceilings were equal; training compute was not. Full-agent and fixed-workflow molecular outputs matched in these runs. Adaptive superiority is **not established**.

The browser connector became unavailable while verifying the new presentation views. Earlier sign-in/wizard checks do not constitute verification of the redesigned UI. JavaScript syntax and API behavior can be verified independently, but final visual/accessibility and complete browser-journey signoff remain open until browser access is restored.

## Backup, restore and rollback

Stop the portal and resolve active or ambiguous jobs first. Then:

```powershell
.venv\Scripts\python.exe scripts\backup_portal.py backup runtime\portal
```

The archive includes the portal's hashed accounts and complete workspace campaign inputs/artifacts. It excludes the plaintext initial-access file. Preserve that file privately if needed. Reference campaigns and shared generator/LLM assets are outside this archive; retain BTP's models, vendor source, environment and provenance files separately.

`scripts/restore_drill.py` preserves the current portal directory under a timestamped name, restores a verified archive to the original absolute location, invalidates sessions, checks SQLite integrity and verifies campaign audit-chain heads. It never automatically launches jobs. The original remains available for rollback. A restore to a different path is an inspection copy because approved artifacts contain absolute paths.

The actual drill passed on 29 October: `runtime/backups/20261029T043400Z/restore-drill.json`. One workspace campaign's chain was verified, sessions were invalidated and zero jobs were launched. The pre-restore directory remains preserved as `runtime/portal-before-restore-20261029T043400Z`.

For manual rollback, stop the portal and all relevant work, preserve the current directory under a new BTP/runtime name, and restore the known-good directory to its original path. Never overwrite a running database or silently rewrite approved paths/hashes.

## Dependencies and portability

Everything project-specific stays inside BTP: source, references, datasets, generator/LLM weights, local runtime and generated artifacts. System Windows, Python and optional Node for development are prerequisites. FastAPI was added to BTP's environment for this release. The older Stage 1–5 offline package snapshot predates that addition; do not claim it alone recreates the portal. `pyproject.toml` declares the portal extras, and the release package list records the installed versions.

## Remaining production gates

Public network deployment, TLS termination, hardened containers, separate web/worker services, GPU scheduling, storage quotas, load/soak testing, external penetration review, independent medicinal-chemistry review, prospective assays and a larger powered benchmark remain unverified. The permitted release decision is **local research demonstration**, not production or autonomous drug-selection deployment.
