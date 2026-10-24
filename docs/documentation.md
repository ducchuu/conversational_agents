# Documentation index

[Project README](../README.md)

## Choose a guide

| Goal | Guide |
|---|---|
| Understand the system | [Architecture](architecture.md) |
| Clone, install, download weights, run locally | [Development](development.md) |
| Understand results and reproduce checks | [Evaluation](evaluation.md) |
| Review audited evidence & test execution | [System Verification Report](system_verification_report.md) |
| Release assets and checksum manifest | [Release Manifest](release_manifest.md) |
| Operate the two deployments or prepare a release | [Deployment](deployment.md) |
| Understand boundaries and data handling | [Limitations](limitations.md) |

## Source of truth

Configuration files and code define implemented behavior. Evaluation reports describe results for a specific artifact and dataset. The README is an overview, not an alternative configuration inventory.

The current documentation snapshot uses the maintainer's verification summary supplied on 24 October 2026 and references source commit `79beb1bc5f04474120234cadd53c34e0a1f22d35`. The complete sanitized verification report is committed in the repository at [system_verification_report.md](system_verification_report.md) and attached to release `v1.0.0`.

The summary supersedes earlier INT8 metrics, 8,765/8,798-record counts, and 87-case golden-suite descriptions. Preserve earlier results only as clearly labeled history.

## Evidence to preserve with a release

- Source commit/release tag and working-tree status.
- Model identity and checksum.
- All dataset, ontology, and vocabulary hashes.
- Audit, evaluation, and test command outputs.
- Runtime versions and hardware/provider settings for performance claims.
- Deployment revision/image identity where exact live provenance is claimed.
- Licensing and redistribution notices.

Do not attach secrets, full environment-variable dumps, or sensitive trace payloads.

## Attribution and licensing

Academic context: Vrije Universiteit Amsterdam, Conversational Agents course; the maintainer identifies the original project as `VU-PCA-2026/agent-2026-am1`.

Original student contributors, as supplied by the maintainer:

- Mikołaj Duchliński (`ducchuu`)
- Fady Eshak (`fady-eshak`)
- Bennett Hampel (`bugheadwhat`)
- Abdelmatine Daddah (`Abdelmatine24`)
- Kabir D'Souza (`kabirds7`)
- Lazar Gyoshev (`lazargyoshev`)

The original course project included framework integration, MARBEL dialogue assets, initial NLU data, and Prolog recipe reasoning. The maintainer attributes the cloud-oriented extension described in the README to Mikołaj Duchliński. Contributor history supports attribution, not a legal ownership determination.

Use MARBEL as the original agent name. This documentation does not independently establish the interpreter/language taxonomy behind the legacy `.mas2g`/`.mod2g` files and does not label those formats as 2APL without further source evidence.

The independent cloud and MLOps extensions are licensed under the MIT License, while retaining third-party notices and attribution for original coursework assets, dependencies, and models in [LICENSE](../LICENSE).

## Documentation maintenance

- Keep current metric definitions and artifact identity in `evaluation.md`.
- Keep setup commands and asset selection in `development.md`.
- Keep delivery configuration and release procedure in `deployment.md`.
- Update README summaries when the underlying verified state changes.
- Keep current limitations visible even after successful test runs.

Repository clone URL is `https://github.com/ducchuu/conversational_agents.git` and the current production release tag is `v1.0.0`.
