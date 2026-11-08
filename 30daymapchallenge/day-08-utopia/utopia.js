/* #30DayMapChallenge · Day 8 · Utopia — Los Angeles.
 * Four utopian models, each paired with its measured outcome, plus the 1974 Concept diagram itself as a
 * rubber-sheeted, translucent overlay with a swipe divider. All figures come from data/stats.json. */

const OUT = {
  realised: { c: "#2a78d6", label: "Realised — ≥5 high-rises + rail" },
  towers:   { c: "#eb6834", label: "Towers, no rail" },
  rail:     { c: "#1baf7a", label: "Rail, no towers" },
  neither:  { c: "#9a9a96", label: "Neither — no towers, no Metro rail" },
};
const BUILT = [
  ["#3f8a2e", "Single-family house (1 unit)"],
  ["#80b340", "Single-family lot with 2+ units (ADU)"],
  ["#8d99a6", "Condo / PUD, or 2–4 units"],
  ["#2f3e4e", "5+ unit apartments"],
  ["#cdc7ba", "Commercial, industrial, other"],
];
const HOLC = { A: "#4f9a5a", B: "#3f86b5", C: "#c9a227", D: "#c0504d" };
const HOLC_LABEL = { A: "A · “Best”", B: "B · “Still desirable”", C: "C · “Definitely declining”", D: "D · “Hazardous”" };
const FATE = {
  abandoned: "Abandoned — plan never built",
  absorbed: "Absorbed into the suburb",
  built: "Built — survives as condominiums",
  privatised: "Built — cooperative dissolved",
  replaced: "Never built — site cleared & replaced",
};
const NB = { jobs: "job centre built low", transit: "transit close or coming", urban: "dense low-rise neighbourhood", suburban: "still suburban" };
const BASIN = [[33.70, -118.70], [34.34, -118.06]];
const fmt = (n) => (n == null ? "–" : n.toLocaleString("en-US"));
const mi = (m) => (m / 1609.34).toFixed(2);
async function getJSON(p) { const r = await fetch(p, { cache: "no-cache" }); return r.json(); }

async function init() {
  const map = L.map("ut-map", { zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 90, preferCanvas: true, maxZoom: 17 })
    .fitBounds(BASIN);
  map.zoomControl.setPosition("topright");
  const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
  L.tileLayer(ESRI + "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 17, maxNativeZoom: 16,
    attribution: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · data: LA City, LA County, Caltrans, LA Metro, Mapping Inequality',
  }).addTo(map);

  const PANES = ["plan", "tiles", "holc", "lines", "rail", "circles", "pts", "top", "sites"];
  PANES.forEach((p, i) => { map.createPane(p).style.zIndex = 300 + i * 20; });
  map.createPane("labels").style.zIndex = 470;
  map.getPane("labels").style.pointerEvents = "none";
  map.getPane("labels").style.opacity = "0.75";
  L.tileLayer(ESRI + "World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", { maxZoom: 17, maxNativeZoom: 16, pane: "labels" }).addTo(map);

  const names = ["stats", "city", "holc", "freeways", "aadt", "bottlenecks", "rail", "stations", "towers", "centers", "utopias"];
  const D = Object.fromEntries(await Promise.all(names.map(async (n) => [n, await getJSON(n === "stats" ? "data/stats.json" : `data/${n}.geojson`)])));
  const S = D.stats, C = S.centers, G = S.garden;

  /* ---------------- the 1974 plan: translucent overlay + swipe ---------------- */
  const planPane = map.getPane("plan");
  const plan = L.tileLayer("tiles/plan1974/{z}/{x}/{y}.webp", {
    pane: "plan", minZoom: 8, maxZoom: 17, minNativeZoom: 9, maxNativeZoom: 13, opacity: 0.75,
    bounds: L.latLngBounds([33.64, -118.78], [34.39, -118.02]), attribution: "1974 diagram: LA City Planning Dept. (Metro Research Library scan)",
  }).addTo(map);
  planPane.style.mixBlendMode = "multiply";
  const swipe = { on: true, x: 0.5 };
  const divider = document.createElement("div");
  divider.className = "swipe-divider";
  divider.innerHTML = '<span class="swipe-tag l">1974 plan</span><span class="swipe-tag r">today</span><button class="swipe-handle" aria-label="Drag to compare the 1974 plan with today">⟷</button>';
  map.getContainer().appendChild(divider);
  L.DomEvent.disableClickPropagation(divider); L.DomEvent.disableScrollPropagation(divider);
  function clipPlan() {
    const size = map.getSize();
    const nw = map.containerPointToLayerPoint([0, 0]), se = map.containerPointToLayerPoint(size);
    const x = swipe.on ? Math.round(size.x * swipe.x) : size.x;
    planPane.style.clip = swipe.on ? `rect(${nw.y}px, ${nw.x + x}px, ${se.y}px, ${nw.x}px)` : "";
    divider.style.left = `${x}px`;
    divider.style.display = swipe.on && map.hasLayer(plan) ? "" : "none";
    const r = document.getElementById("pc-swipe"); if (r) r.value = Math.round(swipe.x * 100);
  }
  let dragging = false;
  const handle = divider.querySelector(".swipe-handle");
  handle.addEventListener("pointerdown", (e) => { dragging = true; map.dragging.disable(); handle.setPointerCapture(e.pointerId); });
  handle.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const r = map.getContainer().getBoundingClientRect();
    swipe.x = Math.min(0.98, Math.max(0.02, (e.clientX - r.left) / r.width)); clipPlan();
  });
  const endDrag = () => { if (dragging) { dragging = false; map.dragging.enable(); } };
  handle.addEventListener("pointerup", endDrag);
  handle.addEventListener("pointercancel", endDrag);
  handle.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") { swipe.x = Math.min(0.98, Math.max(0.02, swipe.x + (e.key === "ArrowLeft" ? -0.03 : 0.03))); clipPlan(); e.preventDefault(); }
  });
  map.on("move zoom resize viewreset", clipPlan);
  const pc = document.getElementById("plan-controls");
  pc.innerHTML = `
    <label><input type="checkbox" id="pc-on" checked> 1974 plan overlay</label>
    <label>Opacity <input type="range" id="pc-op" min="0" max="100" value="75" aria-label="Plan opacity"></label>
    <label><input type="checkbox" id="pc-swipe-on" checked> Swipe</label>
    <label>Divider <input type="range" id="pc-swipe" min="2" max="98" value="50" aria-label="Swipe position"></label>
    <label><input type="checkbox" id="pc-blend" checked> Multiply blend (paper turns transparent)</label>`;
  pc.querySelector("#pc-on").addEventListener("change", (e) => { e.target.checked ? plan.addTo(map) : map.removeLayer(plan); clipPlan(); });
  pc.querySelector("#pc-op").addEventListener("input", (e) => plan.setOpacity(e.target.value / 100));
  pc.querySelector("#pc-swipe-on").addEventListener("change", (e) => { swipe.on = e.target.checked; clipPlan(); });
  pc.querySelector("#pc-swipe").addEventListener("input", (e) => { swipe.x = e.target.value / 100; clipPlan(); });
  pc.querySelector("#pc-blend").addEventListener("change", (e) => { planPane.style.mixBlendMode = e.target.checked ? "multiply" : "normal"; });

  /* ---------------- data layers ---------------- */
  const city = L.geoJSON(D.city, { pane: "lines", interactive: false, style: { color: "#14304a", weight: 1.4, dashArray: "4 4", fill: false, opacity: 0.7 } });
  const tb = L.latLngBounds([33.70, -118.68], [34.34, -118.15]);
  const built = L.tileLayer("tiles/built2026/{z}/{x}/{y}.webp", { pane: "tiles", minNativeZoom: 10, maxNativeZoom: 14, maxZoom: 17, opacity: 0.95, bounds: tb });
  const zoned = L.tileLayer("tiles/zonedsf/{z}/{x}/{y}.webp", { pane: "tiles", minNativeZoom: 10, maxNativeZoom: 14, maxZoom: 17, opacity: 0.9, bounds: tb });
  const holc = L.geoJSON(D.holc, { pane: "holc",
    style: (f) => ({ color: HOLC[f.properties.grade], weight: 1.5, fillColor: HOLC[f.properties.grade], fillOpacity: 0.1 }),
    onEachFeature: (f, l) => { const g = f.properties.grade, h = S.holc[g];
      l.bindPopup(`<div class="ut-pop"><p class="meta">HOLC, 1939 · area ${f.properties.id || ""} · Mapping Inequality</p><h4>Grade ${HOLC_LABEL[g]}</h4>
        <p>All ${g}-graded land in the City today: <b>${h.zoned_sf_pct}%</b> zoned single-family; <b>${h.built_sfr_parcel_pct}%</b> of residential parcels are single-family houses, holding <b>${h.sfr_units_pct}%</b> of the homes.</p></div>`); } });

  const fwy = L.geoJSON(D.freeways, { pane: "lines", interactive: false, style: { color: "#5b5f66", weight: 1.6, opacity: 0.75 } });
  const maxV = S.aadt.max.v, MINV = 100000;
  const aadtR = (v) => 1.5 + 8.5 * Math.sqrt(Math.max(0, v - MINV) / (maxV - MINV));
  const aadt = L.layerGroup(D.aadt.features.filter((f) => f.properties.v >= MINV).map((f) => {
    const p = f.properties, [lng, lat] = f.geometry.coordinates;
    return L.circleMarker([lat, lng], { pane: "pts", radius: aadtR(p.v), color: "#fff", weight: 0.8, fillColor: "#eb6834", fillOpacity: 0.75 })
      .bindPopup(`<div class="ut-pop"><p class="meta">Caltrans AADT 2024 · Route ${p.rte} · PM ${p.pm}</p><h4>${fmt(p.v)} vehicles / day</h4>
        <p>${p.at}<br>back ${fmt(p.b)} · ahead ${fmt(p.a)}</p></div>`);
  }));
  const bott = L.geoJSON(D.bottlenecks, { pane: "top",
    style: (f) => ({ color: "#e34948", weight: f.properties.rank <= 5 ? 6 : 4, opacity: 0.9, lineCap: "round" }),
    onEachFeature: (f, l) => { const p = f.properties;
      l.bindPopup(`<div class="ut-pop"><p class="meta">Caltrans D7 bottleneck #${p.rank}, calendar 2024 · ${p.shift} peak</p>
        <h4>${p.fwy} at ${p.at}</h4><p><b>${fmt(p.delay)}</b> vehicle-hours of delay on ${p.days} days · queue ≈ ${p.mi} mi upstream of PM ${p.pm}
        ${p.q2_2025 ? `<br>Still #${p.q2_2025} in 2025 Q2` : ""}</p></div>`);
      l.bindTooltip(`#${p.rank}`, { permanent: p.rank <= 3, direction: "right", className: "bn-label" }); } });

  const rail = L.geoJSON(D.rail, { pane: "rail", interactive: false, style: (f) => ({ color: f.properties.color, weight: 3, opacity: 0.9 }) });
  const SK = { open: ["#ffffff", null, 3.2], uc: ["#fbeede", "2 2", 4.5], bus: ["#c9d6e3", null, 2.6] };
  const stations = L.geoJSON(D.stations, { pane: "pts",
    filter: (f) => f.properties.k !== "plan",
    pointToLayer: (f, ll) => { const [fill, dash, r] = SK[f.properties.k];
      return L.circleMarker(ll, { radius: r, color: "#14304a", weight: 1.4, dashArray: dash, fillColor: fill, fillOpacity: 1 }); },
    onEachFeature: (f, l) => l.bindTooltip(`${f.properties.name}${f.properties.k === "open" ? " (open)" : f.properties.k === "bus" ? ` (${f.properties.line} busway)` : ` — ${f.properties.line}`}`, { direction: "top" }) });
  const towers = L.geoJSON(D.towers, { pane: "pts",
    pointToLayer: (f, ll) => { const p = f.properties, isNew = p.src === "LADBS CofO";
      return L.circleMarker(ll, { radius: 1.8 + (p.h || p.st * 12.5) / 420, stroke: isNew, color: "#eb6834", weight: 1.5, fillColor: "#14304a", fillOpacity: 0.8 }); },
    onEachFeature: (f, l) => { const p = f.properties;
      l.bindTooltip(p.src === "LADBS CofO" ? `${p.addr} · ${p.st} storeys${p.h ? ` · ${fmt(p.h)} ft` : ""} · CofO ${p.cofo}` : `${fmt(p.h)} ft (LARIAC 2020)`, { direction: "top" }); } });

  let strict = false;
  const ocOf = (p) => (strict ? p.strict : p.oc);
  const centerPopup = (p) => `<div class="ut-pop"><p class="meta">1974 Concept center · ${p.in_city ? "City of LA" : "outside the City"}</p>
    <h4>${p.name}</h4><p>Core: ${p.core}</p>
    <p><b>½ mi:</b> ${OUT[p.oc].label}${p.nb ? ` → <b>${NB[p.nb]}</b>` : ""}<br><b>¼ mi (the plan's own core):</b> ${OUT[p.strict].label}</p>
    <p>${fmt(p.jobs)} jobs (LODES 2023) · ${fmt(p.homes)} homes (${p.sfr_pct}% single-family) within ½ mi${p.mid ? ` · ${p.mid} more buildings of 120–149 ft` : ""}<br>Nearest Metrolink: ${p.ml}, ${fmt(p.ml_m)} m</p>
    <p>${p.tw} buildings ≥150 ft / ≥12 storeys within ½ mi (${p.twq} within ¼ mi${p.twnew ? `; ${p.twnew} completed since 2020` : ""})${p.hmax ? ` · tallest ${fmt(p.hmax)} ft` : ""}<br>
    Nearest open rail: ${p.near} — ${fmt(p.near_m)} m (${mi(p.near_m)} mi)${p.uc ? `<br>Under construction: ${p.uc}` : ""}${p.bus ? `<br>Busway: ${p.bus}` : ""}</p>
    <p class="meta">Drawn ${fmt(p.off)} m from this core on the 1974 diagram</p></div>`;
  const halfStyle = (f) => { const oc = ocOf(f.properties), n = oc === "neither";
    return { color: n ? "#77776f" : "#14304a", weight: n ? 1.3 : 1.1, dashArray: n ? "3 3" : null, opacity: 0.8,
      fillColor: OUT[oc].c, fillOpacity: n ? 0.06 : (f.properties.rail === "building" ? 0.3 : 0.45) }; };
  const centerHalf = L.geoJSON(D.centers, { pane: "circles", style: halfStyle,
    pointToLayer: (f, ll) => L.circle(ll, { radius: 804.7 }),
    onEachFeature: (f, l) => { l.bindPopup(centerPopup(f.properties)); l.bindTooltip(f.properties.name, { direction: "top", sticky: true }); } });
  const centerQuarter = L.geoJSON(D.centers, { pane: "circles", interactive: false,
    pointToLayer: (f, ll) => L.circle(ll, { radius: 402.3, color: "#14304a", weight: 1, fill: false, opacity: 0.9, dashArray: "1 3" }) });
  const centerCore = L.geoJSON(D.centers, { pane: "pts", interactive: false,
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 2.2, stroke: false, fillColor: "#14304a", fillOpacity: 1 }) });
  const drawn = L.layerGroup(D.centers.features.flatMap((f) => {
    const [x, y] = f.geometry.coordinates, [dx, dy] = f.properties.drawn;
    return [L.polyline([[dy, dx], [y, x]], { pane: "circles", color: "#c0392b", weight: 1, opacity: 0.8, interactive: false }),
            L.circleMarker([dy, dx], { pane: "circles", radius: 4, color: "#c0392b", weight: 1.5, fill: false, interactive: false })];
  }));
  const centers = L.layerGroup([centerHalf, centerQuarter, centerCore]);

  const siteIdx = {};
  const siteShapes = L.geoJSON({ type: "FeatureCollection", features: D.utopias.features.filter((f) => f.properties.shape) },
    { pane: "sites", interactive: false, style: { color: "#c1632e", weight: 2, fillColor: "#c1632e", fillOpacity: 0.25 } });
  const pins = D.utopias.features.filter((f) => !f.properties.shape);
  const pinMarkers = pins.map((f, i) => {
    const p = f.properties, [lng, lat] = f.geometry.coordinates;
    const m = L.marker([lat, lng], { pane: "sites",
      icon: L.divIcon({ className: "u-marker", html: `<span>${i + 1}</span>`, iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12] }) })
      .bindPopup(`<div class="ut-pop"><p class="meta">${p.years} · ${FATE[p.fate]}</p><h4>${p.name}</h4>
        <p><b>Ideal.</b> ${p.ideal}</p><p><b>Reality.</b> ${p.reality}</p><p class="meta">Footprint: ${p.geomnote}</p></div>`, { maxWidth: 330 });
    siteIdx[p.id] = m; return m; });
  const sites = L.layerGroup([siteShapes, ...pinMarkers]);

  /* ---------------- modes ---------------- */
  const all = [built, zoned, holc, fwy, aadt, bott, rail, stations, towers, centers, drawn, sites];
  const opt = { holc: false, towers: true, rail: true, drawn: false, gview: "built" };
  const panel = document.getElementById("ut-panel");
  const legendOutcomes = () => Object.entries(OUT).map(([k, o]) =>
    `<div class="row"><span class="sw" style="background:${k === "neither" ? "transparent" : o.c};${k === "neither" ? "border-style:dashed;border-color:#77776f" : ""}"></span>${o.label}
      <b style="margin-left:auto">${(strict ? C.outcomes_quarter_mile : C.outcomes_half_mile)[k] || 0}</b></div>`).join("");
  const toggle = (k, label) => `<label><input type="checkbox" data-opt="${k}" ${opt[k] ? "checked" : ""}> ${label}</label>`;
  const builtLegend = () => BUILT.map(([c, t]) => `<div class="row"><span class="sq" style="background:${c}"></span>${t}</div>`).join("");

  const MODES = {
    all: {
      bounds: BASIN,
      layers: () => [zoned, fwy, bott, rail, centers, sites],
      html: () => `<p class="kicker">Overlay</p><h3>Four utopias, stacked</h3>
        <p>Drag the divider: left of it, the 1974 plan sits under today's evidence. Green = land zoned single-family (Nov 2026);
        grey = freeways, red = the 20 worst bottlenecks of 2024; discs = the plan's 56 centers, coloured by what they became; numbered pins = cooperative experiments.</p>
        <div class="stats">
          <div class="stat"><b>${G.sf_share_of_residential_zoned_land}%</b><span>of residential-zoned land is single-family…</span></div>
          <div class="stat"><b>${G.sfr_share_of_all_units}%</b><span>…but those houses hold this share of the City's ${fmt(G.units_total)} homes</span></div>
          <div class="stat"><b>${C.outcomes_half_mile.realised} / ${C.n}</b><span>plan centers with towers <em>and</em> rail (½ mi)</span></div>
          <div class="stat"><b>${fmt(S.aadt.max.v)}</b><span>vehicles/day, I-10 at Vermont (2024 peak)</span></div>
        </div>
        <div class="legend">${legendOutcomes()}
          <div class="row"><span class="sq" style="background:#3f8a2e;opacity:.55"></span>Zoned single-family (R1/RS/RE/RW1/RZ/RA)</div>
          <div class="row"><span class="ln" style="border-color:#5b5f66;border-top-width:2px"></span>Freeways</div>
          <div class="row"><span class="ln" style="border-color:#e34948;border-top-width:5px"></span>Top-20 bottlenecks, 2024</div>
          <div class="row"><span class="sw" style="background:#c1632e;border-color:#fff"></span>Social-utopia sites</div></div>`,
    },
    garden: {
      bounds: [[33.70, -118.67], [34.34, -118.15]],
      layers: () => [opt.gview === "built" ? built : zoned, ...(opt.holc ? [holc] : [])],
      html: () => `<p class="kicker">Model 1 · from 1904</p><h3>The garden suburb</h3>
        <dl class="iv"><dt>Ideal</dt><dd>A city of homes: a detached house, a yard and a car for every family, spread across the basin.</dd>
        <dt>Reality</dt><dd>The ideal owns the land but not the people: three-quarters of residential land, under a third of the homes. It survives most purely where the 1939 appraisers wrote “best”.</dd></dl>
        <div class="seg" role="group" aria-label="Garden suburb view">
          <button data-gview="built" class="${opt.gview === "built" ? "on" : ""}">Built · 2026 roll</button>
          <button data-gview="zoned" class="${opt.gview === "zoned" ? "on" : ""}">Zoned · Nov 2026</button></div>
        <div class="stats">
          <div class="stat"><b>${G.sf_share_of_residential_zoned_land}%</b><span>of residential-zoned land is single-family</span></div>
          <div class="stat"><b>${G.sfr_share_of_residential_parcels}%</b><span>of residential parcels are single-family houses</span></div>
          <div class="stat"><b>${G.sfr_share_of_all_units}%</b><span>of the City's ${fmt(G.units_total)} homes are in them</span></div>
          <div class="stat"><b>${fmt(G.sfr_parcels_with_2plus_units)}</b><span>single-family lots now carry 2+ units</span></div>
        </div>
        <div class="legend">${opt.gview === "built" ? `Every City parcel, 2026 Assessor roll (dot at the Assessor's centroid)${builtLegend()}` :
          `<div class="row"><span class="sq" style="background:#3f8a2e;opacity:.55"></span>Zoned single-family: R1, RS, RE, RW1, RZ (+ variants) and RA</div>`}
          ${opt.holc ? Object.entries(HOLC).map(([g, c]) => `<div class="row"><span class="sq" style="border:2px solid ${c};background:${c}22"></span>${HOLC_LABEL[g]} — ${S.holc[g].zoned_sf_pct}% zoned SF · ${S.holc[g].sfr_units_pct}% of homes in houses</div>`).join("") : ""}</div>
        <div class="toggles">${toggle("holc", "Overlay the 1939 HOLC grades (Mapping Inequality)")}</div>
        <p class="src">LA County Assessor roll 2026 (805,901 City parcels, official use types); City zoning layer edited 5 Nov 2026. City of LA only. Zoom in: the dots resolve to individual lots.</p>`,
    },
    autopia: {
      bounds: [[33.72, -118.62], [34.32, -117.95]],
      layers: () => [fwy, aadt, bott],
      html: () => `<p class="kicker">Model 2 · 1940 → 1971</p><h3>Autopia</h3>
        <dl class="iv"><dt>Ideal</dt><dd>Frictionless movement across an unbounded basin — the planners' parkways (1940) and freeway plan (1959), then Banham's 1971 celebration of the freeway as a way of life.</dd>
        <dt>Reality</dt><dd>Built, and used to saturation. The region's worst queue still forms where the first freeway begins.</dd></dl>
        <div class="stats">
          <div class="stat"><b>${fmt(S.aadt.max.v)}</b><span>vehicles/day — I-10 at Vermont Ave, Caltrans 2024 peak</span></div>
          <div class="stat"><b>${S.aadt.ge_300k}</b><span>freeway count points above 300,000/day (2024)</span></div>
          <div class="stat"><b>${(S.bottlenecks.delay_2024_top20_veh_hrs / 1e6).toFixed(1)} M</b><span>vehicle-hours lost at the 20 worst bottlenecks, 2024</span></div>
          <div class="stat"><b>#1</b><span>110 north at Solano Ave — 2024, and again in 2025 Q2</span></div>
        </div>
        <div class="legend">
          <div class="row">${[150000, 250000, 345000].map((v) => `<span class="sw" style="background:#eb6834;border:1px solid #fff;width:${2 * aadtR(v)}px;height:${2 * aadtR(v)}px"></span>${v / 1000}k`).join(" ")}&nbsp;vehicles/day (every 2024 freeway count point ≥100k)</div>
          <div class="row"><span class="ln" style="border-color:#e34948;border-top-width:5px"></span>Top-20 recurrent bottlenecks, calendar 2024 (queue drawn upstream of the head postmile)</div>
          <div class="row"><span class="ln" style="border-color:#5b5f66;border-top-width:2px"></span>Interstates &amp; other freeways</div></div>
        <p class="src">Caltrans Traffic Census AADT 2024; Caltrans District 7 Mobility Performance Report (pub. 2025), located on Caltrans tenth-mile postmiles. Caveat: 77.7% of D7 loop detectors were offline in Q4 2024, so delay partly relies on imputation.</p>`,
    },
    centers: {
      bounds: [[33.72, -118.64], [34.30, -118.10]],
      layers: () => [fwy, ...(opt.rail ? [rail, stations] : []), centers, ...(opt.towers ? [towers] : []), ...(opt.drawn ? [drawn] : [])],
      html: () => `<p class="kicker">Model 3 · 1970 / 1974</p><h3>The Centers Concept</h3>
        <dl class="iv"><dt>Ideal</dt><dd>If not one downtown, then 56: high-rise cores ~¼ mile around rapid-transit stations, the single-family suburbs between them left alone.</dd>
        <dt>Reality</dt><dd>The towers mostly went where the plan said; the trains came decades later, often to different centers.</dd></dl>
        <div class="seg" role="group" aria-label="Catchment test">
          <button data-strict="0" class="${strict ? "" : "on"}">½-mile test</button><button data-strict="1" class="${strict ? "on" : ""}">¼-mile (the plan's own core)</button></div>
        <div class="stats">
          <div class="stat"><b>${(strict ? C.outcomes_quarter_mile : C.outcomes_half_mile).realised} / ${C.n}</b><span>centers with ≥5 high-rises <em>and</em> open rail</span></div>
          <div class="stat"><b>${(strict ? C.outcomes_quarter_mile : C.outcomes_half_mile).neither}</b><span>centers with neither</span></div>
          <div class="stat"><b>${Math.round((strict ? C.city_towers_in_quarter : C.city_towers_in_half) / C.city_towers * 100)}%</b><span>of the City's ${C.city_towers} high-rises sit in plan centers…</span></div>
          <div class="stat"><b>${strict ? C.quarter_share_of_city_land : C.half_share_of_city_land}%</b><span>…which cover this share of its land</span></div>
        </div>
        <div class="legend">${legendOutcomes()}
          <div class="row"><span class="sw" style="background:transparent;border:1px dotted #14304a"></span>¼-mile core ring · dot = exact core intersection</div>
          <div class="row"><span class="sw" style="background:#fbeede;border:1.5px dashed #14304a;width:10px;height:10px"></span>Station under construction (paler disc: rail due 2027–31)</div>
          <div class="row"><span class="sw" style="background:#c9d6e3;border:1.5px solid #14304a;width:8px;height:8px"></span>Busway station (G / J Line)</div>
          <div class="row"><span class="sw" style="background:#14304a;border:1.5px solid #eb6834;width:8px;height:8px"></span>High-rise completed 2020–26 (LADBS); plain = LARIAC 2020</div></div>
        <div class="toggles">${toggle("towers", "High-rises (≥150 ft or ≥12 storeys)")}${toggle("rail", "Metro rail, busway &amp; construction")}${toggle("drawn", "Where the 1974 diagram drew each center")}</div>
        <p class="src">Cores: exact street-centerline intersections (County CAMS, Nov 2026). Rail: Metro GTFS 7 Nov 2026 + Metro's construction layer. Full list in the table below the map.</p>`,
    },
    social: {
      bounds: null,
      layers: () => [sites],
      html: () => `<p class="kicker">Model 4 · 1913 → 1962</p><h3>Social utopias</h3>
        <dl class="iv"><dt>Ideal</dt><dd>Cooperative colonies and planned communities that would change how people lived together, not only where.</dd>
        <dt>Reality</dt><dd>None survives as a social form. The survivors are buildings; the site cleared outright is now ${S.dodger_site_acres} acres of stadium and parking.</dd></dl>
        <ul class="site-list">${pins.map((f, i) => `<li data-site="${f.properties.id}"><span class="num">${i + 1}</span><span><b>${f.properties.name}</b> <span style="color:#6a7682">${f.properties.years}</span><span class="fate">${FATE[f.properties.fate]}</span></span></li>`).join("")}</ul>
        <p class="src">Footprints: City Historic-Cultural Monument layer (Nov 2026) and Assessor parcels; Llano del Rio at California Historical Landmark No. 933. Click a row to fly there.</p>`,
    },
  };

  let mode = "all";
  function render(newMode, refit = true) {
    mode = newMode;
    const M = MODES[mode];
    all.forEach((l) => map.hasLayer(l) && map.removeLayer(l));
    city.addTo(map);
    M.layers().forEach((l) => l.addTo(map));
    centerHalf.setStyle(halfStyle);
    panel.innerHTML = M.html();
    if (refit) {
      if (M.bounds) map.flyToBounds(M.bounds, { duration: 0.6 });
      else map.flyToBounds(L.featureGroup(pinMarkers).getBounds().pad(0.12), { duration: 0.6 });
    }
    panel.querySelectorAll("input[data-opt]").forEach((el) => el.addEventListener("change", () => { opt[el.dataset.opt] = el.checked; render(mode, false); }));
    panel.querySelectorAll("[data-gview]").forEach((el) => el.addEventListener("click", () => { opt.gview = el.dataset.gview; render(mode, false); }));
    panel.querySelectorAll("[data-strict]").forEach((el) => el.addEventListener("click", () => { strict = el.dataset.strict === "1"; render(mode, false); }));
    panel.querySelectorAll("[data-site]").forEach((el) => el.addEventListener("click", () => {
      const m = siteIdx[el.dataset.site]; map.flyTo(m.getLatLng(), 15, { duration: 0.8 }); setTimeout(() => m.openPopup(), 850); }));
    document.querySelectorAll(".ut-tab").forEach((b) => { const on = b.dataset.mode === mode; b.classList.toggle("is-active", on); b.setAttribute("aria-selected", on); });
    clipPlan();
  }
  document.querySelectorAll(".ut-tab").forEach((b) => b.addEventListener("click", () => render(b.dataset.mode)));

  /* ---------------- centers table (relief for colour-only encoding) ---------------- */
  const rows = D.centers.features.map((f) => f.properties);
  const tbody = document.querySelector("#ct tbody");
  const ORDER = { realised: 0, towers: 1, rail: 2, neither: 3 };
  let sortK = "oc", asc = true;
  function drawTable() {
    rows.sort((a, b) => {
      let x = a[sortK], y = b[sortK];
      if (sortK === "oc" || sortK === "strict") { x = ORDER[x]; y = ORDER[y]; }
      if (sortK === "nb") { const NO = { jobs: 0, transit: 1, urban: 2, suburban: 3 }; x = NO[x] ?? 9; y = NO[y] ?? 9; }
      if (typeof x === "string") return asc ? x.localeCompare(y) : y.localeCompare(x);
      return asc ? x - y : y - x;
    });
    const dot = (k) => `<span class="dot" style="background:${k === "neither" ? "transparent" : OUT[k].c}"></span>${OUT[k].label.split(" —")[0]}`;
    tbody.innerHTML = rows.map((p) => `<tr><td>${p.name}</td><td>${p.core}</td><td>${dot(p.oc)}</td><td>${dot(p.strict)}</td>
      <td class="num">${p.tw}</td><td class="num">${p.twq}</td><td class="num">${p.hmax ? fmt(p.hmax) : "–"}</td>
      <td class="num">${fmt(p.near_m)}</td><td>${p.rail === "open" ? "open" : p.rail === "building" ? "building" : "–"}</td>
      <td class="num">${fmt(p.jobs)}</td><td class="num">${fmt(p.homes)}</td><td>${p.nb ? NB[p.nb] : ""}</td></tr>`).join("");
  }
  document.querySelectorAll("#ct th").forEach((th) => th.addEventListener("click", () => {
    const k = th.dataset.k; asc = sortK === k ? !asc : ["name", "core", "oc", "strict", "near_m", "nb"].includes(k); sortK = k; drawTable(); }));
  drawTable();
  render("all", false);
}

document.addEventListener("DOMContentLoaded", init);
