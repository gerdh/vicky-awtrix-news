#!/usr/bin/env python3

"""Deterministic offline headline translation for Vicky."""

from __future__ import annotations

import os
import re
from pathlib import Path

import ctranslate2
from transformers import MarianTokenizer


MODELS_DIR = Path(
    os.environ.get(
        "VICKY_TRANSLATION_MODELS",
        "/home/gerd/translation-models",
    )
)

MODEL_PATHS = {
    ("de", "fr"): MODELS_DIR / "opus-mt-de-fr",
    ("en", "fr"): MODELS_DIR / "opus-mt-en-fr",
    ("fr", "de"): MODELS_DIR / "opus-mt-fr-de",
    ("en", "de"): MODELS_DIR / "opus-mt-en-de",
    ("fr", "en"): MODELS_DIR / "opus-mt-fr-en",
    ("de", "en"): MODELS_DIR / "opus-mt-de-en",
}

_RUNTIMES = {}


def _runtime(source_language: str, target_language: str):
    key = (
        str(source_language).lower().strip(),
        str(target_language).lower().strip(),
    )

    if key in _RUNTIMES:
        return _RUNTIMES[key]

    model_path = MODEL_PATHS[key]
    if not model_path.is_dir():
        raise FileNotFoundError(
            f"translation model not found: {model_path}"
        )

    tokenizer = MarianTokenizer.from_pretrained(
        str(model_path),
        local_files_only=True,
    )
    translator = ctranslate2.Translator(
        str(model_path),
        device="cpu",
        compute_type="int8",
        inter_threads=1,
        intra_threads=2,
    )

    _RUNTIMES[key] = (tokenizer, translator)
    return tokenizer, translator

def _unsafe_translation(source: str, translated: str) -> bool:
    if not translated:
        return True

    if len(translated) > max(320, len(source) * 3):
        return True

    words = re.findall(r"\w+", translated.lower(), flags=re.UNICODE)
    if len(words) >= 9:
        trigrams = list(zip(words, words[1:], words[2:]))
        if len(set(trigrams)) < len(trigrams) * 0.65:
            return True

    return False


def translate_title(
    text: str,
    language: str,
    target_language: str = "fr",
) -> str:
    """Translate one headline or return the untouched original."""
    source_text = " ".join(str(text).split())
    source_language = str(language).lower().strip()
    target_language = str(target_language).lower().strip()

    if not source_text:
        return source_text

    if source_language == target_language:
        return source_text

    key = (source_language, target_language)
    if key not in MODEL_PATHS:
        return source_text

    try:
        tokenizer, translator = _runtime(
            source_language,
            target_language,
        )
        source_tokens = tokenizer.convert_ids_to_tokens(
            tokenizer.encode(source_text)
        )
        result = translator.translate_batch(
            [source_tokens],
            beam_size=4,
            max_decoding_length=min(
                192,
                max(64, len(source_tokens) * 5),
            ),
            repetition_penalty=1.2,
        )
        target_tokens = result[0].hypotheses[0]
        target_ids = tokenizer.convert_tokens_to_ids(
            target_tokens
        )
        translated = tokenizer.decode(
            target_ids,
            skip_special_tokens=True,
        )
        translated = " ".join(translated.split())
    except Exception:
        return source_text

    if _unsafe_translation(source_text, translated):
        return source_text

    return translated

