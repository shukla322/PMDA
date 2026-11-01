# Stages 6 and 7: local specialist agents and EGFR campaign

This implementation reconstructs the Solitarius-inspired roles independently. It does not claim to reproduce unavailable original prompts or orchestration code. The controller remains authoritative. Strategist, VECTOR+ and autonomous research-policy changes remain Phase 2.

## Scope and operating model

The Planner proposes against supplied target and predictor identifiers and asks for missing information. The Formulator selects the reviewed conservative activity recipe. The Executor assistant proposes a preview or hold; it cannot launch a process. The Analyser explains a route checked against typed execution, qualification, portfolio and budget evidence. Each role uses a real local Qwen2.5-1.5B-Instruct Q4_K_M call through llama.cpp, with temperature zero, a seed, a JSON schema, at most 384 output tokens and two attempts. These are narrow advisory roles, not autonomous medicinal chemists or unrestricted coding agents.

Only the deterministic controller records approvals, reserves budgets and starts REINVENT. Agents have no executable tools. Adding actions requires reviewed application code. A role sees only its allowlisted fields, not the whole filesystem, previous conversation, raw logs or credentials. Every call archives the prompt, input, schema, provider identity, response, latency, token usage and validation outcome. A rejected response holds the workflow rather than silently substituting a fabricated model answer. Prompt injection cannot grant a tool capability that the adapter does not possess; comprehensive adversarial evaluation remains Stage 8.

## Free local inference

Runtime: llama.cpp b11669, official Windows CPU archive. Model: official Qwen GGUF repository revision `91cad51170dc346986eccefdc2dd33a9da36ead9`. Downloads, licenses, checksums and source URLs are under `models/agents` and `vendor/llama.cpp`. No API key or paid service is required. CPU inference listens on loopback for the duration of a run and is stopped afterwards. Python/Windows remain system prerequisites; project files and inference weights stay in BTP.

From BTP, use PowerShell:

```powershell
.venv\Scripts\python.exe scripts\setup_agent_runtime.py
.venv\Scripts\python.exe scripts\export_agent_contracts.py
.venv\Scripts\python.exe scripts\check_live_agents.py
.venv\Scripts\python.exe scripts\run_egfr_campaign.py
```

The setup command needs internet access once. Runtime calls are local. Restricted environments may require approval for child processes or loopback communication. No global Python or Ollama installation is modified. Generation is seeded but cross-platform bitwise reproducibility is not promised.

## Scientific campaign

The target and predictor are the registered human wild-type EGFR records. The training partition is reconstructed from the frozen curated dataset and scaffold-split algorithm. Lead selection never uses calibration or test endpoint labels: measured training pIC50 at least 7, a quinazoline motif, molecular weight at most 500 and all reward gates, ranked by QED with a deterministic tie break. This is a defensible demonstration selection rule, not evidence that the chosen lead is clinically suitable.

The fixed recipe requires the quinazoline motif, MW <=500, logP <=5, no configured PAINS/Brenk alerts, model-domain qualification and interval half-width <=1.5 pIC50. Alerts are conservative review exclusions in this campaign, not proof of toxicity. Reward is clipped `(predicted lower pIC50 - 5) / 3`. Invalid, unqualified and rejected structures receive zero reward with reasons retained. Prediction errors are explicitly labelled. Model and recipe hashes are bound to approved launch inputs. REINVENT discovers a small BTP-authored `PMDAActivity` shim; the scientific code is in `src/pmda/reward.py`. Model-generated Python, external-process scorers and arbitrary transforms remain prohibited.

Portfolio acceptance is fixed before sampling: at least three candidates with predicted lower pIC50 >=6, absent from the training-reference structures, passing the recipe, with pairwise Morgan Tanimoto similarity <=0.85. This checks training-set novelty only; it does not establish novelty against patents, all ChEMBL, other public datasets or undisclosed generator training data.

The initial Mol2Mol job samples 48 analogues. If the portfolio fails the frozen criteria, one approved revision permits two RL steps of 16 candidates each. A second revision samples 32 candidates independently from the resulting checkpoint. Total budget: three jobs, 112 generated candidates, 600 seconds per job and at most two adaptive revisions. RL trajectories cannot themselves close the campaign. The recipe and acceptance thresholds are never relaxed to manufacture success. A run may legitimately stop without finding an acceptable portfolio. A small successful run does not demonstrate that RL improves potency or outperforms a baseline; equal-budget, multiple-seed comparisons belong to Stage 8.

## Authorization and evidence

The current owner authorized free, bounded development through Stage 7. Automated plan, score, revision and launch records explicitly identify that delegated scope and the local principal. They are not independent scientist or supervisor signoff. An agent cannot create its own approval. Real experimental work or broader autonomous campaigns require separate scope and scientific review.

Each run creates a fresh `runtime/egfr-campaign-<UTC timestamp>` folder, an SQLite controller record, immutable job configurations, input hashes, role-call archives, per-iteration evaluations and Parquet evidence, candidate portfolios, a comparison table and a final ledger. A failed model call or engine run preserves its evidence. There is no automatic retry of an ambiguous engine job. Use existing CLI recovery/cancellation commands after inspecting the recorded job, rather than rerunning it under the same approval. Repeating the campaign command creates a new, separately budgeted demonstration.

## Validation boundary

Live development checks found that the small model could invent treatment-related explanations and misroute budget exhaustion. Those responses were retained, the prompts were clarified, and explanations were restricted to reviewed statements with semantic matching to controller evidence. A bounded retry may include the controller's required route and grounded rationale. These agents provide constrained workflow assistance; this is not evidence of independent scientific reasoning or broad agent reliability.

`test_agents_reward.py` contains five focused checks. Provider fixtures are explicitly labelled as fixtures; they are not evidence of real LLM performance. `check_live_agents.py` records four live calls. Actual campaign evidence must be read from a completed run, not inferred from code or from the previous Stage 1–5 report. The old acceptance report predates these changes and must not be presented as current-source validation.

CPU remains the supported MVP configuration. CUDA performance, real power-loss recovery, comprehensive security testing, independent scientific review, multi-seed effectiveness, prospective laboratory validation, portal authentication and deployment isolation are not claimed here. They do not become completed merely because a local demonstration works.

## Primary references

- [llama.cpp server interface](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
- [Official Qwen model and license](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)
- BTP `references/sources.json`, `PRD.md`, `DEVELOPMENT_ROADMAP.md` and `docs/EGFR_MODEL_CARD.md` retain the project and scientific provenance.
