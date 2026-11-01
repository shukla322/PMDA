# PMDA (B.Tech Deliverable)

Pharmaceutical Molecular Design Agent (PMDA) is a governed multi-agent framework for target-specific molecular candidate generation and computational evaluation.

This repository is a cleaned B.Tech submission package containing only the relevant PMDA project material from the original workspace.

## What This Project Is

PMDA combines:
- Role-separated agent planning/formulation/execution-analysis support.
- A deterministic controller for approvals, state transitions, and budget controls.
- Lead-oriented molecular generation workflow.
- Candidate evaluation with prediction, uncertainty intervals, applicability-domain checks, and policy gates.

The demonstrated campaign is for human wild-type EGFR and is reported as a computational prioritization workflow, not experimental validation.

## What Is Included (Curated)

- `src/pmda/`: core implementation.
- `scripts/`: reproducibility, campaign, and verification scripts.
- `schemas/v1/`: JSON schemas for controlled artifacts and agent proposals.
- `docs/`: architecture, API contract, model card, release and threat docs.
- `tests/`: regression and workflow tests.
- `registries/`: target/dataset/predictor/agent metadata.
- `data/curated/`: curated EGFR dataset artifacts (no raw-heavy dump).
- `report/BTP.pdf`: final B.Tech report.
- `report/figures/`: report figures.
- `results/`: clearly organized evidence area (inputs, outputs, evaluation, PNGs).

## Clear File Structure

```text
PMDA/
  src/pmda/                  # Project source code
  scripts/                   # Utility + pipeline scripts
  schemas/v1/                # Validation schemas
  tests/                     # Automated tests
  docs/                      # Technical and scientific documentation
  registries/                # Versioned metadata registries
  data/curated/              # Curated EGFR dataset outputs
  report/
    BTP.pdf                  # Main project report
    figures/                 # Figures used in report
  results/
    egfr_campaign/
      inputs/                # lead.smi, criteria.json
      outputs/               # iteration samples + execution summaries
      evaluation/iteration-2/# candidates.parquet + evaluation JSON
      final-portfolio.json
      TASK_PLAN.md
      REPORT.md
      summary.json
      status.json
    figures/                 # benchmark/intervals/portfolio/strata PNGs
    benchmark/results.json
    science/report.json
    portal_journey/result.json
```

## Results Area (Where To See Input/Output/PNGs)

Start here:
- `results/egfr_campaign/inputs/` for campaign inputs.
- `results/egfr_campaign/outputs/` for generated output tables and executed configs.
- `results/egfr_campaign/evaluation/iteration-2/` for final evaluated candidate table and metrics.
- `results/figures/` for PNG visual summaries used in reporting.
- `results/benchmark/results.json` for workflow comparison evidence.
- `results/science/report.json` for predictor/science summary.

## Report

Primary report PDF:
- `report/BTP.pdf`

## Quick Setup (Local)

Prerequisites:
- Windows
- Python 3.12+

Install package:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
pip install -e ".[chemistry,mcp,science,agents,portal]"
```

Run tests:

```powershell
python scripts/run_tests.py
```

Run CLI help:

```powershell
python -m pmda.cli --help
```

Run portal:

```powershell
python scripts/serve_portal.py
```

## Key Outcomes (As Reported)

- EGFR-focused governed campaign with bounded multi-stage execution.
- 112 generated rows evaluated across controlled jobs.
- 3 final computationally prioritized candidates after gates.
- Full chain of evidence preserved from objective to final portfolio.

## Scientific Boundaries

- Outputs are computational hypotheses, not experimentally validated drug candidates.
- No claims of clinical efficacy/safety.
- Applicability-domain and uncertainty constraints are explicitly used to avoid over-claiming.

## Future Scope

- Strategist role activation for adaptive exploration policy.
- Expanded evaluation: selectivity, ADMET, improved uncertainty ensembles.
- Stronger multi-seed and equal-budget benchmarking.
- Better deployment packaging (containerization, service split, ops hardening).
- Prospective synthesis and biological validation with experimental collaborators.

## Attribution

Conceptual orchestration inspiration and external tools/datasets are attributed in `docs/` and `report/BTP.pdf`.
Project-authored PMDA implementation remains independent in this repository.
