
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.auth_routes import get_current_user
from client.quran_api_client import QuranApiClient
from config.factory.quran_config_factory import QuranConfigFactory
from constants.api_endpoints import ApiEndpoints
from exceptions.api_exception import ApiException
from utils.http_response import success_response
from utils.logger import Logger

router = APIRouter()
logger = Logger.get_logger(__name__)

config = QuranConfigFactory.create()
client = QuranApiClient(config)


@router.get(ApiEndpoints.HEALTH.value)
def health():
    return success_response({"status": "UP"})


# Protected routes - require JWT
@router.get(ApiEndpoints.CHAPTERS.value)
def get_chapters(language: str = "en", _: dict = Depends(get_current_user)):
    data = client.chapters.get_chapters(language)
    return success_response(data)


@router.get(ApiEndpoints.CHAPTER_BY_ID.value)
def get_chapter(chapter_id: int, language: str = "en", _: dict = Depends(get_current_user)):
    data = client.chapters.get_chapter(chapter_id, language)
    return success_response(data)


@router.get(ApiEndpoints.VERSE_BY_KEY.value)
def get_verse_by_key(
    verse_key: str,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    audio:int = 7,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_key(
        verse_key=verse_key,
        language=language,
        translations=translation_ids,
        words=words,
        audio=audio
    )
    return success_response(data)


@router.get(ApiEndpoints.VERSES_BY_CHAPTER.value)
def get_verses_by_chapter(
    chapter_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    _: dict = Depends(get_current_user),
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_chapter(
        chapter_id=chapter_id,
        language=language,
        translations=translation_ids,
        words=words,
        page=page,
        per_page=per_page,
    )
    return success_response(data)


@router.get(ApiEndpoints.VERSES_BY_JUZ.value)
def get_verses_by_juz(
    juz_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    _: dict = Depends(get_current_user),
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_juz(
        juz_id=juz_id,
        language=language,
        translations=translation_ids,
        words=words,
        page=page,
        per_page=per_page,
    )
    return success_response(data)


@router.get(ApiEndpoints.JUZS.value)
def get_juzs(language: str = "en", _: dict = Depends(get_current_user)):
    data = client.juzs.get_juzs(language)
    return success_response(data)


@router.get(ApiEndpoints.JUZ_BY_ID.value)
def get_juz(juz_id: int, language: str = "en", _: dict = Depends(get_current_user)):
    data = client.juzs.get_juz(juz_id, language)
    return success_response(data)


@router.get(ApiEndpoints.AUDIO_CHAPTER.value)
def get_chapter_audio(chapter_id: int, recitation_id: int, _: dict = Depends(get_current_user)):
    data = client.audio.get_chapter_recitation_audio(
        chapter_id=chapter_id, recitation_id=recitation_id
    )
    return success_response(data)


@router.get(ApiEndpoints.AUDIO_VERSE.value)
def get_verse_audio(
    verse_key: str, recitation_id: int, _: dict = Depends(get_current_user)
):
def get_verse_audio(recitation_id: int, verse_key: Optional[str] = None, chapter_number: Optional[int] = None, juz_number: Optional[int] = None):
    try:
        data = client.audio.get_verse_recitation_audio(
            recitation_id=recitation_id, verse_key=verse_key, chapter_number=chapter_number, juz_number=juz_number
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
