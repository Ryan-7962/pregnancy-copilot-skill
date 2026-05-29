# Host Agent Runtime

v0.1.5 uses this host-Agent entrypoint for Hermes/OpenClaw-style usage.

The intended product shape is:

```text
Pregnant user window or pregnancy bot
  -> one Hermes/OpenClaw host Agent
  -> Pregnancy Copilot Skill
  -> one local pregnancy-data/
```

This means the pregnancy experience is not a separate app. It is a conversation entrypoint managed by the host Agent. A partner or family member can install and maintain the host, but partner-facing features are optional extensions.

## Python API

```python
from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message

result = process_host_message(
    HostMessageRequest(
        text="今天肚子有点紧，休息后好了，没有流血也没有流水",
        sender_id="pregnant-user",
        sender_role="pregnant_user",
        conversation_id="pregnancy-window",
        channel="hermes",
    ),
    data_root="/path/to/pregnancy-data",
)

print(result.reply_text)
print(result.handled)
print(result.intent)
print(result.risk_level)
print(result.context_package["system_prompt"])
```

The call will:

- initialize `pregnancy-data/` if missing,
- save raw input under `inbox/raw_<channel>_messages/`,
- append `events/events.jsonl`,
- rebuild memory and daily artifacts,
- return the reply text instead of sending it directly to a platform,
- return a `context_package` that the host Agent can feed into its own LLM.

For ordinary non-pregnancy chat, it returns `handled=False`, `intent="general_chat"`, and an empty `reply_text`. The host should then answer with its normal conversation flow.

Important: `handled=False` is not a failed skill call. It is an explicit pass-through signal.

## CLI Bridge

```bash
PYTHONPATH=src python scripts/process_host_message.py \
  --data-root ./pregnancy-data \
  --channel hermes \
  --conversation-id pregnancy-window \
  --sender-id pregnant-user \
  --sender-role pregnant_user \
  --text "今天肚子有点紧，休息后好了"
```

This prints JSON with:

- `reply_text`
- `handled`
- `intent`
- `triage_required`
- `risk_level`
- `event_id`
- `mode`
- `privacy_level`
- `artifacts`
- `event`
- `context_package`
- `host_action`

## Host Action Envelope

`host_action` is the routing contract for Hermes/OpenClaw.

For ordinary chat outside Pregnancy Copilot scope:

```json
{
  "type": "pass_through",
  "send_reply": false,
  "use_context_package": false,
  "target_channel": "hermes",
  "target_conversation_id": "pregnancy-window"
}
```

The host should answer normally and should not write pregnancy memory.

Minimal host routing pseudocode:

```python
result = process_host_message(request, data_root)

if result.host_action["type"] == "pass_through":
    # Continue with the host Agent's normal LLM path.
    # Do not send result.reply_text; it is intentionally empty.
    return host_llm_answer(user_message)

if result.host_action["type"] == "answer_with_context_package":
    return host_llm_answer(
        user_message,
        system_prompt=result.context_package["system_prompt"],
        context=result.context_package,
    )
```

If the host only sends a reply when `result.reply_text` is non-empty, ordinary chat will appear to "hang". That is a host integration bug, not a Pregnancy Copilot triage decision.

For pregnancy-handled messages:

```json
{
  "type": "answer_with_context_package",
  "send_reply": true,
  "use_context_package": true,
  "context_package_required": true,
  "target_channel": "agent_default",
  "target_conversation_id": "pregnancy-window",
  "fallback_reply_text": "..."
}
```

The host should generate the final reply using `context_package`. `fallback_reply_text` is only a deterministic fallback when the host has no LLM available.

## Generic Channel JSON Bridge

If the host receives messages from its default chat channel or another gateway, it can use the generic JSON bridge instead of writing a new adapter first. For v0.1.5 testing, treat the host Agent's default chat as the pregnant user's conversation entrypoint:

```bash
PYTHONPATH=src python scripts/process_channel_message.py \
  --data-root ./pregnancy-data \
  --json '{"channel":"agent_default","chat_id":"pregnancy-default-chat","sender_id":"pregnant-user","text":"今天肚子有点紧，休息后好了"}'
```

Accepted aliases:

- text: `text`, `content`, `message`, `body`
- conversation: `conversation_id`, `chat_id`, `room_id`, `session_id`, `thread_id`
- sender: `sender_id`, `user_id`, `open_id`, `from_user`, `from`
- channel: `channel`, `source`, `platform`, `adapter`
- timestamp: `timestamp`, `create_time`, `created_at`, `time`

The bridge only normalizes fields. It does not put pregnancy business logic into the channel layer.

Current topology acceptance:

```bash
PYTHONPATH=src python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel
```

This verifies the host default-channel path. WeChat, Feishu, and other gateways remain replaceable adapters.

## Acceptance Check

Before wiring a real chat window, run the host runtime acceptance check:

```bash
PYTHONPATH=src python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
```

Expected output:

```json
{
  "ok": true
}
```

This validates the host contract without Feishu or WeChat:

- ordinary chat returns `handled=false` and no context package;
- ordinary chat returns `host_action.type=pass_through`, `send_reply=false`, and `use_context_package=false`;
- ordinary chat does not create pregnancy memory, inbox, or event files;
- pregnancy symptom messages return `handled=true` plus `context_package`;
- daily logs are saved without visible red/yellow/green triage;
- later medical observations become current while older values become superseded history;
- raw inbox, events, current context, and current medical state files are written.

## Host Context Package

`context_package` is the LLM-first bridge. It lets the skill act as memory and workflow infrastructure while the host model performs the nuanced medical reasoning.

It contains:

- `system_prompt`: host-model instructions and safety boundaries.
- `context_markdown`: regenerated `memory/current_context.md`.
- `current_medical_state`: parsed `memory/current_medical_state.yaml`.
- `safety_floor`: non-negotiable safety constraints.
- `memory_write_policy`: what should be preserved or extracted after the reply.
- `output_contract`: response-shape hints such as current time, gestational age, delta analysis, and action steps.

Host Agents should prioritize `current_medical_state.metrics.*.current` over old events or `previous_values`.

If a fact is absent, stale, or not source-backed, the host should say it does not know yet and ask for the missing report text/date/value/unit or doctor conclusion. It should not infer unrecorded medical numbers from conversational context.

For high-frequency daily data, read `memory/daily_metrics.yaml` or the "高频日常指标摘要" section in `current_context.md`. This is the quick index for weight, mood, diet, activity, and sleep. It is separate from medical observations because daily records are trend/context data, not automatically doctor-confirmed medical facts.

When the host model extracts structured data from a report or lab result, write it through:

```bash
PYTHONPATH=src python scripts/record_medical_observation.py --data-root ./pregnancy-data --json '<observation-json>'
```

Do not tell the user that a report or lab value has been recorded, inserted, or refreshed in current medical state unless that write command or equivalent API call has succeeded. Before the write succeeds, phrase it as "待记录的新数据" or "用户刚提供的新信息".

See `docs/MEDICAL_STATE.md` for the JSON contract.

## Role Mapping

Use `sender_role="pregnant_user"` for the pregnant user's pregnancy conversation.

Use `sender_role="partner"` only for optional partner extensions such as dad diary or shared artifacts.

If partner extensions are enabled, product code should still enforce the pregnant-user-first sharing model:

- default raw records are private,
- partner access should prefer summaries and artifacts,
- full sharing requires explicit pregnant-user consent.

## Relationship to Feishu Event Loop

The standalone Feishu event loop still works:

```bash
PYTHONPATH=src python scripts/run_feishu_event_loop.py --profile <lark-profile> --data-root ./pregnancy-data
```

Use it for smoke tests, temporary bot operation, or hosts that cannot route events natively.

For Hermes/OpenClaw-style usage, prefer the host runtime API above. The host should receive messages from whichever Feishu bot/window it manages, call `process_host_message`, then send `result.reply_text` back through its own channel.

See `docs/INTENTS.md` for the difference between medical triage, pregnancy logs, mood support, diary messages, and ordinary chat.
