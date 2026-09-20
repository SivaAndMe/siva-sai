#!/usr/bin/env python3
"""Refresh the cached Google Scholar citation metrics.

Fetches the public profile page (robots.txt explicitly allows
/citations?user=), pulls out the "All" column of the metrics table, and
rewrites assets/data/scholar.json.

The script is deliberately fail-closed: if the fetch is blocked, the page
shape changes, or the parsed numbers look implausible, it leaves the existing
JSON untouched and exits non-zero. Stale-but-real numbers beat wrong ones.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timezone, datetime

PROFILE_ID = "et-EvAcAAAAJ"
URL = "https://scholar.google.com/citations?user={}&hl=en".format(PROFILE_ID)
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "data", "scholar.json",
)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

BLOCK_MARKERS = ("captcha", "unusual traffic", "/sorry/", "not a robot")


class RefreshError(RuntimeError):
    pass


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise RefreshError("HTTP {} from Scholar".format(exc.code))
    except Exception as exc:
        raise RefreshError("request failed: {}".format(exc))


def parse(html):
    if len(html) < 5000:
        raise RefreshError("response too short ({} bytes)".format(len(html)))

    low = html.lower()
    for marker in BLOCK_MARKERS:
        if marker in low:
            raise RefreshError("blocked by Scholar (saw {!r})".format(marker))

    values = re.findall(r'<td class="gsc_rsb_std">(\d+)</td>', html)
    if len(values) < 6:
        raise RefreshError(
            "expected 6 metric cells, found {} (page layout changed?)".format(len(values))
        )

    # Column order: citations all/since, h-index all/since, i10 all/since.
    return {
        "citations": int(values[0]),
        "hIndex": int(values[2]),
        "i10Index": int(values[4]),
    }


def load_previous():
    try:
        with open(OUT, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def validate(new, prev):
    """Reject values that cannot be right, so a bad parse never lands."""
    if not (0 < new["hIndex"] <= 200):
        raise RefreshError("implausible h-index: {}".format(new["hIndex"]))
    if not (0 < new["i10Index"] <= 2000):
        raise RefreshError("implausible i10-index: {}".format(new["i10Index"]))
    if not (0 < new["citations"] <= 10_000_000):
        raise RefreshError("implausible citations: {}".format(new["citations"]))
    if new["hIndex"] > new["i10Index"]:
        raise RefreshError("h-index above i10-index, columns likely misread")

    if prev:
        # Scholar corrects downward occasionally, but never by a lot. A big
        # drop means we parsed the wrong thing.
        for key in ("citations", "hIndex", "i10Index"):
            old = prev.get(key)
            if isinstance(old, int) and old > 0 and new[key] < old * 0.8:
                raise RefreshError(
                    "{} fell from {} to {}, refusing to overwrite".format(key, old, new[key])
                )
    return new


def main():
    prev = load_previous()
    try:
        stats = validate(parse(fetch(URL)), prev)
    except RefreshError as exc:
        print("scholar refresh skipped: {}".format(exc), file=sys.stderr)
        if prev:
            print("keeping cached values from {}".format(prev.get("updated", "unknown")),
                  file=sys.stderr)
        return 1

    stats["updated"] = date.today().isoformat()
    stats["source"] = URL

    if prev and all(prev.get(k) == stats[k] for k in ("citations", "hIndex", "i10Index")):
        print("no change ({} citations)".format(stats["citations"]))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(stats, fh, indent=2)
        fh.write("\n")

    if prev:
        print("updated: citations {} -> {}, h-index {} -> {}, i10 {} -> {}".format(
            prev.get("citations"), stats["citations"],
            prev.get("hIndex"), stats["hIndex"],
            prev.get("i10Index"), stats["i10Index"]))
    else:
        print("seeded: {}".format(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
