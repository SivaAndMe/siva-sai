#!/usr/bin/env python3
"""Refresh the cached Google Scholar citation metrics.

Two ways in, tried in this order:

1. SerpAPI, if SERPAPI_KEY is set. Google Scholar CAPTCHAs requests from
   datacenter IP ranges, which is what every CI runner has, so this is the
   only route that works reliably from GitHub Actions. Their free tier covers
   a weekly run many times over.
2. The public profile page directly (robots.txt explicitly allows
   /citations?user=). This works from a home or office connection, so it is
   the right path when running the script by hand, and costs nothing.

Either way the script is fail-closed: if the fetch is blocked, the page shape
changes, or the numbers look implausible, it leaves the existing JSON
untouched and exits non-zero. Stale-but-real numbers beat wrong ones.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from html import unescape

PROFILE_ID = "et-EvAcAAAAJ"

# The public profile, newest first, with every entry on one page. pagesize is
# permitted; the cstart= pagination parameter is not (robots.txt disallows it),
# which is why PAGE_LIMIT below is a hard ceiling rather than a page size.
PROFILE_URL = ("https://scholar.google.com/citations"
               "?hl=en&user={}&view_op=list_works&sortby=pubdate".format(PROFILE_ID))
URL = PROFILE_URL + "&pagesize=100"
PAGE_LIMIT = 100

# Venues that mean "not a peer-reviewed publication yet". Entries matching
# these are excluded from the publication count.
PREPRINT_RE = re.compile(r"arxiv|biorxiv|medrxiv|ssrn|techrxiv|researchsquare|preprint", re.I)
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

    stats = {
        # Column order: citations all/since, h-index all/since, i10 all/since.
        "citations": int(values[0]),
        "hIndex": int(values[2]),
        "i10Index": int(values[4]),
    }
    stats["publications"] = count_publications(html)
    return stats


def count_publications(html):
    """Entries on the profile, minus anything still only a preprint."""
    rows = re.findall(r'<tr class="gsc_a_tr">.*?</tr>', html, re.S)
    if not rows:
        raise RefreshError("no publication rows found (page layout changed?)")
    if len(rows) >= PAGE_LIMIT:
        # Reading further needs cstart=, which robots.txt disallows, so the
        # count would silently undercount. Refuse rather than publish it.
        raise RefreshError(
            "{} rows fills the page; counting the rest needs a disallowed URL".format(len(rows))
        )

    preprints = 0
    for row in rows:
        grays = re.findall(r'<div class="gs_gray">(.*?)</div>', row, re.S)
        # Second gs_gray is the venue; the first is the author list.
        venue = re.sub(r"<[^>]+>", "", grays[1]) if len(grays) > 1 else ""
        if PREPRINT_RE.search(unescape(venue)):
            preprints += 1

    return len(rows) - preprints


def fetch_via_serpapi(key):
    """Read the same numbers through SerpAPI, which is not IP-blocked."""
    url = ("https://serpapi.com/search.json?engine=google_scholar_author"
           "&author_id={}&hl=en&api_key={}".format(PROFILE_ID, key))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RefreshError("SerpAPI HTTP {}".format(exc.code))
    except Exception as exc:
        raise RefreshError("SerpAPI request failed: {}".format(exc))

    if payload.get("error"):
        raise RefreshError("SerpAPI error: {}".format(payload["error"]))

    rows = (payload.get("cited_by") or {}).get("table") or []
    found = {}
    # Rows look like [{"citations": {"all": N}}, {"h_index": {"all": N}}, ...].
    # Scan by key rather than position, so a reordering does not misread them.
    for row in rows:
        for serp_key, our_key in (("citations", "citations"),
                                  ("h_index", "hIndex"),
                                  ("i10_index", "i10Index")):
            cell = row.get(serp_key)
            if isinstance(cell, dict) and isinstance(cell.get("all"), int):
                found[our_key] = cell["all"]

    missing = {"citations", "hIndex", "i10Index"} - set(found)
    if missing:
        raise RefreshError("SerpAPI response missing {}".format(", ".join(sorted(missing))))
    return found


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
    if "publications" in new and not (0 < new["publications"] < PAGE_LIMIT):
        raise RefreshError("implausible publication count: {}".format(new["publications"]))

    if prev:
        # Scholar corrects downward occasionally, but never by a lot. A big
        # drop means we parsed the wrong thing.
        for key in ("citations", "hIndex", "i10Index", "publications"):
            old, fresh = prev.get(key), new.get(key)
            if isinstance(old, int) and old > 0 and isinstance(fresh, int) \
                    and fresh < old * 0.8:
                raise RefreshError(
                    "{} fell from {} to {}, refusing to overwrite".format(key, old, fresh)
                )
    return new


def main():
    prev = load_previous()
    key = os.environ.get("SERPAPI_KEY", "").strip()
    try:
        if key:
            print("source: SerpAPI")
            raw = fetch_via_serpapi(key)
        else:
            print("source: scholar.google.com directly "
                  "(set SERPAPI_KEY if this is blocked)")
            raw = parse(fetch(URL))
        # SerpAPI reports the citation metrics but not a publication count,
        # so carry the last known one forward rather than dropping the field.
        if "publications" not in raw and prev and isinstance(prev.get("publications"), int):
            raw["publications"] = prev["publications"]
        stats = validate(raw, prev)
    except RefreshError as exc:
        print("scholar refresh skipped: {}".format(exc), file=sys.stderr)
        if prev:
            print("keeping cached values from {}".format(prev.get("updated", "unknown")),
                  file=sys.stderr)
        return 1

    stats["updated"] = date.today().isoformat()
    stats["source"] = PROFILE_URL

    keys = [k for k in ("citations", "hIndex", "i10Index", "publications") if k in stats]
    if prev and all(prev.get(k) == stats[k] for k in keys):
        print("no change ({} citations)".format(stats["citations"]))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(stats, fh, indent=2)
        fh.write("\n")

    if prev:
        print("updated: " + ", ".join(
            "{} {} -> {}".format(k, prev.get(k), stats[k]) for k in keys))
    else:
        print("seeded: {}".format(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
