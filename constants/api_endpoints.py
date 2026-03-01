from enum import Enum


class ApiEndpoints(Enum):
    HEALTH = "/health"
    AUTH_TOKEN = "/auth/token"

    CHAPTERS = "/chapters"
    VERSES_BY_CHAPTER = "/verses/by-chapter/{chapter_id}"
    VERSES_BY_JUZ = "/verses/by-juz/{juz_id}"
    JUZS = "/juzs"

    AUDIO_CHAPTER = "/audio/chapter"
    AUDIO_VERSE = "/audio/verse"

    CONTENT_API_V4 = "/content/api/v4"
