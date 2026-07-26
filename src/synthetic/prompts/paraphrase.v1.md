# paraphrase.v1

Rewrite the seed as one different but semantically equivalent utterance.

Style contract: {{STYLE_GUIDE}}

Hard constraints:

- Keep `intent` exactly unchanged.
- Keep every `(slot type, slot value)` pair exactly unchanged.
- Every literal slot value must occur in `utt`.
- Do not add or remove slots.
- Use Traditional Chinese appropriate for Taiwan.

Seed JSON: {{SEED_JSON}}
