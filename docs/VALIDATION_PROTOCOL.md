# Validation Protocol

This document explains what can be verified from this repository, how to run those checks, and what the checks do not establish.

## Scope

The project separates three kinds of evidence:

1. **Deterministic safety checks**: Python validation for protected terms, numeric and unit preservation, and meta-commentary leakage.
2. **Workflow behavior**: unit tests for state transitions, rollback, retry limits, run logging, resource handling, and UI behavior.
3. **Experiment artifacts**: versioned result files under `reports/` and run records produced at runtime under `runs/` (the latter are intentionally git-ignored).

Passing one category must not be presented as proof of another. In particular, a successful test suite does not demonstrate translation quality, and an experiment artifact does not replace human approval.

## Reproduce the repository checks

```bash
python -m venv .venv
source .venv/bin/activate
pip install langchain-core langchain-ollama langchain-openai pydantic gradio pandas pytest
pytest -q tests
```

The test suite covers the agent decision logic, workflow state handling, deterministic validation, translation-memory and resource handling, run logging, result-CSV handling, data-selection utilities, and the UI.

A test-only run should not require an OpenAI API key. The application falls back to its configured mock behavior when an optional escalation key is absent.

## Inspect a run

Run the UI or CLI as described in the repository README. For each execution, inspect:

- the input request and model settings;
- the initial translation and its MQM evaluation;
- every revision attempt, including acceptance or rollback;
- deterministic validation failures;
- unresolved errors and terminal status;
- the human approval or rejection decision.

A run is only complete for delivery after a person explicitly approves it. `AWAITING_HUMAN_APPROVAL` and `HUMAN_REVIEW_REQUIRED` are intentionally non-final delivery states.

## Inspect experiment artifacts

The `reports/` directory stores committed experiment outputs. When comparing results, record the exact report filename, dataset split or sample definition, model configuration, and comparison baseline.

Do not generalize a result beyond its recorded dataset, language direction, model configuration, and evaluation method. The repository does not claim production-scale throughput, human-quality equivalence, or universal translation improvement.

## Change checklist

Before merging a change that affects prompts, routing, validation, or model configuration:

- [ ] Run `pytest -q tests`.
- [ ] Check at least one successful path and one human-review or rollback path.
- [ ] Confirm protected terms, numbers, and units are not silently changed.
- [ ] Keep the relevant run record or experiment output outside confidential sources.
- [ ] Update the README or architecture document when observable behavior changes.

## Evidence boundaries

This repository is an independent personal project. It uses public data and does not contain prior employer or customer data, prompts, source code, evaluation outputs, or internal documentation. See the README's provenance notice for the full boundary statement.