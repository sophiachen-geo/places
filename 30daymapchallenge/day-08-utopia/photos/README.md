# Your photographs

Drop your photos in this folder, then list them in `photos.json`. The page picks them up automatically.

1. Put the image files here (JPG or WebP, about 1600 px on the long side is plenty).
2. Add one entry per photo to `photos.json`:

```json
[
  {
    "file": "dodger-stadium.jpg",
    "place": "Chávez Ravine",
    "caption": "Dodger Stadium from Elysian Park, March 2026",
    "chapter": "coop",
    "lat": 34.0739,
    "lng": -118.2400
  }
]
```

- `file`: the file name in this folder (required).
- `place`, `caption`: shown under the photo (optional).
- `chapter`: where the photo appears in the essay: `prologue`, `chronology`, `pastoral`, `autopia`, `centers`, `coop` or `afterlife`.
  Leave it out and the photo goes into the "Photographs" section before the references.
- `lat`, `lng`: optional. With them, the photo also gets a square marker on the map that opens it.

On GitHub you can do all of this in the browser: open this folder, choose **Add file**, then **Upload files**, then edit `photos.json`.
