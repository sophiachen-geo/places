# Places

An interactive map and gallery of everywhere I&rsquo;ve been and studied. The
main page shows a world map with a pin for each place, plus a browsable gallery
of cards below it. It grows one place at a time.

🗺️ **Live site:** _enable GitHub Pages to publish (see below)._

## How it works

The whole thing is a static site — plain HTML, CSS, and vanilla JS — so it runs
on GitHub Pages with no build step.

```
index.html            ← main page: map + gallery
css/style.css         ← shared styles
css/place.css         ← styles for individual place pages
js/main.js            ← loads data/places.json, draws the map + cards
data/places.json      ← the single source of truth (every place lives here)
<id>/                 ← one folder per place at the repo root (e.g. athens/)
_template/            ← copy this to start a new place
30daymapchallenge/    ← sub-collection: one folder per challenge day (day-NN-theme/)
```

Place folders live at the repo root, so a place is served at
`https://<user>.github.io/places/<id>/` (e.g. `…/places/athens/`).

Each place is listed once in [`data/places.json`](data/places.json). The map and
gallery are generated from that file, so adding a place is mostly a matter of
adding an entry there and dropping in a detail page.

## Adding a new place (branch-per-place workflow)

Every place starts life as its own branch named after it (the first one is
`athens`). See [CONTRIBUTING.md](CONTRIBUTING.md) for the full step-by-step, but
in short:

1. `git checkout -b <place-name>` (e.g. `paris`)
2. Copy `_template/` to `<place-name>/` (at the repo root) and fill it in.
3. Add an entry for the place to `data/places.json` (`page` and `image` point at `<place-name>/`).
4. Commit, push, open a PR, and merge — the new pin appears on the map.

## Publishing to GitHub Pages

1. Push to GitHub.
2. **Settings → Pages → Build and deployment → Source: Deploy from a branch.**
3. Pick the `main` branch and the `/ (root)` folder, then save.

The site will be live at `https://<user>.github.io/places/`.

## Places so far

- **Athens, Greece** — visited & studied. The cradle of democracy.
- **Mykonos, Greece** — studied. An ecological reading of a rocky Cycladic island and the architecture of Chora and its hamlets.

## Sub-collection: #30DayMapChallenge

[`30daymapchallenge/`](30daymapchallenge/) holds one map per challenge day, each in its own
`day-NN-theme/` folder with its data, processing scripts and a card on the hub page. Each day is also
registered in `data/places.json`, so it gets a pin on the main map.

- **Day 8 · Utopia — Los Angeles** — four utopian models for LA (garden suburb, Autopia, the 1970
  Centers Concept, cooperative colonies), fact-checked and mapped against where each ended up.
