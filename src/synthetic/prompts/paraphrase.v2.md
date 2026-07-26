# paraphrase.v2

Rewrite the seed as one different but semantically equivalent utterance.

Style contract: {{STYLE_GUIDE}}

Hard constraints:

- Copy `intent` exactly from the seed.
- Copy the complete `slots` array exactly, character for character. Slot values may
  include grammatical particles such as 「的」; those particles are part of the value.
- Every complete literal slot value must occur contiguously in `utt`.
- Do not add or remove slots.
- The result must be a complete, meaningful request in Traditional Chinese for Taiwan.

Before returning JSON, silently verify every slot value by finding the exact characters in
your new `utt`.

Seed JSON: {{SEED_JSON}}
