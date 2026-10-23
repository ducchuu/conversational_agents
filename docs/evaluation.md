# Evaluation and data quality

[Back to README](../README.md)

## Current evidence status

The available project descriptions report evaluation tooling and historical results, but do not supply a single consistent current release benchmark. This documentation intentionally does not select the most favorable result or silently resolve contradictory data counts.

| Item | Supplied information | Interpretation |
|---|---|---|
| Intent acceptance threshold | 0.85 | Configured minimum, not measured accuracy |
| Slot F1 acceptance threshold | 0.80 | Configured minimum; metric definition still needs publication |
| Intent accuracy | Approximately 93.7–94.9% across reported runs | Historical reports; identify the exact artifact and split before publishing a current value |
| Slot F1 | Approximately 0.87–0.89 across reported runs | Historical reports; averaging and token/entity scope need clarification |
| Local NLU inference | Approximately 6–8 ms reported | Not a verified end-to-end or percentile benchmark |
| Dataset total | 8,765 and 8,798 appear in earlier notes | Reconcile against the current files |
| Holdout total | 1,943 and 1,946 appear in earlier notes | Reconcile against the current files |
| Train/test overlap | Both zero leakage and 73 overlapping utterances are reported | Unresolved; do not claim a clean holdout until explained or corrected |
| Dialogue test count | 87 in the earlier README; 50+ in the branch comparison | Derive the current count from collection/results, including parametrization |

The branch comparison also describes experiment tracking in `experiments_history.json`, including commit and dataset hashes. Use those records as a starting point, then verify they correspond to the deployed model.

## Dataset assets

The documented NLU data location is:

```text
social-interaction-cloud/sic_framework/services/nlu/utils/data/
```

Documented split files include `train.json`, `exclusion_examples.json`, `test.json`, and `exclusion_examples_test.json`. The ontology defines canonical intents and slot types; synonym assets support normalization.

The earlier README describes 17 intents and 15 slot types, expanding to 31 BIO token labels. Confirm those counts from the current ontology before using them as release statistics.

## Audit workflow

```bash
python social-interaction-cloud/sic_framework/services/nlu/utils/dataset_audit.py \
  --max_conflicts 0 --max_leakage 0
```

The audit is described as using out-of-fold classification signals and TF-IDF similarity to identify suspicious labels and overlapping examples. Inspect the implementation and report to distinguish exact duplicates, similarity-based candidates, and confirmed annotation errors.

A passing automated audit means the implemented checks passed at their configured thresholds. It does not prove the absence of every form of leakage or label error.

### Resolve the conflicting overlap reports

1. Record the branch, commit, file hashes, and audit command.
2. Recompute split counts and both raw and normalized overlap.
3. Inspect reported overlaps and similarity candidates rather than treating every candidate as a confirmed error.
4. Remove unintended train/test duplicates or document intentional overlaps and their evaluation consequences.
5. Where related generated examples share a template or source, consider group-aware splitting to reduce overly similar examples across partitions.
6. Retrain or re-evaluate the matching artifact after changes; do not retain metrics from an older split without labeling them historical.

## Model evaluation

```bash
python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py \
  --eval_only --min_intent_acc 0.85 --min_slot_f1 0.80
```

Confirm the command loads the intended INT8 ONNX artifact and evaluates the intended files. The gate is only meaningful when those inputs are unambiguous.

A published result should include:

- Git commit, model SHA-256, dataset hashes, and ontology/vocabulary versions.
- Split sizes and the policy used to create the split.
- Intent accuracy and per-intent support; optionally macro F1 and a confusion matrix.
- Exact slot metric definition: token or entity span, averaging method, and treatment of `O`, padding, and subword labels.
- Whether the test exercises local BERT alone or the hybrid system including heuristics/LLM fallback.
- Evaluation command, dependency versions, execution date, and linked output.

Do not compare PyTorch and ONNX results as a quantization experiment unless they use equivalent inputs and scoring.

## Dialogue and application tests

The documented suite includes unit tests, dialogue-behavior tests, golden dialogue cases, and live Cloud Run smoke tests.

```bash
pytest social-interaction-cloud/tests/ --collect-only -q
pytest social-interaction-cloud/tests/ -ra
```

Report collected, passed, failed, and skipped tests separately. Parameterized cases, dialogue scenarios, and conversation turns are different counting units. State which one is being reported.

A golden suite establishes regression coverage for its selected cases. It does not establish conversational quality for arbitrary users. Live HTTP and WebSocket checks verify integration paths, not comprehensive security, load capacity, or multi-user isolation.

## Latency methodology

Measure separately:

- Cold landing-page availability.
- Cold inference readiness.
- Warm STT, NLU, dialogue, and server turn latency.
- Remote-fallback latency and frequency.
- Browser-observed time to first response and completion of speech.

Include hardware/Cloud Run resources, runtime thread settings, utterance/audio lengths, sample count, warmup policy, and p50/p95 where possible. A 6–8 ms NLU stage must not be presented as a 6–8 ms spoken interaction.

## Release evidence checklist

Before updating the README's results, attach or link one reproducible evaluation report, the relevant CI run, dataset audit output, model artifact identity, and any benchmark script. Keep historical runs in the experiment history rather than repeating changing metrics across documentation pages.
