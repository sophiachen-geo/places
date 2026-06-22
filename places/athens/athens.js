/* Athens map: boundaries + neighborhoods + themed "parcours" (routes).
 *
 * - City/municipality and neighborhood boundary polygons (boundaries.geojson).
 * - Neighborhoods without an OSM polygon fall back to a circle.
 * - Each parcours is ONE toggleable layer (a Leaflet featureGroup): all of its
 *   places, its connecting route line, and any corridors live together.
 * - For each parcours a suggested visiting order is computed (open-path TSP:
 *   nearest-neighbour from every start + 2-opt). Stops are numbered and joined
 *   by a route line; the sidebar lists them in that order.
 *
 * A place may carry explicit "lat"/"lng" or just an "address" string, which is
 * geocoded on load via OpenStreetMap Nominatim (cached in localStorage). */

const GEOCODE_URL = "https://nominatim.openstreetmap.org/search";
const CACHE_KEY = "athens-geocode-cache-v1";

function loadCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY)) || {}; }
  catch { return {}; }
}
function saveCache(cache) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch {}
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function geocode(query, cache) {
  if (cache[query]) return cache[query];
  const url = `${GEOCODE_URL}?format=json&limit=1&q=${encodeURIComponent(query)}`;
  const res = await fetch(url, { headers: { "Accept-Language": "en" } });
  const data = await res.json();
  if (!data.length) return null;
  const coords = { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
  cache[query] = coords;
  saveCache(cache);
  await sleep(1100); // be polite to Nominatim (max ~1 req/sec)
  return coords;
}

/* ---------- geometry / routing ---------- */
function distKm(a, b) {
  const R = 6371, toRad = (x) => (x * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat), dLng = toRad(b.lng - a.lng);
  const la1 = toRad(a.lat), la2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function tourLength(order, pts) {
  let s = 0;
  for (let i = 0; i < order.length - 1; i++) s += distKm(pts[order[i]], pts[order[i + 1]]);
  return s;
}
function nearestNeighbour(pts, start) {
  const n = pts.length, used = Array(n).fill(false), order = [start];
  used[start] = true;
  for (let k = 1; k < n; k++) {
    const last = order[order.length - 1];
    let best = -1, bd = Infinity;
    for (let j = 0; j < n; j++) if (!used[j]) {
      const d = distKm(pts[last], pts[j]);
      if (d < bd) { bd = d; best = j; }
    }
    order.push(best); used[best] = true;
  }
  return order;
}
function twoOpt(order, pts) {
  let improved = true;
  while (improved) {
    improved = false;
    for (let i = 1; i < order.length - 1; i++) {
      for (let k = i + 1; k < order.length; k++) {
        const candidate = order.slice(0, i)
          .concat(order.slice(i, k + 1).reverse(), order.slice(k + 1));
        if (tourLength(candidate, pts) + 1e-9 < tourLength(order, pts)) {
          order = candidate; improved = true;
        }
      }
    }
  }
  return order;
}
/* Returns an ordering of indices for an open path (no return to start). */
function optimizeRoute(pts) {
  if (pts.length <= 2) return pts.map((_, i) => i);
  let best = null, bestLen = Infinity;
  for (let s = 0; s < pts.length; s++) {
    const o = twoOpt(nearestNeighbour(pts, s), pts);
    const l = tourLength(o, pts);
    if (l < bestLen) { bestLen = l; best = o; }
  }
  return best;
}

/* ---------- icons ---------- */
function neighborhoodIcon(color) {
  return L.divIcon({
    className: "hood-marker",
    html: `<span style="display:block;width:14px;height:14px;border-radius:50%;
      background:${color};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -8],
  });
}
function placeIcon(color) {
  return L.divIcon({
    className: "addr-marker",
    html: `<span style="display:block;width:14px;height:14px;background:${color};
      border:2px solid #fff;border-radius:3px;transform:rotate(45deg);
      box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -10],
  });
}
function numberedIcon(color, n) {
  return L.divIcon({
    className: "num-marker",
    html: `<span style="display:flex;align-items:center;justify-content:center;
      width:24px;height:24px;border-radius:50%;background:${color};color:#fff;
      border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.45);
      font:700 12px/1 'Segoe UI',sans-serif">${n}</span>`,
    iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -13],
  });
}

async function resolveCoords(item, cache) {
  if (typeof item.lat === "number" && typeof item.lng === "number") {
    return { lat: item.lat, lng: item.lng };
  }
  if (Array.isArray(item.line) && item.line.length) {
    return { lat: item.line[0][0], lng: item.line[0][1] };
  }
  if (item.address) {
    const q = /greece/i.test(item.address) ? item.address : `${item.address}, Greece`;
    try { return await geocode(q, cache); }
    catch (e) { console.warn("Geocode failed for", item.address, e); return null; }
  }
  return null;
}

function placePopup(place, parcoursName, order) {
  const approx = place.approx ? " <em>(approx.)</em>" : "";
  const head = order ? `${order}. ${place.label}` : place.label;
  return (
    `<div class="popup-card"><h3>${head}</h3>` +
    `<p>${place.address ? place.address + approx : ""}` +
    (place.year ? `<br><strong>${parcoursName} · ${place.year}</strong>`
      : `<br><strong>${parcoursName}</strong>`) +
    (place.note ? `<br><span class="popup-note">${place.note}</span>` : "") +
    `</p></div>`
  );
}

async function init() {
  let data, boundaries;
  try {
    const [d, b] = await Promise.all([
      fetch("athens.json", { cache: "no-cache" }).then((r) => r.json()),
      fetch("boundaries.geojson", { cache: "no-cache" }).then((r) => r.json()).catch(() => null),
    ]);
    data = d; boundaries = b;
  } catch (e) {
    console.error("Could not load athens data", e);
    return;
  }

  const map = L.map("hood-map", { scrollWheelZoom: false })
    .setView([data.center.lat, data.center.lng], data.zoom || 14);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  const cache = loadCache();

  /* ---- Boundary polygons (cities + neighborhoods) ---- */
  const boundaryGroup = L.featureGroup().addTo(map);
  const hoodsWithPolygon = new Set();
  if (boundaries && boundaries.features) {
    L.geoJSON(boundaries, {
      style: (f) => {
        const p = f.properties || {};
        if (p.kind === "city") {
          return { color: "#14304a", weight: 2, opacity: 0.6, dashArray: "5 5", fill: false };
        }
        return { color: p.color || "#2a6f97", weight: 2, opacity: 0.8,
                 fillColor: p.color || "#2a6f97", fillOpacity: 0.10 };
      },
      onEachFeature: (f, layer) => {
        const p = f.properties || {};
        if (p.kind === "neighborhood") hoodsWithPolygon.add(p.name);
        const label = p.kind === "city" ? `${p.name} (commune)` : p.name;
        layer.bindTooltip(label, { sticky: true });
      },
    }).addTo(boundaryGroup);
  }

  /* ---- Neighborhood labels (+ circle fallback where no polygon) ---- */
  const hoodGroup = L.featureGroup().addTo(map);
  const hoodListEl = document.getElementById("hood-list");
  (data.neighborhoods || []).forEach((hood) => {
    if (!hoodsWithPolygon.has(hood.id)) {
      L.circle([hood.lat, hood.lng], {
        radius: 320, color: hood.color, weight: 1.5,
        fillColor: hood.color, fillOpacity: 0.12, dashArray: "4 4",
      }).addTo(hoodGroup);
    }
    L.marker([hood.lat, hood.lng], { icon: neighborhoodIcon(hood.color) })
      .addTo(hoodGroup)
      .bindPopup(`<div class="popup-card"><h3>${hood.name}</h3><p>${hood.blurb || ""}</p></div>`);

    const item = document.createElement("li");
    item.className = "hood-item";
    item.innerHTML =
      `<span class="hood-swatch" style="background:${hood.color}"></span>` +
      `<span class="hood-name">${hood.name}</span>`;
    item.addEventListener("click", () => map.flyTo([hood.lat, hood.lng], 16));
    hoodListEl.appendChild(item);
  });

  /* Boundaries toggle */
  const bToggle = document.getElementById("toggle-boundaries");
  if (bToggle) {
    bToggle.addEventListener("change", (e) => {
      if (e.target.checked) boundaryGroup.addTo(map); else map.removeLayer(boundaryGroup);
    });
  }

  /* ---- Parcours (each is one layer; with suggested route) ---- */
  const parcoursEl = document.getElementById("parcours-container");
  const groups = []; // { group, visible }

  function refit() {
    let bounds = null;
    const collect = (fg) => {
      if (!fg || !map.hasLayer(fg)) return;
      const b = fg.getBounds();
      if (b && b.isValid()) bounds = bounds ? bounds.extend(b) : L.latLngBounds(b.getSouthWest(), b.getNorthEast());
    };
    collect(hoodGroup);
    groups.forEach((g) => { if (g.visible) collect(g.group); });
    if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40] });
  }

  let lastCategory = null;
  for (const parcours of data.parcours || []) {
    if (parcours.category && parcours.category !== lastCategory) {
      const cat = document.createElement("h3");
      cat.className = "parcours-cat";
      cat.textContent = parcours.category;
      parcoursEl.appendChild(cat);
      lastCategory = parcours.category;
    }

    const visible = parcours.default !== false;
    const doRoute = parcours.route !== false;
    const group = L.featureGroup();
    if (visible) group.addTo(map);
    const entry = { group, visible };
    groups.push(entry);

    // Resolve coordinates for all places (in file order)
    const resolved = [];
    for (const place of parcours.places) {
      resolved.push({ place, coords: await resolveCoords(place, cache) });
    }

    // Stops eligible for routing: have coords, not a corridor line
    const stopIdx = resolved
      .map((r, i) => i)
      .filter((i) => resolved[i].coords && !Array.isArray(resolved[i].place.line));

    const numberOf = {}; // resolvedIndex -> 1-based order
    let routeKm = 0;
    let listOrder = resolved.map((_, i) => i);

    if (doRoute && stopIdx.length >= 2) {
      const pts = stopIdx.map((i) => resolved[i].coords);
      const order = optimizeRoute(pts);
      routeKm = tourLength(order, pts);
      const routeCoords = order.map((o) => [pts[o].lat, pts[o].lng]);
      L.polyline(routeCoords, {
        color: parcours.color, weight: 2.5, opacity: 0.55,
      }).addTo(group);
      order.forEach((o, pos) => { numberOf[stopIdx[o]] = pos + 1; });
      // sidebar: routed stops first (in order), then the rest (corridors/unmapped)
      const routed = order.map((o) => stopIdx[o]);
      const rest = resolved.map((_, i) => i).filter((i) => !routed.includes(i));
      listOrder = routed.concat(rest);
    }

    // Markers + corridors
    resolved.forEach((r, i) => {
      const { place, coords } = r;
      if (Array.isArray(place.line) && place.line.length > 1) {
        L.polyline(place.line, {
          color: parcours.color, weight: 3, opacity: 0.7, dashArray: "6 6",
        }).addTo(group);
      }
      if (coords) {
        const icon = numberOf[i] ? numberedIcon(parcours.color, numberOf[i]) : placeIcon(parcours.color);
        L.marker([coords.lat, coords.lng], { icon })
          .addTo(group)
          .bindPopup(placePopup(place, parcours.name, numberOf[i]));
      }
    });

    // ---- DOM: parcours block ----
    const block = document.createElement("div");
    block.className = "parcours";
    const toggleId = `toggle-${parcours.id}`;
    const routeNote = doRoute && stopIdx.length >= 2
      ? `<p class="parcours-route">Itinéraire suggéré : ${stopIdx.length} arrêts · ≈ ${routeKm.toFixed(1)} km</p>`
      : "";
    block.innerHTML =
      `<div class="parcours-head">` +
      `<span class="parcours-swatch" style="background:${parcours.color}"></span>` +
      `<h4>${parcours.name}</h4>` +
      `<span class="parcours-count">${parcours.places.length}</span>` +
      `<label class="parcours-toggle"><input type="checkbox" id="${toggleId}" ${visible ? "checked" : ""}> carte</label>` +
      `</div>` +
      (parcours.description ? `<p class="parcours-desc">${parcours.description}</p>` : "") +
      routeNote;
    const list = document.createElement("ol");
    list.className = "parcours-list";
    block.appendChild(list);
    parcoursEl.appendChild(block);

    block.querySelector(`#${toggleId}`).addEventListener("change", (e) => {
      entry.visible = e.target.checked;
      if (entry.visible) group.addTo(map); else map.removeLayer(group);
      refit();
    });

    listOrder.forEach((i) => {
      const { place, coords } = resolved[i];
      const num = numberOf[i];
      const li = document.createElement("li");
      li.className = "parcours-item" + (coords ? "" : " is-unmapped");
      li.innerHTML =
        (num ? `<span class="pi-num" style="background:${parcours.color}">${num}</span>` : `<span class="pi-num pi-num-empty"></span>`) +
        `<span class="pi-text"><span class="pi-label">${place.label}` +
        (place.approx ? ` <span class="pi-flag" title="Approximate / representative location">~</span>` : "") +
        (coords ? "" : ` <span class="pi-flag" title="Not mapped">?</span>`) +
        `</span>` +
        `<span class="pi-meta">${place.address || ""}${place.year ? " · " + place.year : ""}</span></span>`;
      if (coords) {
        li.addEventListener("click", () => {
          if (!entry.visible) {
            entry.visible = true; group.addTo(map);
            const cb = block.querySelector(`#${toggleId}`);
            if (cb) cb.checked = true;
          }
          map.flyTo([coords.lat, coords.lng], 16);
        });
      }
      list.appendChild(li);
    });
  }

  refit();
}

document.addEventListener("DOMContentLoaded", init);
