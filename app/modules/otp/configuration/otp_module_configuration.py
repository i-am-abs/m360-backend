from __future__ import annotations

from typing import Optional

from redis import Redis

from app.core.config import Settings
from app.gateways.msg91_gateway import Msg91OtpGateway
from app.integrations.msg91_pending_req import Msg91PendingReqIdStore
from app.interfaces.user_repository import UserRepository
from app.modules.otp.facade.otp_module_facade import OtpModuleFacade
from app.services.phone_auth_service import PhoneAuthService
from app.utils.phone import IndiaPhoneValidator


class OtpModuleConfiguration:
    def __init__(
            self,
            settings: Settings,
            redisClient: Optional[Redis],
            userRepository: UserRepository,
    ) -> None:
        self.settings = settings
        self.redisClient = redisClient
        self.userRepository = userRepository

    def createFacade(self) -> OtpModuleFacade:
        msg91PendingReqIdStore = Msg91PendingReqIdStore(
            redis_client=self.redisClient,
            ttl_seconds=300.0,
            key_prefix=self.settings.redis_key_prefix,
        )
        return OtpModuleFacade(
            phoneAuthService=PhoneAuthService(
                userRepository=self.userRepository,
                otpGateway=Msg91OtpGateway(self.settings),
                phoneValidator=IndiaPhoneValidator(self.settings.msg91_country_code),
                sessionTtlSeconds=self.settings.auth_session_ttl_seconds,
                msg91PendingReqIdStore=msg91PendingReqIdStore,
                msg91AsyncReqIdWaitSeconds=self.settings.msg91_async_req_id_wait_seconds,
            ),
            msg91PendingReqIdStore=msg91PendingReqIdStore,
        )
