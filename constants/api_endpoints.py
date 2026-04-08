from enum import Enum


class ApiEndpoints(Enum):
    HEALTH = "/health"
    AUTH_TOKEN = "/auth/token"

    CHAPTERS = "/chapters"
    VERSES_BY_CHAPTER = "/verses/by-chapter/{chapter_id}"
    VERSES_BY_JUZ = "/verses/by-juz/{juz_id}"
    JUZS = "/juzs"
    JUZS_BY_ID = "/juzs/{juz_id}"

    AUDIO_CHAPTER = "/audio/chapter"
    AUDIO_VERSE = "/audio/verse"

    MASJID_NEARBY = "/masjids/nearby"
    MASJID_SEARCH = "/masjids/search"
    MASJID_SEARCH_SHORT = "/search"
    MASJID_BY_CITY = "/masjids/by-city"
    MASJID_PLACE = "/masjids/place"
    MASJID_STATUS = "/masjids/status"

    CONTENT_API_V4 = "/content/api/v4"
    AUTH_TOKEN_STATUS = "/auth/token/status"
    AUTH_PHONE_REQUEST_OTP = "/auth/phone/request-otp"
    AUTH_PHONE_VERIFY_OTP = "/auth/phone/verify-otp"

    MASJID_DETAILS = "/masjids/{place_id}/details"
    MY_MASJIDS = "/users/me/masjids"
    MY_MASJID_ADD = "/users/me/masjids/{place_id}"
    MY_MASJID_REMOVE = "/users/me/masjids/{place_id}"
