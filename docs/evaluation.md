# Evaluation and verification

[Documentation index](documentation.md) · [README](../README.md)

## Evidence scope

This snapshot transcribes the maintainer's verification summary supplied on 24 October 2026. The documentation author did not independently run the repository, inspect the full local report, or reproduce the live checks. Preserve actual command output and machine-readable experiment records alongside the release where possible.

The referenced source version is `2a706d891d5dea630d495c77a73245dd9c102520`, branch `cloud`, reported with a clean working tree. Later documentation commits do not automatically invalidate these results, but code/data/model changes require a new evaluation.

## Runtime

| Tool | Reported version |
|---|---|
| Python | 3.12.7 |
| pip | 26.2.2 |
| pytest | 9.1.1 |

Execution hardware, ONNX Runtime version, thread settings, and provider configuration should be included in release evidence before publishing comparative latency or throughput claims.

## Dataset

| Partition | Examples |
|---|---:|
| Combined training | 7,037 |
| Combined evaluation | 1,971 |
| Total | 9,008 |

The training and evaluation paths combine the base and exclusion-example files. These counts supersede earlier 8,765/8,798-example documentation; do not mix metrics from different revisions.

Reported SHA-256 values:

```text
train.json
244a033700e8605f3742617f8fa0343e941f384de9bfdb8baadb830eba545200

test.json
644b6ac0424bb2d3deb94d102c175003f6471f15bdb081b204d639d95ff8e3f9

exclusion_examples.json
a23ad6e6c076a35754edb05fa7d67e4ef786faba87232e751cb3fd184d5f56cf

exclusion_examples_test.json
662e879fa98ef31a908317dda29412d9456c992371629af864a8141ef6e9b490

ontology.json
c9635c7bb9866c50d9659e47eaa358bbc2756a29b4145d8cfa8a48c3849d296b

vocab.txt
07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3

synonyms.json
6e52334590889148192274ff2e6a8619efd065597b5bd409e3cfe46ad06304e6
```

All hashes are recorded in the [release manifest](release_manifest.md) and [SHA256SUMS](SHA256SUMS).

## Dataset audit

```bash
python social-interaction-cloud/sic_framework/services/nlu/utils/dataset_audit.py \
  --max_conflicts 0 --max_leakage 0
```

Reported result: 9,008 audited records, zero detected cross-intent near-duplicate conflicts, and zero normalized train/test text overlaps. The maintainer resolved two overlapping contrastive examples before verification.

The audit also flagged 846 heuristic label review candidates using Cleanlab out-of-fold probabilistic predictions. These represent natural conversational phrasing ambiguity flagged for review rather than duplicate conflicts. See [system verification report](system_verification_report.md) for full audit output.

## Model artifact and results

```text
Backend: onnx_fp32
File: bert_nlu.onnx
SHA-256:
7e77e9ef55c57af6cbf888f6ce26ed04e4c57e3f9edcc1b0dc6d57f94c11dee5
```

| Metric | Reported result | Configured minimum |
|---|---:|---:|
| Intent accuracy | 94.98% | 85.00% |
| Weighted slot-type F1 | 88.48% | 80.00% |

Evaluation scope: standalone local BERT on 1,971 holdout examples, not the end-to-end hybrid system.

Slot metric: support-weighted WordPiece-token slot-type F1. BIO prefixes are merged, `O` is excluded from the averaged class list, and padding/special-token labels are ignored. This does not measure entity-span or BIO-boundary correctness. Errors between `O` and selected slot classes can still affect their precision/recall.

To reproduce the documented gate:

```bash
python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py \
  --eval_only --min_intent_acc 0.85 --min_slot_f1 0.80
```

Before interpreting the result, verify that the evaluator selects FP32 `bert_nlu.onnx`. Do not leave an older INT8 checkpoint where automatic artifact-selection logic could prefer it. Keep the runtime and evaluation artifact-selection settings aligned; the current summary does not provide an explicit backend-selection CLI flag.

## Automated tests

Reported result: 138 passed in 16.61 seconds.

| Category | Cases |
|---|---:|
| Single-turn golden utterances | 110 |
| Dialogue behavior/state rollback | 7 |
| Service initialization/subword alignment | 6 |
| Webserver/telemetry/Prolog hydration | 12 |
| Live deployment E2E | 3 |
| Total | 138 |

The golden cases are single-turn utterance evaluations, not 110 multi-turn sessions. Passing tests cover their selected scenarios, not arbitrary conversations, security, or load capacity.

```bash
python -m pytest social-interaction-cloud/tests/ --collect-only -q
python -m pytest social-interaction-cloud/tests/ -ra
```

Live target configuration:

```bash
export CLOUD_RUN_URL="https://cookingbroski.mduchlinski.eu"
export READY_TIMEOUT_S=120
python -m pytest social-interaction-cloud/tests/test_e2e_cloud_run.py -ra
```

The summary reports three live tests passed against that tunnel URL in 2.22 seconds. That suite duration is not per-turn response latency.

## Integration and live checks

The maintainer reports:

- Direct access to configured `claude-haiku-5-5`, structured extraction, and conversational response generation.
- A provider-unavailable test using rule/template fallback without a hang or crash.
- Successful health and readiness probes on both hosting endpoints.
- WSS Socket.IO event transmission and manual microphone/filter/TTS interaction.

Reported healthy responses:

```json
{"models_ready": true, "service": "social-agent-cloud", "status": "ok"}
```

```json
{"models_ready": true, "status": "ready"}
```

A point-in-time health check does not establish continuous availability. The supplied summary does not identify the Cloud Run image digest or independent deployed-model hash; record them in release evidence if exact deployment provenance is claimed.

## Performance reporting

No standardized current per-turn latency benchmark is included. Avoid carrying forward 6–8 ms INT8 timing as an FP32 result or calling the home-server service universally instantaneous.

For future benchmarks, record cold page availability, model readiness, warm STT/NLU/dialogue timing, fallback rate, and browser-observed response latency separately. Include hardware, sample count, audio duration, runtime versions, and p50/p95.
