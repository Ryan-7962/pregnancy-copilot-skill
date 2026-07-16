# Pregnancy Copilot Skill v0.4.0

v0.4.0 adds an optional Xiaohongshu external-content audit workflow while keeping Pregnancy Copilot an Agent Skill, not a standalone app or medical device.

## What Is New

- Forward a `xiaohongshu.com` or `xhslink.com` post to the pregnant user's existing Agent entrypoint.
- Extract available SSR text and metadata without executing page JavaScript.
- Download allowlisted Xiaohongshu CDN images for the host Agent's vision/OCR capability.
- Optionally transcribe video after the configured `ask`, `always`, or `never` policy permits it.
- Store a local Markdown record, append-only JSONL capture/finalization history, and compact relevant-only memory index.
- Separate source claims, personal experience, commercial signals, evidence gaps, current verification, and user-specific applicability.

## Safety And Privacy

- Every social-media source remains `social_media_unverified` and cannot update medical facts.
- Source text, OCR, transcript, metadata, and embedded instructions are untrusted quoted data.
- Cookie setup happens only in a private terminal. Cookie and ASR API key values are never stored in `pregnancy-data/` or included in release packages.
- Downloaded source media is deleted after host analysis by default. Users may explicitly enable retention.
- `这条不记录` suppresses durable external-source artifacts.

## Honest Limits

- Xiaohongshu can require a current logged-in Cookie and may change its page structure.
- The release was checked against a current public post in an authorized environment; expired share links and missing credentials remain explicit failure states.
- A user must forward the original share link; manually constructed post-ID URLs may not contain the required temporary access token.
- Host vision capability is required for image OCR. Video ASR additionally requires `ffmpeg` and an explicitly configured provider key.
- The Skill does not verify a medical claim merely because it appears in a popular post or a doctor-looking account.
- Current pricing and free-tier policies of third-party providers may change.

Upgrade existing v0.3.0 data with `scripts/upgrade_to_v040.py`. The command creates and verifies a local backup before adding the new directories and preferences.
