# EGFR campaign results

This report describes a bounded computational development demonstration, not drug discovery or experimental validation.

Controller state: **COMPLETED**. Frozen scientific criteria met: **True**.

## Fixed inputs

Lead SMILES: `CCOc1cc2ncnc(Nc3ccc(C)cc3)c2c2c1OCCO2`

Training-record pIC50: 8.4437. This is a curated public assay aggregate; it is not a measurement of any generated analogue.

Target: human wild-type EGFR. Predictor: EGFR-rf-v1. Dataset, model, recipe, seed and acceptance policy are recorded with hashes in the campaign inputs and approvals.

## Observed iterations

| Iteration | Mode | Rows | Portfolio size | Mean reward | Criteria met |
|---|---|---:|---:|---:|---|
| 0 | sampling | 48 | 0 | 0.0229 | False |
| 1 | staged_learning | 32 | 1 | 0.0966 | False |
| 2 | sampling | 32 | 3 | 0.2011 | True |

RL trajectory and independent samples are different populations with small, unequal sample counts. This table does not establish an optimization improvement or causal treatment effect.

## Rejection evidence

Iteration 0: 48/48 valid structures. Rejection reasons may overlap: molecular_weight_outside_policy=1, outside_predictor_domain=2, structural_alert_review_required=39.

Iteration 1: 32/32 valid structures. Rejection reasons may overlap: structural_alert_review_required=24.

Iteration 2: 31/32 valid structures. Rejection reasons may overlap: invalid_or_empty_smiles=1, logp_above_policy=1, outside_predictor_domain=1, structural_alert_review_required=11.

## Final independently sampled portfolio

| SMILES | Predicted pIC50 | Lower bound | Upper bound | Evidence |
|---|---:|---:|---:|---|
| `Clc1cccc(Nc2ncnc3cc(OC4CCOC4)c4c(c23)OCCO4)c1` | 7.815 | 6.417 | 9.214 | Computational, level 3 |
| `Fc1ccc(Nc2ncnc3cc(OC4CCOC4)c4c(c23)OCCO4)cc1Cl` | 7.588 | 6.190 | 8.987 | Computational, level 3 |
| `Clc1ccc(Nc2ncnc3cc(OC4CCOC4)c4c(c23)OCCO4)cc1Cl` | 7.470 | 6.071 | 8.868 | Computational, level 3 |

## Agent and approval evidence

Recorded 14 real local inference attempts, including 12 accepted role responses. Invalid responses remain in the record. Reviewed explanation choices and deterministic routing checks limit what these small-model agents can claim.

Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.

## Limits and next scientific work

- Predictions are not measured activity, selectivity, safety, efficacy or synthesis feasibility.
- Conformal intervals are broad and calibration coverage under generated-molecule distribution shift is unproven.
- Novelty is relative to the training partition only. Generator-training overlap, patents and global novelty were not assessed.
- PAINS/Brenk exclusions are conservative review rules, not toxicity determinations.
- A larger equal-budget multi-seed baseline comparison and independent medicinal-chemistry review are needed before interpreting effectiveness.
- Review failures and the original thresholds before approving any larger campaign; do not silently relax criteria.

## Reproduce or inspect

From BTP: `.venv\Scripts\python.exe scripts\run_egfr_campaign.py` starts a fresh bounded run. First install the local inference assets using `scripts/setup_agent_runtime.py`. See `docs/STAGES_6_7.md` for dependencies and scope.

Use `TASK_PLAN.md`, `iteration-comparison.json`, `inputs.json`, the SQLite event ledger, role context/response archives, job logs and evaluation JSON/Parquet for detailed evidence. This report does not overwrite those records.
