# Local development and model setup

[Back to README](../README.md)

## Prerequisites

- A checkout of this repository's `cloud` branch.
- Python 3.12, matching the documented runtime environment.
- SWI-Prolog and FFmpeg on the host.
- Sufficient local memory for speech recognition, ONNX inference, and Prolog.
- Model artifacts, obtained through local training or an authorized artifact download.
- Provider credentials for any remote features you intend to exercise.

The branch notes mention a lower packaging minimum; this guide uses Python 3.12 to avoid implying that every supported package version has been tested.

### System packages

macOS with Homebrew:

```bash
brew install swi-prolog ffmpeg
```

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y swi-prolog ffmpeg python3-venv
```

Make sure your chosen Python interpreter is available separately. Package names and library discovery can vary by operating system. If `pyswip` cannot locate SWI-Prolog, verify the system installation and shared-library configuration before troubleshooting the application.

## Python environment

Run from the repository root:

```bash
git switch cloud
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "./social-interaction-cloud[webserver,nlu,dev]"
```

On Windows, activate the environment using `.venv\Scripts\Activate.ps1`; the system-package commands above are not Windows instructions.

The supplied installation extras are intended for application development and tests. Training may need additional dependencies; inspect `setup.py`, `pyproject.toml`, and the training imports before assuming the runtime environment includes PyTorch and export tools.

The supplied Conda alternative is:

```bash
conda env create -f environment.yaml
conda activate PCA26
```

Check the `name:` field in `environment.yaml` if the environment name has changed. Use one environment approach at a time.

## Credentials

Configure credentials only for services you intend to use. A complete remote-fallback setup can include:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export ANTHROPIC_MODEL="your-provider-supported-model-id"
export YOUTUBE_API_KEY="your-youtube-key"
export ELEVENLABS_API_KEY="your-elevenlabs-key"
export OPENAI_API_KEY="your-openai-key"
```

`ANTHROPIC_MODEL` must match both the application's configuration interface and a model available to your account. Earlier documentation gives a model identifier that has not been independently validated here; do not copy it blindly.

Optional Langfuse configuration:

```bash
export LANGFUSE_SECRET_KEY="your-secret-key"
export LANGFUSE_PUBLIC_KEY="your-public-key"
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

These shell exports avoid assuming that a `.env` file is loaded automatically. Use a `.env` file only after confirming the application loads it from the intended directory. Never commit populated credential files.

Local speech recognition and local NLU do not need remote inference keys. That does not mean every application path works without credentials: open-ended LLM responses, remote fallback, and video search require their respective services, and startup behavior should be tested with missing keys.

## Obtain NLU weights

The ONNX model is excluded from Git. Two workflows are documented.

### Option A: train and export locally

From the repository root, with training/export dependencies installed:

```bash
python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py
```

The documented output directory is:

```text
social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints/
```

The runtime expects the quantized model and its compatible vocabulary/ontology assets. Keep them version-aligned. Training is not necessary when compatible pretrained weights are available.

### Option B: authorized GCS download

The project documentation identifies the following model object. Access requires suitable Google Cloud credentials and bucket permissions; public access is not established by this guide.

```bash
mkdir -p social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints
gcloud storage cp \
  gs://cloud-agent-conversational-models/bert_nlu_int8.onnx \
  social-interaction-cloud/sic_framework/services/nlu/utils/checkpoints/bert_nlu_int8.onnx
```

If the object has moved to a commit-tagged naming scheme, use the artifact referenced by the intended release. Do not assume a mutable unversioned object reproduces an older benchmark.

Local Whisper may also need an initial model download unless its cache is already populated. The container build is described as preloading speech weights; that does not automatically populate a host Python environment.

## Start the application

From the repository root:

```bash
python social-interaction-cloud/sic_framework/services/webserver/webserver_pca.py
```

Open `http://localhost:8080` and allow microphone access. Wait for the inference-ready indicator before recording.

Documented endpoints:

- `/api/health`: liveness information.
- `/api/ready`: model-readiness information.
- `/api/metrics`: in-process telemetry summaries.

Confirm their current response schemas in the application code. A successful liveness response does not necessarily mean speech recognition is ready.

## Tests and evaluation

```bash
pytest social-interaction-cloud/tests/
```

Live deployment tests are environment-dependent and should not be confused with isolated unit tests. Check `tests/test_e2e_cloud_run.py` for required target configuration before running it; do not assume the ordinary suite tests a public deployment.

Dataset audit:

```bash
python social-interaction-cloud/sic_framework/services/nlu/utils/dataset_audit.py \
  --max_conflicts 0 --max_leakage 0
```

Model gate:

```bash
python social-interaction-cloud/sic_framework/services/nlu/train_and_export.py \
  --eval_only --min_intent_acc 0.85 --min_slot_f1 0.80
```

See [evaluation](evaluation.md) before interpreting the output or publishing results.

## Troubleshooting checklist

- Import error: confirm the active environment and editable installation.
- Prolog load error: verify SWI-Prolog discovery and the working directory expected by the code.
- Missing model: check artifact paths and access permissions.
- Landing page works but audio fails: inspect readiness and model-loading logs.
- Remote capability fails: verify the relevant provider configuration without logging secret values.
- Unexpected dialogue behavior: close other sessions; current shared state can interfere with independent conversations.
