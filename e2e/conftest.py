"""Playwright fixtures for the web share-analytics E2E tests.

Starts the API on port 8099, stubs the Mixpanel CDN and browser APIs, and
forwards every analytics call to Python so assertions survive page navigation.
"""

from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8099
BASE = f"http://127.0.0.1:{PORT}"
MESSAGE_ID = "6a9f11dc182e3ea0ddc6b070"
MASJID_ID = "ChIJBZ8snybG5zsRvqUTGeQUeNI"

STUB_JS = """
window.__record = window.__record || function () {};
window.mixpanel = {
  // Pretend to be the Mixpanel snippet so mixpanel-loader.js does not replace
  // this stub with the async loader (which would load the real SDK).
  __SV: 1.2,
  init: function (token, opts) {
    window.__record('__init', { token: token, api_host: opts && opts.api_host });
  },
  register: function (props) {
    window.__super = Object.assign(window.__super || {}, props || {});
    window.__record('__register', props || {});
  },
  identify: function (id) { window.__record('__identify', { id: id }); },
  track: function (event, props) {
    window.__record('__track', {
      event: event,
      props: Object.assign({}, window.__super || {}, props || {})
    });
  }
};
navigator.sendBeacon = function (url, data) {
  window.__record('__beacon', { url: String(url) });
  return false; // force the track() fallback so assertions see the event
};
try {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: {
      writeText: function (text) {
        window.__record('__copied', { url: String(text) });
        return Promise.resolve();
      }
    }
  });
} catch (e) {}
"""


def _wait_port(host: str, port: int, timeout: float = 40.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.3)
    return False


@pytest.fixture(scope="session")
def server() -> str:
    proc = subprocess.Popen(
        [
            str(ROOT / ".venv" / "bin" / "python3"),
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _wait_port("127.0.0.1", PORT):
            pytest.fail("API server did not start on port 8099")
        ready = False
        for _ in range(40):
            try:
                if httpx.get(f"{BASE}/api/v1/health", timeout=1).status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not ready:
            pytest.fail("API server did not become healthy on port 8099")
        yield BASE
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def ctx(browser: Browser, server: str):
    """A fresh context that records every analytics call in Python.

    Depends on `server` so the API is guaranteed to be running before any page
    navigates (without this the fixtures yield with nothing listening on 8099).

    Returns (context, events, store_urls).
    """
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    events: List[Dict[str, Any]] = []
    store_urls: List[str] = []

    def record(source: Any, name: str, payload: Any) -> None:
        events.append({"name": name, "payload": payload or {}})

    context.expose_binding("__record", record)
    context.add_init_script(STUB_JS)

    def cdn(route):
        route.fulfill(status=200, content_type="application/javascript", body="/* stub */")

    def store(route):
        store_urls.append(route.request.url)
        route.fulfill(status=200, content_type="text/html", body="ok")

    context.route("https://cdn.mxpnl.com/**", cdn)
    context.route("https://play.google.com/**", store)
    context.route("https://apps.apple.com/**", store)

    yield context, events, store_urls
    context.close()


def analytics_events(events: List[Dict[str, Any]], name: str | None = None):
    out = [e for e in events if e["name"] == "__track"]
    if name is not None:
        out = [e for e in out if e["payload"].get("event") == name]
    return out


def wait_for(page, predicate, timeout: float = 8.0) -> None:
    """Poll `predicate` while pumping Playwright's event loop.

    The sync API only dispatches queued binding callbacks (our `__record`
    events) and route handlers while a Playwright call is on the stack, so a
    plain ``time.sleep`` here would never observe analytics fired asynchronously
    after a click. ``page.wait_for_timeout`` keeps those callbacks flowing.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        page.wait_for_timeout(100)
    raise AssertionError("timed out waiting for condition")
