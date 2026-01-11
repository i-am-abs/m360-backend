from typing import Optional, List
from services.base_service import BaseService


class VerseService(BaseService):

    def by_key(
        self,
        verse_key: str,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(f"/content/api/v4/verses/by_key/{verse_key}", params)

    def by_chapter(
        self,
        chapter_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page
        return self._get(f"/content/api/v4/verses/by_chapter/{chapter_id}", params)

    def by_juz(
        self,
        juz_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(f"/content/api/v4/verses/by_juz/{juz_id}", params)

    def by_page(
        self,
        page_number: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(f"/content/api/v4/verses/by_page/{page_number}", params)

    def by_rub_el_hizb(
        self,
        rub_el_hizb_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(
            f"/content/api/v4/verses/by_rub_el_hizb/{rub_el_hizb_id}", params
        )

    def by_hizb(
        self,
        hizb_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(f"/content/api/v4/verses/by_hizb/{hizb_id}", params)

    def by_ruku(
        self,
        ruku_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(f"/content/api/v4/verses/by_ruku/{ruku_id}", params)

    def by_manzil(
        self,
        manzil_id: int,
        language: str = "en",
        translations: Optional[List[int]] = None,
        words: bool = False,
    ):
        params = {"language": language}
        if translations:
            params["translations"] = ",".join(map(str, translations))
        if words:
            params["words"] = "true"
        return self._get(f"/content/api/v4/verses/by_manzil/{manzil_id}", params)
