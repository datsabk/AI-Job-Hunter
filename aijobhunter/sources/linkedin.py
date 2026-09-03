"""LinkedIn source adapter (browser automation via Playwright).

This automates YOUR logged-in LinkedIn in a real Chrome profile. It is the
highest-risk adapter: LinkedIn's Terms prohibit automation and aggressive use
can get an account restricted. It is therefore built defensively:

* a **persistent** browser profile so you log in / solve 2FA once, by hand;
* **attended** by default (visible window) so you can watch and intervene;
* **hard caps** on cards collected and wall-clock minutes;
* **randomized, human-like** scroll pauses.

LinkedIn's DOM changes often, so selectors are intentionally broad and every
step is wrapped defensively — a layout change degrades to "collected fewer
jobs", not a crash.
"""

from __future__ import annotations

import logging
import random
import re
import time
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
        headless = bool(config.get("headless", False))
        pause_range = config.get("scroll_pause_seconds", [2.0, 5.0])
        profile_dir = config.get("browser_profile_dir") or Settings().browser_profile_dir
        label = config.get("label", "linkedin")

        deadline = time.monotonic() + max_minutes * 60
        collected: dict[str, RawJob] = {}

        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
            )
            page = context.pages[0] if context.pages else context.new_page()
            try:
                for url in urls:
                    if time.monotonic() > deadline or len(collected) >= max_cards:
                        break
                    self._collect_from_url(
                        page, url, collected, max_cards, deadline, pause_range, label
                    )
            finally:
                context.close()

        logger.info("LinkedIn: collected %d job(s)", len(collected))
        return list(collected.values())

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
