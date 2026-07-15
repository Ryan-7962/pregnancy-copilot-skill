# LLM Strategy

Pregnancy Copilot Skill is designed for Agent hosts such as OpenClaw, Codex, Claude Code, and similar tools.

## Default: Host Agent Mode

In the default mode, users do not configure a separate LLM.

The host Agent already has a model. The skill provides:

- local memory files
- current context
- safety triage
- prompt templates
- event writing
- artifact generation

The host Agent should use its own model to answer with the generated context and safety rules.

This is the recommended mode for OpenClaw-style usage.

In v0.1.5, the Host Agent Runtime gives the host a direct message API and a stable local memory substrate. The host can call `process_host_message`, receive `reply_text`, and send it back to the active pregnant-user conversation. No extra model configuration is required unless the host wants unattended standalone replies.

The core product direction is LLM-first: the host model performs most nuanced medical reasoning and response generation, while the skill provides durable pregnancy memory, current medical state, safety floor rules, and artifact workflows.

Host runtime results include `context_package`, a structured package that can be passed to the host model. This is the preferred integration point for Hermes/OpenClaw/Codex/Claude Code style agents.

Host models should prioritize:

1. `memory/current_medical_state.yaml` for current effective medical facts.
2. `memory/current_context.md` for recent context and workflow state.
3. Historical events as traceable background, not as current facts when superseded.

## Optional: Standalone Event Loop Mode

The standalone Feishu event loop is just a Python process reading `lark-cli` events.

Because that process does not automatically have access to the host Agent model, it can optionally call external commands:

- `PREGNANCY_COPILOT_TRIAGE_LLM_COMMAND`
- `PREGNANCY_COPILOT_RESPONSE_LLM_COMMAND`

These hooks are advanced escape hatches for unattended automation.

They are not required for normal skill installation.

The response command receives the full Pregnancy Q&A prompt on stdin and prints the final reply on stdout.

If it fails or returns empty output, the event loop falls back to the deterministic safety-bounded triage reply.

## Safety

The local rule layer always remains available as a limited safety fallback, not the primary medical reasoning engine.

For triage:

- local rules catch a small set of explicit emergency red flags and conservative fallback cases
- optional semantic LLM can upgrade risk
- semantic LLM cannot downgrade a rule-based red result
- invalid, refused, empty, or failed model output falls back to local rules without claiming semantic assessment

For answer generation:

- host Agent mode should use the host model directly
- standalone mode can call a configured command
- red risk replies must preserve doctor/emergency guidance

## User Choice

Recommended install flow:

1. Use Host Agent Mode by default.
2. Run `scripts/install_check.py`.
3. Configure Feishu if needed.
4. Only configure standalone LLM commands if the user wants unattended auto-reply without an active host Agent.
