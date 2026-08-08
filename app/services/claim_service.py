from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.exceptions.base import ApiException
from app.interfaces.claim_repository import ClaimRepository
from app.interfaces.masjid_repository import MasjidEntityRepository

log = get_logger(__name__)


class ClaimService:
    def __init__(
        self,
        claim_repo: ClaimRepository,
        masjid_repo: MasjidEntityRepository,
        fcm_service=None,
    ) -> None:
        self._claim_repo = claim_repo
        self._masjid_repo = masjid_repo
        self._fcm_service = fcm_service

    def submit_claim(self, user_id: str, masjid_id: str, role: str, note: Optional[str] = None) -> Dict[str, Any]:
        masjid = self._masjid_repo.get_by_id(masjid_id)
        if not masjid:
            raise ApiException(
                "Masjid not found in database. Sync it first.",
                status_code=HTTPStatus.NOT_FOUND,
            )
        if masjid.get("management", {}).get("is_claimed", False):
            committee = masjid["management"].get("committee", [])
            if any(m.get("user_id") == user_id for m in committee):
                raise ApiException(
                    "You are already a committee member of this masjid",
                    status_code=HTTPStatus.BAD_REQUEST,
                )
        existing = self._claim_repo.get_user_claim_for_masjid(user_id, masjid_id)
        if existing:
            raise ApiException(
                f"You already have a {existing['status']} claim for this masjid",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        claim = self._claim_repo.create_claim(user_id, masjid_id, role, note)
        log.info("Claim submitted: userId=%s masjidId=%s role=%s", user_id, masjid_id, role)
        return {
            "claim": {
                "id": str(claim.get("_id", claim.get("id", ""))),
                "status": claim.get("status", "pending"),
                "claimed_role": role,
            },
            "message": "Your claim has been submitted for review.",
        }

    def get_claim_status(self, user_id: str, masjid_id: str) -> Optional[Dict[str, Any]]:
        claim = self._claim_repo.get_user_claim_for_masjid(user_id, masjid_id)
        if not claim:
            return None
        return {
            "claim": {
                "id": str(claim.get("_id", claim.get("id", ""))),
                "status": claim.get("status"),
                "claimed_role": claim.get("claimed_role"),
                "applicant_note": claim.get("applicant_note"),
                "created_at": claim.get("created_at"),
                "reviewer_note": claim.get("reviewer_note"),
                "reviewed_at": claim.get("reviewed_at"),
            }
        }

    def check_relationship(self, user_id: str, masjid_id: str) -> str:
        masjid = self._masjid_repo.get_by_id(masjid_id)
        if not masjid:
            return "none"

        committee = masjid.get("management", {}).get("committee", [])
        if any(m.get("user_id") == user_id for m in committee):
            return "committee_member"

        claim = self._claim_repo.get_user_claim_for_masjid(user_id, masjid_id)
        if claim:
            return "pending_claim"

        return "none"

    def approve_claim(self, claim_id: str, reviewer_id: str, note: Optional[str] = None) -> Dict[str, Any]:
        claim = self._claim_repo.get_claim(claim_id)
        if not claim:
            raise ApiException("Claim not found", status_code=HTTPStatus.NOT_FOUND)
        if claim.get("status") != "pending":
            raise ApiException(
                f"Claim is already {claim['status']}",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        claim = self._claim_repo.approve_claim(claim_id, reviewer_id, note)
        masjid_id = claim.get("masjid_id")
        user_id = claim.get("user_id")
        role = claim.get("claimed_role", "General Member")

        self._masjid_repo.add_committee_member(
            masjid_id,
            {
                "user_id": user_id,
                "name": claim.get("applicant_note", ""),
                "role": role,
            },
        )

        log.info(
            "Claim approved: claimId=%s userId=%s masjidId=%s reviewerId=%s",
            claim_id, user_id, masjid_id, reviewer_id,
        )
        if self._fcm_service:
            masjid = self._masjid_repo.get_by_id(masjid_id)
            masjid_name = masjid.get("name", "Masjid") if masjid else "Masjid"
            self._fcm_service.send_to_user(
                user_id=user_id,
                title="Claim Approved",
                body=f"Your request for {masjid_name} as {role} has been approved",
                data={"type": "claim", "masjid_id": masjid_id, "status": "approved"},
            )
        return {"claim": {"id": claim_id, "status": "approved"}}

    def reject_claim(self, claim_id: str, reviewer_id: str, note: str) -> Dict[str, Any]:
        claim = self._claim_repo.get_claim(claim_id)
        if not claim:
            raise ApiException("Claim not found", status_code=HTTPStatus.NOT_FOUND)
        if claim.get("status") != "pending":
            raise ApiException(
                f"Claim is already {claim['status']}",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        claim = self._claim_repo.reject_claim(claim_id, reviewer_id, note)
        log.info(
            "Claim rejected: claimId=%s reviewerId=%s",
            claim_id, reviewer_id,
        )
        if self._fcm_service:
            masjid_id = claim.get("masjid_id")
            user_id = claim.get("user_id")
            if masjid_id and user_id:
                masjid = self._masjid_repo.get_by_id(masjid_id)
                masjid_name = masjid.get("name", "Masjid") if masjid else "Masjid"
                self._fcm_service.send_to_user(
                    user_id=user_id,
                    title="Claim Rejected",
                    body=f"Your request for {masjid_name} was not approved",
                    data={"type": "claim", "masjid_id": masjid_id, "status": "rejected"},
                )
        return {"claim": {"id": claim_id, "status": "rejected", "reviewer_note": note}}

    def list_claims(self, status: Optional[str], page: int, limit: int) -> Dict[str, Any]:
        result = self._claim_repo.list_claims(status, page, limit)
        claims = result.get("claims", result.get("items", []))
        enriched = []
        for claim in claims:
            masjid_id = claim.get("masjid_id", "")
            masjid = self._masjid_repo.get_by_id(masjid_id) if masjid_id else None
            enriched.append({
                "id": str(claim.get("_id", claim.get("id", ""))),
                "user_id": claim.get("user_id"),
                "masjid_id": masjid_id,
                "masjid_name": masjid.get("name", "Unknown") if masjid else "Unknown",
                "masjid_city": masjid.get("city", "") if masjid else "",
                "claimed_role": claim.get("claimed_role"),
                "applicant_note": claim.get("applicant_note"),
                "status": claim.get("status"),
                "created_at": claim.get("created_at"),
            })
        total = result.get("total", len(claims))
        return {
            "claims": enriched,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": max(1, (total + limit - 1) // limit),
            },
        }