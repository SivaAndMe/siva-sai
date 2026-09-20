# Personal website

A single-page academic site. Plain HTML, CSS and a small script, so there is no
build step and nothing to install.

```
index.html               the whole page
assets/css/styles.css    all styling, light and dark
assets/js/site.js        email reveal, publication filter, active nav highlight
assets/img/              portrait and NUS campus banner
assets/data/scholar.json cached citation metrics, refreshed weekly
scripts/fetch_scholar.py the refresher
.github/workflows/       the schedule that runs it
```

No CV, phone number or personal email address is published. The CV PDF is kept
locally in `_local (not published)/` and is excluded by `.gitignore`.

## Viewing it locally

Open `index.html` in a browser. That is all it needs.

## Live site

The site is published from this repository at
**https://sivaandme.github.io/siva-sai/**

GitHub Pages serves the `main` branch from the repository root, so any push to
`main` republishes the site within a minute or two:

```
git add -A
git commit -m "Update publications"
git push
```

If you would rather the site lived at `https://sivaandme.github.io` with no
`/siva-sai` path, rename this repository to `sivaandme.github.io` in Settings.
Nothing in the code needs to change, because every link and asset path is
relative.

## Keeping it current

**Citations, h-index and i10-index update themselves.** A GitHub Actions job
runs every Monday, reads the Google Scholar profile, and writes
`assets/data/scholar.json`. The page fetches that file on load and replaces the
numbers, including the "updated" date in the footer.

The numbers written into `index.html` are the fallback. If the JSON is missing,
corrupt, or cannot be fetched, the page silently keeps whatever is in the
markup, so it can never show a blank or a zero. Keep those hardcoded values
roughly current as a safety net.

Scholar cannot be read from the browser directly: it sends no
`Access-Control-Allow-Origin` header, so a fetch from the page is blocked
whatever you do. Going through a scheduled job is the only way to do this from
a static site, and it is also gentler on Scholar, which rate-limits and
CAPTCHAs anything that looks like scraping.

The refresher is fail-closed. If Scholar returns a CAPTCHA, or the page layout
changes, or the parsed numbers look implausible (h-index above i10-index, a
sudden collapse in citations), it writes nothing and exits non-zero. The
previous values stay. Run it by hand any time:

```
python scripts/fetch_scholar.py
```

or trigger the workflow from the Actions tab with "Run workflow".

**One catch worth knowing.** Google Scholar serves a CAPTCHA to requests from
datacenter IP addresses, which is what every CI runner has. So the scheduled
job, left alone, will usually skip and keep the previous numbers rather than
refresh them. Two ways round it:

- *Free, fully automatic:* sign up at serpapi.com, take the API key from your
  dashboard, and add it to the repository under Settings, Secrets and
  variables, Actions, as `SERPAPI_KEY`. The workflow picks it up with no code
  change. The free tier is 100 searches a month and the schedule uses about
  four.
- *Free, occasional:* run `python scripts/fetch_scholar.py` on your own
  machine and push. Home and university connections are not blocked, so the
  direct path works there. Takes a few seconds.

**The publications count comes from Scholar too.** The script counts the
entries on the profile and subtracts anything whose venue looks like a preprint
(arXiv, bioRxiv, SSRN, TechRxiv and similar), which currently gives 61 minus 2,
so 59. Adjust `PREPRINT_RE` in the script if a venue is being classified wrongly.

One limit: it reads the profile with `pagesize=100` in a single request, because
Scholar's robots.txt disallows the `cstart=` pagination parameter. Past 100
entries the count would silently truncate, so the script refuses to write rather
than publish a wrong number. If you pass 100 publications, switch the count to
SerpAPI or set it by hand.

SerpAPI returns the citation metrics but not a publication count, so on that
route the last known count is carried forward unchanged.

**Adding a publication.** Copy any `<article class="pub">` block in the
publications section and edit it. The `data-area` attribute controls which
filter buttons show it, and a paper can belong to more than one area, for
example `data-area="quantum distributed"`. The available areas are `quantum`,
`distributed`, `blockchain`, `genai` and `sensing`; they must match the
`data-filter` values on the buttons above the list.

**The email address.** It is deliberately absent from the HTML and from the
JavaScript source. `site.js` holds it as a list of shifted character codes and
assembles it only when a visitor clicks "Show email address", so an address
harvester reading the page source finds nothing to take. To change the address,
run this and paste the result over the `MAIL` array in `site.js`:

```
python -c "print([ord(c)+23 for c in 'new.address@example.com'])"
```

This stops bulk email harvesters and search engine indexing. It does not stop a
determined person, or a scraper that runs a real browser and clicks the button.
Treat it as raising the cost, not as a guarantee.

## Notes on the build

The page uses two webfonts from Google Fonts (Newsreader and Geist) and the
Phosphor icon font from jsDelivr, all loaded over CDN. If you would rather have
no external requests, download those files into `assets/` and swap the three
`<link>` tags in the head for local `@font-face` rules.

Colours, spacing and the type scale are all defined as custom properties at the
top of `styles.css`, including the dark palette, so the whole site can be
retinted from that one block.
