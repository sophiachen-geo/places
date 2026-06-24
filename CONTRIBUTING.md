# Adding a place

Every place is added the same way: as its own branch, named after the place.
Athens was the first. Here is the full recipe.

## 1. Create a branch for the place

```bash
git checkout main
git pull
git checkout -b paris        # use the place's id (lowercase, no spaces)
```

## 2. Create the place's folder

Copy the template and rename it (place folders live at the repo root):

```bash
cp -r _template paris
```

Then edit `paris/index.html`:

- Replace the title, eyebrow (country), and `<h1>` name.
- Keep only the tags that apply (`visited`, `studied`, or both).
- Write the sections: *Why this place*, *What I studied*, *Highlights*.
- Replace `cover.svg` with a real photo (`cover.jpg`/`cover.png`) — or keep an
  SVG. If you change the filename, update the `background-image` in the hero and
  the `image` field in `places.json`.

## 3. Register it in `data/places.json`

Add one object to the `places` array:

```json
{
  "id": "paris",
  "name": "Paris",
  "country": "France",
  "year": "",
  "lat": 48.8566,
  "lng": 2.3522,
  "tags": ["visited"],
  "summary": "One sentence that shows up on the gallery card and the map popup.",
  "image": "paris/cover.jpg",
  "page": "paris/"
}
```

| Field     | Notes                                                              |
|-----------|-------------------------------------------------------------------|
| `id`      | Must match the folder name and branch name.                       |
| `lat`/`lng` | Decimal degrees. Look them up on any map.                       |
| `tags`    | Any of `"visited"` / `"studied"`. This drives the marker colour.  |
| `image`   | Path to the cover, relative to the repo root.                     |
| `page`    | Path to the detail page (trailing slash loads its `index.html`).  |

## 4. Commit, push, and merge

```bash
git add .
git commit -m "Add Paris"
git push -u origin paris
```

Open a pull request from `paris` into `main` and merge it. The moment it lands
on `main`, the new pin and card appear on the live site.
