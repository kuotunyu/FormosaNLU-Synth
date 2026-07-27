# M9 Overnight Runbook

This runbook covers the six primary Gemma QLoRA training runs only. It does not
silently start F7 judging, adapter evaluation, publishing, or any sibling
project.

## Before sleep

The user only needs to tell Codex: **「開始跑 M9」**. That instruction means:

- use the frozen 3,760-row filtered corpus honestly;
- run the six seed-42 groups sequentially on the local RTX 4090;
- resume an incomplete group from its latest valid checkpoint;
- never terminate or modify a sibling project's process;
- keep Git authorship restricted to `kuotunyu`.

Codex must first run the CPU-only readiness gate:

```powershell
.\.venv\Scripts\python.exe -m scripts.m9_overnight
```

The gate verifies contributor history, worktree state, all six input counts,
Gemma file sizes, the cross-process resume smoke, GPU availability, and free
disk. Any failed line means the batch must not start.

The guarded launch command is:

```powershell
.\.venv\Scripts\python.exe -m scripts.m9_overnight `
  --execute --confirm M9-OVERNIGHT-3760-4090
```

The confirmation text deliberately includes `3760`: starting it records that
the batch uses the corpus that actually passed the frozen F1-F6 thresholds. It
does not claim that the planned 8,000-row gate was met.

## While the user sleeps

- Six groups run sequentially; only one training process should load the GPU.
- A completed group is skipped on restart.
- An incomplete group resumes from the highest valid `checkpoint-*`.
- The live machine-readable summary is
  `runs/m9_overnight_status.json`.
- The batch report is `runs/m9_batch_report.json`.
- A failed preflight or failed group is reported; thresholds, model, data, and
  training configuration are not changed automatically.

Expected training time remains approximately 5-8 hours. This is an estimate,
not a deadline.

## After training

Adapter evaluation is intentionally a separate resumable GPU phase. The M8
full-test baseline took about one hour, so automatically evaluating all six
adapters could extend GPU use well beyond the user's sleep period.

After the six training rows are complete:

```powershell
.\.venv\Scripts\python.exe -m scripts.eval
```

This first prints the dry plan. Actual evaluation still requires its separate
confirmation guard. When all evaluations are complete:

```powershell
.\.venv\Scripts\python.exe -m scripts.report_results
```

That fills the seven-row M10 table from raw run and evaluation reports.

## Safe interruption

Do not delete a run directory. Stop only the active FormosaNLU training process
when the user explicitly requests it. The next guarded launch uses `--resume`
and skips every completed group.
