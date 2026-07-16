"""
Gets the QR-code image shown to donors, in this priority order:

  1. A local file committed to the repo (e.g. static/qr.jpg) — most reliable,
     recommended. Just add/replace that file on GitHub whenever your QR changes.
  2. Scraping a public Telegram channel post (e.g. https://t.me/scisst/16) —
     kept as a fallback since Telegram can change that page's markup any time.
  3. A telegram file_id set in QR_FALLBACK_FILE_ID env var.

If none of these work, get_qr_source() returns (None, None, "<reason>") so the
caller (and /diag) can show exactly what went wrong instead of a blank image.
"""

import os
import re
import logging

import requests

import config

log = logging.getLogger("rdh-helper-hands.qr")

_UA = "Mozilla/5.0 (compatible; RDHHelperHandsBot/1.0)"


def _local_file_bytes():
    path = config.QR_LOCAL_PATH
    if path and os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            log.exception("Found QR local file at %s but couldn't read it", path)
    return None


def _post_url_to_embed_url(url: str) -> str:
    url = url.strip()
    if "?" in url:
        return url + "&embed=1"
    return url + "?embed=1"


def _scrape_channel_post():
    if not config.QR_CHANNEL_POST_URL:
        return None
    try:
        resp = requests.get(
            _post_url_to_embed_url(config.QR_CHANNEL_POST_URL),
            headers={"User-Agent": _UA},
            timeout=10,
        )
        resp.raise_for_status()
        html = resp.text

        image_url = None
        m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if m:
            image_url = m.group(1)
        if not image_url:
            m = re.search(
                r'tgme_widget_message_photo_wrap["\'][^>]*style="[^"]*background-image:url\(\'([^\']+)\'\)',
                html,
            )
            if m:
                image_url = m.group(1)
        if not image_url:
            log.warning("Could not find an image URL in the channel post HTML")
            return None

        img_resp = requests.get(image_url, headers={"User-Agent": _UA}, timeout=10)
        img_resp.raise_for_status()
        return img_resp.content
    except requests.RequestException:
        log.exception("Failed to scrape QR from channel post")
        return None


def get_qr_source():
    """
    Returns (kind, value, reason):
      ("bytes", <raw image bytes>, "local")    -- from the repo file
      ("bytes", <raw image bytes>, "scraped")  -- from the channel post
      ("file_id", "<telegram file id>", "fallback_file_id")
      (None, None, "<why nothing worked>")
    """
    local = _local_file_bytes()
    if local:
        return "bytes", local, "local"

    scraped = _scrape_channel_post()
    if scraped:
        return "bytes", scraped, "scraped"

    if config.QR_FALLBACK_FILE_ID:
        return "file_id", config.QR_FALLBACK_FILE_ID, "fallback_file_id"

    return None, None, (
        f"No local file at '{config.QR_LOCAL_PATH}', channel scrape failed, "
        "and QR_FALLBACK_FILE_ID is not set."
    )
