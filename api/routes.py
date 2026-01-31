import uuid
from typing import Optional
from fastapi import APIRouter, Body, HTTPException

from client.quran_api_client import QuranApiClient
from config.factory.quran_config_factory import QuranConfigFactory
from constants.api_endpoints import ApiEndpoints
from db.factory.device_repository_factory import DeviceRepositoryFactory
from dto.models import DeviceRegisterRequest
from exceptions.api_exception import ApiException
from utils.logger import Logger
from utils.http_response import success_response

router = APIRouter()
logger = Logger.get_logger(__name__)

config = QuranConfigFactory.create()

client = QuranApiClient(config)
device_repository = DeviceRepositoryFactory.create()


@router.get(ApiEndpoints.HEALTH.value)
def health():
    return success_response({"status": "UP"})


@router.post(ApiEndpoints.DEVICE_REGISTER.value)
def register_device(request: Optional[DeviceRegisterRequest] = Body(default=None)):
    device_uuid = request.uuid if request and request.uuid else str(uuid.uuid4())
    result = device_repository.save_device(device_uuid)
    if result:
        return success_response({**result}, message="Device registered")
    raise HTTPException(status_code=500, detail="Failed to register device")


@router.get(ApiEndpoints.DEVICES.value)
def get_all_devices():
    devices = device_repository.get_all_devices()
    return success_response({"count": len(devices), "devices": devices})


@router.get(ApiEndpoints.DEVICE_BY_UUID.value)
def get_device(device_uuid: str):
    device = device_repository.get_device_by_uuid(device_uuid)
    if device:
        return success_response(device)
    raise HTTPException(status_code=404, detail="Device not found")


@router.delete(ApiEndpoints.DEVICE_BY_UUID.value)
def delete_device(device_uuid: str):
    success = device_repository.delete_device(device_uuid)
    if success:
        return success_response({"uuid": device_uuid}, message="Device deleted")
    raise HTTPException(
        status_code=404, detail="Device not found or could not be deleted"
    )


@router.get(ApiEndpoints.CHAPTERS.value)
def get_chapters(language: str = "en"):
    data = client.chapters.get_chapters(language)
    return success_response(data)


@router.get(ApiEndpoints.CHAPTER_BY_ID.value)
def get_chapter(chapter_id: int, language: str = "en"):
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


@router.get(ApiEndpoints.VERSES_BY_PAGE.value)
def get_verses_by_page(
    page_number: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_page(
        page_number=page_number,
        language=language,
        translations=translation_ids,
        words=words,
    )
    return success_response(data)


@router.get(ApiEndpoints.VERSES_BY_HIZB.value)
def get_verses_by_hizb(
    hizb_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_hizb(
        hizb_id=hizb_id, language=language, translations=translation_ids, words=words
    )
    return success_response(data)


@router.get(ApiEndpoints.VERSES_BY_RUKU.value)
def get_verses_by_ruku(
    ruku_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_ruku(
        ruku_id=ruku_id, language=language, translations=translation_ids, words=words
    )
    return success_response(data)


@router.get(ApiEndpoints.VERSES_BY_MANZIL.value)
def get_verses_by_manzil(
    manzil_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_manzil(
        manzil_id=manzil_id,
        language=language,
        translations=translation_ids,
        words=words,
    )
    return success_response(data)


@router.get(ApiEndpoints.VERSES_BY_RUB_EL_HIZB.value)
def get_verses_by_rub_el_hizb(
    rub_el_hizb_id: int,
    language: str = "en",
    translations: Optional[str] = None,
    words: bool = False,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    data = client.verses.by_rub_el_hizb(
        rub_el_hizb_id=rub_el_hizb_id,
        language=language,
        translations=translation_ids,
        words=words,
    )
    return success_response(data)


@router.get(ApiEndpoints.JUZS.value)
def get_juzs(language: str = "en"):
    return success_response(client.juzs.get_juzs(language))


@router.get(ApiEndpoints.JUZ_BY_ID.value)
def get_juz(juz_id: int, language: str = "en"):
    return success_response(client.juzs.get_juz(juz_id, language))


@router.get(ApiEndpoints.HIZBS.value)
def get_hizbs(language: str = "en"):
    return success_response(client.hizbs.get_hizbs(language))


@router.get(ApiEndpoints.HIZB_BY_ID.value)
def get_hizb(hizb_id: int, language: str = "en"):
    return success_response(client.hizbs.get_hizb(hizb_id, language))


@router.get(ApiEndpoints.RUKUS.value)
def get_rukus(language: str = "en"):
    return success_response(client.rukus.get_rukus(language))


@router.get(ApiEndpoints.RUKU_BY_ID.value)
def get_ruku(ruku_id: int, language: str = "en"):
    return success_response(client.rukus.get_ruku(ruku_id, language))


@router.get(ApiEndpoints.MANZILS.value)
def get_manzils(language: str = "en"):
    return success_response(client.manzils.get_manzils(language))


@router.get(ApiEndpoints.MANZIL_BY_ID.value)
def get_manzil(manzil_id: int, language: str = "en"):
    return success_response(client.manzils.get_manzil(manzil_id, language))


@router.get(ApiEndpoints.RUB_EL_HIZBS.value)
def get_rub_el_hizbs(language: str = "en"):
    return success_response(client.rub_el_hizbs.get_rub_el_hizbs(language))


@router.get(ApiEndpoints.RUB_EL_HIZB_BY_ID.value)
def get_rub_el_hizb(rub_el_hizb_id: int, language: str = "en"):
    return success_response(
        client.rub_el_hizbs.get_rub_el_hizb(rub_el_hizb_id, language)
    )


@router.get(ApiEndpoints.AUDIO_CHAPTER.value)
def get_chapter_audio(chapter_id: int, recitation_id: int):
    data = client.audio.get_chapter_recitation_audio(
        chapter_id=chapter_id, recitation_id=recitation_id
    )
    return success_response(data)


@router.get(ApiEndpoints.AUDIO_VERSE.value)
def get_verse_audio(recitation_id: int, verse_key: Optional[str] = None, chapter_number: Optional[int] = None, juz_number: Optional[int] = None):
    try:
        data = client.audio.get_verse_recitation_audio(
            recitation_id=recitation_id, verse_key=verse_key, chapter_number=chapter_number, juz_number=juz_number
        )
        return success_response(data)
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.RECITATIONS.value)
def get_recitations(language: Optional[str] = None):
    return success_response(client.audio.get_recitations(language))


@router.get(ApiEndpoints.RECITATION_BY_ID.value)
def get_recitation(recitation_id: int):
    try:
        return success_response(client.audio.get_recitation(recitation_id))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.TRANSLATIONS.value)
def get_translations(language: Optional[str] = None):
    return success_response(client.translations.get_translations(language))


@router.get(ApiEndpoints.TRANSLATION_BY_ID.value)
def get_translation(translation_id: int):
    try:
        return success_response(client.translations.get_translation(translation_id))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.CHAPTER_TRANSLATION.value)
def get_chapter_translation(translation_id: int, chapter_id: int, language: str = "en"):
    try:
        return success_response(
            client.translations.get_chapter_translation(
                chapter_id=chapter_id, translation_id=translation_id, language=language
            )
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.VERSE_TRANSLATION.value)
def get_verse_translation(translation_id: int, verse_key: str, language: str = "en"):
    try:
        return success_response(
            client.translations.get_verse_translation(
                verse_key=verse_key, translation_id=translation_id, language=language
            )
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.TAFSIRS.value)
def get_tafsirs(language: Optional[str] = None):
    return success_response(client.tafsirs.get_tafsirs(language))


@router.get(ApiEndpoints.TAFSIR_BY_ID.value)
def get_tafsir(tafsir_id: int):
    try:
        return success_response(client.tafsirs.get_tafsir(tafsir_id))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.CHAPTER_TAFSIR.value)
def get_chapter_tafsir(tafsir_id: int, chapter_id: int, language: str = "en"):
    try:
        return success_response(
            client.tafsirs.get_chapter_tafsir(
                chapter_id=chapter_id, tafsir_id=tafsir_id, language=language
            )
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.VERSE_TAFSIR.value)
def get_verse_tafsir(tafsir_id: int, verse_key: str, language: str = "en"):
    try:
        return success_response(
            client.tafsirs.get_verse_tafsir(
                verse_key=verse_key, tafsir_id=tafsir_id, language=language
            )
        )
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.RESOURCE_TRANSLATIONS.value)
def get_resource_translations(language: Optional[str] = None):
    return success_response(client.resources.translations(language))


@router.get(ApiEndpoints.RESOURCE_TAFSIRS.value)
def get_resource_tafsirs(language: Optional[str] = None):
    return success_response(client.resources.tafsirs(language))


@router.get(ApiEndpoints.RESOURCE_RECITATIONS.value)
def get_resource_recitations(language: Optional[str] = None):
    return success_response(client.resources.recitations(language))


@router.get(ApiEndpoints.RESOURCE_LANGUAGES.value)
def get_resource_languages():
    return success_response(client.resources.languages())


@router.get(ApiEndpoints.RESOURCE_CHAPTER_INFO.value)
def get_resource_chapter_info(language: Optional[str] = None):
    return success_response(client.resources.chapter_info(language))


@router.get(ApiEndpoints.RESOURCE_VERSE_MEDIA.value)
def get_resource_verse_media(verse_key: str):
    try:
        return success_response(client.resources.verse_media(verse_key))
    except ApiException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(ApiEndpoints.RESOURCE_CHAPTER_RECITERS.value)
def get_resource_chapter_reciters():
    return success_response(client.resources.chapter_reciters())


@router.get(ApiEndpoints.SEARCH.value)
def search(q: str, size: int = 10, page: Optional[int] = None, language: str = "en"):
    return success_response(
        client.search.search(q, size=size, page=page, language=language)
    )


@router.get(ApiEndpoints.JUZ_RECITATION.value)
def list_juz_recitation(recitation_id: int, juz_number: int, page: int = 1):
    data = client.audio.get_juz_recitation_audio(
        juz_number=juz_number,
        recitation_id=recitation_id,
        page=page,
    )
    return success_response(data)
