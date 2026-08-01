"""Explain per-intent movement across seeds instead of from a single run.

The primary table reports per-intent gains and regressions from seed 42. Those
figures are dramatic, and it turns out they are largely a property of which
seed was drawn rather than of the training data. This recomputes per-intent
accuracy for every available seed and reports the spread, so a single-seed
extreme cannot be mistaken for a stable effect.

Reads prediction JSONL files, which stay untracked because they contain
upstream Test utterances. Paths and row counts are recorded in the JSON report.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

GROUPS = ("real_only", "real_syn_filtered")
DEFAULT_SEEDS = (42, 43, 44)


def load_predictions(path: Path) -> dict[str, tuple[str, str | None, str]]:
    """Return {row_id: (gold_intent, predicted_intent_or_None, utterance)}."""
    rows: dict[str, tuple[str, str | None, str]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            try:
                predicted = json.loads(record["raw_prediction"]).get("intent")
            except (json.JSONDecodeError, TypeError):
                # Unparseable output counts as a wrong prediction, never as a
                # skipped row.
                predicted = None
            expected = record["expected"]
            rows[expected["id"]] = (expected["intent"], predicted, expected["utt"])
    return rows


def per_intent_accuracy(
    rows: dict[str, tuple[str, str | None, str]],
) -> dict[str, tuple[int, int]]:
    """Return {intent: (correct, total)}."""
    tally: dict[str, list[int]] = {}
    for gold, predicted, _ in rows.values():
        entry = tally.setdefault(gold, [0, 0])
        entry[1] += 1
        if predicted == gold:
            entry[0] += 1
    return {intent: (correct, total) for intent, (correct, total) in tally.items()}


def _spread(values: list[float]) -> dict[str, Any]:
    return {
        "per_seed": values,
        "mean": statistics.fmean(values),
        "sample_std": statistics.stdev(values) if len(values) > 1 else None,
        "range": max(values) - min(values) if values else 0.0,
    }


def analyse(
    predictions: dict[str, dict[int, dict[str, tuple[str, str | None, str]]]],
    *,
    seeds: list[int],
    top_n: int = 5,
) -> dict[str, Any]:
    intents = sorted({gold for _, _, rows in _iter(predictions) for gold, _, _ in rows.values()})
    per_intent: dict[str, Any] = {}
    for intent in intents:
        entry: dict[str, Any] = {}
        for group in GROUPS:
            values = []
            for seed in seeds:
                correct, total = per_intent_accuracy(predictions[group][seed]).get(
                    intent, (0, 0)
                )
                values.append(correct / total * 100 if total else 0.0)
            entry[group] = _spread(values)
        entry["paired_delta"] = _spread(
            [
                f - r
                for r, f in zip(
                    entry["real_only"]["per_seed"],
                    entry["real_syn_filtered"]["per_seed"],
                    strict=True,
                )
            ]
        )
        entry["support"] = per_intent_accuracy(predictions["real_only"][seeds[0]]).get(
            intent, (0, 0)
        )[1]
        per_intent[intent] = entry

    # The intents worth reporting are the ones where a single seed would have
    # told the most misleading story.
    most_unstable = sorted(
        per_intent.items(),
        key=lambda kv: kv[1]["real_only"]["range"],
        reverse=True,
    )[:top_n]
    biggest_single_seed_swing = sorted(
        per_intent.items(),
        key=lambda kv: max(abs(v) for v in kv[1]["paired_delta"]["per_seed"]),
        reverse=True,
    )[:top_n]

    return {
        "schema_version": 1,
        "seeds": seeds,
        "intents_analysed": len(per_intent),
        "per_intent": per_intent,
        "most_unstable_baseline_intents": [name for name, _ in most_unstable],
        "largest_single_seed_swing_intents": [
            name for name, _ in biggest_single_seed_swing
        ],
        "note": (
            "Per-intent figures from one seed can differ from the three-seed "
            "mean by tens of points. Accuracy is computed per seed and then "
            "summarised; unparseable predictions count as wrong."
        ),
    }


def _iter(predictions: dict[str, dict[int, Any]]):
    for group, by_seed in predictions.items():
        for seed, rows in by_seed.items():
            yield group, seed, rows


def confusion_flow(
    predictions: dict[str, dict[int, Any]], *, gold: str, seeds: list[int]
) -> dict[str, Any]:
    """Where a gold intent's rows land under each group, per seed."""
    out: dict[str, Any] = {}
    for group in GROUPS:
        counts: dict[int, dict[str, int]] = {}
        for seed in seeds:
            rows = predictions[group][seed]
            counter = Counter(
                predicted or "<unparseable>"
                for g, predicted, _ in rows.values()
                if g == gold
            )
            counts[seed] = dict(counter.most_common(6))
        out[group] = counts
    return out


def render_markdown(report: dict[str, Any], flows: dict[str, Any]) -> str:
    seeds = report["seeds"]
    lines = [
        "# Per-intent movement is mostly seed variance",
        "",
        f"- Seeds: {', '.join(str(s) for s in seeds)}",
        f"- Intents analysed: {report['intents_analysed']}",
        "- Accuracy computed per seed, then summarised. Unparseable predictions",
        "  count as wrong.",
        "",
        "## The intents where one seed would mislead most",
        "",
        "Ranked by how far the 20-shot baseline swings between seeds.",
        "",
        "| Intent | n | real_only per seed | SD | real_syn_filtered per seed | SD |",
        "|---|---:|---|---:|---|---:|",
    ]
    for intent in report["most_unstable_baseline_intents"]:
        entry = report["per_intent"][intent]
        ro, fl = entry["real_only"], entry["real_syn_filtered"]
        lines.append(
            f"| `{intent}` | {entry['support']} | "
            + " / ".join(f"{v:.1f}%" for v in ro["per_seed"])
            + f" | {ro['sample_std']:.1f} | "
            + " / ".join(f"{v:.1f}%" for v in fl["per_seed"])
            + f" | {fl['sample_std']:.1f} |"
        )
    lines += [
        "",
        "## Paired delta per seed for those intents",
        "",
        "| Intent | per-seed Δ | mean Δ |",
        "|---|---|---:|",
    ]
    for intent in report["most_unstable_baseline_intents"]:
        delta = report["per_intent"][intent]["paired_delta"]
        lines.append(
            f"| `{intent}` | "
            + " / ".join(f"{v:+.1f}" for v in delta["per_seed"])
            + f" | {delta['mean']:+.1f} |"
        )
    lines += ["", "## Where the confused rows go", ""]
    for gold, flow in flows.items():
        lines.append(f"### gold `{gold}`")
        lines.append("")
        for group in GROUPS:
            lines.append(f"- `{group}`:")
            for seed, counts in flow[group].items():
                rendered = ", ".join(f"{k} {v}" for k, v in counts.items())
                lines.append(f"  - seed {seed}: {rendered}")
        lines.append("")
    lines += [report["note"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument(
        "--flow-intents",
        nargs="+",
        default=["general_quirky", "qa_factoid"],
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=REPO_ROOT / "reports" / "m17_intent_confusion.json",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=REPO_ROOT / "reports" / "m17_intent_confusion.md",
    )
    args = parser.parse_args()

    predictions: dict[str, dict[int, Any]] = {}
    sources: dict[str, str] = {}
    for group in GROUPS:
        predictions[group] = {}
        for seed in args.seeds:
            path = REPO_ROOT / "results" / "m9" / f"{group}_seed_{seed}.jsonl"
            if not path.is_file():
                print(f"missing predictions: {path}")
                return 1
            predictions[group][seed] = load_predictions(path)
            sources[f"{group}_seed_{seed}"] = str(path.relative_to(REPO_ROOT))

    report = analyse(predictions, seeds=args.seeds)
    report["prediction_sources"] = sources
    flows = {
        intent: confusion_flow(predictions, gold=intent, seeds=args.seeds)
        for intent in args.flow_intents
    }
    report["confusion_flows"] = flows

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_out.write_text(render_markdown(report, flows), encoding="utf-8")
    print(
        f"analysed {report['intents_analysed']} intents over seeds {args.seeds}; "
        f"most unstable baseline intent: {report['most_unstable_baseline_intents'][0]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
