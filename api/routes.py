"""Quran API routes: chapters, verses, juzs, audio. Depends on injected client."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from client.quran_api_client import QuranApiClient
from config.factory.quran_config_factory import create_config
from constants.api_endpoints import ApiEndpoints
from exceptions.api_exception import ApiException
from utils.http_response import success_response
from utils.logger import Logger

router = APIRouter()
logger = Logger.get_logger(__name__)

_client: Optional[QuranApiClient] = None


def get_client() -> QuranApiClient:
    global _client
    if _client is None:
        _client = QuranApiClient(create_config())
    return _client


@router.get(ApiEndpoints.HEALTH.value)
def health():
    return success_response({"status": "UP"})


@router.get(ApiEndpoints.CHAPTERS.value)
def get_chapters(
    language: str = "en",
    client: QuranApiClient = Depends(get_client),
):
    try:
        data = client.chapters.get_chapters(language)
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.VERSES_BY_CHAPTER.value)
def get_verses_by_chapter(
    chapter_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    client: QuranApiClient = Depends(get_client),
):
    try:
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
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.VERSES_BY_JUZ.value)
def get_verses_by_juz(
    juz_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    client: QuranApiClient = Depends(get_client),
):
    try:
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
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.JUZS.value)
def get_juzs(
    language: str = "en",
    client: QuranApiClient = Depends(get_client),
):
    try:
        return success_response(client.juzs.get_juzs(language))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.AUDIO_CHAPTER.value)
def get_chapter_audio(
    chapter_id: int,
    recitation_id: int,
    client: QuranApiClient = Depends(get_client),
):
    try:
        data = client.audio.get_chapter_recitation_audio(
            chapter_id=chapter_id, recitation_id=recitation_id
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.AUDIO_VERSE.value)
def get_verse_audio(
    recitation_id: int,
    verse_key: Optional[str] = None,
    chapter_number: Optional[int] = None,
    juz_number: Optional[int] = None,
    client: QuranApiClient = Depends(get_client),
):
    try:
        data = client.audio.get_verse_recitation_audio(
            recitation_id=recitation_id,
            verse_key=verse_key,
            chapter_number=chapter_number,
            juz_number=juz_number,
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
