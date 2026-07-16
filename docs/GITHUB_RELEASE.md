# GitHub Release Guide

Current public version target: `v0.4.0` Public Alpha.

## Release Gates

1. Full local test suite passes.
2. Runtime, channel, single-user, synthetic, and install acceptance scripts pass.
3. Clean release directory passes `scripts/release_check.py`.
4. Clean release directory is zipped, re-extracted, installed, and fully retested.
5. No private archive, real pregnancy data, local absolute path, token, bot ID, cache, `.env`, ZIP, or diff is present in source assets.
6. Downloaded GitHub asset hash matches the local release asset hash.

## Build

```bash
PYTHONPATH=src .venv/bin/python scripts/build_release_package.py \
  --source . \
  --target /tmp/pregnancy-copilot-skill-v0.4.0-release

PYTHONPATH=src .venv/bin/python scripts/release_check.py \
  --root /tmp/pregnancy-copilot-skill-v0.4.0-release
```

Run tests in an extracted copy, then rebuild the final release directory so generated `__pycache__` files are not included in the ZIP.

## Publish

Use a clean clone of the public repository. Synchronize only the clean release directory, inspect the diff, commit, tag, and push:

```bash
git add .
git commit -m "Release Pregnancy Copilot Skill v0.4.0"
git tag -a v0.4.0 -m "Pregnancy Copilot Skill v0.4.0"
git push origin main
git push origin v0.4.0
```

Create the GitHub Release from `docs/PUBLIC_RELEASE_NOTES_v0.4.0.md`, upload `pregnancy-copilot-skill-v0.4.0.zip`, and verify the downloaded SHA256.
