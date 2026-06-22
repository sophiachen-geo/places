/* Athens neighborhood map.
 * Loads athens.json and plots each neighborhood as a colored circle + marker.
 * Addresses live inside each neighborhood's "addresses" array. An address can be:
 *   { "label": "Acropolis Museum", "lat": 37.9683, "lng": 23.7286, "note": "..." }
 * or just a street string, which is geocoded on load via OpenStreetMap Nominatim:
 *   { "label": "Acropolis Museum", "address": "Dionysiou Areopagitou 15, Athens", "note": "..." }
 * Geocoded coordinates are cached in localStorage so lookups happen only once. */

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

function addressIcon(color) {
  return L.divIcon({
    className: "addr-marker",
    html: `<span style="display:block;width:14px;height:14px;
      background:${color};border:2px solid #fff;border-radius:3px;transform:rotate(45deg);
      box-shadow:0 1px 4px rgba(0,0,0,.4)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    popupAnchor: [0, -8],
  });
}

async function resolveAddress(addr, hood, cache) {
  if (typeof addr.lat === "number" && typeof addr.lng === "number") {
    return { lat: addr.lat, lng: addr.lng };
  }
  if (addr.address) {
    const q = /athens/i.test(addr.address) ? addr.address : `${addr.address}, Athens, Greece`;
    try { return await geocode(q, cache); }
    catch (e) { console.warn("Geocode failed for", addr.address, e); return null; }
  }
  return null;
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

  const listEl = document.getElementById("hood-list");
  const cache = loadCache();
  const hoods = data.neighborhoods || [];

  for (const hood of hoods) {
    // Soft zone circle + center marker for the neighborhood
    L.circle([hood.lat, hood.lng], {
      radius: 320,
      color: hood.color,
      weight: 1.5,
      fillColor: hood.color,
      fillOpacity: 0.12,
    }).addTo(map);

    L.marker([hood.lat, hood.lng], { icon: neighborhoodIcon(hood.color) })
      .addTo(map)
      .bindPopup(
        `<div class="popup-card"><h3>${hood.name}</h3><p>${hood.blurb || ""}</p></div>`
      );

    const addresses = hood.addresses || [];

    // Sidebar entry
    const item = document.createElement("li");
    item.className = "hood-item";
    item.innerHTML = `
      <span class="hood-swatch" style="background:${hood.color}"></span>
      <span class="hood-name">${hood.name}</span>
      <span class="hood-count">${addresses.length || ""}</span>`;
    item.addEventListener("click", () => map.flyTo([hood.lat, hood.lng], 16));
    listEl.appendChild(item);

    // Plot addresses (resolving coordinates as needed)
    for (const addr of addresses) {
      const coords = await resolveAddress(addr, hood, cache);
      if (!coords) continue;
      L.marker([coords.lat, coords.lng], { icon: addressIcon(hood.color) })
        .addTo(map)
        .bindPopup(
          `<div class="popup-card"><h3>${addr.label || "Spot"}</h3>` +
          `<p>${addr.address || ""}${addr.note ? "<br>" + addr.note : ""}</p></div>`
        );
    }
  }
}

document.addEventListener("DOMContentLoaded", init);
