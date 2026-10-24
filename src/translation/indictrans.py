from __future__ import annotations

import logging
from typing import Any

from .languages import get_translation_language_code

LOGGER = logging.getLogger(__name__)


class TranslationUnavailableError(RuntimeError):
    """Raised when optional IndicTrans2 components or models are unavailable."""


class IndicTranslator:
    """Lazy, reusable IndicTrans2 translator with batching and CPU fallback."""

    def __init__(self, en_to_indic: str, indic_to_en: str, device: str | None = None) -> None:
        self.en_to_indic = en_to_indic
        self.indic_to_en = indic_to_en
        self.requested_device = device
        self._models: dict[str, tuple[Any, Any, str]] = {}
        self._processor: Any | None = None
        self.load_counts = {"to_en": 0, "from_en": 0}

    def _get_processor(self) -> Any:
        if self._processor is None:
            try:
                from IndicTransToolkit import IndicProcessor
                self._processor = IndicProcessor(inference=True)
            except (ImportError, OSError) as error:
                raise TranslationUnavailableError(
                    "IndicTransToolkit is unavailable. Use the documented WSL translation environment."
                ) from error
        return self._processor

    def _load(self, direction: str) -> tuple[Any, Any, str]:
        if direction in self._models:
            return self._models[direction]
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as error:
            raise TranslationUnavailableError("Install torch and transformers>=4.51,<5") from error
        model_name = self.indic_to_en if direction == "to_en" else self.en_to_indic
        device = self.requested_device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name, trust_remote_code=True, torch_dtype=dtype
            ).to(device).eval()
        except ImportError as error:
            raise TranslationUnavailableError(
                f"IndicTrans2 tokenizer dependency is missing: {error}"
            ) from error
        except Exception as error:
            raise TranslationUnavailableError(
                f"Could not load gated IndicTrans2 model {model_name}. "
                "Confirm Hugging Face access and run `hf auth login` in WSL."
            ) from error
        self._models[direction] = tokenizer, model, device
        self.load_counts[direction] += 1
        LOGGER.info("Loaded %s on %s", model_name, device)
        return self._models[direction]

    @property
    def loaded_devices(self) -> dict[str, str]:
        return {direction: bundle[2] for direction, bundle in self._models.items()}

    def translate_batch(self, texts: list[str], source_language: str, target_language: str,
                        batch_size: int = 16, max_length: int = 256) -> list[str]:
        if source_language == target_language:
            return list(texts)
        if not texts:
            return []
        direction = "to_en" if target_language == "en" else "from_en"
        if direction == "to_en" and source_language == "en":
            raise ValueError("Indic-to-English translation requires an Indic source language")
        if direction == "from_en" and source_language != "en":
            raise ValueError("English-to-Indic translation requires English as source")
        source_code = get_translation_language_code(source_language)
        target_code = get_translation_language_code(target_language)
        processor = self._get_processor()
        tokenizer, model, device = self._load(direction)
        import torch

        outputs: list[str] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            processed = processor.preprocess_batch(batch, src_lang=source_code, tgt_lang=target_code)
            encoded = tokenizer(processed, padding=True, truncation=True, max_length=max_length,
                                return_tensors="pt").to(device)
            with torch.inference_mode():
                generated = model.generate(**encoded, max_length=max_length, num_beams=5, num_return_sequences=1)
            decoded = tokenizer.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=True)
            outputs.extend(processor.postprocess_batch(decoded, lang=target_code))
        return outputs

    def translate_to_english(self, text: str, source_language: str) -> str:
        return self.translate_batch([text], source_language, "en")[0]

    def translate_from_english(self, text: str, target_language: str) -> str:
        return self.translate_batch([text], "en", target_language)[0]

    def unload(self, direction: str | None = None) -> None:
        """Release one or both cached models, useful for memory-constrained batch jobs."""
        directions = [direction] if direction else list(self._models)
        for key in directions:
            self._models.pop(key, None)
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
