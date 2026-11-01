# EGFR-rf-v1: research baseline model card

## Intended use

Rank or inspect compounds resembling this curated training distribution, with pIC50 intervals and domain flags. This is an assay-aggregated research model, not a claim of efficacy, selectivity, safety, noncovalent binding, clinical benefit or prospective experimental validation. Its registry eligibility means it passed the declared internal research gates, not that a scientist has approved a real campaign or that it is integrated into the REINVENT RL reward.

## Data

Source: ChEMBL_37, human EGFR CHEMBL203/P00533. The raw snapshot has 18,381 exact IC50/nM binding records. Curation retains explicit wild-type assay descriptions, direct confidence-9 target assignment and single-protein assay format, and excludes explicit variants, ambiguous construct descriptions, flagged duplicates/validity issues, salts/mixtures and incompatible endpoints. Nine molecules with greater than one log-unit measurement spread were quarantined. Result: 777 standardized molecules, 354 scaffold categories.

Functional-group cleanup and canonical tautomer selection use RDKit 2026.03.3 defaults. Charges are retained. Tautomerization can remove tautomer-dependent stereochemistry, and enumeration uses RDKit's default limits; several raw structures reached those limits during curation. This is a documented limitation requiring review before stereochemistry-sensitive optimization. Ordinary stereoisomers, invalid inputs and salts are covered by tests, but those tests are not a proof that all chemical representations are equivalent. Cross-assay medians remain approximations because ATP concentration, construct boundaries and experimental conditions vary. Explicit description-based WT selection does not replace source-publication review.

## Training and validation

Model: 200-tree random forest, Morgan radius-2 / 2048-bit fingerprints, minimum leaf 2, max_features 0.5, seed 42. Fixed hash-ranked scaffold groups split into train/calibration/test; actual rows: 518 / 88 / 171. No hyperparameter tuning against the test set. Mean predictor and nearest-training-neighbor baselines use the same split. A separate calibration set supplies 90% split-conformal absolute-residual intervals. Similarity domain threshold is derived from training leave-one-out neighbors, floored at 0.35.

| Held-out metric | Forest | Mean baseline | Nearest neighbor |
|---|---:|---:|---:|
| MAE (pIC50) | 0.5573 | 1.0301 | 0.7618 |
| RMSE (pIC50) | 0.7647 | 1.2849 | 1.1061 |
| R-squared | 0.6432 | -0.0074 | 0.2535 |
| Spearman | 0.8294 | undefined | 0.6698 |

Interval half-width: 1.3983 pIC50; observed held-out coverage: 93.57% for nominal 90%. Tanimoto domain threshold: 0.5604; 79.53% of test molecules are in-domain. In-domain MAE: 0.4547. These are broad intervals: a one-unit pIC50 difference corresponds to a tenfold concentration ratio. Do not equate a small predicted improvement with a reliable potency gain.

Qualification thresholds were encoded before fitting: at least 100/30/30 train/calibration/test rows; MAE below 1.0 and below the mean baseline; R-squared above zero; interval coverage at least 0.80; domain coverage at least 0.50; full interval width at most 3.0. The model passed. Repeated training reproduced the inert JSON model exactly and metrics within 1e-10 (`runtime/science-reproduction-20261027T142920Z/reproduction.json`).

## Important limits

- 38 publications overlap train/test despite scaffold disjointness. Scaffold split is not a document or time split. Do not describe these results as an independent external benchmark.
- The test partition has 89 measurements with pIC50 >= 7 and only five with pIC50 <= 5. Group ordering is a small sanity check, not proof of reliable inactive-class recognition. No classifier or calibrated probability of activity is supplied.
- Split-conformal exchangeability is not assured under scaffold shift; reported coverage is empirical. The domain rule is a similarity heuristic, not a physical guarantee.
- The model is trained on exact measurements. Censored weak activities were excluded rather than treated as exact labels; selection bias is possible.
- A single target and seed are sufficient for initial implementation verification, not final dissertation claims. Later benchmarking needs multiple seeds, more stringent split sensitivity and matched-budget ablations.
- Generator pretraining overlap is unknown. Novelty means novelty against a named reference set, not global chemical novelty or patentability.

## Artifacts

`data/curated/egfr-20261027T135452Z/` contains curated rows, per-source-row decisions and curation report. `models/egfr-20261027T135452Z/` contains model.json, fixed split assignments, report and fingerprints. `registries/` holds immutable target/dataset/predictor metadata with artifact hashes. `runtime/registered-egfr-evaluation/` demonstrates JSON and Parquet evidence. Model inference uses JSON tree arrays, avoiding arbitrary pickle execution.
