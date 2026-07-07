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
    AUTH_REFRESH = "/auth/refresh"

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

    # Masjid entity (Phase 1)
    MASJID_LIST = "/masjids"
    MASJID_GET = "/masjids/{masjid_id}"
    MASJID_SYNC = "/masjids/sync"
    MASJID_UPDATE = "/masjids/{masjid_id}"
    MASJID_UPDATE_FACILITIES = "/masjids/{masjid_id}/facilities"
    MASJID_UPDATE_TIMINGS = "/masjids/{masjid_id}/timings"
    MASJID_COMMITTEE_ADD = "/masjids/{masjid_id}/committee"
    MASJID_COMMITTEE_REMOVE = "/masjids/{masjid_id}/committee/{user_id}"

    # Claims (Phase 2)
    CLAIM_SUBMIT = "/masjids/{masjid_id}/claim"
    CLAIM_STATUS = "/masjids/{masjid_id}/claim/status"
    ADMIN_CLAIMS_LIST = "/admin/claims"
    ADMIN_CLAIM_GET = "/admin/claims/{claim_id}"
    ADMIN_CLAIM_APPROVE = "/admin/claims/{claim_id}/approve"
    ADMIN_CLAIM_REJECT = "/admin/claims/{claim_id}/reject"
    ADMIN_CLAIM_STATS = "/admin/claims/stats"

    # Broadcast (Phase 3)
    BROADCAST_LIST = "/masjids/{masjid_id}/broadcast"
    BROADCAST_POST = "/masjids/{masjid_id}/broadcast"
    BROADCAST_DELETE = "/broadcast/{message_id}"
    BROADCAST_REACT = "/broadcast/{message_id}/react"
    FOLLOW_MASJID = "/masjids/{masjid_id}/follow"
    UNFOLLOW_MASJID = "/masjids/{masjid_id}/follow"
    FOLLOW_STATUS = "/masjids/{masjid_id}/follow/status"
    FOLLOWER_COUNT = "/masjids/{masjid_id}/followers/count"

    # Donations (Phase 4)
    CAMPAIGN_CREATE = "/masjids/{masjid_id}/campaigns"
    CAMPAIGN_LIST = "/masjids/{masjid_id}/campaigns"
    CAMPAIGN_GET = "/campaigns/{campaign_id}"
    CAMPAIGN_UPDATE = "/campaigns/{campaign_id}"
    CAMPAIGN_CANCEL = "/campaigns/{campaign_id}"
    DONATION_INITIATE = "/campaigns/{campaign_id}/donate"
    DONATION_STATUS = "/donations/{donation_id}/status"
    DONATION_HISTORY = "/donations/history"
    PAYMENT_WEBHOOK = "/webhooks/payment"
    CAMPAIGN_DONORS = "/campaigns/{campaign_id}/donors"
