# Release Manifest: CookingBroski v1.0.0

**Release Tag**: `v1.0.0`  
**Target Source Commit**: `2a706d891d5dea630d495c77a73245dd9c102520`  
**Repository**: `ducchuu/conversational_agents`  
**Release Date**: October 2026  
**Evaluated Backend**: FP32 ONNX (`bert_nlu.onnx`)  

---

## 1. Verified Model Artifacts

| Asset | Path | Format | SHA-256 Checksum |
|---|---|---|---|
| `bert_nlu.onnx` | `social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints/bert_nlu.onnx` | ONNX FP32 | `7e77e9ef55c57af6cbf888f6ce26ed04e4c57e3f9edcc1b0dc6d57f94c11dee5` |

---

## 2. Dataset & Preprocessing Checksums

| Asset | Path | Size | SHA-256 Checksum |
|---|---|---|---|
| `train.json` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/train.json` | 927 KB | `244a033700e8605f3742617f8fa0343e941f384de9bfdb8baadb830eba545200` |
| `test.json` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/test.json` | 242 KB | `644b6ac0424bb2d3deb94d102c175003f6471f15bdb081b204d639d95ff8e3f9` |
| `exclusion_examples.json` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/exclusion_examples.json` | 283 KB | `a23ad6e6c076a35754edb05fa7d67e4ef786faba87232e751cb3fd184d5f56cf` |
| `exclusion_examples_test.json` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/exclusion_examples_test.json` | 84 KB | `662e879fa98ef31a908317dda29412d9456c992371629af864a8141ef6e9b490` |
| `ontology.json` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/ontology.json` | 347 KB | `c9635c7bb9866c50d9659e47eaa358bbc2756a29b4145d8cfa8a48c3849d296b` |
| `vocab.txt` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/vocab.txt` | 226 KB | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` |
| `synonyms.json` | `social-interaction-cloud/sic_framework/services/nlu/utils/data/synonyms.json` | 9.2 KB | `6e52334590889148192274ff2e6a8619efd065597b5bd409e3cfe46ad06304e6` |

---

## 3. Evaluation & Quality Gate Summary

- **Dataset Audit**: 9,008 samples (7,037 train, 1,971 test)
  - Train/test leakage: **0**
  - Near-duplicate label conflicts: **0**
  - Heuristic review candidates: **846**
- **Holdout Test Set Performance** (1,971 samples):
  - **Intent Accuracy**: **94.98%** (CI gate `≥ 85.00%`)
  - **Weighted Slot F1**: **88.48%** (CI gate `≥ 80.00%`, support-weighted WordPiece-token F1)
  - **Throughput**: ~34.2 samples/sec on CPU
- **Test Suite Pass Rate**: **138 of 138 passed (100%)**
  - 110 single-turn golden utterance cases
  - 7 dialogue behavior / state tests
  - 18 service, webserver, telemetry tests
  - 3 live deployment E2E tests