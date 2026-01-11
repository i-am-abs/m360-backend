from enum import Enum


class ApiEndpoints(Enum):
    HEALTH = "/health"
    DEVICES = "/devices"
    DEVICE_REGISTER = "/device/register"
    DEVICE_BY_UUID = "/device/{device_uuid}"
    AUTH_TOKEN = "/auth/token"

    CHAPTERS = "/chapters"
    CHAPTER_BY_ID = "/chapters/{chapter_id}"

    VERSE_BY_KEY = "/verses/by-key/{verse_key}"
    VERSES_BY_CHAPTER = "/verses/by-chapter/{chapter_id}"
    VERSES_BY_JUZ = "/verses/by-juz/{juz_id}"
    VERSES_BY_PAGE = "/verses/by-page/{page_number}"
    VERSES_BY_HIZB = "/verses/by-hizb/{hizb_id}"
    VERSES_BY_RUKU = "/verses/by-ruku/{ruku_id}"
    VERSES_BY_MANZIL = "/verses/by-manzil/{manzil_id}"
    VERSES_BY_RUB_EL_HIZB = "/verses/by-rub-el-hizb/{rub_el_hizb_id}"

    JUZS = "/juzs"
    JUZ_BY_ID = "/juzs/{juz_id}"

    HIZBS = "/hizbs"
    HIZB_BY_ID = "/hizbs/{hizb_id}"

    RUKUS = "/rukus"
    RUKU_BY_ID = "/rukus/{ruku_id}"

    MANZILS = "/manzils"
    MANZIL_BY_ID = "/manzils/{manzil_id}"

    RUB_EL_HIZBS = "/rub-el-hizbs"
    RUB_EL_HIZB_BY_ID = "/rub-el-hizbs/{rub_el_hizb_id}"

    AUDIO_CHAPTER = "/audio/chapter"
    AUDIO_VERSE = "/audio/verse"
    RECITATIONS = "/recitations"
    RECITATION_BY_ID = "/recitations/{recitation_id}"

    TRANSLATIONS = "/translations"
    TRANSLATION_BY_ID = "/translations/{translation_id}"
    CHAPTER_TRANSLATION = "/translations/chapter/{translation_id}/{chapter_id}"
    VERSE_TRANSLATION = "/translations/verse/{translation_id}/{verse_key}"

    TAFSIRS = "/tafsirs"
    TAFSIR_BY_ID = "/tafsirs/{tafsir_id}"
    CHAPTER_TAFSIR = "/tafsirs/chapter/{tafsir_id}/{chapter_id}"
    VERSE_TAFSIR = "/tafsirs/verse/{tafsir_id}/{verse_key}"

    RESOURCE_TRANSLATIONS = "/resources/translations"
    RESOURCE_TAFSIRS = "/resources/tafsirs"
    RESOURCE_RECITATIONS = "/resources/recitations"
    RESOURCE_LANGUAGES = "/resources/languages"
    RESOURCE_CHAPTER_INFO = "/resources/chapter-info"
    RESOURCE_VERSE_MEDIA = "/resources/verse-media/{verse_key}"
    RESOURCE_CHAPTER_RECITERS = "/resources/chapter-reciters"

    SEARCH = "/search"
