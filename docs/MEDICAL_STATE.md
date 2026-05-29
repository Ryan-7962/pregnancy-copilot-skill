# Medical State and Delta Updates

Pregnancy Copilot should not treat every remembered medical value as current.

If a later B 超, blood test, urine test, or doctor order updates the same metric, the skill must preserve the old record but make the newer value the current source of truth.

## Files

```text
events/medical_observations.jsonl
memory/current_medical_state.yaml
memory/medical_observation_timeline.md
```

## Recording an Observation

Host Agents can record an already-extracted medical observation:

```bash
PYTHONPATH=src python scripts/record_medical_observation.py \
  --data-root ./pregnancy-data \
  --json '{"metric_key":"placenta_position","display_name":"胎盘位置","value":"宫底后壁","measured_at":"2026-05-08","status":"resolved","interpretation":"旧 23mm 状态已被刷新，当前胎盘低置警报解除。"}'
```

Or pass a JSON file:

```bash
PYTHONPATH=src python scripts/record_medical_observation.py \
  --data-root ./pregnancy-data \
  --file ./reports/2026-05-08-placenta-observation.json
```

The script appends `events/medical_observations.jsonl`, rebuilds `memory/current_medical_state.yaml`, updates `memory/medical_observation_timeline.md`, and regenerates `memory/current_context.md`.

## Candidate Extraction From Imports

Historical Gemini/Kortex imports should not automatically become medical facts. First extract candidates:

```bash
PYTHONPATH=src python scripts/extract_medical_observation_candidates.py \
  --data-root ./pregnancy-data
```

Outputs:

```text
exports/medical_observation_candidates.jsonl
exports/medical_observation_candidate_review.md
```

Candidate records are `review_decision: pending` by default and must be checked against the private source before promotion. The review Markdown excludes raw user and assistant text.

After review, edit `exports/medical_observation_candidates.jsonl` and set only confirmed records to:

```json
"review_decision": "promote"
```

Then apply:

```bash
PYTHONPATH=src python scripts/extract_medical_observation_candidates.py \
  --data-root ./pregnancy-data \
  --promote-reviewed
```

Only promoted candidates are appended to `events/medical_observations.jsonl`; pending and skipped candidates do not affect current medical state.

## LLM Extraction Contract

The skill does not perform OCR or medical interpretation by itself. A host LLM or a human reviewer should extract report facts into this JSON shape:

```json
{
  "metric_key": "cervical_length",
  "display_name": "宫颈管长度",
  "value": 29,
  "unit": "mm",
  "measured_at": "2026-05-08",
  "status": "watch",
  "interpretation": "仍高于 25mm 阈值，但需要后续随访。",
  "source_event_id": "evt-0508-us",
  "raw_source_path": "reports/2026-05-08-ultrasound.md"
}
```

Required fields:

- `metric_key`: stable machine key, such as `placenta_position`, `cervical_length`, `thyroid_tsh`.
- `display_name`: user-facing Chinese label.
- `value`: exact extracted value, without optimistic rewriting.
- `measured_at`: report date or observation date.
- `status`: one of `normal`, `watch`, `resolved`, `active`, `unknown`.

Guidelines:

- Use the newest report date as `measured_at`.
- If two observations use the same `measured_at`, the later `recorded_at` wins for `current`.
- Do not infer missing values.
- Do not infer missing report dates. If `measured_at` is unknown, ask the user for the report date or original report.
- Do not mark an item `resolved` unless the new observation directly refreshes the old concern.
- Keep report text in `raw_source_path`; do not paste private report content into public docs.

## Principle

- `events/medical_observations.jsonl` is append-only.
- `memory/current_medical_state.yaml` is regenerated.
- Host LLMs should use `current` first.
- `previous_values` are historical and superseded unless a newer observation reactivates the issue.
- If no reliable current fact exists, answer "unknown / needs more information" instead of filling gaps from older chat memory.

## Example

```yaml
metrics:
  placenta_position:
    display_name: 胎盘位置
    current:
      value: 宫底后壁
      measured_at: 2026-05-08
      status: resolved
      interpretation: 旧 23mm 状态已被刷新，当前胎盘低置警报解除。
    previous_values:
      - value: 距宫颈内口 23mm
        measured_at: 2026-03-26
        status: watch
        effective_status: superseded
```

The model may mention the history when useful, but current medical reasoning must not continue using the old 23mm value as the active state.

## Status Values

- `normal`: current measurement is normal.
- `watch`: still needs follow-up or doctor confirmation.
- `resolved`: a previous risk or concern has been refreshed or cleared by a newer report.
- `active`: still-active doctor order, medication, or restriction.
- `unknown`: captured but not yet interpreted.

## Product Role

This is the memory layer that ordinary Gemini/ChatGPT conversations do not reliably provide. The host model still performs medical reasoning; the skill keeps the medical data fresh, traceable, and portable across models.

Daily weight, mood, diet, activity, and sleep are indexed separately in `memory/daily_metrics.yaml`. Do not force every daily record into `medical_observations.jsonl`; reserve medical observations for report values, labs, doctor conclusions, medication restrictions, and other clinically meaningful facts.
