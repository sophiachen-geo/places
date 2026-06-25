/* København–Malmö map: themed project/culture layers ("parcours").
 *
 * - Each parcours is ONE toggleable Leaflet layer (a featureGroup), grouped in
 *   the side panel by `category` — Section 1 (urbanisme) and Section 2 (culture)
 *   all draw onto the SAME map, just as separate layers you can switch on/off.
 * - A parcours with `route: false` is a pure project/site map (numbered order is
 *   skipped, markers are diamonds). A routed parcours computes a visiting order
 *   (open-path TSP) and draws a route following REAL STREETS / TRANSIT:
 *     • À pied  -> OSRM foot router
 *     • Transports en commun -> transitous (MOTIS), routed leg by leg
 *     • Vol d'oiseau -> straight lines
 *   Routing happens in the browser, with a straight-line fallback.
 *
 * Addresses without coords are geocoded via Nominatim (cached in localStorage). */

const GEOCODE_URL = "https://nominatim.openstreetmap.org/search";
const CACHE_KEY = "copenhagen-malmo-geocode-cache-v1";
let currentMode = "walking";

function loadCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY)) || {}; } catch { return {}; }
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
  cache[query] = coords; saveCache(cache); await sleep(1100);
  return coords;
}

/* ---------- geometry / routing helpers ---------- */
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
      const d = distKm(pts[last], pts[j]); if (d < bd) { bd = d; best = j; }
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
/* Google encoded polyline decoder (configurable precision). */
function decodePolyline(str, precision) {
  let index = 0, lat = 0, lng = 0;
  const coords = [], factor = Math.pow(10, precision || 5);
  while (index < str.length) {
    let b, shift = 0, result = 0;
    do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lat += (result & 1) ? ~(result >> 1) : (result >> 1);
    shift = 0; result = 0;
    do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lng += (result & 1) ? ~(result >> 1) : (result >> 1);
    coords.push([lat / factor, lng / factor]);
  }
  return coords;
}

/* ---------- icons ---------- */
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
    const a = item.address;
    const q = /(denmark|danmark|sweden|sverige)/i.test(a) ? a
      : /malmö|malmo|hyllie|sweden/i.test(a) ? `${a}, Sweden` : `${a}, Denmark`;
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
    (place.note ? `<br><span class="popup-note">${place.note}</span>` : "") +
    (place.photos ? `<br><span class="popup-note">📷 ${place.photos} photos</span>` : "") + `</p></div>`;
}

/* ---------- routers (browser-side) ---------- */
async function osrmFoot(coords) {
  const cstr = coords.map((c) => `${c.lng},${c.lat}`).join(";");
  const url = `https://routing.openstreetmap.de/routed-foot/route/v1/driving/${cstr}?overview=full&geometries=geojson`;
  const j = await (await fetch(url)).json();
  if (j.code === "Ok" && j.routes && j.routes[0]) return j.routes[0];
  throw new Error("foot code " + (j.code || "?"));
}
async function transitRoute(coords, color) {
  const group = L.featureGroup();
  let totalMin = 0, anyTransit = false;
  for (let i = 0; i < coords.length - 1; i++) {
    const a = coords[i], b = coords[i + 1];
    let it = null;
    try {
      const url = `https://api.transitous.org/api/v1/plan?fromPlace=${a.lat},${a.lng}&toPlace=${b.lat},${b.lng}`;
      const j = await (await fetch(url)).json();
      it = (j.itineraries || [])[0];
    } catch (e) { it = null; }
    if (it) {
      totalMin += (it.duration || 0) / 60;
      for (const leg of it.legs || []) {
        const g = leg.legGeometry || {};
        const pts = g.points ? decodePolyline(g.points, g.precision || 7) : [];
        if (pts.length < 2) continue;
        const transit = leg.mode !== "WALK";
        if (transit) anyTransit = true;
        L.polyline(pts, {
          color: transit ? color : "#8a8f98",
          weight: transit ? 5 : 3,
          opacity: transit ? 0.75 : 0.6,
          dashArray: transit ? null : "4 5",
        }).addTo(group);
      }
    } else {
      totalMin += (distKm(a, b) / 5) * 60; // rough walk estimate for the gap
      L.polyline([[a.lat, a.lng], [b.lat, b.lng]], { color: "#8a8f98", weight: 2, opacity: 0.5, dashArray: "2 6" }).addTo(group);
    }
  }
  if (group.getLayers().length === 0) throw new Error("no transit geometry");
  return { layer: group, min: totalMin, anyTransit };
}

/* Draw/refresh a parcours route for the given mode (cached per mode). */
async function renderRoute(entry, mode) {
  const coords = entry.routeCoords;
  if (!coords || coords.length < 2 || !entry.summaryEl) return;
  if (entry.routeLayer) { entry.group.removeLayer(entry.routeLayer); entry.routeLayer = null; }

  const show = (layer, text) => {
    entry.routeLayers[mode] = layer; entry.routeSummaries[mode] = text;
    entry.routeLayer = layer; entry.group.addLayer(layer); entry.summaryEl.textContent = text;
  };
  if (entry.routeLayers[mode]) { show(entry.routeLayers[mode], entry.routeSummaries[mode]); return; }

  const n = coords.length;
  const straightKm = tourLength(coords.map((_, i) => i), coords);
  const straightLayer = () => L.polyline(coords.map((c) => [c.lat, c.lng]),
    { color: entry.color, weight: 2.5, opacity: 0.55, dashArray: "1 6" });

  if (mode === "straight") {
    show(straightLayer(), `Itinéraire (vol d'oiseau) : ${n} arrêts · ≈ ${straightKm.toFixed(1)} km`);
    return;
  }

  entry.summaryEl.textContent = "Calcul de l'itinéraire…";
  try {
    if (mode === "walking") {
      const r = await osrmFoot(coords);
      const layer = L.geoJSON({ type: "Feature", geometry: r.geometry },
        { style: { color: entry.color, weight: 4, opacity: 0.65 } });
      show(layer, `Itinéraire à pied : ${n} arrêts · ≈ ${(r.distance / 1000).toFixed(1)} km · ~${Math.round(r.duration / 60)} min`);
    } else if (mode === "transit") {
      const { layer, min, anyTransit } = await transitRoute(coords, entry.color);
      show(layer, `${anyTransit ? "Transports en commun" : "Transports en commun (partiel)"} : ${n} arrêts · ~${Math.round(min)} min`);
    }
  } catch (e) {
    console.warn("Routing failed", entry.id, mode, e);
    show(straightLayer(), `Itinéraire (vol d'oiseau, routage indisponible) : ${n} arrêts · ≈ ${straightKm.toFixed(1)} km`);
  }
}

async function init() {
  let data;
  try {
    data = await fetch("copenhagen.json", { cache: "no-cache" }).then((r) => r.json());
  } catch (e) { console.error("Could not load copenhagen data", e); return; }

  const map = L.map("hood-map", { scrollWheelZoom: true, wheelPxPerZoomLevel: 90, zoomSnap: 0.25 })
    .setView([data.center.lat, data.center.lng], data.zoom || 12);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd", maxZoom: 20,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  }).addTo(map);

  const cache = loadCache();

  /* ---- Parcours (toggleable layers, grouped by category/section) ---- */
  const parcoursEl = document.getElementById("parcours-container");
  const groups = [];   // { group, visible }
  const routed = [];   // entries with a route

  function refit() {
    let bounds = null;
    const collect = (fg) => {
      if (!fg || !map.hasLayer(fg)) return;
      const b = fg.getBounds();
      if (b && b.isValid()) bounds = bounds ? bounds.extend(b) : L.latLngBounds(b.getSouthWest(), b.getNorthEast());
    };
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
                    routeCoords: null, routeLayer: null, routeLayers: {}, routeSummaries: {}, summaryEl: null };
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
      if (entry.visible) { group.addTo(map); if (entry.routeCoords) renderRoute(entry, currentMode); }
      else map.removeLayer(group);
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
        `<span class="pi-meta">${place.address || ""}${place.year ? " · " + place.year : ""}${place.photos ? " · 📷 " + place.photos : ""}</span></span>`;
      if (coords) li.addEventListener("click", () => {
        if (!entry.visible) {
          entry.visible = true; group.addTo(map);
          if (entry.routeCoords) renderRoute(entry, currentMode);
          const cb = block.querySelector(`#${toggleId}`); if (cb) cb.checked = true;
        }
        map.flyTo([coords.lat, coords.lng], 16);
      });
      list.appendChild(li);
    });
  }

  function applyMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".rm-btn").forEach((b) => b.classList.toggle("is-active", b.dataset.mode === mode));
    routed.forEach((entry) => { if (entry.visible) renderRoute(entry, mode); });
  }
  document.querySelectorAll(".rm-btn").forEach((b) => b.addEventListener("click", () => applyMode(b.dataset.mode)));

  refit();
  applyMode(currentMode);
}

document.addEventListener("DOMContentLoaded", init);
