from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.enums.api_endpoints import ApiEndpoint
from app.core.logging import get_logger
from app.schemas.msg91_webhook import Msg91OtpWebhookPayload
from app.utils.response import success_response

_log = get_logger(__name__)

router = APIRouter(tags=["Integrations"])


@router.post(ApiEndpoint.MSG91_OTP_WEBHOOK.value, summary="MSG91 OTP widget webhook")
def msg91_otp_webhook(body: Msg91OtpWebhookPayload, request: Request):
    store = getattr(request.app.state, "msg91_pending_req_id_store", None)
    if store is not None and body.identifier and body.request_id:
        event = (body.event or "SEND_OTP").strip().upper()
        if event in {"SEND_OTP", "OTP_SENT", "OTP SENT"}:
            store.record(body.identifier, body.request_id)
            _log.info(
                "MSG91 webhook %s stored requestId for identifier=%s",
                body.event or "SEND_OTP",
                body.identifier,
            )
    return success_response({"accepted": True}, message="OK")
