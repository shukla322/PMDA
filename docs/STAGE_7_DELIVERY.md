# Stage 6–7 MVP delivery — 28 October 2026

The four constrained local specialist roles and a full bounded EGFR campaign have now run using real local inference and REINVENT. This is the CPU research MVP delivery, not a declaration that every broader roadmap validation or deployment requirement is finished.

## Recorded result

Campaign: `runtime/egfr-campaign-20261028T051715Z/ee978718-7c9b-49ca-b98a-d5d2833e88f6`.

The controller reached **COMPLETED** after the final independently sampled portfolio met all frozen computational criteria. The campaign generated **112 rows** in three jobs: 48 initial samples, 32 RL trajectory samples over two steps, and 32 final samples. There were **111 valid structures** across the three sets; these counts are not counts of unique compounds. Final portfolio: **three candidates**, each passing the motif/property/alert/domain/uncertainty gates, novel relative to the training partition, lower predicted pIC50 >=6, and pairwise similarity <=0.85. These are research predictions, not experimentally validated leads.

| Stage | Result |
|---|---|
| Initial Mol2Mol sampling | 48 rows; no acceptable portfolio members |
| Bounded Mol2Mol RL | 32 trajectory rows; one portfolio-eligible candidate, not used to close the campaign |
| Independent checkpoint sampling | 32 rows; three portfolio members; criteria met |

The unequal, small sample counts do not establish RL effectiveness. No clinical, selectivity, synthesis or safety claims are made. The prior's training-set overlap and global/patent novelty are unassessed. See the campaign's `REPORT.md`, JSON/Parquet evidence and `docs/EGFR_MODEL_CARD.md` for intervals and limitations.

## Agents and controls

Planner, Formulator, Executor assistant and Analyser use the BTP-local Qwen2.5-1.5B GGUF model through the pinned llama.cpp CPU server. The successful standalone check is `runtime/live-agents-20261028T051632Z`. The campaign made 14 model attempts, with 12 accepted role responses and two rejected attempts retained. Early development failures are also retained separately; the model's limitations are not hidden.

Scientific explanations now come from reviewed, evidence-grounded choices. The controller validates decisions and supplies corrective route information on bounded retries. These are narrow advisory agents, not independently validated scientific reasoning systems. The Formulator selects a reviewed declarative recipe; it cannot execute generated Python. The Executor has no launch authority. Agents cannot approve their own proposals, change state or relax criteria.

The new reward bridge uses a hash-pinned qualified EGFR model and recipe. Frozen criteria, references and models are launch-manifest inputs. Controller approval checks also bind reward components, weights, model/recipe identity and generation seed. Research completion requires qualified evidence. These changes close the practical target-specific reward gap in the previous Stage 1–5 delivery.

## Validation performed

Ten focused checks passed in `runtime/stage67-checks-20261028T052002Z`: five new agent/reward checks and five controller regressions. Four live role calls then passed, and the real three-job campaign completed. This is not a new claim that the entire historical regression suite passed on current source. The previous 57-test acceptance report remains historical.

Approvals record the owner's delegated authorization for bounded free development, the actual local principal and artifact hashes. They are **not independent scientist/supervisor signoff**. The campaign did not require an API key or paid service.

## Handoff

- Read `docs/STAGES_6_7.md` for operating instructions, role restrictions and the fixed scientific policy.
- Read the campaign's `REPORT.md` for actual molecules and observed results.
- Run `scripts/report_campaign.py <run-directory>` to rebuild the human-readable report from preserved evidence.
- Run `scripts/run_egfr_campaign.py` from BTP for a fresh bounded demonstration after local runtime setup.

The next roadmap work is Stage 8: equal-budget baseline comparisons, multiple seeds, broader agent diagnostics and independent scientific review. Stage 9 is the web portal; Stage 10 is deployment hardening. Strategist and other original research extensions remain Phase 2.

CUDA, genuine machine-power-loss recovery, broad adversarial robustness, deployment-grade isolation/authentication and experimental validation remain unverified. Those items are not relabelled complete to satisfy a percentage target. CPU is the currently supported MVP execution mode.
