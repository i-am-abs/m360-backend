"""ASGI entrypoint — `.env` is loaded from the project root in `app.core.config` before Settings."""

from app.factory import create_app

app = create_app()
