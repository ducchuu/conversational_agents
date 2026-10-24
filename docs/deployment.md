# Deployment and operations

[Documentation index](documentation.md) · [README](../README.md)

## Two separate hosting paths

| Endpoint | Application host | Public access |
|---|---|---|
| `https://cookingbroski.mduchlinski.eu/` | Home server | Cloudflare Tunnel |
| `https://social-agent-cloud-511906064574.us-central1.run.app/` | Google Cloud Run, `us-central1` | Cloud Run HTTPS endpoint |

The recommended demonstration endpoint is the warm home-server application. The maintainer reports more responsive interaction there. The Cloud Run demo remains useful as evidence of cloud delivery and scale-to-zero operation.

Do not describe the home-server URL as tunneling to Cloud Run. Do not attribute all response delay to a cheap region: startup, network round trips, resources, inference, and provider calls are separate factors requiring measurement.

## Cloud delivery definitions

- [GitHub Actions](../.github/workflows/deploy.yml)
- [Cloud Build](../social-interaction-cloud/cloudbuild.yaml)
- [Dockerfile](../social-interaction-cloud/Dockerfile)

These files are the authority for triggers, IAM, checks, build steps, and resource flags. Do not assume both delivery paths enforce identical gates.

The documented workflow includes dataset checks, holdout model thresholds, application regression tests, container publication/deployment, and post-deployment smoke checks. A post-deployment failure does not imply automatic rollback unless implemented and tested.

## FP32 release alignment

Current verified results use `bert_nlu.onnx`, not the old INT8 artifact. Audit every artifact consumer when preparing the release:

- Local inference path and automatic selection logic.
- Model evaluation selection.
- Docker COPY/download instructions.
- GCS upload and retrieval paths, if retained.
- GitHub Actions caches and cache keys.
- Cloud Build artifact retrieval.
- Release download instructions and hashes.

The summary reports FP32 deployed but does not provide all these configuration values. Confirm that an older INT8 cache or GCS object cannot silently override the intended model. A public GitHub Release is a distribution path; it need not replace private CI artifact storage, but both must reference the same intended model identity.

## Resource settings and startup

Earlier configuration describes 4 vCPUs, 4 GiB, minimum instances 0, maximum instances 1, startup CPU boost, no CPU throttling, and a 3600-second timeout. Confirm actual settings in the deployment definitions and service revision before treating them as a current configuration inventory.

Scale-to-zero permits idle shutdown; it is not a zero-cost guarantee. Persistent connections, compute, builds, storage, logs, and provider requests can contribute costs.

Background warmup lets the server bind before models are ready. Separate liveness from readiness; the UI should wait for `/api/ready` rather than treating page availability as inference readiness.

The instance cap does not isolate users. Maintain the single-conversation demo constraint until state isolation is implemented.

## Secrets and authentication

The project describes Workload Identity Federation for GitHub-to-GCP authentication and Secret Manager for cloud credentials. Review actual trust bindings, service-account permissions, and secret references. Never include populated `.env` files, keys, or sensitive traces in release assets.

For the home server, use the deployment's existing secret-management approach. This document does not invent a tunnel configuration, process supervisor, or host provisioning command that has not been supplied.

## Health and observability

The maintainer reports successful health/readiness probes for both endpoints, WSS event transmission, and manual browser microphone/filter/TTS checks. See [evaluation](evaluation.md) for evidence scope.

Use structured telemetry to distinguish STT, NLU, dialogue, and fallback costs. Process-local metrics/cache contents reset on restart. External log and Langfuse retention depend on configuration; do not call them permanent archives without a policy.

## Release publication checklist

1. Finalize documentation with actual public repository (`https://github.com/ducchuu/conversational_agents`) and release tag (`v1.0.0`).
2. Confirm redistribution rights and attribution notices in [LICENSE](../LICENSE).
3. Verify FP32 selection in local, CI, container, and deployed paths (`bert_nlu.onnx`).
4. Commit documentation and generate tag `v1.0.0` targeting commit `79beb1bc5f04474120234cadd53c34e0a1f22d35` (or the documentation tag commit).
5. Attach the compatible `bert_nlu.onnx` and [SHA256SUMS](SHA256SUMS).
6. Include the [release manifest](release_manifest.md) containing source SHA, model hash, dataset/ontology/vocab hashes, runtime versions, and evaluation gates.
7. Attach the sanitized [system verification report](system_verification_report.md).
8. Completed fresh walkthrough verification of model download, checksums, application startup, and live dialogue interaction.
9. Verify live revision and model readiness on Cloud Run (`https://social-agent-cloud-511906064574.us-central1.run.app`) and Cloudflare Tunnel (`https://cookingbroski.mduchlinski.eu/`).
10. Publish release `v1.0.0` via `gh release create v1.0.0`.

See [release manifest](release_manifest.md) for full commands and asset listing.

## Recovery

Retain compatible application images, model artifacts, and configuration for rollback. An image-pruning policy alone is not a rollback test. Document and rehearse the actual recovery process before claiming automatic or zero-downtime recovery.
