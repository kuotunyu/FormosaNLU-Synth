# noise_codeswitch.v2

Create one realistic Taiwan spoken-language robustness variant of the seed. It must remain
a complete, grammatical and actionable request—not just a noun phrase or particles.

Choose at most one light phenomenon:

- one natural English assistant/device word, or
- one Taiwan spoken particle at a natural boundary, or
- punctuation removal that still leaves a clear utterance.

Hard constraints:

- Copy `intent` and the complete `slots` array exactly from the seed.
- Every complete literal slot value must occur contiguously in `utt`.
- Never insert noise inside a slot value.
- Preserve the seed's full meaning; do not invent a different action.
- Avoid word salad, excessive particles, fake accents and arbitrary typos.

Before returning JSON, silently check that the sentence is something a Taiwan speaker could
actually say to an assistant.

Seed JSON: {{SEED_JSON}}
