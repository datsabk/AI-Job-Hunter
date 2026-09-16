"""LinkedIn source adapter (browser automation via Playwright).

This automates YOUR logged-in LinkedIn in a real Chrome profile. It is the
highest-risk adapter: LinkedIn's Terms prohibit automation and aggressive use
can get an account restricted. It is therefore built defensively:

* a **persistent** browser profile so you log in / solve 2FA once, by hand;
* **attended** by default (visible window) so you can watch and intervene;
* **hard caps** on cards collected and wall-clock minutes;
* **randomized, human-like** scroll pauses.

Browser profile: by default a dedicated Playwright profile (log in once, it's
remembered). Set ``use_real_chrome: true`` to instead launch your installed
Google Chrome against your real profile (already logged in) — Chrome must be
fully quit first, since it locks the profile while running.

LinkedIn's DOM changes often, so selectors are intentionally broad and every
step is wrapped defensively — a layout change degrades to "collected fewer
jobs", not a crash.
"""

from __future__ import annotations

import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

from ..config import Settings
from ..models import RawJob
from .base import SourceAdapter

logger = logging.getLogger(__name__)

_JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")


class LinkedInSource(SourceAdapter):
    name = "linkedin"

    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise RuntimeError(
                "Playwright is required for the LinkedIn adapter. Install it with:\n"
                "  pip install -r requirements.txt && python -m playwright install chromium"
            ) from exc

        urls: list[str] = config.get("urls", [])
        if not urls:
            raise ValueError("linkedin portal entry requires a non-empty 'urls' list")

        max_cards = int(config.get("max_cards", 25))
        max_minutes = float(config.get("max_minutes", 10))
        pause_range = config.get("scroll_pause_seconds", [2.0, 5.0])
        label = config.get("label", "linkedin")

        deadline = time.monotonic() + max_minutes * 60
        collected: dict[str, RawJob] = {}

        with sync_playwright() as pw:
            page, cleanup = self._launch_page(pw, config)
            try:
                for url in urls:
                    if time.monotonic() > deadline or len(collected) >= max_cards:
                        break
                    self._collect_from_url(
                        page, url, collected, max_cards, deadline, pause_range, label
                    )
            finally:
                cleanup()

        logger.info("LinkedIn: collected %d job(s)", len(collected))
        return list(collected.values())

    def _launch_page(self, pw: Any, config: dict[str, Any]) -> tuple[Any, Any]:
        """Return ``(page, cleanup)`` for the configured launch mode.

        Three modes, in priority order:

        * **Attach over CDP** (``cdp_url`` or ``connect_cdp: true``) — connect to a
          Chrome that YOU launched yourself, already logged in. This is the only
          approach that reliably reuses your real LinkedIn session on Chrome
          >= 136: Chrome deliberately refuses automation against the *default*
          user-data dir, and a Playwright-launched Chrome sets
          ``navigator.webdriver`` (triggering Google/LinkedIn's "this browser may
          not be secure" check). A Chrome you started by hand has neither problem.
          Launch it once with, e.g.::

              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
                  --remote-debugging-port=9222 \\
                  --user-data-dir="$HOME/.li-br-chrome"

          then log into LinkedIn in that window. ``cleanup`` only *disconnects*;
          it never quits your Chrome.
        * ``use_real_chrome: true`` — launch your installed Google Chrome against
          your real profile. NOTE: broken on Chrome >= 136 for the default
          profile (see above); prefer the CDP mode.
        * default — a dedicated persistent Playwright profile (log in once).
        """
        headless = bool(config.get("headless", False))

        cdp_url = _resolve_cdp_url(config)
        if cdp_url:
            logger.info("LinkedIn: attaching to your Chrome over CDP at %s", cdp_url)
            try:
                browser = pw.chromium.connect_over_cdp(cdp_url)
            except Exception as exc:  # noqa: BLE001 - give an actionable message
                raise RuntimeError(
                    f"Could not attach to Chrome over CDP at {cdp_url}. Start Chrome "
                    "yourself first (fully quit it, then run):\n"
                    '  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" '
                    "--remote-debugging-port=9222 "
                    '--user-data-dir="$HOME/.li-br-chrome"\n'
                    "then log into LinkedIn in that window and re-run. "
                    f"Original error: {exc}"
                ) from exc
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()

            def cleanup() -> None:
                # Close only the tab we opened, then DISCONNECT. Because Chrome
                # was launched externally, browser.close() detaches Playwright
                # without quitting the user's Chrome.
                for closer in (page.close, browser.close):
                    try:
                        closer()
                    except Exception:  # noqa: BLE001
                        pass

            return page, cleanup

        if config.get("use_real_chrome"):
            user_data_dir = config.get("chrome_user_data_dir") or _default_chrome_user_data_dir()
            profile = config.get("chrome_profile", "Default")
            logger.info(
                "LinkedIn: launching your real Chrome (profile '%s' at %s). "
                "Chrome must be fully quit or this will fail on the profile lock. "
                "NOTE: on Chrome >= 136 this cannot reuse the default profile's "
                "login — prefer connect_cdp (attach to a Chrome you launched).",
                profile,
                user_data_dir,
            )
            try:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    channel="chrome",  # your installed Google Chrome, not bundled Chromium
                    headless=headless,
                    args=[f"--profile-directory={profile}"],
                )
            except Exception as exc:  # noqa: BLE001 - give an actionable message
                raise RuntimeError(
                    "Could not launch your real Chrome profile. Make sure Google Chrome "
                    "is FULLY QUIT (Cmd-Q — it locks the profile while running) and that "
                    f"the profile path exists: {user_data_dir}. Original error: {exc}"
                ) from exc
            page = context.pages[0] if context.pages else context.new_page()
            return page, context.close

        profile_dir = config.get("browser_profile_dir") or Settings().browser_profile_dir
        context = pw.chromium.launch_persistent_context(user_data_dir=profile_dir, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()
        return page, context.close

    def _collect_from_url(
        self,
        page: Any,
        url: str,
        collected: dict[str, RawJob],
        max_cards: int,
        deadline: float,
        pause_range: list[float],
        label: str,
    ) -> None:
        logger.info("LinkedIn: opening %s", url)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:  # noqa: BLE001 - navigation is best-effort
            logger.warning("LinkedIn: failed to open %s: %s", url, exc)
            return

        self._sleep(pause_range)

        # Scroll and harvest job links until a cap is hit or nothing new appears.
        stagnant_rounds = 0
        while time.monotonic() < deadline and len(collected) < max_cards:
            before = len(collected)
            self._harvest_links(page, collected, max_cards, label)
            if len(collected) == before:
                stagnant_rounds += 1
                if stagnant_rounds >= 3:
                    break
            else:
                stagnant_rounds = 0
            try:
                page.mouse.wheel(0, random.randint(1200, 2400))
            except Exception:  # noqa: BLE001
                pass
            self._sleep(pause_range)

        # Enrich each collected job with its detail-page HTML (bounded by deadline).
        for raw in list(collected.values()):
            if time.monotonic() > deadline or raw.raw_text:
                continue
            self._enrich(page, raw, pause_range)

    def _harvest_links(
        self, page: Any, collected: dict[str, RawJob], max_cards: int, label: str
    ) -> None:
        try:
            hrefs = page.eval_on_selector_all(
                'a[href*="/jobs/view/"]', "els => els.map(e => e.href)"
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("LinkedIn: link harvest failed: %s", exc)
            return
        for href in hrefs:
            match = _JOB_ID_RE.search(href)
            if not match:
                continue
            job_id = match.group(1)
            if job_id in collected:
                continue
            collected[job_id] = RawJob(
                source=self.name,
                external_id=job_id,
                url=f"https://www.linkedin.com/jobs/view/{job_id}/",
                portal_label=label,
            )
            if len(collected) >= max_cards:
                break

    def _enrich(self, page: Any, raw: RawJob, pause_range: list[float]) -> None:
        try:
            page.goto(raw.url, wait_until="domcontentloaded", timeout=60_000)
            self._sleep(pause_range)
            # Try to expand a "see more" description button if present.
            try:
                page.click("button:has-text('See more')", timeout=2000)
            except Exception:  # noqa: BLE001
                pass
            raw.raw_text = page.content()
        except Exception as exc:  # noqa: BLE001
            logger.debug("LinkedIn: enrich failed for %s: %s", raw.url, exc)

    @staticmethod
    def _sleep(pause_range: list[float]) -> None:
        low, high = (pause_range + [pause_range[-1]])[:2] if pause_range else (2.0, 5.0)
        time.sleep(random.uniform(float(low), float(high)))


def _resolve_cdp_url(config: dict[str, Any]) -> str | None:
    """Resolve the CDP endpoint to attach to, or ``None`` for a launch mode.

    * ``cdp_url: http://host:port`` — used verbatim.
    * ``connect_cdp: true`` — builds ``http://localhost:<cdp_port>`` (default 9222).
    * neither set — returns ``None`` (fall back to a launch mode).
    """
    url = config.get("cdp_url")
    if url:
        return str(url)
    if config.get("connect_cdp"):
        return f"http://localhost:{int(config.get('cdp_port', 9222))}"
    return None


def _default_chrome_user_data_dir() -> str:
    """Best-effort path to the OS default Google Chrome user-data directory."""
    home = Path.home()
    if sys.platform == "darwin":
        return str(home / "Library" / "Application Support" / "Google" / "Chrome")
    if sys.platform.startswith("win"):
        return os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    return str(home / ".config" / "google-chrome")
