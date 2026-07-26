# noise_codeswitch.v1

Create one realistic Taiwan spoken-language robustness variant of the seed.
Choose one or two light phenomena: an English assistant/device word, a spoken particle,
a harmless typo away from slot spans, or mild ASR-like punctuation loss.

Hard constraints:

- Keep `intent` exactly unchanged.
- Keep every `(slot type, slot value)` pair exactly unchanged and visibly contiguous.
- Never insert noise inside a slot value.
- Do not make the utterance incomprehensible or cartoonish.
- Return Traditional Chinese with only natural, limited code-switching.

Seed JSON: {{SEED_JSON}}
