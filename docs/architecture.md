# Architecture and design decisions

[Back to README](../README.md)

## Scope

CookingBroski combines statistical language understanding with deterministic dialogue and recipe filtering. The Python dialogue manager owns conversational flow; Prolog evaluates recipe constraints; the local NLU model predicts intent and slots. An optional LLM handles selected ambiguous requests and open-ended cooking responses.

This document describes the cloud extension from the supplied project notes. Exact routing conditions and runtime settings should be checked against the linked implementation when changing behavior.

## Request lifecycle

1. The browser captures an utterance through `MediaRecorder`. The completed WebM recording is sent over Socket.IO. This is utterance-level upload, not continuous audio streaming.
2. `stt_service.py` attempts local transcription with `faster-whisper`. The documented configuration uses `base.en` with CTranslate2 INT8 CPU inference. On local processing errors, configured ElevenLabs or OpenAI services can provide fallback transcription.
3. `fast_bert_nlu.py` performs intent classification and BIO slot tagging with the quantized ONNX model. Slot normalization maps predictions into the application's domain vocabulary.
4. `llm_nlu_service.py` coordinates additional heuristics and optional Claude extraction. Structured validation checks response shape; it does not establish that the interpretation is semantically correct. The precise ordering of heuristics and remote calls is implementation-dependent and should remain documented alongside the code.
5. `dialog_manager.py` dispatches the interpreted request, updates dialogue state, and invokes recipe filtering where needed.
6. `prolog_interface.py` uses `pyswip` to query the existing Prolog rules and facts in-process.
7. The server emits response text and UI events. The browser updates recipe views and uses `window.speechSynthesis` for spoken output. A watchdog releases the interaction if a speech callback fails.
8. Telemetry records server-side processing stages. Optional Langfuse integration traces LLM operations.

## Main implementation locations

Paths below are relative to the repository root.

| Component | Location |
|---|---|
| Dialogue routing | `social-interaction-cloud/dialog_mngr/agent_python/dialog_manager.py` |
| Dialogue state | `social-interaction-cloud/dialog_mngr/agent_python/state.py` |
| Prolog bridge | `social-interaction-cloud/dialog_mngr/agent_python/prolog_interface.py` |
| Local NLU | `social-interaction-cloud/sic_framework/services/nlu/fast_bert_nlu.py` |
| Training/export | `social-interaction-cloud/sic_framework/services/nlu/train_and_export.py` |
| Dataset audit | `social-interaction-cloud/sic_framework/services/nlu/utils/dataset_audit.py` |
| Web orchestration | `social-interaction-cloud/sic_framework/services/webserver/webserver_pca.py` |
| Browser interaction | `social-interaction-cloud/sic_framework/services/webserver/static/` |

## Dialogue state

The cloud extension describes accumulated positive and negative filters, filter history for undo, and rejected-recipe tracking. These features support refinement across turns rather than treating each request as an isolated recipe search.

Browser `sessionStorage` can preserve UI information across page transitions. It does not establish independent server-side sessions or durable conversation storage.

The current server-side design includes shared in-process state and mutable Prolog predicates. One Cloud Run instance is not equivalent to one user, and an instance cap does not solve cross-user state interference. See [limitations](limitations.md).

## Why retain Prolog?

Keeping the existing knowledge base avoids rewriting the recipe rules while making constraint filtering explicit. The extension replaces the legacy bridge with direct Python integration rather than replacing every part of the original application.

The documented database contains 895 recipes. Other ontology counts may differ because the NLU vocabulary and the recipe fact store are different assets; they should not be treated as interchangeable counts.

## Why local quantized NLU plus a remote fallback?

The local model supports a bounded cooking-domain schema without requiring a remote request for every interpretation. Quantization reduces the deployed artifact size and allows CPU inference. The LLM broadens support for open-ended language at the cost of external dependencies, variable latency, and provider charges.

Local NLU timing is not end-to-end conversation timing. Transcription, filtering, fallback calls, transport, and browser speech each contribute separately.

## Supporting services

- YouTube search supplies recipe-video suggestions and uses an in-memory LRU cache. Older notes disagree on cache size; inspect `youtube_service.py` for the current value.
- Telemetry exposes in-process summaries and emits structured logs. Browser speech duration should not be inferred from server processing time unless instrumented explicitly.
- Model warmup runs in the background. Port binding, landing-page availability, and inference readiness are separate milestones.

## State-isolation direction

Before supporting concurrent users, move conversation data into explicitly session-scoped storage and make Prolog filtering operate on request-specific arguments rather than shared mutable facts. Introduce appropriate locking or engine isolation where required, test simultaneous conversations, and only then consider horizontal scaling. A Redis message broker or session affinity alone does not make shared application state safe.
