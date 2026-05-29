# Persistent Worker Deployment

Pregnancy Copilot only replies when one runtime is actively consuming or polling Feishu events for the pregnancy bot profile.

For real use, run either:

- `scripts/run_feishu_event_loop.py` when Feishu event consume is available and stable for the bot.
- `scripts/run_feishu_runtime_worker.py` when you want deterministic Host Runtime behavior from a specific P2P chat. This path polls the chat, calls `process_host_message`, and sends `reply_text` exactly.

## Required Command Shape

```bash
cd /path/to/pregnancy-copilot
PYTHONPATH=src .venv/bin/python scripts/run_feishu_event_loop.py \
  --profile <lark-profile> \
  --data-root /path/to/pregnancy-data
```

Use the real `lark-cli` profile name for the pregnancy bot. Do not use `/tmp` for real family data.

Direct runtime worker shape:

```bash
cd /path/to/pregnancy-copilot
PYTHONPATH=src .venv/bin/python scripts/run_feishu_runtime_worker.py \
  --profile <lark-profile> \
  --chat-id <feishu_chat_id> \
  --bot-app-id <feishu_app_id> \
  --data-root /path/to/pregnancy-data \
  --state-file /path/to/pregnancy-data/runtime/feishu-seen-message-ids.json \
  --interval 3
```

## Option 1: Docker Compose

Use `ops/docker-compose.worker.yml` as a template. The service should:

- mount a persistent `pregnancy-data` directory,
- mount the `lark-cli` config for the selected profile,
- restart with `unless-stopped`,
- run without `--max-events`.

This is the preferred NAS/container deployment when the host already uses Docker Compose.

## Option 2: systemd

Use `ops/pregnancy-copilot.service` as a template. Adjust:

- `WorkingDirectory`,
- `.venv/bin/python` path,
- `--profile`,
- `--data-root`,
- `PATH` so it can find `lark-cli`.

Then install on the host:

```bash
sudo cp ops/pregnancy-copilot.service /etc/systemd/system/pregnancy-copilot.service
sudo systemctl daemon-reload
sudo systemctl enable --now pregnancy-copilot.service
sudo systemctl status pregnancy-copilot.service
```

## Option 3: nohup Temporary Worker

Use this only when the host has no process supervisor:

```bash
PREGNANCY_COPILOT_PROJECT_DIR=/path/to/pregnancy-copilot \
PREGNANCY_COPILOT_DATA_ROOT=$HOME/pregnancy-data \
PREGNANCY_COPILOT_LARK_PROFILE=<lark-profile> \
bash ops/run-worker-nohup.sh
```

This survives terminal close, but it may not survive container or host restart.

## Option 4: macOS launchd

Use `ops/com.pregnancy-copilot.feishu-runtime-worker.plist` as a local Mac template for the direct runtime worker. Edit the paths, profile, chat id, and app id first.

Install for the current user:

```bash
mkdir -p ~/Library/LaunchAgents
cp ops/com.pregnancy-copilot.feishu-runtime-worker.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.pregnancy-copilot.feishu-runtime-worker.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.pregnancy-copilot.feishu-runtime-worker.plist
launchctl list | grep pregnancy-copilot
```

Stop it:

```bash
launchctl unload ~/Library/LaunchAgents/com.pregnancy-copilot.feishu-runtime-worker.plist
```

## Verification

After starting the worker:

1. Send one message to the pregnancy bot.
2. Confirm the bot replies.
3. Confirm `events/events.jsonl` adds one line.
4. Confirm the worker is still running after processing the message.
5. Confirm logs are written to `pregnancy-data/worker.log` or your process manager's log.

If the bot does not reply, check `docs/RUNTIME_CONNECTION.md`.
