from __future__ import annotations

from enum import Enum


class CommitteeDesignation(str, Enum):
    IMAM = "imam"
    KHATIB = "khatib"
    MUEZZIN = "muezzin"
    CARETAKER = "caretaker"
    TRUSTEE = "trustee"
    SECRETARY = "secretary"
    TREASURER = "treasurer"
    COMMITTEE_MEMBER = "committee_member"
    ADMIN = "admin"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def labels(cls) -> dict[str, str]:
        return {
            cls.IMAM.value: "Imam",
            cls.KHATIB.value: "Khatib",
            cls.MUEZZIN.value: "Muezzin",
            cls.CARETAKER.value: "Caretaker",
            cls.TRUSTEE.value: "Trustee",
            cls.SECRETARY.value: "Secretary",
            cls.TREASURER.value: "Treasurer",
            cls.COMMITTEE_MEMBER.value: "Committee Member",
            cls.ADMIN.value: "Masjid Admin",
        }

    @classmethod
    def normalize(cls, value: str | None) -> str:
        if not value:
            return cls.COMMITTEE_MEMBER.value
        key = str(value).strip().lower().replace(" ", "_")
        aliases = {
            "muazzin": cls.MUEZZIN.value,
            "moazzin": cls.MUEZZIN.value,
            "masjid_admin": cls.ADMIN.value,
            "committee": cls.COMMITTEE_MEMBER.value,
            "member": cls.COMMITTEE_MEMBER.value,
        }
        key = aliases.get(key, key)
        if key in cls.values():
            return key
        return cls.COMMITTEE_MEMBER.value
