def normalize_place_id_for_path(place_id: str) -> str:
    raw = (place_id or "").strip()
    if raw.startswith("places/"):
        raw = raw[len("places/"):]
    if not raw:
        raise ValueError("place_id is required")
    return raw
