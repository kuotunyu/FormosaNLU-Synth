# hard_negative.v2

Create one target-intent utterance that forms a useful minimal contrast with the anchor.

Style contract: {{STYLE_GUIDE}}

The two inputs have different roles:

1. **TARGET is the only source of labels.** Copy its `intent` and complete `slots` array
   exactly, character for character.
2. **ANCHOR supplies only a confusable intent/wording idea.** Never copy the anchor's slot
   types or slot values into the output.

Hard constraints:

- Every complete target slot value must occur contiguously in `utt`.
- Add the decisive action cue that makes the TARGET intent unambiguous.
- Prefer a small semantic contrast, but abandon lexical similarity if it conflicts with
  target labels or natural grammar.
- Return a complete, meaningful Traditional Chinese request.

Before returning JSON, compare the output `intent` and `slots` against TARGET one final time.

Confusable anchor (wording reference only): {{ANCHOR_JSON}}

AUTHORITATIVE TARGET LABELS: {{TARGET_JSON}}
