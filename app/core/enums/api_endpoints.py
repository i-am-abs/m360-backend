from enum import Enum


class ApiEndpoint(Enum):
    HEALTH = "/health"
    HEALTH_LIVE = "/health/live"
    HEALTH_READY = "/health/ready"

    AUTH_TOKEN = "/auth/token"
    AUTH_TOKEN_STATUS = "/auth/token/status"

    AUTH_PHONE_REQUEST_OTP = "/auth/phone/request-otp"
    AUTH_PHONE_RETRY_OTP = "/auth/phone/retry-otp"
    AUTH_PHONE_VERIFY_OTP = "/auth/phone/verify-otp"
    AUTH_LOGIN = "/auth/login"

    MSG91_OTP_WEBHOOK = "/webhooks/msg91/otp-events"

    CHAPTERS = "/chapters"
    VERSES_BY_CHAPTER = "/verses/by-chapter/{chapter_id}"
    VERSES_BY_JUZ = "/verses/by-juz/{juz_id}"
    JUZS = "/juzs"
    JUZS_BY_ID = "/juzs/{juz_id}"
    AUDIO_CHAPTER = "/audio/chapter"
    AUDIO_VERSE = "/audio/verse"
    CONTENT_API_V4 = "/content/api/v4"

    MASJID_NEARBY = "/masjids/nearby"
    MASJID_SEARCH = "/masjids/search"
    MASJID_SEARCH_SHORT = "/search"
    MASJID_BY_CITY = "/masjids/by-city"
    MASJID_PLACE = "/masjids/place"
    MASJID_STATUS = "/masjids/status"
    MASJID_DETAILS = "/masjids/{place_id}/details"

    MY_MASJIDS = "/users/me/masjids"
    MY_MASJID_ADD = "/users/me/masjids/{place_id}"
    MY_MASJID_REMOVE = "/users/me/masjids/{place_id}"
