# Deployment and operations

[Back to README](../README.md)

## Deployment definition

The project describes two delivery paths:

- [GitHub Actions](../.github/workflows/deploy.yml): developer-facing checks and deployment for the `cloud` branch.
- [Cloud Build](../social-interaction-cloud/cloudbuild.yaml): GCP-native image build and deployment workflow.

The [Dockerfile](../social-interaction-cloud/Dockerfile) defines the runtime image. Inspect these files for the current triggers, exact commands, permissions, and gate ordering. The pipelines should not be assumed to provide identical checks merely because they target the same service.

This is an operational overview, not a standalone infrastructure provisioning script. Project setup, IAM bindings, buckets, secrets, registry repositories, and billing must exist before a first deployment.

## Runtime image

The branch notes describe a Python 3.12 slim image with SWI-Prolog, FFmpeg, ONNX Runtime, and CTranslate2-based speech inference. Speech model weights are preloaded during the container build, and Python bytecode is compiled ahead of startup.

Training-only libraries are intended to be excluded from the runtime image. Verify the built dependency inventory rather than inferring the final image contents from a source requirements file alone. Development/training environments can legitimately have additional dependencies.

## Model artifacts

Weights are excluded from Git and retrieved from Google Cloud Storage during delivery. Earlier notes describe an unversioned `bert_nlu_int8.onnx`; the newer branch comparison describes commit-tagged artifacts and a mutable latest pointer.

For reproducibility:

1. Pin deployment to an identified model object/version.
2. Record the artifact checksum with the application commit and dataset hashes.
3. Evaluate that exact artifact before release.
4. Keep vocabulary and ontology assets compatible with it.
5. Retain the model artifact needed to reproduce or roll back a release.

A mutable latest pointer is convenient for discovery but is not a reproducible release identity. Verify the current upload/retrieval logic in the workflows before relying on commit-tagged storage.

## Quality gates

The GitHub workflow is described as including:

1. Dataset audit for configured conflict/leakage thresholds.
2. Holdout model evaluation against configured intent/slot minimums.
3. Unit and golden dialogue regression tests.
4. Post-deployment live HTTP/Socket.IO checks.

The last gate occurs after a revision has been deployed. A failing post-deployment check does not itself prove that traffic is rolled back automatically. Confirm rollback behavior or implement a tested response procedure.

See [evaluation](evaluation.md) for unresolved dataset evidence and the distinction between configured thresholds and measured performance.

## Cloud Run settings

The supplied documentation describes:

```text
--memory=4Gi
--cpu=4
--min-instances=0
--max-instances=1
--timeout=3600
--cpu-boost
--no-cpu-throttling
```

| Setting | Intent and caveat |
|---|---|
| 4 vCPUs / 4 GiB | Resource budget for local speech, NLU, and Prolog; verify memory and latency under actual load |
| Minimum instances 0 | Permits scale-to-zero; does not guarantee a zero monthly bill |
| Maximum instances 1 | Caps instance count; does not isolate concurrent user conversations |
| Timeout 3600 | Extends the request/connection window; clients still need reconnect handling |
| Startup CPU boost | Provides additional startup resources; measure readiness rather than assuming a fixed speedup |
| No CPU throttling | Supports background work; verify the selected billing behavior and cost implications |

Billing can include active instances, startup activity, storage, logging, network usage, and provider APIs. Local inference avoids an external per-request inference fee; compute is not universally free.

## Startup and readiness

Heavy models warm in a background thread so the web interface can bind its port before initialization completes. Keep these states separate:

- Process listening.
- Liveness endpoint responding.
- Landing page usable.
- Speech and NLU engines ready.

The documented `/api/ready` endpoint should control readiness messaging in the browser. Port binding alone is not evidence that the assistant can process audio.

The browser also includes an inactivity disconnect mechanism, described as seven minutes in the earlier README. This helps close idle sessions; actual scale-down and billing behavior must be verified in the deployed service.

## Authentication and secrets

GitHub Actions is described as using Workload Identity Federation rather than a stored service-account key. Scope trust to the intended repository/ref and grant the deployment identity only the permissions the workflow needs. Verify the actual IAM configuration separately from the YAML.

Cloud deployment is described as using Google Secret Manager for provider and observability credentials. Check secret bindings and service-account access in the deployed revision; never publish credential values in documentation, screenshots, or logs.

## Observability

- `/api/health`: liveness.
- `/api/ready`: model initialization state.
- `/api/metrics`: process-local summaries.
- Structured `TELEMETRY_LOG` events: stage timing and engine selection.
- Optional Langfuse traces: LLM behavior and usage.

In-memory counters reset on restart. External log/trace retention depends on configuration; neither service should be described as permanent storage without a defined retention policy. Review request content capture and access controls before enabling traces for public use.

## Image cleanup and rollback

The supplied workflows retain the three newest image digests and delete older images. Check that any cleanup operation preserves artifacts required by active revisions and the intended rollback window.

Before relying on rollback:

1. Identify a known-good application revision and its model/configuration.
2. Confirm required images and model objects are still available.
3. Rehearse traffic reassignment and smoke-test the result.
4. Record the recovery procedure and limitations.

Retaining three images is a storage policy, not proof of immediate or zero-downtime recovery.
