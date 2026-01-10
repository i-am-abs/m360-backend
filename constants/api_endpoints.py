from enum import Enum


class ApiEndpoints(Enum):
    HEALTH = "/health"
    DEVICES = "/devices"
    DEVICE_REGISTER = "/device/register"
    DEVICE_BY_UUID = "/device/{device_uuid}"
    AUDIO_CHAPTER = "/audio/chapter"
    SEARCH = "/search"
    CHAPTERS = "/chapters"
    CHAPTER_BY_ID = "/chapters/{chapter_id}"
    VERSE_BY_KEY = "/verses/by-key/{verse_key}"
    AUTH_TOKEN = "/auth/token"
