/* Places — main page logic.
 * Loads the central data file (data/places.json) and renders:
 *   1. an interactive Leaflet map with one marker per place
 *   2. a filterable gallery grid below the map
 * Adding a place is just adding an entry to data/places.json. */

const TYPE_COLORS = {
  visited: "#c1632e",
  studied: "#2a6f97",
  both: "#6a7b53",
};

/* A place can be visited, studied, or both. Derive a single "kind"
 * for marker colouring from its tags. */
function placeKind(place) {
  const tags = place.tags || [];
  const visited = tags.includes("visited");
  const studied = tags.includes("studied");
  if (visited && studied) return "both";
  if (studied) return "studied";
  return "visited";
}

function makeMarkerIcon(kind) {
  const color = TYPE_COLORS[kind] || TYPE_COLORS.visited;
  return L.divIcon({
    className: "place-marker",
    html: `<span style="
      display:block;width:18px;height:18px;border-radius:50%;
      background:${color};border:3px solid #fff;
      box-shadow:0 1px 5px rgba(0,0,0,.4);"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -10],
  });
}

function tagPills(tags) {
  return (tags || [])
    .filter((t) => t === "visited" || t === "studied")
    .map((t) => `<span class="tag tag-${t}">${t}</span>`)
    .join("");
}

function buildCard(place) {
  const a = document.createElement("a");
  a.className = "card";
  a.href = place.page || "#";
  a.dataset.tags = (place.tags || []).join(",");

  const cover = place.image
    ? `style="background-image:url('${place.image}')"`
    : "";

  a.innerHTML = `
    <div class="card-cover" ${cover}></div>
    <div class="card-body">
      <h3 class="card-title">${place.name}</h3>
      <p class="card-place">${place.country || ""}${place.year ? " · " + place.year : ""}</p>
      <p class="card-summary">${place.summary || ""}</p>
      <div class="card-tags">${tagPills(place.tags)}</div>
    </div>`;
  return a;
}

function buildPopup(place) {
  return `
    <div class="popup-card">
      <h3>${place.name}</h3>
      <p>${place.country || ""}${place.year ? " · " + place.year : ""}</p>
      ${place.page ? `<a href="${place.page}">Explore &rarr;</a>` : ""}
    </div>`;
}

async function init() {
  const map = L.map("map", {
    scrollWheelZoom: true,   // zoom with the mouse wheel / trackpad
    wheelPxPerZoomLevel: 80, // smoother, less jumpy wheel zoom
    zoomSnap: 0.25,          // finer zoom increments
    zoomDelta: 0.5,
    worldCopyJump: true,     // seamless panning across the date line
  }).setView([30, 15], 2);
  map.zoomControl.setPosition("topright");
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 20,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  }).addTo(map);

  let data;
  try {
    const res = await fetch("data/places.json", { cache: "no-cache" });
    data = await res.json();
  } catch (err) {
    console.error("Could not load places.json", err);
    return;
  }

  const places = (data && data.places) || [];
  const gallery = document.getElementById("gallery");
  const emptyState = document.getElementById("empty-state");
  const bounds = [];

  places.forEach((place) => {
    if (typeof place.lat === "number" && typeof place.lng === "number") {
      const marker = L.marker([place.lat, place.lng], {
        icon: makeMarkerIcon(placeKind(place)),
      }).addTo(map);
      marker.bindPopup(buildPopup(place));
      bounds.push([place.lat, place.lng]);
    }
    gallery.appendChild(buildCard(place));
  });

  if (bounds.length === 1) {
    map.setView(bounds[0], 5);
  } else if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [50, 50] });
  }

  /* Filters */
  const buttons = document.querySelectorAll(".filter");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      const filter = btn.dataset.filter;
      let visible = 0;
      gallery.querySelectorAll(".card").forEach((card) => {
        const tags = card.dataset.tags.split(",");
        const show = filter === "all" || tags.includes(filter);
        card.style.display = show ? "" : "none";
        if (show) visible++;
      });
      emptyState.hidden = visible !== 0;
    });
  });
}

document.addEventListener("DOMContentLoaded", init);
