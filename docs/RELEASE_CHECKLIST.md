# Release Checklist

Use this before publishing Pregnancy Copilot Skill to GitHub.

## Required Checks

```bash
.venv/bin/python -m pytest -v
```

The suite must include the `test_v021_*` adversarial modules for routing, onboarding, medical state, identity isolation, storage reliability, LLM failure, privacy scanning, migration, and backup restore.

```bash
PYTHONPATH=src .venv/bin/python scripts/run_single_user_acceptance.py \
  --data-root /tmp/pregnancy-copilot-single-user-acceptance
```

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_runtime_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-runtime-acceptance
```

```bash
PYTHONPATH=src .venv/bin/python scripts/run_host_channel_acceptance.py \
  --data-root /tmp/pregnancy-copilot-host-channel
```

```bash
PYTHONPATH=src .venv/bin/python scripts/run_synthetic_case_acceptance.py \
  --data-root /tmp/pregnancy-copilot-synthetic-cases
```

```bash
.venv/bin/python scripts/evaluate_host_channel_blackbox.py \
  --messages /tmp/pregnancy-copilot-host-channel-blackbox-messages.json
```

Only run the Hermes blackbox check after exporting real host Agent channel chat messages from a connected test channel. It uses synthetic prompts and must not require private Gemini records.

```bash
PYTHONPATH=src .venv/bin/python scripts/release_check.py --root .
```

The working directory is expected to fail release check if it still contains private local files such as:

- `.venv/`
- `docs/private/`
- real pregnancy exports such as `*.zip`
- local `pregnancy-data/`

Build a clean release package instead:

```bash
PYTHONPATH=src .venv/bin/python scripts/build_release_package.py \
  --source . \
  --target /tmp/pregnancy-copilot-skill-release
```

Then check the package:

```bash
PYTHONPATH=src .venv/bin/python scripts/release_check.py \
  --root /tmp/pregnancy-copilot-skill-release
```

If you run pytest inside `/tmp/pregnancy-copilot-skill-release`, Python will create `__pycache__/` files. Rebuild the release directory once more before zipping, or run `release_check` again after cleanup. The final zip must not contain `__pycache__/` or `.pyc` files.

After zipping, extract into a new directory and rerun installation plus the full test suite. Verify one backup round trip and record the local ZIP SHA256. After GitHub upload, download the public asset and require an exact hash match.

## Do Not Publish

- real pregnancy data
- Feishu message exports
- Gemini/Kortex source zip files
- `docs/private/`
- `.env`
- local virtual environments

## Publishable Demo

The fictional demo data under `examples/demo-pregnancy-data/` is publishable.

Run:

```bash
PYTHONPATH=src python scripts/generate_daily_log.py \
  --data-root examples/demo-pregnancy-data \
  --date 2026-05-05
```
