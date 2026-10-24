# Architecture

[Documentation index](documentation.md) · [README](../README.md)

## Scope

CookingBroski combines local language models, deterministic dialogue control, and symbolic recipe filtering. Claude broadens selected interpretations and responses; it does not replace the dialogue state machine or Prolog knowledge base.

## Request lifecycle

1. The browser records a complete utterance with `MediaRecorder` and sends audio through Socket.IO.
2. `stt_service.py` attempts local `faster-whisper` transcription. Configured ElevenLabs/OpenAI services provide error-triggered fallback paths.
3. `fast_bert_nlu.py` executes the local ONNX model for intent and slot predictions.
4. `llm_nlu_service.py` applies routing/heuristics and optional Claude extraction. Pydantic validates structure, not semantic correctness.
5. The Python dialogue manager updates constraints, rejection history, and dialogue state.
6. `prolog_interface.py` queries SWI-Prolog for recipe filtering and metadata.
7. The server emits response text and UI events. The browser displays recipes and invokes `window.speechSynthesis`.
8. Telemetry records server-stage timings; optional Langfuse integration traces LLM calls.

Off-script cooking requests can use Claude response generation. The maintainer reports a tested provider-unavailable path that falls back to rules and Prolog templates without hanging or crashing. This establishes the tested failure behavior, not equivalence to all online capabilities.

## Main components

| Component | Location relative to `social-interaction-cloud/` |
|---|---|
| Dialogue routing | `dialog_mngr/agent_python/dialog_manager.py` |
| State/history | `dialog_mngr/agent_python/state.py` |
| Prolog bridge | `dialog_mngr/agent_python/prolog_interface.py` |
| NLU runtime | `sic_framework/services/nlu/fast_bert_nlu.py` |
| Training/export | `sic_framework/services/nlu/train_and_export.py` |
| Dataset audit | `sic_framework/services/nlu/utils/dataset_audit.py` |
| Shared tokenizer | `sic_framework/services/nlu/utils/tokenization.py` |
| Web orchestration | `sic_framework/services/webserver/webserver_pca.py` |

## Current model backend

The current reported evaluation and deployment use FP32 `bert_nlu.onnx`. Earlier revisions used dynamically quantized INT8 ONNX. The maintainer selected FP32 after encountering cross-architecture INT8 behavior differences between ARM macOS development and Linux x86 hosting.

This is a project-specific consistency decision. FP32 alone does not guarantee bitwise-identical output across processors, execution providers, or runtime versions. Preserve runtime settings and test representative predictions on each target platform before making stronger reproducibility claims.

The shared tokenizer wraps the Rust-backed `tokenizers` package and loads bundled `vocab.txt`. Sharing the implementation reduces preprocessing differences; vocabulary, normalization, truncation, and label alignment must also remain compatible.

## Dialogue and Prolog state

The original recipe assets include eight Prolog files and 895 recipes, reported intact in the latest verification. Dialogue refinement supports multiple filters, exclusions, rejection tracking, and undo.

The server currently shares in-process dialogue and mutable Prolog state. Browser `sessionStorage` helps UI continuity, not server-side user isolation. Restrict demo use to one active conversation; an instance cap does not enforce that restriction.

For multi-user support, introduce explicit per-session state and request-specific Prolog inputs or appropriately isolated engines. Test simultaneous conversations before adding horizontal scaling. Redis messaging and sticky sessions alone do not isolate shared business state.

## Browser and supporting services

- Audio is utterance-based, not full-duplex streaming with barge-in.
- Browser TTS has a watchdog for missing completion callbacks.
- YouTube lookup uses a 512-entry process-local LRU cache.
- Background model warmup separates port availability from inference readiness.
- Cache/metric state is ephemeral. External log retention depends on configuration.

## Hosting topology

The home-server application is exposed through Cloudflare Tunnel at `cookingbroski.mduchlinski.eu`. The Cloud Run application is a separate deployment in `us-central1`; the tunnel is not described as a proxy to that Cloud Run origin.

The maintainer reports faster perceived interaction on the warm home server. Do not attribute the entire difference to region or hosting price without measurements that separate network, startup, and processing time.
