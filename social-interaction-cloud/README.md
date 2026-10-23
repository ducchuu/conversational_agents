# Social Interaction Cloud (SIC) — Service Package

This package contains the core Python services, dialogue state management, and neural inference components for the **CookingBroski** conversational agent:

- **Dialogue Management & Symbolic Reasoning:** Table-driven `DialogManager` state machine interfacing with SWI-Prolog facts via `pyswip`.
- **Fast Local BERT NLU:** Fine-tuned BERT model compiled to ONNX with INT8 dynamic quantization for ~6ms CPU inference.
- **Speech-to-Text & Fallbacks:** `faster-whisper` local offline STT with ElevenLabs Scribe v2 and OpenAI Whisper API cloud fallbacks.
- **Webserver & Client Interface:** Flask + Socket.IO orchestration server with streaming LLM NLG responses and client-side Web Speech TTS.
- **Evaluation Benchmarks:** 87-turn Golden Dialogue regression suite and MLOps quality gates.

---

> [!NOTE]
> For the comprehensive project architecture, Docker deployment guides, MLOps CI/CD pipelines, and local development setup, please refer to the primary project documentation README.md at the root directory of this repository.**
