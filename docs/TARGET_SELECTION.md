# First benchmark: human EGFR inhibition

Decision date: 27 October 2026. The project owner delegated dataset selection and requires free resources. Intended context: final-year BTech project at IIT Guwahati. This is a computational research benchmark; no clinical or experimental efficacy claim is implied.

## Selection and rationale

Use human epidermal growth factor receptor (EGFR), ChEMBL `CHEMBL203`, UniProt `P00533`. Start from ChEMBL binding-assay IC50 records and curate a compatible subset before fitting a pIC50 regressor. The official API verified the target as human and single-protein and returned 18,381 exact IC50/nM binding-assay records in an initial query. This is a raw activity count, not a count of unique eligible training molecules.

EGFR offers traceable experimental records and an established open educational reference: TeachOpenCADD uses this target for data acquisition and predictive modeling. This supports comparison and reproducibility, but makes ordinary EGFR prediction alone insufficient as the project's novel contribution. The contribution is a Solitarius-inspired, independently implemented agent with enforced approvals, traceable evidence, constrained optimization, recovery, and explicit uncertainty/domain qualification.

Compared with starting from a multi-target BindingDB collection, one ChEMBL target and endpoint keeps the initial scope tractable while retaining assay and publication provenance. A later second target would test transferability; it is not required to establish the first pipeline. This is a scope judgment, not a claim that EGFR is the best target for every drug-design task.

## Curation protocol to implement and evaluate

### Downloaded feasibility evidence

The complete bounded query snapshot is stored at `data/raw/egfr-20261027T134420Z/`, with ChEMBL_37 recorded before and after retrieval. `runtime/egfr-feasibility.json` records manifest verification and profiling: 18,381 activity records, 10,524 distinct molecule identifiers, 1,910 referenced assays and 1,022 documents. A broader target binding-assay metadata download contains 5,654 assays. Of the activity rows, 13,842 have confidence-9 assay assignments, 4,266 have an explicit variant field, and 17 lack SMILES. These counts overlap and must not be subtracted as independent exclusion groups.

Description heuristics identify 1,751 records covering 1,440 molecule identifiers mentioning wild type without a mutation-pattern match; 10,282 records have no construct designation recognized by that heuristic. These are review flags, not an approved wild-type dataset. The substantial variant/construct uncertainty is why fitting all downloaded IC50 records together would be scientifically misleading.

1. Preserve unmodified API responses, query URLs, retrieval dates, database release and SHA256 checksums inside BTP. Keep assay metadata as well as activities.
2. Require a direct single-protein assay assignment with confidence 9, binding assay type, compatible organism and endpoint, exact positive finite IC50 in nM, and valid molecular structure. Review data-validity and duplicate flags. Confidence 9 indicates confidence in target assignment; it does not guarantee measurement quality or prove a wild-type construct.
3. Separate explicit mutations and variants. A missing mutation field is not proof of wild type. Inspect descriptions and construct metadata; quarantine ambiguous mutant/cellular/phenotypic records. Do not silently combine wild-type, T790M, L858R or other variants into one claim.
4. Preserve assay/document grouping and original measurements. Define parent/salt, charge, tautomer and stereochemistry policies. Deduplicate before splitting. Quantify conflicting replicate measurements; aggregate only compatible evidence and retain disagreement.
5. Convert using `pIC50 = 9 - log10(IC50_nM)`. Do not mix Ki, Kd, EC50 or percentage inhibition into the same endpoint. Different assay conditions remain a limitation even after endpoint filtering.
6. Compare a trivial baseline, nearest-neighbor method and a CPU-friendly fingerprint model. Use held-out scaffold groups; retain a separate calibration partition. Where feasible, add document/time separation and nearest-neighbor overlap analysis. Scaffold splitting alone is not proof of independence.
7. Report MAE, RMSE, R-squared, rank correlation, sample/scaffold counts, uncertainty interval coverage and domain coverage. Fix model selection and qualification thresholds using training/validation data before examining the final test set. Do not repeatedly optimize against test results.
8. Compute similarity-based applicability domain against training molecules only; calibrate uncertainty without test leakage. Poor coverage or predictive performance must block use as an optimization reward rather than be hidden.

The dataset and predictor remain provisional until these checks succeed. If assay heterogeneity or insufficient curated data defeats validation, document the failure and revise the subset or target. Do not weaken the scientific checks merely to report Stage 5 complete.

## Evaluation of the agent's contribution

Compare fixed-budget unguided sampling, a fixed objective pipeline, and the full controlled loop using the same starting prior, seeds where supported, evaluator and candidate budget. Report validity, uniqueness, reference-relative novelty, diversity, property/alert compliance, in-domain qualified predictions, runtime and failure/recovery behavior. Separate predicted improvement from experimentally demonstrated activity. A holdout predictor and reward-hacking checks are desirable before strong optimization claims. Generation-prior training overlap may be unknown and must be acknowledged.

## Free-resource policy

Use the local CPU environment, public data, RDKit and existing local REINVENT assets. No paid cloud, paid LLM API or subscription is authorized. Free remote GPU availability is not assumed. Record compute time and resource limits. No API key is needed for the ChEMBL download or the Stage 1–5 deterministic foundation.

## Sources and attribution

- ChEMBL target API: https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL203.json
- ChEMBL activity API: https://www.ebi.ac.uk/chembl/api/data/activity.json
- ChEMBL API documentation: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
- Confidence and assay definitions: https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions
- TeachOpenCADD target acquisition: https://projects.volkamerlab.org/teachopencadd/talktorials/T001_query_chembl.html
- TeachOpenCADD predictive modeling example: https://projects.volkamerlab.org/teachopencadd/talktorials/T022_ligand_based_screening_neural_network.html
- ChEMBL licensing FAQ: https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/general-questions

Check the downloaded release's license before redistributing curated data; retain ChEMBL attribution. Database data, reference tutorials, third-party engine source and original PMDA source have distinct provenance. No tutorial implementation is being copied as original PMDA work.
