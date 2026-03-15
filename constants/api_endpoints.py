from enum import Enum


class ApiEndpoints(Enum):
    HEALTH = "/health"
    AUTH_TOKEN = "/auth/token"
    AUTH_TOKEN_STATUS = "/auth/token/status"

    CHAPTERS = "/chapters"
    VERSES_BY_CHAPTER = "/verses/by-chapter/{chapter_id}"
    VERSES_BY_JUZ = "/verses/by-juz/{juz_id}"
    JUZS = "/juzs"

    AUDIO_CHAPTER = "/audio/chapter"
    AUDIO_VERSE = "/audio/verse"

    CONTENT_API_V4 = "/content/api/v4"

    # OTP
    OTP_VERIFY = "/otp/verify"

    # Feature Flags
    FEATURE_FLAGS = "/feature-flags"
    FEATURE_FLAG_BY_NAME = "/feature-flags/{flag_name}"

    # Masjid
    MASJID_NEARBY = "/masjids/nearby"
    MASJID_CREATE = "/masjids"
    MASJID_AMENITIES = "/masjids/{masjid_id}/amenities"
    MASJID_AMENITIES_MASTER = "/masjids/amenities/master"
