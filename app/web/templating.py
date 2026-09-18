from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("app/web/templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
