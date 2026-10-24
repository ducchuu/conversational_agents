# System Verification & Operational Healthcheck Report

**Target Commit SHA**: `79beb1bc5f04474120234cadd53c34e0a1f22d35`  
**Branch**: `cloud` (clean working tree, 0 uncommitted changes)  
**Date & Timestamp**: 2026-10-24 19:28 UTC+2  
**Active Python Runtime**: Python 3.12.7, Pip 26.2.2, Pytest 9.1.1 (`.venv`)  

---

## 1. Verified Environment & Dependencies

- **Interpreter**: Python 3.12.7 (macOS Darwin)
- **Virtual Environment**: `.venv`
- **Key Packages**:
  - `pytest`: 9.1.1
  - `onnxruntime`: Active INT8 & FP32 inference engines
  - `faster-whisper`: CTranslate2 INT8 CPU speech-to-text
  - `anthropic`: Messages API with prompt caching (`cache_control`)
  - `pyswip`: In-process SWI-Prolog bridge
  - `flask` & `python-socketio`: Real-time WebSocket event orchestration

---

## 2. Implementation & Git Integrity

- **Committed SHA**: `79beb1bc5f04474120234cadd53c34e0a1f22d35`
- **Working Tree**: Completely clean (`git status --short` returns empty).
- **Credentials & Artifacts**:
  - All `.env` files, API keys, and local secrets are excluded via `.gitignore`.
- **Knowledge Base Integrity**:
  - All 8 legacy SWI-Prolog rule and fact files in `social-interaction-cloud/dialog_mngr/*.pl` are retained and intact:
    - `recipe_database.pl` (895 structured recipe predicates)
    - `ingredient_hierarchies.pl` (ontology taxonomy)
    - `dialog.pl`, `dialogflow.pl`, `recipe_selection.pl`, `responses.pl`, `patterns.pl`, `utils.pl`

---

## 3. Dataset Audit & Data Quality Gate

Run command:
```bash
python social-interaction-cloud/sic_framework/services/nlu/utils/dataset_audit.py \
  --max_conflicts 0 \
  --max_leakage 0
```

### Results
- **Total Audited Records**: 9,008
- **Split Distribution**:
  - Train: 7,037 examples
  - Holdout Test: 1,971 examples
- **Quality Gates**:
  - **Near-duplicate label conflicts**: `0` (Gate: `<= 0` — **PASSED**)
  - **Train/Test exact leakage**: `0` (Gate: `<= 0` — **PASSED**)
- **Heuristic Review Candidates**: `846`
  - *Context*: These represent Cleanlab out-of-fold probabilistic label uncertainty candidates from cross-validation, not duplicate collisions. They are retained as naturally ambiguous human phrasing candidates rather than defects.

### Dataset File Checksums (SHA-256)
- `train.json`: `244a033700e8605f3742617f8fa0343e941f384de9bfdb8baadb830eba545200`
- `test.json`: `644b6ac0424bb2d3deb94d102c175003f6471f15bdb081b204d639d95ff8e3f9`
- `exclusion_examples.json`: `a23ad6e6c076a35754edb05fa7d67e4ef786faba87232e751cb3fd184d5f56cf`
- `exclusion_examples_test.json`: `662e879fa98ef31a908317dda29412d9456c992371629af864a8141ef6e9b490`
- `ontology.json`: `c9635c7bb9866c50d9659e47eaa358bbc2756a29b4145d8cfa8a48c3849d296b`
- `vocab.txt`: `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3`
- `synonyms.json`: `6e52334590889148192274ff2e6a8619efd065597b5bd409e3cfe46ad06304e6`

---

## 4. Fresh NLU Model Evaluation

Run command:
```bash
python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py \
  --eval_only \
  --min_intent_acc 0.85 \
  --min_slot_f1 0.80
```

### Results & Metrics
- **Model Checkpoint**: `social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints/bert_nlu.onnx`
- **Model Checkpoint SHA-256**: `7e77e9ef55c57af6cbf888f6ce26ed04e4c57e3f9edcc1b0dc6d57f94c11dee5`
- **Backend Architecture**: `onnx_fp32`
  *(Decision: FP32 model deployed to ensure cross-platform parity between ARM macOS and Linux container kernels, avoiding quantization drift)*
- **Evaluated Test Examples**: 1,971
- **Overall Intent Accuracy**: **94.98%** (Gate: `≥ 85.00%` — **PASSED**)
- **Weighted Slot F1**: **88.48%** (Gate: `≥ 80.00%` — **PASSED**)
  *(Metric definition: Support-weighted WordPiece-token slot-type F1, with BIO prefixes merged and 'O' excluded from averaged classes)*
- **Inference Throughput**: 34.2 samples/sec (~29.2 ms/sample on CPU)
- **Exit Code**: `0`
- **Experiment Log**: Recorded to `experiments_history.json`

---

## 5. Automated Test Suite Execution

Run command:
```bash
export CLOUD_RUN_URL="https://cookingbroski.mduchlinski.eu"
export READY_TIMEOUT_S=120
python -m pytest social-interaction-cloud/tests/ -ra
```

### Execution Summary
- **Total Tests Collected**: 138
- **Total Tests Passed**: **138** (100% pass rate in 16.61s)
- **Failures / Errors**: **0**
- **Skipped**: **0**

### Sub-Suite Breakdown
1. **Golden Utterance Evaluations** (`test_golden_dialogues.py`):
   - **110 single-turn utterance tests passed** across all 17 intents and complex multi-slot configurations (addFilter, clearFilters, cookingQuestion, recipeRequest, disconfirmation, etc.).
2. **Dialogue Behaviors & State Management** (`test_dialog_behaviors.py`):
   - **7 passed** (Clear filters, undo last filter, ordinal candidate selection, quickest recipe pick, recipe rejection tracking).
3. **Services & Pipelines** (`test_google_services.py`, `test_openai_services.py`):
   - **6 passed** (STT/TTS initialization, subword slot alignment, FastBERTNLU initialization and normalization).
4. **Web Orchestrator & Telemetry** (`test_webserver.py`):
   - **12 passed** (Dynamic HTML routes, health/readiness probes, telemetry ONNX accounting, Prolog context hydration, Claude clause streaming).
5. **Live Deployment E2E** (`test_e2e_cloud_run.py`):
   - **3 passed** (Live probes, HTTP assets, WebSocket connection).

---

## 6. Claude API Integration & Fallback Resilience

- **Primary Model**: `claude-haiku-5-5` (configured via `ANTHROPIC_MODEL`).
- **Direct Ping**: Direct API call verified responsive (`Pong! How can I help you today?`).
- **Structured LLM NLU**:
  - Utterance: `"I want an Italian pasta with mushrooms"`
  - Predicted intent: `addFilter`
  - Normalized slots: `{'cuisine': 'italian', 'tag': 'pasta', 'ingredient': 'mushroom'}`
  - Schema: Strict Pydantic model validation (`NLUOutput`).
- **Conversational Response Generation**:
  - Dynamic agent speech grounded in current `DialogState` and Prolog context.
- **Circuit Breaker & Fallback**:
  - Missing API key or provider failure immediately falls back to deterministic Prolog canned templates and regex-based keyword intent classification (`infer_fallback_intent`) without hanging or throwing unhandled exceptions.

---

## 7. Cloud Run & Cloudflare Tunnel Live Deployments

### A. Primary Cloud Run Service
- **URL**: `https://social-agent-cloud-511906064574.us-central1.run.app`
- **Liveness & Readiness**:
  - `/api/health` -> `{"models_ready": true, "service": "social-agent-cloud", "status": "ok"}`
  - `/api/ready` -> `{"models_ready": true, "status": "ready"}`
- **Container Build**: Triggered via Cloud Build from commit `79beb1b`.

### B. Stable Cloudflare Tunnel Endpoint
- **Public Domain**: `https://cookingbroski.mduchlinski.eu`
- **Edge Routing**:
  - Network: Cloudflare Global Anycast Edge (AMS PoP)
  - Protocol: `HTTP/2 200 OK` (HTTPS TLS terminated at edge, routed via `cloudflared` tunnel)
  - Headers: `server: cloudflare`, `cf-cache-status: DYNAMIC`
- **API Health Probes**:
  - `GET /api/health` -> `200 OK` (`models_ready: true`)
  - `GET /api/ready` -> `200 OK` (`models_ready: true`)
- **E2E Live Verification**:
  - Pytest E2E suite executed directly against `https://cookingbroski.mduchlinski.eu`: **3 passed in 2.22s**.
  - **WebSocket / Socket.IO**: Clean handshake and bidirectional channel established over WSS.
  - **Manual UI / Audio Verification**: Completed in browser:
    1. Utterance recording via `MediaRecorder` WebM upload.
    2. Real-time STT transcription & NLU slot filtering.
    3. Live recipe grid updates and Prolog constraint queries.
    4. Text-to-speech feedback via `window.speechSynthesis`.

---

## 8. Licensing & Attribution Boundary

- **Framework Baseline**: Inherited multi-modal conversational framework from course baseline (`VU-PCA-2026/agent-2026-am1`).
- **Independent Cloud & MLOps Extensions**:
  - DistilBERT ONNX FP32 intent/slot pipeline & training export.
  - In-process Prolog integration via `pyswip`.
  - Cloud Run containerization and Cloudflare Tunnel integration.
  - Automated CI/CD quality gates (audit, evaluation, E2E live tests).
  - Claude Haiku streaming & LLMOps caching fallback.
- **Statement**: README retains a strict, narrow boundary distinguishing original framework materials from cloud extensions.

