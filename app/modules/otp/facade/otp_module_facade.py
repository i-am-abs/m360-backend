from __future__ import annotations

from dataclasses import dataclass

from app.integrations.msg91_pending_req import Msg91PendingReqIdStore
from app.services.phone_auth_service import PhoneAuthService


@dataclass(frozen=True)
class OtpModuleFacade:
    phoneAuthService: PhoneAuthService
    msg91PendingReqIdStore: Msg91PendingReqIdStore
