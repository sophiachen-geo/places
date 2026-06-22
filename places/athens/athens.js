/* Athens map: neighborhoods + themed "parcours" (routes).
 *
 * - Neighborhoods are plotted as soft colored zones with a label marker.
 * - Each parcours (e.g. "typography") is a themed collection of places,
 *   plotted as diamond markers in the parcours color.
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

function neighborhoodIcon(color) {
  return L.divIcon({
    className: "hood-marker",
    html: `<span style="display:block;width:16px;height:16px;border-radius:50%;
      background:${color};border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8],
  });
}

function placeIcon(color) {
  return L.divIcon({
    className: "addr-marker",
    html: `<span style="display:block;width:14px;height:14px;
      background:${color};border:2px solid #fff;border-radius:3px;transform:rotate(45deg);
      box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -10],
  });
}

async function resolveCoords(item, cache) {
  if (typeof item.lat === "number" && typeof item.lng === "number") {
    return { lat: item.lat, lng: item.lng };
  }
  if (item.address) {
    const q = /greece/i.test(item.address) ? item.address : `${item.address}, Greece`;
    try { return await geocode(q, cache); }
    catch (e) { console.warn("Geocode failed for", item.address, e); return null; }
  }
  return null;
}

function placePopup(place, parcoursName) {
  const approx = place.approx ? " <em>(approx.)</em>" : "";
  return (
    `<div class="popup-card"><h3>${place.label}</h3>` +
    `<p>${place.address || ""}${approx}` +
    (place.year ? `<br><strong>${parcoursName} · ${place.year}</strong>` : "") +
    (place.note ? `<br><span class="popup-note">${place.note}</span>` : "") +
    `</p></div>`
  );
}

async function init() {
  let data;
  try {
    const res = await fetch("athens.json", { cache: "no-cache" });
    data = await res.json();
  } catch (e) {
    console.error("Could not load athens.json", e);
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
  const bounds = [];

  /* ---- Neighborhoods ---- */
  const hoodListEl = document.getElementById("hood-list");
  (data.neighborhoods || []).forEach((hood) => {
    L.circle([hood.lat, hood.lng], {
      radius: 320, color: hood.color, weight: 1.5,
      fillColor: hood.color, fillOpacity: 0.12,
    }).addTo(map);
    L.marker([hood.lat, hood.lng], { icon: neighborhoodIcon(hood.color) })
      .addTo(map)
      .bindPopup(`<div class="popup-card"><h3>${hood.name}</h3><p>${hood.blurb || ""}</p></div>`);

    const item = document.createElement("li");
    item.className = "hood-item";
    item.innerHTML =
      `<span class="hood-swatch" style="background:${hood.color}"></span>` +
      `<span class="hood-name">${hood.name}</span>`;
    item.addEventListener("click", () => map.flyTo([hood.lat, hood.lng], 16));
    hoodListEl.appendChild(item);
    bounds.push([hood.lat, hood.lng]);
  });

  /* ---- Parcours (themed routes) ---- */
  const parcoursEl = document.getElementById("parcours-container");
  for (const parcours of data.parcours || []) {
    const block = document.createElement("div");
    block.className = "parcours";
    block.innerHTML =
      `<div class="parcours-head">` +
      `<span class="parcours-swatch" style="background:${parcours.color}"></span>` +
      `<h3>${parcours.name}</h3>` +
      `<span class="parcours-count">${parcours.places.length}</span></div>` +
      (parcours.description ? `<p class="parcours-desc">${parcours.description}</p>` : "");
    const list = document.createElement("ol");
    list.className = "parcours-list";
    block.appendChild(list);
    parcoursEl.appendChild(block);

    for (const place of parcours.places) {
      const coords = await resolveCoords(place, cache);
      let marker = null;
      if (coords) {
        marker = L.marker([coords.lat, coords.lng], { icon: placeIcon(parcours.color) })
          .addTo(map)
          .bindPopup(placePopup(place, parcours.name));
        bounds.push([coords.lat, coords.lng]);
      }

      const li = document.createElement("li");
      li.className = "parcours-item" + (coords ? "" : " is-unmapped");
      li.innerHTML =
        `<span class="pi-label">${place.label}` +
        (place.approx ? ` <span class="pi-flag" title="Approximate location">~</span>` : "") +
        (coords ? "" : ` <span class="pi-flag" title="Not mapped">?</span>`) +
        `</span>` +
        `<span class="pi-meta">${place.address || ""}${place.year ? " · " + place.year : ""}</span>`;
      if (coords && marker) {
        li.addEventListener("click", () => {
          map.flyTo([coords.lat, coords.lng], 17);
          marker.openPopup();
        });
      }
      list.appendChild(li);
    }
  }

  if (bounds.length > 1) map.fitBounds(bounds, { padding: [40, 40] });
}

document.addEventListener("DOMContentLoaded", init);
