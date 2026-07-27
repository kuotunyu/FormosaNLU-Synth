"""Local Marian zh→en→zh backtranslation for the standard-augmentation group."""

from __future__ import annotations

from pathlib import Path

from opencc import OpenCC


class MarianRoundTrip:
    """Load two pinned local Marian models and translate deterministically."""

    def __init__(
        self,
        *,
        zh_en_path: Path,
        en_zh_path: Path,
        device: str,
        batch_size: int,
        max_length: int,
    ) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested for backtranslation but is unavailable")
        self._device = torch.device(device)
        self._batch_size = batch_size
        self._max_length = max_length
        self._zh_en_tokenizer = AutoTokenizer.from_pretrained(
            zh_en_path,
            local_files_only=True,
        )
        self._zh_en_model = AutoModelForSeq2SeqLM.from_pretrained(
            zh_en_path,
            local_files_only=True,
        ).to(self._device)
        self._en_zh_tokenizer = AutoTokenizer.from_pretrained(
            en_zh_path,
            local_files_only=True,
        )
        self._en_zh_model = AutoModelForSeq2SeqLM.from_pretrained(
            en_zh_path,
            local_files_only=True,
        ).to(self._device)
        self._zh_en_model.eval()
        self._en_zh_model.eval()
        self._to_traditional = OpenCC("s2twp")

    def _translate(self, texts: list[str], tokenizer: object, model: object) -> list[str]:
        import torch

        outputs: list[str] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            encoded = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self._max_length,
            ).to(self._device)
            with torch.inference_mode():
                generated = model.generate(
                    **encoded,
                    do_sample=False,
                    max_length=self._max_length,
                    renormalize_logits=True,
                )
            outputs.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
        return outputs

    def translate(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        english = self._translate(texts, self._zh_en_tokenizer, self._zh_en_model)
        chinese = self._translate(english, self._en_zh_tokenizer, self._en_zh_model)
        return [self._to_traditional.convert(text) for text in chinese]
