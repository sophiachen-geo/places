/* Athens map: neighborhoods + themed "parcours" (routes).
 *
 * - Neighborhoods are plotted as soft colored zones with a label marker.
 * - Each parcours (e.g. "typography") is a themed collection of places,
 *   plotted as diamond markers in the parcours color. A place may also carry a
 *   "line" ([[lat,lng], ...]) drawn as a dashed corridor (e.g. the Long Walls).
 * - Parcours can be toggled on/off; the map refits to whatever is visible.
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

function placePopup(place, parcoursName) {
  const approx = place.approx ? " <em>(approx.)</em>" : "";
  return (
    `<div class="popup-card"><h3>${place.label}</h3>` +
    `<p>${place.address ? place.address + approx : ""}` +
    (place.year ? `<br><strong>${parcoursName} · ${place.year}</strong>` :
      `<br><strong>${parcoursName}</strong>`) +
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

  /* ---- Neighborhoods (always visible) ---- */
  const hoodGroup = L.featureGroup().addTo(map);
  const hoodListEl = document.getElementById("hood-list");
  (data.neighborhoods || []).forEach((hood) => {
    L.circle([hood.lat, hood.lng], {
      radius: 320, color: hood.color, weight: 1.5,
      fillColor: hood.color, fillOpacity: 0.12,
    }).addTo(hoodGroup);
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

  /* ---- Parcours (themed routes) ---- */
  const parcoursEl = document.getElementById("parcours-container");
  const groups = []; // { group: featureGroup, visible: bool }

  function refit() {
    let bounds = null;
    const collect = (fg) => {
      if (!fg) return;
      const b = fg.getBounds();
      if (b && b.isValid()) bounds = bounds ? bounds.extend(b) : L.latLngBounds(b.getSouthWest(), b.getNorthEast());
    };
    collect(hoodGroup);
    groups.forEach((g) => { if (g.visible) collect(g.group); });
    if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40] });
  }

  let lastCategory = null;
  for (const parcours of data.parcours || []) {
    // Category subheading
    if (parcours.category && parcours.category !== lastCategory) {
      const cat = document.createElement("h3");
      cat.className = "parcours-cat";
      cat.textContent = parcours.category;
      parcoursEl.appendChild(cat);
      lastCategory = parcours.category;
    }

    const visible = parcours.default !== false;
    const group = L.featureGroup();
    if (visible) group.addTo(map);
    const entry = { group, visible };
    groups.push(entry);

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
    const list = document.createElement("ol");
    list.className = "parcours-list";
    block.appendChild(list);
    parcoursEl.appendChild(block);

    block.querySelector(`#${toggleId}`).addEventListener("change", (e) => {
      entry.visible = e.target.checked;
      if (entry.visible) group.addTo(map); else map.removeLayer(group);
      refit();
    });

    for (const place of parcours.places) {
      const coords = await resolveCoords(place, cache);

      if (Array.isArray(place.line) && place.line.length > 1) {
        L.polyline(place.line, {
          color: parcours.color, weight: 3, opacity: 0.7, dashArray: "6 6",
        }).addTo(group);
      }

      let marker = null;
      if (coords) {
        marker = L.marker([coords.lat, coords.lng], { icon: placeIcon(parcours.color) })
          .addTo(group)
          .bindPopup(placePopup(place, parcours.name));
      }

      const li = document.createElement("li");
      li.className = "parcours-item" + (coords ? "" : " is-unmapped");
      li.innerHTML =
        `<span class="pi-label">${place.label}` +
        (place.approx ? ` <span class="pi-flag" title="Approximate / representative location">~</span>` : "") +
        (coords ? "" : ` <span class="pi-flag" title="Not mapped">?</span>`) +
        `</span>` +
        `<span class="pi-meta">${place.address || ""}${place.year ? " · " + place.year : ""}</span>`;
      if (coords && marker) {
        li.addEventListener("click", () => {
          if (!entry.visible) {
            entry.visible = true;
            group.addTo(map);
            const cb = block.querySelector(`#${toggleId}`);
            if (cb) cb.checked = true;
          }
          map.flyTo([coords.lat, coords.lng], 16);
          marker.openPopup();
        });
      }
      list.appendChild(li);
    }
  }

  refit();
}

document.addEventListener("DOMContentLoaded", init);
