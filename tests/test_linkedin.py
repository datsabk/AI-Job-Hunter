"""Tests for the LinkedIn adapter's Chrome-attach (CDP) launch path.

Browser automation itself can't be unit-tested without a real browser, so these
cover the pure URL resolution and the CDP acquisition wiring with a fake
Playwright — in particular that cleanup DISCONNECTS (does not kill) the user's
externally-launched Chrome.
"""

from aijobhunter.sources.linkedin import LinkedInSource, _resolve_cdp_url


# ---- _resolve_cdp_url ----

def test_resolve_cdp_url_explicit():
    assert _resolve_cdp_url({"cdp_url": "http://localhost:9999"}) == "http://localhost:9999"


def test_resolve_cdp_url_connect_flag_default_port():
    assert _resolve_cdp_url({"connect_cdp": True}) == "http://localhost:9222"


def test_resolve_cdp_url_connect_flag_custom_port():
    assert _resolve_cdp_url({"connect_cdp": True, "cdp_port": 9333}) == "http://localhost:9333"


def test_resolve_cdp_url_none_when_unset():
    assert _resolve_cdp_url({"use_real_chrome": True}) is None
    assert _resolve_cdp_url({}) is None


# ---- CDP acquisition wiring (fake Playwright) ----

class _FakePage:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeContext:
    def __init__(self, pages=None):
        self._pages = list(pages or [])

    @property
    def pages(self):
        return self._pages

    def new_page(self):
        page = _FakePage()
        self._pages.append(page)
        return page


class _FakeBrowser:
    def __init__(self, contexts):
        self.contexts = contexts
        self.closed = False

    def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self, browser):
        self._browser = browser
        self.cdp_url = None

    def connect_over_cdp(self, url):
        self.cdp_url = url
        return self._browser


class _FakePW:
    def __init__(self, browser):
        self.chromium = _FakeChromium(browser)


def test_launch_page_cdp_attaches_to_existing_context():
    ctx = _FakeContext()
    browser = _FakeBrowser([ctx])
    pw = _FakePW(browser)

    page, cleanup = LinkedInSource()._launch_page(pw, {"connect_cdp": True, "cdp_port": 9333})

    assert pw.chromium.cdp_url == "http://localhost:9333"
    assert isinstance(page, _FakePage)
    assert page in ctx.pages  # created inside the user's existing context


def test_launch_page_cdp_cleanup_disconnects_not_kills():
    ctx = _FakeContext()
    browser = _FakeBrowser([ctx])
    pw = _FakePW(browser)

    page, cleanup = LinkedInSource()._launch_page(pw, {"connect_cdp": True})
    cleanup()

    # Our page is closed and we disconnect the browser handle, but because Chrome
    # was launched externally, browser.close() only detaches — it does not quit
    # the user's Chrome. We assert we called it (disconnect), not context.close().
    assert page.closed is True
    assert browser.closed is True
