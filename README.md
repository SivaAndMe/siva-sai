# Personal website

A single-page academic site. Plain HTML, CSS and a small script, so there is no
build step and nothing to install.

```
index.html               the whole page
assets/css/styles.css    all styling, light and dark
assets/js/site.js        email reveal, publication filter, active nav highlight
assets/img/              portrait and NUS campus banner
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

**Publication counts.** Four numbers live in the metrics band near the top of
`index.html`: papers, citations, h-index and i10-index. They are hardcoded, so
refresh them from Google Scholar every few months and update the
"Publication counts last checked" line in the footer at the same time.

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
