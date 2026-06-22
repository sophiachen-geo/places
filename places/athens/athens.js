/* Athens map: boundaries + neighborhoods + themed "parcours" (routes).
 *
 * - City/municipality and neighborhood boundary polygons (boundaries.geojson).
 *   Hand-traced (approximate) neighborhood polygons are drawn dashed.
 * - Each parcours is ONE toggleable layer (a Leaflet featureGroup).
 * - Per parcours a visiting order is computed (open-path TSP: nearest-neighbour
 *   from every start + 2-opt). Stops are numbered and joined by a route.
 * - The route follows REAL STREETS via OSRM (walking or driving), fetched in the
 *   browser. If a router is unreachable it falls back to a straight-line route.
 *
 * A place may carry explicit "lat"/"lng" or just an "address" string, which is
 * geocoded on load via OpenStreetMap Nominatim (cached in localStorage). */

const GEOCODE_URL = "https://nominatim.openstreetmap.org/search";
const CACHE_KEY = "athens-geocode-cache-v1";

/* Routing back-ends (called from the visitor's browser). Path token "driving"
 * is ignored by OSRM — the profile is fixed per instance. */
const ROUTERS = {
  walking: {
    label: "à pied",
    url: (c) => `https://routing.openstreetmap.de/routed-foot/route/v1/driving/${c}?overview=full&geometries=geojson`,
  },
  driving: {
    label: "en voiture",
    url: (c) => `https://router.project-osrm.org/route/v1/driving/${c}?overview=full&geometries=geojson`,
  },
};
let currentMode = "walking";

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
  await sleep(1100);
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
        const cand = order.slice(0, i).concat(order.slice(i, k + 1).reverse(), order.slice(k + 1));
        if (tourLength(cand, pts) + 1e-9 < tourLength(order, pts)) { order = cand; improved = true; }
      }
    }
  }
  return order;
}
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
  return L.divIcon({ className: "hood-marker",
    html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -8] });
}
function placeIcon(color) {
  return L.divIcon({ className: "addr-marker",
    html: `<span style="display:block;width:14px;height:14px;background:${color};border:2px solid #fff;border-radius:3px;transform:rotate(45deg);box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -10] });
}
function numberedIcon(color, n) {
  return L.divIcon({ className: "num-marker",
    html: `<span style="display:flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:${color};color:#fff;border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.45);font:700 12px/1 'Segoe UI',sans-serif">${n}</span>`,
    iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -13] });
}

async function resolveCoords(item, cache) {
  if (typeof item.lat === "number" && typeof item.lng === "number") return { lat: item.lat, lng: item.lng };
  if (Array.isArray(item.line) && item.line.length) return { lat: item.line[0][0], lng: item.line[0][1] };
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
  return `<div class="popup-card"><h3>${head}</h3>` +
    `<p>${place.address ? place.address + approx : ""}` +
    (place.year ? `<br><strong>${parcoursName} · ${place.year}</strong>` : `<br><strong>${parcoursName}</strong>`) +
    (place.note ? `<br><span class="popup-note">${place.note}</span>` : "") + `</p></div>`;
}

/* Draw/refresh a parcours route line for the given mode. */
async function renderRoute(entry, mode) {
  const coords = entry.routeCoords;
  if (!coords || coords.length < 2) return;
  if (entry.routeLayer) { entry.group.removeLayer(entry.routeLayer); entry.routeLayer = null; }

  const straightKm = tourLength(coords.map((_, i) => i), coords);
  const n = coords.length;

  const drawStraight = (suffix) => {
    entry.routeLayer = L.polyline(coords.map((c) => [c.lat, c.lng]), {
      color: entry.color, weight: 2.5, opacity: 0.55, dashArray: "1 6",
    }).addTo(entry.group);
    entry.summaryEl.textContent = `Itinéraire (vol d'oiseau${suffix || ""}) : ${n} arrêts · ≈ ${straightKm.toFixed(1)} km`;
  };

  if (mode === "straight") { drawStraight(); return; }

  // cached?
  const cached = entry.routeCache[mode];
  const render = (geo, km, min) => {
    entry.routeLayer = L.geoJSON({ type: "Feature", geometry: geo }, {
      style: { color: entry.color, weight: 4, opacity: 0.65 },
    }).addTo(entry.group);
    entry.summaryEl.textContent =
      `Itinéraire ${ROUTERS[mode].label} : ${n} arrêts · ≈ ${km.toFixed(1)} km · ~${Math.round(min)} min`;
  };
  if (cached) { render(cached.geo, cached.km, cached.min); return; }

  entry.summaryEl.textContent = `Calcul de l'itinéraire (${ROUTERS[mode].label})…`;
  const cstr = coords.map((c) => `${c.lng},${c.lat}`).join(";");
  try {
    const res = await fetch(ROUTERS[mode].url(cstr));
    const json = await res.json();
    if (json.code === "Ok" && json.routes && json.routes[0]) {
      const r = json.routes[0];
      const km = r.distance / 1000, min = r.duration / 60;
      entry.routeCache[mode] = { geo: r.geometry, km, min };
      render(r.geometry, km, min);
      return;
    }
    throw new Error("router code " + (json.code || "?"));
  } catch (e) {
    console.warn("Routing failed for", entry.id, mode, e);
    drawStraight(", routage indisponible");
  }
}

async function init() {
  let data, boundaries;
  try {
    const [d, b] = await Promise.all([
      fetch("athens.json", { cache: "no-cache" }).then((r) => r.json()),
      fetch("boundaries.geojson", { cache: "no-cache" }).then((r) => r.json()).catch(() => null),
    ]);
    data = d; boundaries = b;
  } catch (e) { console.error("Could not load athens data", e); return; }

  const map = L.map("hood-map", { scrollWheelZoom: false })
    .setView([data.center.lat, data.center.lng], data.zoom || 14);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  const cache = loadCache();

  /* ---- Boundary polygons ---- */
  const boundaryGroup = L.featureGroup().addTo(map);
  const hoodsWithPolygon = new Set();
  if (boundaries && boundaries.features) {
    L.geoJSON(boundaries, {
      style: (f) => {
        const p = f.properties || {};
        if (p.kind === "city") return { color: "#14304a", weight: 2, opacity: 0.6, dashArray: "5 5", fill: false };
        return { color: p.color || "#2a6f97", weight: 2, opacity: 0.8,
                 fillColor: p.color || "#2a6f97", fillOpacity: 0.10,
                 dashArray: p.approx ? "6 5" : null };
      },
      onEachFeature: (f, layer) => {
        const p = f.properties || {};
        if (p.kind === "neighborhood") hoodsWithPolygon.add(p.name);
        const label = p.kind === "city" ? `${p.name} (commune)`
          : (p.approx ? `${p.name} (approx.)` : p.name);
        layer.bindTooltip(label, { sticky: true });
      },
    }).addTo(boundaryGroup);
  }

  /* ---- Neighborhood labels (+ circle fallback) ---- */
  const hoodGroup = L.featureGroup().addTo(map);
  const hoodListEl = document.getElementById("hood-list");
  (data.neighborhoods || []).forEach((hood) => {
    if (!hoodsWithPolygon.has(hood.id)) {
      L.circle([hood.lat, hood.lng], { radius: 320, color: hood.color, weight: 1.5,
        fillColor: hood.color, fillOpacity: 0.12, dashArray: "4 4" }).addTo(hoodGroup);
    }
    L.marker([hood.lat, hood.lng], { icon: neighborhoodIcon(hood.color) })
      .addTo(hoodGroup)
      .bindPopup(`<div class="popup-card"><h3>${hood.name}</h3><p>${hood.blurb || ""}</p></div>`);
    const item = document.createElement("li");
    item.className = "hood-item";
    item.innerHTML = `<span class="hood-swatch" style="background:${hood.color}"></span><span class="hood-name">${hood.name}</span>`;
    item.addEventListener("click", () => map.flyTo([hood.lat, hood.lng], 16));
    hoodListEl.appendChild(item);
  });

  const bToggle = document.getElementById("toggle-boundaries");
  if (bToggle) bToggle.addEventListener("change", (e) => {
    if (e.target.checked) boundaryGroup.addTo(map); else map.removeLayer(boundaryGroup);
  });

  /* ---- Parcours ---- */
  const parcoursEl = document.getElementById("parcours-container");
  const groups = [];   // { group, visible }
  const routed = [];   // entries with a route (for mode switching)

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
    const entry = { id: parcours.id, group, visible, color: parcours.color,
                    routeCoords: null, routeLayer: null, routeCache: {}, summaryEl: null };
    groups.push(entry);

    const resolved = [];
    for (const place of parcours.places) resolved.push({ place, coords: await resolveCoords(place, cache) });

    const stopIdx = resolved.map((r, i) => i)
      .filter((i) => resolved[i].coords && !Array.isArray(resolved[i].place.line) && !resolved[i].place.noroute);

    const numberOf = {};
    let listOrder = resolved.map((_, i) => i);

    if (doRoute && stopIdx.length >= 2) {
      const pts = stopIdx.map((i) => resolved[i].coords);
      const order = optimizeRoute(pts);
      order.forEach((o, pos) => { numberOf[stopIdx[o]] = pos + 1; });
      entry.routeCoords = order.map((o) => pts[o]);
      const routedIdx = order.map((o) => stopIdx[o]);
      const rest = resolved.map((_, i) => i).filter((i) => !routedIdx.includes(i));
      listOrder = routedIdx.concat(rest);
    }

    // markers + corridors
    resolved.forEach((r, i) => {
      const { place, coords } = r;
      if (Array.isArray(place.line) && place.line.length > 1) {
        L.polyline(place.line, { color: parcours.color, weight: 3, opacity: 0.7, dashArray: "6 6" }).addTo(group);
      }
      if (coords) {
        const icon = numberOf[i] ? numberedIcon(parcours.color, numberOf[i]) : placeIcon(parcours.color);
        L.marker([coords.lat, coords.lng], { icon }).addTo(group).bindPopup(placePopup(place, parcours.name, numberOf[i]));
      }
    });

    // DOM block
    const block = document.createElement("div");
    block.className = "parcours";
    const toggleId = `toggle-${parcours.id}`;
    block.innerHTML =
      `<div class="parcours-head">` +
      `<span class="parcours-swatch" style="background:${parcours.color}"></span>` +
      `<h4>${parcours.name}</h4>` +
      `<span class="parcours-count">${parcours.places.length}</span>` +
      `<label class="parcours-toggle"><input type="checkbox" id="${toggleId}" ${visible ? "checked" : ""}> carte</label>` +
      `</div>` +
      (parcours.description ? `<p class="parcours-desc">${parcours.description}</p>` : "");
    if (entry.routeCoords) {
      const summary = document.createElement("p");
      summary.className = "parcours-route";
      block.appendChild(summary);
      entry.summaryEl = summary;
      routed.push(entry);
    }
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
        (coords ? "" : ` <span class="pi-flag" title="Not mapped">?</span>`) + `</span>` +
        `<span class="pi-meta">${place.address || ""}${place.year ? " · " + place.year : ""}</span></span>`;
      if (coords) li.addEventListener("click", () => {
        if (!entry.visible) {
          entry.visible = true; group.addTo(map);
          const cb = block.querySelector(`#${toggleId}`); if (cb) cb.checked = true;
        }
        map.flyTo([coords.lat, coords.lng], 16);
      });
      list.appendChild(li);
    });
  }

  /* Route-mode toggle */
  function applyMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".rm-btn").forEach((b) =>
      b.classList.toggle("is-active", b.dataset.mode === mode));
    routed.forEach((entry) => renderRoute(entry, mode));
  }
  document.querySelectorAll(".rm-btn").forEach((b) =>
    b.addEventListener("click", () => applyMode(b.dataset.mode)));

  refit();
  applyMode(currentMode);
}

document.addEventListener("DOMContentLoaded", init);
