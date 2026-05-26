from __future__ import annotations

from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_quran_api_client
from app.services.quran.client import QuranApiClient
from app.utils.response import success_response

router = APIRouter(tags=["quran"])


def parse_translation_ids(raw: Optional[str]) -> Optional[list]:
    return list(map(int, raw.split(","))) if raw else None


@router.get("/chapters", summary="List all chapters")
def get_chapters(language: str = "en", client: QuranApiClient = Depends(get_quran_api_client)):
    return success_response(client.chapters.get_chapters(language))


@router.get("/verses/by-chapter/{chapter_id}", summary="Get verses by chapter")
def get_verses_by_chapter(chapter_id: int, language: str = "en", translations: Optional[str] = None,
                          words: bool = False, page: Optional[int] = None, per_page: Optional[int] = None,
                          client: QuranApiClient = Depends(get_quran_api_client), ):
    data = client.verses.by_chapter(
        chapter_id, language=language,
        translations=parse_translation_ids(translations),
        words=words, page=page, per_page=per_page,
    )
    return success_response(data)


@router.get("/verses/by-juz/{juz_id}", summary="Get verses by juz")
def get_verses_by_juz(juz_id: int, language: str = "en", translations: Optional[str] = None, words: bool = False,
                      page: Optional[int] = None, per_page: Optional[int] = None,
                      client: QuranApiClient = Depends(get_quran_api_client), ):
    data = client.verses.by_juz(
        juz_id, language=language,
        translations=parse_translation_ids(translations),
        words=words, page=page, per_page=per_page,
    )
    return success_response(data)


@router.get("/juzs", summary="List all juzs")
def get_juzs(language: str = "en", client: QuranApiClient = Depends(get_quran_api_client)):
    return success_response(client.juzs.get_juzs(language))


@router.get("/juzs/{juz_id}", summary="Get juz by ID")
def get_juzs_by_id(juz_id: int, language: str = "en", translations: Optional[str] = None, words: bool = False,
                   page: Optional[int] = None, per_page: Optional[int] = None,
                   client: QuranApiClient = Depends(get_quran_api_client), ):
    data = client.verses.by_juz(
        juz_id, language=language,
        translations=parse_translation_ids(translations),
        words=words, page=page, per_page=per_page,
    )
    return success_response(data)


@router.get("/audio/chapter", summary="Chapter recitation audio")
def get_chapter_audio(chapter_id: Optional[int] = Query(None), chapterId: Optional[int] = Query(None),
                      recitation_id: Optional[int] = Query(None), recitationId: Optional[int] = Query(None),
                      client: QuranApiClient = Depends(get_quran_api_client), ):
    cid = chapter_id if chapter_id is not None else chapterId
    rid = recitation_id if recitation_id is not None else recitationId
    if cid is None or rid is None:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            detail="chapter_id and recitation_id are required",
        )
    return success_response(client.audio.get_chapter_recitation_audio(cid, rid))


@router.get("/audio/verse", summary="Verse recitation audio")
def get_verse_audio(recitation_id: Optional[int] = Query(None), recitationId: Optional[int] = Query(None),
                    verse_key: Optional[str] = Query(None), verseKey: Optional[str] = Query(None),
                    chapter_number: Optional[int] = Query(None), chapterNumber: Optional[int] = Query(None),
                    juz_number: Optional[int] = Query(None), juzNumber: Optional[int] = Query(None),
                    client: QuranApiClient = Depends(get_quran_api_client), ):
    rid = recitation_id if recitation_id is not None else recitationId
    if rid is None:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            detail="recitation_id is required",
        )
    vk = verse_key if verse_key is not None else verseKey
    cn = chapter_number if chapter_number is not None else chapterNumber
    jn = juz_number if juz_number is not None else juzNumber
    return success_response(
        client.audio.get_verse_recitation_audio(rid, verse_key=vk, chapter_number=cn, juz_number=jn)
    )
