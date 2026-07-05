/* Syros — historical evolution time-slider map (MapLibre GL JS).
 *
 * The analytical spine: settlement points filtered by the slider year and
 * coloured by `founding_driver` (defensive_citadel / piracy_refuge /
 * commercial_port / sanctuary). The frame card narrates the naming +
 * cartographic record per period. Pre-modern charts are NOT projected here
 * (per the brief's hard rule); the card cites them unwarped instead.
 *
 * Base map: CARTO Positron raster (no key). Historical raster tiles (F7,
 * georeferenced) would be added as additional raster sources once the manual
 * GCP step is done. */

const BBOX = [24.85, 37.37, 25.0, 37.52];
const START_YEAR = 1537;

function fmtYear(y) {
  y = Math.round(y);
  return y < 0 ? `${-y} BC` : `${y} AD`;
}
const ongoing = (pe) => (pe === null || pe === undefined ? 3000 : pe);

let DATA, FRAMES, map, markersById = {};

function activeFrame(year) {
  const fr = FRAMES.frames;
  for (const f of fr) if (year >= f.period_start && year < f.period_end) return f;
  return year < fr[0].period_start ? fr[0] : fr[fr.length - 1];
}

function renderFrameCard(year) {
  const f = activeFrame(year);
  document.getElementById("frame-badge").textContent = `${f.id} · ${f.name}`;
  const c = f.carto || {};
  const planimTag = c.planimetric === true
    ? `<span class="planim planim-yes">planimetric → georeference</span>`
    : c.planimetric === "semi"
      ? `<span class="planim planim-semi">semi — unwarped</span>`
      : c.planimetric === false
        ? `<span class="planim planim-no">pictorial — unwarped</span>`
        : "";
  const cartoBlock = c.title
    ? `<div class="fc-carto"><b>Cartographic record</b>${planimTag}<br>${c.title}` +
      (c.repo ? `<br><span style="opacity:.8">${c.repo}${c.license ? " · " + c.license : ""}</span>` : "") +
      (c.note ? `<br>${c.note}` : "") +
      (c.browse ? `<br><a href="${c.browse}" target="_blank" rel="noopener">Browse charts ↗</a>` : "") +
      `</div>`
    : "";
  document.getElementById("frame-card").innerHTML =
    `<h3>${f.id} · ${f.name}</h3>` +
    `<div class="fc-period">${f.period_label}</div>` +
    `<div class="fc-row">Island named: <span class="fc-name">${f.island_name}</span></div>` +
    `<div class="fc-row"><b>Control:</b> ${f.control}</div>` +
    `<div class="fc-row"><b>Settlement focus:</b> ${f.settlement_focus}</div>` +
    cartoBlock;

  document.querySelectorAll(".frame-tick").forEach((t) =>
    t.classList.toggle("is-active", t.dataset.id === f.id));
}

function renderLegend() {
  const d = FRAMES.drivers;
  document.getElementById("legend").innerHTML =
    `<h4>Founding driver <span style="font-weight:400;color:#8a949e">(the thesis)</span></h4>` +
    Object.keys(d).map((k) =>
      `<div class="lg-row"><span class="lg-dot" style="background:${d[k].color}"></span>${d[k].label}</div>`).join("") +
    `<div class="lg-row" style="margin-top:6px"><span class="lg-dot" style="background:#fff;border:2px solid var(--terracotta)"></span>★ tagged sea-event</div>`;
}

function activeFeatures(year) {
  return DATA.features.filter((f) => {
    const p = f.properties;
    return p.period_start <= year && ongoing(p.period_end) >= year;
  });
}

function renderActiveList(year) {
  const el = document.getElementById("active-list");
  const feats = activeFeatures(year);
  if (!feats.length) { el.innerHTML = `<li style="cursor:default;color:#8a949e">No settlement recorded at ${fmtYear(year)}.</li>`; return; }
  const d = FRAMES.drivers;
  el.innerHTML = feats.map((f) => {
    const p = f.properties;
    const color = (d[p.founding_driver] || {}).color || "#888";
    const end = p.period_end === null ? "ongoing" : fmtYear(p.period_end);
    return `<li data-name="${p.name}">` +
      `<span class="al-dot" style="background:${color}"></span>` +
      `<span><span class="al-name">${p.name}${p.approx ? " ~" : ""}</span>` +
      `<span class="al-meta">${p.control} · ${fmtYear(p.period_start)}–${end}</span>` +
      (p.event ? `<span class="al-event">★ ${p.event}</span>` : "") + `</span></li>`;
  }).join("");
  el.querySelectorAll("li[data-name]").forEach((li) => {
    li.addEventListener("click", () => {
      const f = DATA.features.find((x) => x.properties.name === li.dataset.name);
      if (!f) return;
      map.flyTo({ center: f.geometry.coordinates, zoom: 14 });
      openPopup(f);
    });
  });
}

function popupHTML(f) {
  const p = f.properties;
  const end = p.period_end === null ? "ongoing" : fmtYear(p.period_end);
  return `<div class="sp-pop"><h3>${p.name}</h3>` +
    `<p>${p.type.replace(/_/g, " ")} · ${fmtYear(p.period_start)}–${end}</p>` +
    `<p><b>Control:</b> ${p.control}</p>` +
    `<p><b>Driver:</b> ${(FRAMES.drivers[p.founding_driver] || {}).label || p.founding_driver}</p>` +
    (p.event ? `<p class="sp-event">★ ${p.event}</p>` : "") +
    `<p style="opacity:.7">Source: ${p.source}${p.approx ? " · approx." : ""}</p></div>`;
}
function openPopup(f) {
  new maplibregl.Popup({ offset: 14 }).setLngLat(f.geometry.coordinates).setHTML(popupHTML(f)).addTo(map);
}

function updateFilter(year) {
  const filter = ["all",
    ["<=", ["get", "period_start"], year],
    [">=", ["coalesce", ["get", "period_end"], 3000], year],
  ];
  ["pts", "pts-event"].forEach((id) => { if (map.getLayer(id)) map.setFilter(id, id === "pts-event" ? ["all", filter, ["!=", ["get", "event"], null]] : filter); });
}

function setYear(year) {
  year = Math.round(year);
  document.getElementById("year-readout").textContent = fmtYear(year);
  document.getElementById("year-slider").value = year;
  updateFilter(year);
  renderFrameCard(year);
  renderActiveList(year);
}

function buildTicks() {
  const el = document.getElementById("frame-ticks");
  el.innerHTML = FRAMES.frames.map((f) =>
    `<button class="frame-tick" data-id="${f.id}" data-year="${f.period_start}" title="${f.name} · ${f.period_label}">${f.id}</button>`).join("");
  el.querySelectorAll(".frame-tick").forEach((t) =>
    t.addEventListener("click", () => setYear(+t.dataset.year + 1)));
}

const driverColorExpr = (drivers) => {
  const expr = ["match", ["get", "founding_driver"]];
  Object.keys(drivers).forEach((k) => { expr.push(k, drivers[k].color); });
  expr.push("#888");
  return expr;
};

async function init() {
  [DATA, FRAMES] = await Promise.all([
    fetch("settlements.geojson", { cache: "no-cache" }).then((r) => r.json()),
    fetch("frames.json", { cache: "no-cache" }).then((r) => r.json()),
  ]);

  const style = {
    version: 8,
    sources: {
      positron: {
        type: "raster",
        tiles: ["https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      },
    },
    layers: [{ id: "base", type: "raster", source: "positron" }],
  };

  map = new maplibregl.Map({
    container: "syros-map", style,
    bounds: [[BBOX[0], BBOX[1]], [BBOX[2], BBOX[3]]], fitBoundsOptions: { padding: 30 },
    attributionControl: true,
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");
  map.scrollZoom.enable();

  map.on("load", () => {
    map.addSource("settlements", { type: "geojson", data: DATA });
    map.addLayer({
      id: "pts", type: "circle", source: "settlements",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 6, 14, 11],
        "circle-color": driverColorExpr(FRAMES.drivers),
        "circle-stroke-width": 2, "circle-stroke-color": "#fff",
      },
    });
    // event ring highlight
    map.addLayer({
      id: "pts-event", type: "circle", source: "settlements",
      filter: ["!=", ["get", "event"], null],
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 12, 14, 18],
        "circle-color": "rgba(0,0,0,0)",
        "circle-stroke-width": 2.5, "circle-stroke-color": "#c1632e",
      },
    });
    map.on("click", "pts", (e) => {
      const f = DATA.features.find((x) => x.properties.name === e.features[0].properties.name);
      if (f) openPopup(f);
    });
    map.on("mouseenter", "pts", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "pts", () => { map.getCanvas().style.cursor = ""; });

    buildTicks();
    renderLegend();
    setYear(START_YEAR);
  });

  // slider + play
  document.getElementById("year-slider").addEventListener("input", (e) => setYear(+e.target.value));
  let playing = null;
  document.getElementById("play").addEventListener("click", (e) => {
    if (playing) { clearInterval(playing); playing = null; e.target.textContent = "▶"; return; }
    e.target.textContent = "⏸";
    playing = setInterval(() => {
      let y = +document.getElementById("year-slider").value;
      // accelerate through the empty antiquity, slow down in the dense modern era
      y += y < 1000 ? 60 : 12;
      if (y >= 2025) { y = 2025; clearInterval(playing); playing = null; e.target.textContent = "▶"; }
      setYear(y);
    }, 120);
  });
}

document.addEventListener("DOMContentLoaded", init);
