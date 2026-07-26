# hard_negative.v1

Create one target-intent utterance that is lexically close to the anchor where natural,
but contains the decisive cue that makes the target label unambiguous.

Style contract: {{STYLE_GUIDE}}

Hard constraints:

- The target JSON supplies the authoritative `intent` and complete `slots` list.
- Copy every target slot type and literal value exactly.
- Every target slot value must occur in `utt`.
- Do not copy labels or slot values from the anchor.
- Prefer a minimal semantic contrast, not an unrelated rewrite.

Confusable anchor JSON: {{ANCHOR_JSON}}

Target-label seed JSON: {{TARGET_JSON}}
