# M9 Preflight

Status: **technically ready; long batch not started**.

## Six primary groups

| Group | Train rows |
|---|---:|
| `real_only` | 1,176 |
| `real_std_aug` | 4,936 |
| `real_syn_unfiltered_full` | 12,440 |
| `real_syn_unfiltered_eqn` | 4,936 |
| `real_syn_filtered` | 4,936 |
| `full_real` | 11,514 |

The three compute-matched additions are exactly equal:
filtered synthetic = unfiltered control = Standard Aug = **3,760 rows**.
All six assembled datasets have unique IDs and cover all 60 intents.

## Standard Aug

The 3,760 deterministic rows contain:

- 2,200 slot-aware EDA rows
- 514 character-noise rows
- 1,046 slot-protected round-trip backtranslations

Output SHA-256:
`5e83285d95bd70eabf737285d4fb519eca569effc67b106e8196186af955df8e`.
The two Marian checkpoints are pinned by immutable revisions and locally
hashed in `reports/m9_translation_models.json`.

## Resume and safety checks

- A first smoke run wrote `checkpoint-1`.
- A second process loaded that checkpoint and completed at global step 2.
- It wrote `checkpoint-2` and the final adapter.
- Peak allocated VRAM was 20,646 MiB; peak reserved was 22,434 MiB.
- The batch runner is sequential, skips completed runs, records each failure,
  and always invokes training with resume enabled.
- A dry plan validated all six inputs and the shared config digest.
- The adapter-evaluation entry is also resumable and has a separate execution
  confirmation guard.

For the overnight batch, use the stricter CPU preflight and launch guard in
`docs/M9_OVERNIGHT_RUNBOOK.md`. Its confirmation text explicitly records use
of the honest 3,760-row filtered corpus. The planned 8,000-row gate was not met.
