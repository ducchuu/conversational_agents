# Development and model setup

[Documentation index](documentation.md) · [README](../README.md)

## Prerequisites

- Git and the repository's actual clone URL.
- Python 3.12; the reported verified environment uses 3.12.7.
- SWI-Prolog and FFmpeg.
- Compatible FP32 ONNX weights and bundled preprocessing assets.
- Provider credentials only for the remote capabilities you want to enable.

macOS/Homebrew:

```bash
brew install swi-prolog ffmpeg
```

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y swi-prolog ffmpeg python3-venv
```

Install an appropriate Python 3.12 interpreter separately if needed.

## Clone and install

Clone the `cloud` branch from GitHub:

```bash
git clone --branch cloud https://github.com/ducchuu/conversational_agents.git cookingbroski
cd cookingbroski
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "./social-interaction-cloud[webserver,nlu,dev]"
```

Windows PowerShell activation uses `.venv\Scripts\Activate.ps1`; the system-package commands above are not Windows instructions.

For a specific pinned release, check out tag `v1.0.0` instead of a moving branch.

The maintainer confirmed a functioning Python 3.12.7 environment, clean dependency installation, and complete test execution.

## Pretrained model download

Pretrained model weights (`bert_nlu.onnx`) and verification checksums are distributed via GitHub Release `v1.0.0` on `ducchuu/conversational_agents`.

Download the compatible release assets using the GitHub CLI:

```bash
mkdir -p social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints

gh release download v1.0.0 \
  --repo ducchuu/conversational_agents \
  --pattern bert_nlu.onnx \
  --pattern SHA256SUMS \
  --dir social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints
```

Alternatively, download `bert_nlu.onnx` directly from the release page at:
`https://github.com/ducchuu/conversational_agents/releases/tag/v1.0.0`

### Verify the model

From the repository root:

```bash
python - <<'PY'
import hashlib
from pathlib import Path
p = Path('social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints/bert_nlu.onnx')
expected = '7e77e9ef55c57af6cbf888f6ce26ed04e4c57e3f9edcc1b0dc6d57f94c11dee5'
actual = hashlib.sha256(p.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit(f'Checksum mismatch: {actual}')
print('Model checksum verified:', actual)
PY
```

This checksum applies to the documented artifact only; update it when intentionally publishing a different model. A correct checksum does not establish that the runtime selected that file. Check startup logs and evaluator output, especially if older INT8 artifacts remain present.

## Optional provider configuration

Use shell exports unless you have confirmed automatic `.env` loading:

```bash
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_MODEL="claude-haiku-5-5"
export YOUTUBE_API_KEY="your-key"
```

Optional remote speech fallbacks:

```bash
export ELEVENLABS_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

Optional Langfuse tracing:

```bash
export LANGFUSE_SECRET_KEY="your-secret"
export LANGFUSE_PUBLIC_KEY="your-public-key"
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

Never commit real credentials. Local BERT and local speech inference do not need remote inference keys, but credentials and provider access are required for the corresponding online features. Check startup behavior with omitted keys rather than assuming every optional-service combination has been tested.

Local speech recognition may download its model on first use if the host cache is empty. Container-preloaded weights do not automatically populate a local Python cache.

## Run

```bash
python social-interaction-cloud/sic_framework/services/webserver/webserver_pca.py
```

Open `http://localhost:8080`, allow microphone access, and wait for readiness.

- `/api/health`: liveness/health information.
- `/api/ready`: model readiness.
- `/api/metrics`: process-local telemetry.

## Tests and evaluation

```bash
python -m pytest social-interaction-cloud/tests/ -ra

python social-interaction-cloud/sic_framework/services/nlu/utils/dataset_audit.py \
  --max_conflicts 0 --max_leakage 0

python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py \
  --eval_only --min_intent_acc 0.85 --min_slot_f1 0.80
```

Live tests use `CLOUD_RUN_URL` and can be skipped when it is unset. See [evaluation](evaluation.md) for exact interpretation and backend-selection cautions.

## Optional training

Training is not needed when compatible release weights are available. Install the training/export dependencies defined by the current packaging/environment files, then run:

```bash
python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py
```

Training can create multiple artifacts. Explicitly verify which file the application and evaluator use; do not assume export order determines runtime selection.

## Troubleshooting

- Missing Prolog library: verify SWI-Prolog installation/discovery.
- Missing model: check download location, checksum, and selected backend.
- Page loads but speech fails: inspect readiness and warmup logs.
- Provider error: check account access/configuration without logging keys.
- Cross-session surprises: close other sessions; current server state is shared.
