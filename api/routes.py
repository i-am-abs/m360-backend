import uuid
from typing import Optional
from fastapi import APIRouter, Body

from client.quran_api_client import QuranApiClient
from config.factory.quran_config_factory import QuranConfigFactory
from constants.api_endpoints import ApiEndpoints
from db.factory.device_repository_factory import DeviceRepositoryFactory
from dto.models import DeviceRegisterRequest
from utils.logger import Logger

router = APIRouter()
logger = Logger.get_logger(__name__)

config = QuranConfigFactory.create()
client = QuranApiClient(config)
device_repository = DeviceRepositoryFactory.create()


@router.get(ApiEndpoints.HEALTH.value)
def health():
    return {"status": "UP"}


@router.get(ApiEndpoints.CHAPTERS.value)
def get_chapters(language: str = "en"):
    return client.chapters.get_chapters(language)


@router.get(ApiEndpoints.SEARCH.value)
def search(q: str, size: int = 10, page: int | None = None, language: str = "en"):
    return client.search.search(q, size=size, page=page, language=language)


@router.get(ApiEndpoints.AUDIO_CHAPTER.value)
def chapter_audio(chapter_id: int, recitation_id: int):
    return client.audio.get_chapter_recitation_audio(
        chapter_id=chapter_id, recitation_id=recitation_id
    )


@router.post(ApiEndpoints.DEVICE_REGISTER.value)
def register_device(request: Optional[DeviceRegisterRequest] = Body(default=None)):
    device_uuid = request.uuid if request and request.uuid else str(uuid.uuid4())
    
    result = device_repository.save_device(device_uuid)
    if result:
        return {"status": "success", **result}
    return {"error": "Failed to register device"}


@router.get(ApiEndpoints.DEVICES.value)
def get_all_devices():
    devices = device_repository.get_all_devices()
    return {"count": len(devices), "devices": devices}


@router.get("/chapters/{chapter_id}")
def get_chapter(chapter_id: int, language: str = "en"):
    return client.chapters.get_chapter(chapter_id, language)


@router.get("/verses/by-key/{verse_key}")
def get_verse_by_key(
    verse_key: str,
    language: str = "en",
    translations: str | None = None,
    words: bool = False,
):
    translation_ids = list(map(int, translations.split(","))) if translations else None
    return client.verses.by_key(
        verse_key=verse_key,
        language=language,
        translations=translation_ids,
        words=words,
    )


@router.get("/device/{device_uuid}")
def get_device(device_uuid: str):
    device = device_repository.get_device_by_uuid(device_uuid)
    if device:
        return device
    return {"error": "Device not found"}


@router.delete("/device/{device_uuid}")
def delete_device(device_uuid: str):
    success = device_repository.delete_device(device_uuid)
    if success:
        return {"status": "success", "message": f"Device {device_uuid} deleted"}
    return {"error": "Device not found or could not be deleted"}
