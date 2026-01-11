from functools import lru_cache
from typing import Optional

from deep_translator import GoogleTranslator

from utils.logger import Logger

logger = Logger.get_logger(__name__)

LANG_CODE_TO_NAME = {
    "en": "english",
    "hi": "hindi",
    "ar": "arabic",
    "ur": "urdu",
    "bn": "bengali",
    "mr": "marathi",
    "ta": "tamil",
    "te": "telugu",
    "gu": "gujarati",
    "pa": "punjabi",
    "fa": "persian",
    "fr": "french",
    "de": "german",
    "id": "indonesian",
}


def _to_google_lang(lang: Optional[str]) -> Optional[str]:
    if not lang:
        return None
    lang = lang.strip().lower()
    return LANG_CODE_TO_NAME.get(lang, lang)


@lru_cache(maxsize=256)
def _get_translator(source: Optional[str], target: Optional[str]) -> GoogleTranslator:
    src = _to_google_lang(source) or "auto"
    tgt = _to_google_lang(target) or "english"
    return GoogleTranslator(source=src, target=tgt)


def translate_text(text: Optional[str], target_language: Optional[str], source_language: Optional[str] = None) -> Optional[str]:
    if not text or not target_language:
        return text
    try:
        translator = _get_translator(source_language, target_language)
        return translator.translate(text)
    except Exception as e:
        logger.error(f"Error translating text: {text}, {e}")
        return text
