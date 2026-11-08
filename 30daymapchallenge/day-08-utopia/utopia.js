/* #30DayMapChallenge · Day 8 · Utopia — Los Angeles.
 * Four utopian models, each paired with its measured outcome.
 * Data are pre-built (see scripts/) into data/*.geojson; stats.json holds every quoted figure. */

const OUT = {
  realised: { c: "#2a78d6", label: "Realised — ≥5 high-rises + rail" },
  towers:   { c: "#eb6834", label: "Towers, no rail" },
  rail:     { c: "#1baf7a", label: "Rail, no towers" },
  neither:  { c: "#9a9a96", label: "Neither — still suburban" },
};
const GREEN = ["#f1f4ea", "#d7e3c3", "#b5cd97", "#8db26b", "#5f8f43", "#356b26"];
const GREEN_BREAKS = [0.1, 0.3, 0.5, 0.7, 0.85];
const HOLC = { A: "#4f9a5a", B: "#3f86b5", C: "#c9a227", D: "#c0504d" };
const HOLC_LABEL = { A: "A · “Best”", B: "B · “Still desirable”", C: "C · “Declining”", D: "D · “Hazardous”" };
const FATE = {
  abandoned: "Abandoned — plan never built",
  absorbed: "Absorbed into the suburb",
  built: "Built — survives as condominiums",
  privatised: "Built — cooperative dissolved",
  replaced: "Never built — site cleared & replaced",
};
const BASIN = [[33.70, -118.70], [34.34, -118.06]];

const fmt = (n) => n.toLocaleString("en-US");
const greenFor = (v) => { let i = 0; while (i < GREEN_BREAKS.length && v >= GREEN_BREAKS[i]) i++; return GREEN[i]; };

async function getJSON(p) { const r = await fetch(p, { cache: "no-cache" }); return r.json(); }

async function init() {
  const map = L.map("ut-map", { zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 90, preferCanvas: true })
    .fitBounds(BASIN);
  map.zoomControl.setPosition("topright");
  const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
  L.tileLayer(ESRI + "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16,
    attribution: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · data: LA City, LA County, Caltrans, LA Metro',
  }).addTo(map);
  map.createPane("labels").style.zIndex = 470;
  map.getPane("labels").style.pointerEvents = "none";
  map.getPane("labels").style.opacity = "0.75";
  L.tileLayer(ESRI + "World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", { maxZoom: 16, pane: "labels" }).addTo(map);

  ["hex", "holc", "lines", "rail", "circles", "pts", "top", "sites"].forEach((p, i) => {
    map.createPane(p).style.zIndex = 390 + i * 10;
  });

  const names = ["stats", "city", "sf_hex", "holc", "freeways", "aadt", "bottlenecks", "rail", "stations", "towers", "centers", "utopias"];
  const D = Object.fromEntries(await Promise.all(names.map(async (n) => [n, await getJSON(n === "stats" ? "data/stats.json" : `data/${n}.geojson`)])));
  const S = D.stats;

  /* ---------------- layers ---------------- */
  const city = L.geoJSON(D.city, { pane: "lines", interactive: false,
    style: { color: "#14304a", weight: 1.4, dashArray: "4 4", fill: false, opacity: 0.7 } });

  const hex = L.geoJSON(D.sf_hex, { pane: "hex",
    style: (f) => ({ fillColor: greenFor(f.properties.sf), fillOpacity: 0.8, color: "#fff", weight: 0.4, opacity: 0.6 }),
    onEachFeature: (f, l) => {
      const p = f.properties;
      l.bindPopup(`<div class="ut-pop"><p class="meta">≈1 km² hexagon · City zoning</p>
        <h4>${Math.round(p.sf * 100)}% of zoned land is single-family</h4>
        <p>${p.sfr == null ? "No residential zoning here." : `Of the residential land, <b>${Math.round(p.sfr * 100)}%</b> is single-family.`}
        ${p.os > 0.2 ? `<br>${Math.round(p.os * 100)}% open space / agricultural.` : ""}</p></div>`);
    } });

  const holc = L.geoJSON(D.holc, { pane: "holc",
    style: (f) => ({ color: HOLC[f.properties.grade], weight: 1.6, fillColor: HOLC[f.properties.grade], fillOpacity: 0.12 }),
    onEachFeature: (f, l) => l.bindPopup(`<div class="ut-pop"><p class="meta">HOLC, 1939 · ${f.properties.id || ""}</p><h4>Grade ${HOLC_LABEL[f.properties.grade]}</h4>
      <p>Today, ${S.holc_sf_share_today[f.properties.grade]}% of all ${f.properties.grade}-graded land in the City is still zoned single-family.</p></div>`) });

  const fwy = L.geoJSON(D.freeways, { pane: "lines", interactive: false, style: { color: "#5b5f66", weight: 1.6, opacity: 0.75 } });

  const maxV = S.aadt_max[0], MINV = 200000;
  const kept = [];
  D.aadt.features.filter((f) => f.properties.v >= MINV)            // already sorted high → low
    .forEach((f) => {
      const ll = L.latLng(f.geometry.coordinates[1], f.geometry.coordinates[0]);
      if (!kept.some((k) => k.ll.distanceTo(ll) < 1200)) kept.push({ f, ll });
    });
  const aadtR = (v) => 2.5 + 7.5 * Math.sqrt((v - MINV) / (maxV - MINV));
  const aadt = L.layerGroup(kept.map(({ f, ll }) => {
    const p = f.properties;
    return L.circleMarker(ll, { pane: "pts", radius: aadtR(p.v), color: "#fff", weight: 1, fillColor: "#eb6834", fillOpacity: 0.8 })
      .bindPopup(`<div class="ut-pop"><p class="meta">Caltrans AADT · Route ${p.rte}</p><h4>${fmt(p.v)} vehicles / day</h4><p>${p.at}</p></div>`);
  }));

  const bott = L.geoJSON(D.bottlenecks, { pane: "top",
    style: { color: "#e34948", weight: 5, opacity: 0.9, lineCap: "round" },
    onEachFeature: (f, l) => {
      const p = f.properties;
      l.bindPopup(`<div class="ut-pop"><p class="meta">Caltrans bottleneck #${p.rank} · District 7 · 2022</p>
        <h4>${p.fwy} at ${p.at} (${p.shift})</h4>
        <p><b>${fmt(p.delay)}</b> vehicle-hours of delay over ${p.days} active days · queue ≈ ${p.mi} mi.</p></div>`);
    } });

  const rail = L.geoJSON(D.rail, { pane: "rail", interactive: false,
    style: (f) => ({ color: f.properties.color, weight: 3, opacity: 0.9 }) });
  const stations = L.geoJSON(D.stations, { pane: "pts",
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: f.properties.uc ? 4.5 : 3.2, color: "#14304a", weight: 1.5,
      dashArray: f.properties.uc ? "2 2" : null, fillColor: f.properties.uc ? "#fbeede" : "#fff", fillOpacity: 1 }),
    onEachFeature: (f, l) => l.bindTooltip(f.properties.name + (f.properties.uc ? "" : " (open)"), { direction: "top" }) });

  const towers = L.geoJSON(D.towers, { pane: "pts",
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 1.6 + f.properties.h / 400, stroke: false, fillColor: "#14304a", fillOpacity: 0.75 }),
    onEachFeature: (f, l) => l.bindTooltip(`${fmt(f.properties.h)} ft`, { direction: "top" }) });

  const centerPopup = (p) => `<div class="ut-pop"><p class="meta">1974 Concept center · ${p.in_city ? "City of LA" : "outside the City"}</p>
    <h4>${p.name}</h4><p>${p.core}</p>
    <p><b style="color:${p.oc === "neither" ? "#5a5a56" : OUT[p.oc].c}">${OUT[p.oc].label}</b><br>
    ${p.towers} building${p.towers === 1 ? "" : "s"} ≥150 ft within 800 m${p.hmax ? ` (tallest ${fmt(p.hmax)} ft)` : ""}<br>
    Nearest open rail: ${p.near} — ${fmt(p.near_m)} m${p.rail === "building" ? `<br>Under construction: ${p.uc}` : ""}</p>
    <p class="meta">Drawn ${fmt(p.off)} m from this core on the 1974 diagram</p></div>`;
  const centers = L.geoJSON(D.centers, { pane: "circles",
    pointToLayer: (f, ll) => {
      const oc = f.properties.oc, neither = oc === "neither";
      return L.circle(ll, { radius: 800, color: neither ? "#77776f" : "#14304a", weight: neither ? 1.4 : 1.2,
        dashArray: neither ? "3 3" : null, opacity: 0.8,
        fillColor: OUT[oc].c, fillOpacity: neither ? 0.08 : (f.properties.rail === "building" ? 0.35 : 0.5) });
    },
    onEachFeature: (f, l) => { l.bindPopup(centerPopup(f.properties)); l.bindTooltip(f.properties.name, { direction: "top", sticky: true }); } });
  const drawn = L.layerGroup(D.centers.features.flatMap((f) => {
    const [x, y] = f.geometry.coordinates, [dx, dy] = f.properties.drawn;
    return [L.polyline([[dy, dx], [y, x]], { pane: "circles", color: "#c0392b", weight: 1, opacity: 0.8, interactive: false }),
            L.circleMarker([dy, dx], { pane: "circles", radius: 4, color: "#c0392b", weight: 1.5, fill: false, interactive: false })];
  }));

  const siteIdx = {};
  const sites = L.layerGroup(D.utopias.features.map((f, i) => {
    const p = f.properties, [lng, lat] = f.geometry.coordinates;
    const m = L.marker([lat, lng], { pane: "sites",
      icon: L.divIcon({ className: "u-marker", html: `<span>${i + 1}</span>`, iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12] }) })
      .bindPopup(`<div class="ut-pop"><p class="meta">${p.years} · ${FATE[p.fate]} · ${p.km} km from City Hall</p><h4>${p.name}</h4>
        <p><b>Ideal.</b> ${p.ideal}</p><p><b>Reality.</b> ${p.reality}</p></div>`, { maxWidth: 320 });
    siteIdx[p.id] = m;
    return m;
  }));

  /* ---------------- modes ---------------- */
  const all = [hex, holc, fwy, aadt, bott, rail, stations, towers, centers, drawn, sites];
  const opt = { holc: false, towers: true, rail: true, drawn: false };
  const panel = document.getElementById("ut-panel");

  const legendOutcomes = () => Object.entries(OUT).map(([k, o]) =>
    `<div class="row"><span class="sw" style="background:${k === "neither" ? "transparent" : o.c};${k === "neither" ? "border-style:dashed;border-color:#77776f" : ""}"></span>${o.label} <b style="margin-left:auto">${S.centers.outcomes[k]}</b></div>`).join("");
  const ramp = () => `<div class="ramp">${GREEN.map((c) => `<i style="background:${c}"></i>`).join("")}</div>
    <div class="rlab"><span>0%</span><span>10</span><span>30</span><span>50</span><span>70</span><span>85</span><span>100%</span></div>`;
  const toggle = (k, label) => `<label><input type="checkbox" data-opt="${k}" ${opt[k] ? "checked" : ""}> ${label}</label>`;

  const MODES = {
    all: {
      bounds: BASIN,
      layers: () => [hex, fwy, bott, rail, centers, sites],
      style: () => { hex.setStyle({ fillOpacity: 0.4, opacity: 0.25 }); },
      html: () => `<p class="kicker">Overlay</p><h3>Four utopias, stacked</h3>
        <p>Green hexagons are the garden suburb as written into zoning law; grey lines are Autopia, with its ten worst bottlenecks in red;
        coloured discs are the 56 centers of 1974, coloured by what became of them; numbered pins are the cooperative experiments.</p>
        <div class="stats">
          <div class="stat"><b>${S.zoning.sf_share_of_residential}%</b><span>of residential land still single-family</span></div>
          <div class="stat"><b>${S.centers.outcomes.realised} / ${S.centers.n}</b><span>plan centers with towers <em>and</em> rail</span></div>
          <div class="stat"><b>${fmt(S.aadt_max[0])}</b><span>vehicles/day at the busiest count point (I-10)</span></div>
          <div class="stat"><b>0 / 5</b><span>social utopias still living as designed</span></div>
        </div>
        <div class="legend">${legendOutcomes()}
          <div class="row"><span class="ln" style="border-color:#5b5f66;border-top-width:2px"></span>Freeways</div>
          <div class="row"><span class="ln" style="border-color:#e34948;border-top-width:5px"></span>Top-10 bottlenecks (2022)</div>
          <div class="row"><span class="sw" style="background:#c1632e;border-color:#fff"></span>Social-utopia sites</div>
          <div style="margin-top:6px">Single-family share of zoned land</div>${ramp()}</div>`,
    },
    garden: {
      bounds: [[33.70, -118.67], [34.34, -118.15]],
      layers: () => [hex, ...(opt.holc ? [holc] : [])],
      style: () => { hex.setStyle({ fillOpacity: 0.82, opacity: 0.6 }); },
      html: () => `<p class="kicker">Model 1 · from 1904</p><h3>The garden suburb</h3>
        <dl class="iv"><dt>Ideal</dt><dd>A city of homes: a detached house, a yard and a car for every family, spread across the basin instead of piled into a core.</dd>
        <dt>Reality</dt><dd>The ideal became the default setting of the zoning code. It survives almost untouched — and it survives most purely where the 1939 appraisers said “best”.</dd></dl>
        <div class="stats">
          <div class="stat"><b>${S.zoning.sf_share_of_residential}%</b><span>of residential-zoned land is single-family</span></div>
          <div class="stat"><b>${fmt(Math.round(S.zoning.sf_km2))} km²</b><span>single-family vs ${fmt(Math.round(S.zoning.mf_km2))} km² multi-family</span></div>
          <div class="stat"><b>${S.holc_sf_share_today.A}%</b><span>of HOLC “A” land still single-family</span></div>
          <div class="stat"><b>${S.holc_sf_share_today.D}%</b><span>of HOLC “D” land still single-family</span></div>
        </div>
        <div class="legend">Single-family share of zoned land, per ≈1 km² hexagon${ramp()}
          ${opt.holc ? Object.entries(HOLC).map(([g, c]) => `<div class="row"><span class="sq" style="border:2px solid ${c};background:${c}22"></span>${HOLC_LABEL[g]} — ${S.holc_sf_share_today[g]}% single-family today</div>`).join("") : ""}</div>
        <div class="toggles">${toggle("holc", "Overlay the 1939 HOLC grades")}</div>
        <p class="src">City of LA zoning (58,859 zoning polygons, CATEGORY field); LA County HOLC layer. City only — other cities are blank.</p>`,
    },
    autopia: {
      bounds: [[33.72, -118.62], [34.32, -117.95]],
      layers: () => [fwy, aadt, bott],
      style: () => {},
      html: () => `<p class="kicker">Model 2 · 1940 → 1971</p><h3>Autopia</h3>
        <dl class="iv"><dt>Ideal</dt><dd>Frictionless movement across an unbounded basin — first the planners’ parkways (1940) and statewide freeway plan (1959), then Banham’s 1971 celebration of the freeway as a way of life.</dd>
        <dt>Reality</dt><dd>The system was built and is used to saturation. The heaviest flows cluster where freeways converge on the old core.</dd></dl>
        <div class="stats">
          <div class="stat"><b>${fmt(S.aadt_max[0])}</b><span>vehicles/day — I-10 at Vermont Ave, the county peak</span></div>
          <div class="stat"><b>${S.aadt_ge_300k}</b><span>freeway count points above 300,000/day</span></div>
          <div class="stat"><b>${(S.bottleneck_delay_total_veh_hrs / 1e6).toFixed(2)} M</b><span>vehicle-hours lost at the 10 worst bottlenecks (2022)</span></div>
          <div class="stat"><b>#1</b><span>bottleneck: 110 north into the 1940 Arroyo Seco Parkway</span></div>
        </div>
        <div class="legend">
          <div class="row">${[200000, 275000, 345000].map((v) => `<span class="sw" style="background:#eb6834;border:1px solid #fff;width:${2 * aadtR(v)}px;height:${2 * aadtR(v)}px"></span>${v / 1000}k`).join(" ")}&nbsp;vehicles/day</div>
          <div class="row"><span class="ln" style="border-color:#e34948;border-top-width:5px"></span>Top-10 recurrent bottlenecks, District 7 (2022)</div>
          <div class="row"><span class="ln" style="border-color:#5b5f66;border-top-width:2px"></span>Interstates &amp; other freeways</div></div>
        <p class="src">Caltrans AADT (freeway count points ≥200k/day, busiest per 1.2 km shown); Caltrans Mobility Performance Report bottlenecks.</p>`,
    },
    centers: {
      bounds: [[33.72, -118.64], [34.30, -118.10]],
      layers: () => [fwy, ...(opt.rail ? [rail, stations] : []), centers, ...(opt.towers ? [towers] : []), ...(opt.drawn ? [drawn] : [])],
      style: () => {},
      html: () => `<p class="kicker">Model 3 · 1970 / 1974</p><h3>The Centers Concept</h3>
        <dl class="iv"><dt>Ideal</dt><dd>If not one downtown, then 56: high-rise cores of ~¼ mile around rapid-transit stations, with the single-family suburbs between them left alone.</dd>
        <dt>Reality</dt><dd>The towers mostly went where the plan said. The trains came decades later — and often to different centers than the towers.</dd></dl>
        <div class="stats">
          <div class="stat"><b>${S.centers.outcomes.realised} / ${S.centers.n}</b><span>centers with ≥5 high-rises <em>and</em> open rail</span></div>
          <div class="stat"><b>${S.centers.outcomes.neither}</b><span>centers with neither</span></div>
          <div class="stat"><b>${Math.round(S.centers.towers_in_city_in_catchments / S.towers_in_city * 100)}%</b><span>of the City’s high-rises sit in plan centers…</span></div>
          <div class="stat"><b>${S.centers.catchment_share_of_city}%</b><span>…which cover this share of its land</span></div>
        </div>
        <div class="legend">${legendOutcomes()}
          <div class="row"><span class="sw" style="background:#fbeede;border:1.5px dashed #14304a;width:10px;height:10px"></span>Station under construction · paler disc = rail arriving 2027–31</div>
          <div class="row"><span class="sw" style="background:#14304a;border:none;width:6px;height:6px"></span>Building ≥150 ft (2020)</div></div>
        <div class="toggles">${toggle("towers", "High-rises ≥150 ft (LARIAC 2020)")}${toggle("rail", "Metro rail today")}${toggle("drawn", "Where the 1974 diagram drew each center")}</div>
        <p class="src">Discs = 800 m around each center’s named core. Full list in the table below the map.</p>`,
    },
    social: {
      bounds: null,
      layers: () => [sites],
      style: () => {},
      html: () => `<p class="kicker">Model 4 · 1913 → 1962</p><h3>Social utopias</h3>
        <dl class="iv"><dt>Ideal</dt><dd>Cooperative colonies and planned communities that would change how people lived together, not only where.</dd>
        <dt>Reality</dt><dd>None survives as a social form. The ones that survive did so as architecture; the one cleared outright became a stadium in a sea of parking.</dd></dl>
        <ul class="site-list">${D.utopias.features.map((f, i) => `<li data-site="${f.properties.id}"><span class="num">${i + 1}</span><span><b>${f.properties.name}</b> <span style="color:#6a7682">${f.properties.years}</span><span class="fate">${FATE[f.properties.fate]}</span></span></li>`).join("")}</ul>
        <p class="src">Site-level evidence: documented locations and fates, not a statistical surface. Click a row to fly there.</p>`,
    },
  };

  let mode = "all";
  function render(newMode, refit = true) {
    mode = newMode;
    const M = MODES[mode];
    all.forEach((l) => map.hasLayer(l) && map.removeLayer(l));
    city.addTo(map);
    M.layers().forEach((l) => l.addTo(map));
    M.style();
    panel.innerHTML = M.html();
    if (refit) {
      if (M.bounds) map.flyToBounds(M.bounds, { duration: 0.6 });
      else map.flyToBounds(L.featureGroup(sites.getLayers()).getBounds().pad(0.12), { duration: 0.6 });
    }
    panel.querySelectorAll("input[data-opt]").forEach((el) => el.addEventListener("change", () => {
      opt[el.dataset.opt] = el.checked; render(mode, false);
    }));
    panel.querySelectorAll("[data-site]").forEach((el) => el.addEventListener("click", () => {
      const m = siteIdx[el.dataset.site];
      map.flyTo(m.getLatLng(), 13, { duration: 0.8 });
      setTimeout(() => m.openPopup(), 850);
    }));
    document.querySelectorAll(".ut-tab").forEach((b) => {
      const on = b.dataset.mode === mode;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", on);
    });
  }
  document.querySelectorAll(".ut-tab").forEach((b) => b.addEventListener("click", () => render(b.dataset.mode)));
  render("all", false);

  /* ---------------- centers table (relief for colour-only encoding) ---------------- */
  const rows = D.centers.features.map((f) => f.properties);
  const tbody = document.querySelector("#ct tbody");
  const ORDER = { realised: 0, towers: 1, rail: 2, neither: 3 };
  let sortK = "oc", asc = true;
  function drawTable() {
    rows.sort((a, b) => {
      let x = a[sortK], y = b[sortK];
      if (sortK === "oc") { x = ORDER[x]; y = ORDER[y]; }
      if (typeof x === "string") return asc ? x.localeCompare(y) : y.localeCompare(x);
      return asc ? x - y : y - x;
    });
    tbody.innerHTML = rows.map((p) => `<tr>
      <td>${p.name}</td>
      <td><span class="dot" style="background:${p.oc === "neither" ? "transparent" : OUT[p.oc].c}"></span>${OUT[p.oc].label.split(" —")[0]}</td>
      <td class="num">${p.towers}</td><td class="num">${p.hmax ? fmt(p.hmax) : "–"}</td>
      <td class="num">${fmt(p.near_m)}</td><td>${p.rail === "open" ? "open" : p.rail === "building" ? "building" : "–"}</td></tr>`).join("");
  }
  document.querySelectorAll("#ct th").forEach((th) => th.addEventListener("click", () => {
    const k = th.dataset.k; asc = sortK === k ? !asc : (k === "name" || k === "oc" || k === "near_m"); sortK = k; drawTable();
  }));
  drawTable();
}

document.addEventListener("DOMContentLoaded", init);
