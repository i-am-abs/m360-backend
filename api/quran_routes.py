from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_quran_api_client
from client.quran_api_client import QuranApiClient
from constants.api_endpoints import ApiEndpoints
from exceptions.api_exception import ApiException
from utils.http_response import success_response

quran_router = APIRouter()


def _verses_by_juz_payload(
    client: QuranApiClient,
    juz_id: int,
    language: str,
    translations: Optional[str],
    words: bool,
    page: Optional[int],
    per_page: Optional[int],
):
    translation_ids = (
        list(map(int, translations.split(","))) if translations else None
    )
    return client.verses.by_juz(
        juz_id=juz_id,
        language=language,
        translations=translation_ids,
        words=words,
        page=page,
        per_page=per_page,
    )


@quran_router.get(ApiEndpoints.HEALTH.value)
def health():
    return success_response({"status": "UP"})


@quran_router.get(ApiEndpoints.CHAPTERS.value)
def get_chapters(
    language: str = "en",
    client: QuranApiClient = Depends(get_quran_api_client),
):
    try:
        data = client.chapters.get_chapters(language)
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@quran_router.get(ApiEndpoints.VERSES_BY_CHAPTER.value)
def get_verses_by_chapter(
    chapter_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    client: QuranApiClient = Depends(get_quran_api_client),
):
    try:
        translation_ids = (
            list(map(int, translations.split(","))) if translations else None
        )
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


@quran_router.get(ApiEndpoints.VERSES_BY_JUZ.value)
def get_verses_by_juz(
    juz_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    client: QuranApiClient = Depends(get_quran_api_client),
):
    try:
        data = _verses_by_juz_payload(
            client, juz_id, language, translations, words, page, per_page
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@quran_router.get(ApiEndpoints.JUZS.value)
def get_juzs(
    language: str = "en",
    client: QuranApiClient = Depends(get_quran_api_client),
):
    try:
        return success_response(client.juzs.get_juzs(language))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@quran_router.get(ApiEndpoints.JUZS_BY_ID.value)
def get_juzs_by_id(
    juz_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    client: QuranApiClient = Depends(get_quran_api_client),
):
    """Same payload as GET /verses/by-juz/{juz_id} (friendly alias)."""
    try:
        data = _verses_by_juz_payload(
            client, juz_id, language, translations, words, page, per_page
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@quran_router.get(ApiEndpoints.AUDIO_CHAPTER.value)
def get_chapter_audio(
    chapter_id: Optional[int] = Query(None),
    chapterId: Optional[int] = Query(None),
    recitation_id: Optional[int] = Query(None),
    recitationId: Optional[int] = Query(None),
    client: QuranApiClient = Depends(get_quran_api_client),
):
    cid = chapter_id if chapter_id is not None else chapterId
    rid = recitation_id if recitation_id is not None else recitationId
    if cid is None or rid is None:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            detail="chapter_id (or chapterId) and recitation_id (or recitationId) are required",
        )
    try:
        data = client.audio.get_chapter_recitation_audio(
            chapter_id=cid, recitation_id=rid
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@quran_router.get(ApiEndpoints.AUDIO_VERSE.value)
def get_verse_audio(
    recitation_id: Optional[int] = Query(None),
    recitationId: Optional[int] = Query(None),
    verse_key: Optional[str] = Query(None),
    verseKey: Optional[str] = Query(None),
    chapter_number: Optional[int] = Query(None),
    chapterNumber: Optional[int] = Query(None),
    juz_number: Optional[int] = Query(None),
    juzNumber: Optional[int] = Query(None),
    client: QuranApiClient = Depends(get_quran_api_client),
):
    rid = recitation_id if recitation_id is not None else recitationId
    if rid is None:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            detail="recitation_id or recitationId is required",
        )
    vk = verse_key if verse_key is not None else verseKey
    cn = chapter_number if chapter_number is not None else chapterNumber
    jn = juz_number if juz_number is not None else juzNumber
    try:
        data = client.audio.get_verse_recitation_audio(
            recitation_id=rid,
            verse_key=vk,
            chapter_number=cn,
            juz_number=jn,
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
