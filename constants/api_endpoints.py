from enum import Enum


class ApiEndpoints(Enum):
    HEALTH = "/health"
    CHAPTERS = "/chapters"
    CHAPTER_BY_ID = "/chapters/{chapter_id}"
    VERSES_BY_CHAPTER = "/verses/by-chapter/{chapter_id}"
    VERSES_BY_JUZ = "/verses/by-juz/{juz_id}"
    JUZS = "/juzs"
    JUZ_BY_ID = "/juzs/{juz_id}"
    AUDIO_CHAPTER = "/audio/chapter"
    AUDIO_VERSE = "/audio/verse"
    MASJID_NEARBY = "/masjid/nearby"
