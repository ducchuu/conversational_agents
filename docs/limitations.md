# Limitations and data handling

[Documentation index](documentation.md) · [README](../README.md)

## Intended use

CookingBroski is a deployed portfolio prototype. Successful tests and live demonstrations do not establish unrestricted multi-user production readiness, continuous availability, or safety certification.

## Shared state

The documented dialogue manager and mutable Prolog state are shared in-process. Independent users can interfere with conversation state. Use one active conversation at a time; this is a stated usage constraint, not an enforced isolation mechanism.

Before public multi-user use, introduce per-session state and appropriately isolated/stateless Prolog operations, then add simultaneous-user regression tests. Instance limits and session affinity alone do not solve shared state.

## Interaction and language

- Audio is push-to-talk, with completed recordings uploaded over Socket.IO.
- No continuous full-duplex recognition or voice interruption is claimed.
- Local BERT interprets individual utterances and a bounded intent/slot schema.
- Rules and Claude extend behavior but do not guarantee correct interpretation.
- Browser TTS quality and callbacks vary; watchdog recovery is not universal compatibility.

## Hosting and performance

The home-server service is normally warm and is recommended for demonstration. Its availability depends on host uptime, connectivity, and the tunnel. Cloud Run can add cold-start delay and network latency. No current standardized end-to-end latency benchmark is supplied.

Do not promise instantaneous responses, fixed cold-start duration, or guaranteed availability. FP32 was selected for observed cross-platform consistency, not proof of identical results on every runtime/hardware combination.

## Provider failures

The maintainer reports testing an Anthropic-unavailable path that returns rule/template responses without hanging. Offline behavior can have less functionality than the online system. This test does not establish all possible provider, quota, partial-response, or network failure behavior.

## Data handling

The live summary verifies functionality, not privacy or retention policies. Before making definitive public statements, inspect the actual configuration and service code.

| Data | Potential path | Details to confirm |
|---|---|---|
| Audio | Browser to application; configured remote STT fallback | Persistence, deletion, size limits, provider retention |
| Transcript/request | Local NLU; selected Claude requests | Exact prompts/context and redaction |
| LLM traces | Optional Langfuse | Content capture, retention, access |
| Operational events | Configured application/cloud logs | Sensitive fields, retention, access |
| Video query | YouTube service | Query content and cache behavior |

Visitors should not submit sensitive information. Do not imply every browser's speech implementation is fully offline merely because the application calls the browser API.

## Ephemeral state

Dialogue memory, video cache entries, and process-local counters are not durable storage. Restarts can reset them. Browser session storage preserves selected UI state, not independently isolated server conversations.

## Cooking and dietary boundaries

Recipe metadata and ingredient filters can be incomplete. Generated cooking guidance can be wrong. Independently verify ingredients, food handling, and dietary suitability. Excluding an ingredient is not a certified allergen-safety guarantee.

## Licensing

Independent cloud and MLOps extensions are licensed under the MIT License in [LICENSE](../LICENSE). Original course framework assets, recipe databases, and third-party models retain their respective academic and open-source attribution notices. See [attribution](documentation.md#attribution-and-licensing) and [LICENSE](../LICENSE).

## Next improvements

- Implement and test independent concurrent sessions.
- Publish sanitized, artifact-linked evidence and a downloadable model release.
- Add reproducible cold/warm and browser-observed latency measurements.
- Verify public-demo abuse controls, payload limits, and access requirements.
- Define audio/log/trace retention and redaction policies.
- Rehearse recovery and verify the deployed artifact identity.

These are improvement/release tasks, not assertions that the supplied test results failed.
