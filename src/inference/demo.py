"""Lazy single-model inference runtime and Gradio UI for the M11 demo."""

from __future__ import annotations

import json
import os
import time
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from src.evaluation.parse import parse_prediction
from src.training.model import load_quantized_text_model
from src.training.prompt_template import build_prompt_messages

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "train.yaml"
DEFAULT_ADAPTER = REPO_ROOT / "runs" / "real_syn_filtered" / "seed_42" / "adapter"

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

:root {
  --ink: #071218;
  --panel: rgba(10, 29, 38, 0.88);
  --panel-strong: rgba(8, 23, 30, 0.98);
  --line: rgba(126, 217, 226, 0.22);
  --cyan: #7ed9e2;
  --amber: #ffb84d;
  --coral: #ff6b4a;
  --paper: #eaf6f5;
  --muted: #8ba8ac;
}

html, body { background: var(--ink) !important; }
.gradio-container {
  min-height: 100vh !important;
  max-width: none !important;
  font-family: "Noto Sans TC", sans-serif !important;
  color: var(--paper) !important;
  background:
    linear-gradient(rgba(126, 217, 226, .035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(126, 217, 226, .035) 1px, transparent 1px),
    radial-gradient(circle at 78% 12%, rgba(255, 107, 74, .16), transparent 28rem),
    radial-gradient(circle at 14% 30%, rgba(126, 217, 226, .12), transparent 30rem),
    var(--ink) !important;
  background-size: 32px 32px, 32px 32px, auto, auto, auto !important;
}

.formosa-shell { max-width: 1380px; margin: 0 auto; padding: 24px 18px 48px; }
.hero {
  position: relative;
  overflow: hidden;
  padding: 34px 36px 30px;
  border: 1px solid var(--line);
  background: linear-gradient(115deg, rgba(11, 34, 43, .96), rgba(7, 18, 24, .84));
  box-shadow: 0 24px 80px rgba(0, 0, 0, .28);
}
.hero::after {
  content: "FORMOSA / NLU";
  position: absolute;
  right: -8px;
  bottom: -25px;
  color: rgba(126, 217, 226, .055);
  font: 900 76px/1 "IBM Plex Mono", monospace;
  letter-spacing: -.08em;
}
.eyebrow, .metric-kicker {
  color: var(--amber);
  font: 600 11px/1.4 "IBM Plex Mono", monospace;
  letter-spacing: .18em;
  text-transform: uppercase;
}
.hero h1 {
  margin: 9px 0 7px;
  color: var(--paper);
  font-size: clamp(34px, 6vw, 68px);
  letter-spacing: -.055em;
}
.hero p { max-width: 760px; margin: 0; color: #b8ced0; font-size: 15px; line-height: 1.8; }
.signal-row { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 22px; }
.signal {
  padding: 7px 10px;
  border: 1px solid var(--line);
  color: #cce4e5;
  background: rgba(126, 217, 226, .055);
  font: 500 11px/1 "IBM Plex Mono", monospace;
}
.signal.hot { border-color: rgba(255, 184, 77, .45); color: var(--amber); }

.input-deck, .model-card {
  border: 1px solid var(--line) !important;
  background: var(--panel) !important;
  box-shadow: 0 18px 42px rgba(0, 0, 0, .18);
}
.input-deck { padding: 20px !important; margin-top: 16px; }
.model-card { padding: 18px !important; min-height: 435px; }
.model-card.base { border-top: 3px solid var(--muted) !important; }
.model-card.tuned { border-top: 3px solid var(--coral) !important; }
.model-label {
  margin-bottom: 8px;
  color: #b8ced0;
  font: 600 12px/1.3 "IBM Plex Mono", monospace;
  letter-spacing: .12em;
}
.model-label span { color: var(--muted); }
.model-label strong { color: var(--coral); }

button.primary {
  border: 0 !important;
  color: #071218 !important;
  background: var(--amber) !important;
  font-weight: 900 !important;
  letter-spacing: .04em;
  box-shadow: 0 8px 24px rgba(255, 184, 77, .18);
}
button.primary:hover { transform: translateY(-1px); filter: brightness(1.06); }
.example-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 3px; }
.example-list span {
  padding: 7px 9px;
  border: 1px solid var(--line);
  color: #a9c3c6;
  background: rgba(126, 217, 226, .035);
  font-size: 12px;
}

.mono textarea, .mono input, .mono .json-holder {
  font-family: "IBM Plex Mono", monospace !important;
}
.footer-note {
  margin-top: 18px;
  color: var(--muted);
  font: 400 11px/1.7 "IBM Plex Mono", monospace;
}
"""


@dataclass(frozen=True)
class Prediction:
    """UI-safe representation of one unconstrained generation."""

    raw: str
    intent: str
    slots: list[dict[str, str]]
    valid: bool
    error: str | None
    latency_ms: float


class ComparisonRuntime(Protocol):
    """Minimum runtime contract used by the UI and tests."""

    def predict(self, utterance: str, *, adapted: bool) -> Prediction: ...


def _prediction(raw: str, elapsed: float) -> Prediction:
    parsed, error = parse_prediction(raw)
    if parsed is None:
        return Prediction(
            raw=raw,
            intent="INVALID",
            slots=[],
            valid=False,
            error=error,
            latency_ms=elapsed * 1000,
        )
    return Prediction(
        raw=raw,
        intent=parsed.intent,
        slots=[slot.model_dump() for slot in parsed.slots],
        valid=True,
        error=None,
        latency_ms=elapsed * 1000,
    )


class GemmaComparisonRuntime:
    """Load one quantized PeftModel and toggle LoRA for before/after inference."""

    def __init__(
        self,
        *,
        config_path: Path = DEFAULT_CONFIG,
        adapter_dir: Path = DEFAULT_ADAPTER,
    ) -> None:
        self.config_path = config_path
        self.adapter_dir = adapter_dir
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._max_new_tokens = 128

    def _load(self) -> None:
        if self._model is not None:
            return
        if not self.adapter_dir.is_dir():
            raise FileNotFoundError(f"Adapter not found: {self.adapter_dir}")

        import torch
        from peft import PeftModel
        from transformers import AutoTokenizer, BitsAndBytesConfig

        config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        model_path = REPO_ROOT / config["model"]["local_path"]
        quant = config["quantization"]
        self._max_new_tokens = int(config["inference"]["max_new_tokens"])
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._tokenizer.padding_side = "left"
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=quant["load_in_4bit"],
            bnb_4bit_quant_type=quant["quant_type"],
            bnb_4bit_use_double_quant=quant["double_quant"],
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        base = load_quantized_text_model(
            model_path,
            quantization_config=quantization_config,
            dtype=torch.bfloat16,
        )
        self._model = PeftModel.from_pretrained(base, self.adapter_dir)
        self._model.eval()

    def predict(self, utterance: str, *, adapted: bool) -> Prediction:
        self._load()
        assert self._tokenizer is not None
        assert self._model is not None

        import torch

        messages = build_prompt_messages(utterance, zero_shot=not adapted)
        inputs = self._tokenizer.apply_chat_template(
            [messages],
            tokenize=True,
            padding=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)
        input_length = inputs["input_ids"].shape[-1]
        adapter_context = nullcontext() if adapted else self._model.disable_adapter()
        started = time.perf_counter()
        with adapter_context, torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                do_sample=False,
            )[0]
        elapsed = time.perf_counter() - started
        raw = self._tokenizer.decode(output[input_length:], skip_special_tokens=True)
        return _prediction(raw, elapsed)


class MockComparisonRuntime:
    """Deterministic model-free runtime for UI validation and screenshots."""

    def predict(self, utterance: str, *, adapted: bool) -> Prediction:
        normalized = utterance.strip()
        if "搜尋" in normalized and "歌" in normalized:
            intent = "music_query"
            slots = [{"type": "artist_name", "value": "周杰倫"}]
        elif "周杰倫" in normalized:
            intent = "play_music"
            slots = [{"type": "artist_name", "value": "周杰倫"}]
        elif "起床" in normalized or "七點" in normalized:
            intent = "alarm_set"
            slots = [{"type": "time", "value": "明天早上七點"}]
        elif "雨" in normalized:
            intent = "weather_query"
            slots = [
                {"type": "place_name", "value": "台北"},
                {"type": "date", "value": "明天"},
            ]
        else:
            intent = "email_sendemail"
            slots = [{"type": "person", "value": "小美"}]

        if not adapted and "搜尋" in normalized:
            intent = "play_music"
        raw = json.dumps({"intent": intent, "slots": slots}, ensure_ascii=False)
        return _prediction(raw, 0.031 if adapted else 0.044)


_RUNTIME: ComparisonRuntime | None = None


def get_runtime(*, mock: bool | None = None) -> ComparisonRuntime:
    """Return a process-wide lazy runtime; model weights load on first click."""
    global _RUNTIME
    if _RUNTIME is None:
        use_mock = (
            os.getenv("FORMOSANLU_DEMO_MOCK", "").lower() in {"1", "true", "yes"}
            if mock is None
            else mock
        )
        _RUNTIME = MockComparisonRuntime() if use_mock else GemmaComparisonRuntime()
    return _RUNTIME


def compare_utterance(
    utterance: str,
    *,
    runtime: ComparisonRuntime | None = None,
) -> tuple[str, list[list[str]], str, str, list[list[str]], str]:
    """Run base and adapted inference sequentially for a single utterance."""
    cleaned = utterance.strip()
    if not cleaned:
        raise ValueError("請輸入一句繁體中文語句。")
    engine = runtime or get_runtime()
    base = engine.predict(cleaned, adapted=False)
    tuned = engine.predict(cleaned, adapted=True)

    def status(prediction: Prediction) -> str:
        validity = "VALID JSON" if prediction.valid else "INVALID"
        detail = prediction.intent if prediction.valid else prediction.error or "parse error"
        return f"{validity} · {detail} · {prediction.latency_ms:.0f} ms"

    def slot_rows(prediction: Prediction) -> list[list[str]]:
        rows = [[slot["type"], slot["value"]] for slot in prediction.slots]
        return rows or [["—", "—"]]

    return (
        status(base),
        slot_rows(base),
        base.raw,
        status(tuned),
        slot_rows(tuned),
        tuned.raw,
    )


def build_demo(*, mock: bool | None = None) -> Any:
    """Build the Gradio Blocks app without launching it."""
    import gradio as gr

    runtime = get_runtime(mock=mock)
    theme = gr.themes.Base(
        primary_hue="orange",
        secondary_hue="cyan",
        neutral_hue="slate",
        spacing_size="md",
        radius_size="none",
        text_size="md",
    ).set(
        body_background_fill="#071218",
        body_background_fill_dark="#071218",
    )
    with gr.Blocks(title="FormosaNLU Signal Lab") as demo:
        with gr.Column(elem_classes=["formosa-shell"]):
            gr.HTML(
                """
                <section class="hero">
                  <div class="eyebrow">LOCAL · ZERO API · RTX 4090</div>
                  <h1>FormosaNLU Signal Lab</h1>
                  <p>同一句台灣華語，並排觀察 Gemma 4 微調前後的 intent、
                  slot 與原始 JSON。所有生成皆為 unconstrained decoding，
                  JSON 合法率本身就是被測量的結果。</p>
                  <div class="signal-row">
                    <span class="signal hot">FILTERED SYNTHETIC · 3,760</span>
                    <span class="signal">INTENT ACC · 76.19%</span>
                    <span class="signal">SLOT F1 · 66.54%</span>
                    <span class="signal">EXACT · 52.12%</span>
                  </div>
                </section>
                """
            )
            with gr.Column(elem_classes=["input-deck"]):
                utterance = gr.Textbox(
                    value="搜尋周杰倫的歌",
                    label="輸入語句 / UTTERANCE",
                    placeholder="例如：台北明天會不會下雨",
                    lines=2,
                    elem_classes=["mono"],
                )
                run_button = gr.Button("分析訊號 →", variant="primary")
                gr.HTML(
                    """
                    <div class="metric-kicker">SUGGESTED SIGNALS</div>
                    <div class="example-list">
                      <span>播放周杰倫</span><span>搜尋周杰倫的歌</span>
                      <span>明天早上七點叫我起床</span>
                      <span>台北明天會不會下雨</span>
                      <span>幫我寄信給小美說會晚到</span>
                    </div>
                    """
                )

            with gr.Row(equal_height=True):
                with gr.Column(elem_classes=["model-card", "base"]):
                    gr.HTML(
                        '<div class="model-label"><span>01 / BASE</span> '
                        "Gemma 4 zero-shot</div>"
                    )
                    base_status = gr.Textbox(
                        label="解析狀態 / INTENT / LATENCY",
                        interactive=False,
                        elem_classes=["mono"],
                    )
                    base_slots = gr.Dataframe(
                        value=[["—", "—"]],
                        headers=["slot type", "literal value"],
                        datatype=["str", "str"],
                        interactive=False,
                        label="Slots",
                    )
                    base_raw = gr.Code(
                        label="Raw JSON",
                        language="json",
                        interactive=False,
                        elem_classes=["mono"],
                    )

                with gr.Column(elem_classes=["model-card", "tuned"]):
                    gr.HTML(
                        '<div class="model-label"><strong>02 / ADAPTED</strong> '
                        "filtered synthetic LoRA</div>"
                    )
                    tuned_status = gr.Textbox(
                        label="解析狀態 / INTENT / LATENCY",
                        interactive=False,
                        elem_classes=["mono"],
                    )
                    tuned_slots = gr.Dataframe(
                        value=[["—", "—"]],
                        headers=["slot type", "literal value"],
                        datatype=["str", "str"],
                        interactive=False,
                        label="Slots",
                    )
                    tuned_raw = gr.Code(
                        label="Raw JSON",
                        language="json",
                        interactive=False,
                        elem_classes=["mono"],
                    )

            gr.HTML(
                """
                <div class="footer-note">MODEL google/gemma-4-E4B-it · NF4 QLoRA ·
                ADAPTER real_syn_filtered / seed 42 / best step 250 ·
                PROMPT formosanlu_nlu.v1</div>
                """
            )

        run_button.click(
            fn=lambda text: compare_utterance(text, runtime=runtime),
            inputs=utterance,
            outputs=[
                base_status,
                base_slots,
                base_raw,
                tuned_status,
                tuned_slots,
                tuned_raw,
            ],
            api_name="compare",
        )
    demo.formosa_theme = theme
    demo.formosa_css = CUSTOM_CSS
    return demo
