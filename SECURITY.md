# Security And Privacy

Pregnancy Copilot Skill stores sensitive pregnancy and health context. Treat all real `pregnancy-data/`, chat exports, report images, medical documents, and channel logs as private health data.

## Do Not Publish

- `pregnancy-data/`
- `docs/private/`
- Gemini, ChatGPT, Feishu, WeChat, Kortex, NotebookLM, or Obsidian raw exports
- screenshots containing names, avatars, locations, hospitals, account IDs, or medical identifiers
- `.env`, app credentials, Feishu/Lark tokens, private keys, or OAuth artifacts
- release zips that were built from an unchecked source tree

## Public Test Data

Only use public fixtures under `examples/`.

`examples/synthetic_cases/pregnancy_synthetic_cases.json` contains manually rewritten synthetic cases. They are for runtime regression testing only and are not medical correctness tests.

## Reporting Security Issues

If this project is published to GitHub, report security or privacy issues privately first. Do not open a public issue containing real pregnancy data, credentials, or channel logs.

## Medical Safety

This project is not a medical device and does not replace obstetric care. Host Agents and users must escalate urgent symptoms to clinicians or emergency services.
