# Limitations, data handling, and next steps

[Back to README](../README.md)

## Intended use

CookingBroski is a portfolio prototype demonstrating conversational interaction, hybrid NLU, symbolic recipe filtering, and cloud delivery. A deployed demo and automated tests do not establish readiness for public multi-user production use.

## Shared dialogue state

The current design is documented as using one in-process dialogue manager and a Prolog interface with mutable global predicates. Independent users may interfere with each other's filters, selected recipes, or conversation state.

Keep demo use to one active conversation at a time. This is a usage constraint, not an enforced access-control mechanism. A single Cloud Run instance can still receive multiple connections.

Supporting multiple users requires explicit session isolation, request-specific Prolog state, concurrency tests, and an appropriate Socket.IO deployment architecture. Session affinity or Redis messaging alone does not repair shared mutable business state.

## Startup and persistence

Cloud Run can scale to zero. Reported cold startup is approximately 10–15 seconds, but it varies with runtime conditions. Early landing-page availability is distinct from model readiness.

The recipe-video cache, process metric counters, and in-process dialogue state are ephemeral. They are not a durable user history. Browser session storage does not replace a server-side persistence design.

## Language and interaction boundaries

- The local NLU model operates on individual utterances and has a bounded domain schema.
- Contextual replies and compound requests can require state-aware rules or LLM assistance.
- LLM output validation checks structure, not factual correctness or complete understanding.
- Push-to-talk uploads a completed recording; the system does not provide continuous voice activity detection or full-duplex interruption.
- Browser voices and speech callbacks vary across platforms. The watchdog is recovery logic, not a universal compatibility guarantee.

## External dependencies

Remote STT, Claude responses, YouTube lookup, and tracing depend on the configured providers. Missing credentials, quota exhaustion, service errors, or network failures can reduce functionality. Fallback paths should be tested explicitly rather than described as guaranteed high availability.

The browser speech interface also should not be interpreted as a blanket guarantee of offline execution across every OS/browser configuration.

## Data handling

The implemented provider order and observability settings determine which data leaves the host. Review the current service code and configuration before publishing a privacy statement.

| Data | Documented processing path | What needs verification |
|---|---|---|
| Microphone audio | Sent from the browser to the application for transcription | Whether recordings are persisted; size/duration limits; cleanup |
| Fallback audio | May be sent to ElevenLabs or OpenAI on the configured fallback path | Trigger conditions, provider settings, retention, user notice |
| Transcripts and cooking requests | Processed by local NLU; selected requests may reach Claude | Exact prompt/context content and fallback triggers |
| LLM traces | May be recorded through Langfuse | Content capture, redaction, retention, access permissions |
| Operational logs | Structured events sent to configured logging | Whether transcript content is included; retention and access |
| Recipe-video queries | Sent to YouTube search | Query contents and cache policy |

This table is a data-flow checklist, not a claim that privacy compliance has been established. Until these details are verified, visitors should not provide sensitive information.

## Cooking and dietary safety

Recipe constraints and ingredient taxonomies are software filters, not a guarantee that a meal is medically suitable or allergen-free. Recipe metadata can be incomplete, and generated cooking advice can be incorrect. Users should independently verify ingredients, food-handling instructions, and relevant dietary requirements.

Do not frame an exclusion such as “no peanuts” as a certified allergy-safety feature.

## Evaluation caveat

Earlier documentation reports conflicting split sizes and train/test overlap. Current headline model metrics should only be published after reconciling the dataset and tying the result to a specific model artifact. See [evaluation](evaluation.md).

## Prioritized next steps

1. Reconcile dataset counts/overlap and publish an artifact-linked evaluation report.
2. Isolate conversation state and add simultaneous-session regression tests.
3. Verify missing-provider and failed-provider behavior end to end.
4. Review public-demo controls: rate limits, request sizes, audio limits, authentication needs, and abuse handling. These are review items, not claims that such controls are currently absent.
5. Establish data retention/redaction policies and verify tracing behavior.
6. Add a measured startup/latency report and a tested rollback procedure.
7. Verify licenses and attribution for inherited code, datasets, recipes, models, and media.
8. Add an actual UI screenshot or short demo recording to the README, with no visible secrets or sensitive traces.

These are proposed improvements, not completed features or promised delivery dates.
