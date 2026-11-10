/* #30DayMapChallenge · Day 8 · Utopia — "Los Angeles and the Afterlife of Utopia", illustrated.
 * The essay scrolls; the map follows it. Each paragraph carries a step (data-s):
 *   v = view (basin | city | region | centers | pastoral | plate | sites | topo:<site> | place ids)
 *   y = year shown by the morphogenesis layer (or "play")
 *   o = original map under the swipe (transit1925 | parks1930 | parkways1946 | plan1974 | topo:<site> | none) — inherited within a chapter
 *   x = extra evidence layers (holc, zoned, aadt, bott, bh500, towers, rail)
 *   w = swipe divider position (0–1)
 * The chapter (section[data-ch]) decides which utopia is lit; the other four are dimmed. */
(() => {
  "use strict";
  // five riso inks, one per utopia, and nothing else uses them; everything else is black ink on white paper
  const COL = { pastoral: "#00a95c", autopia: "#f0a202", centers: "#3255a4", transit: "#9e2a2b", coop: "#ff48b0", all: "#111111" };
  const LINE = { pastoral: "#007a42", autopia: "#b07600", centers: "#22397a", transit: "#7a1f20", coop: "#d12c8a" }; // darker steps of the same inks, for strokes
  const GROUPS = ["transit", "pastoral", "autopia", "centers", "coop"];   // chapter order
  const NUM = { transit: "I", pastoral: "II", autopia: "III", centers: "IV", coop: "V" };
  const UNAME = { pastoral: "Pastoral suburb", autopia: "Autopia", centers: "Polycentric", transit: "Transit", coop: "Cooperative" };
  const INK = "#111111";
  const D0 = "";
  const Y0 = 1880, Y1 = 2026;
  const fmt = (n) => Number(n).toLocaleString("en-US");
  // data files carry the build stamp, so a new deploy is never read from a stale cache
  const J = (p) => fetch(D0 + p + "?v=" + (window.D8V || "")).then((r) => { if (!r.ok) throw new Error(p); return r.json(); });
  const VIEWS = {
    basin: [[33.70, -118.70], [34.34, -118.06]],
    city: [[33.72, -118.67], [34.34, -118.15]],
    region: [[33.66, -118.80], [34.56, -117.70]],
    centers: [[33.74, -118.62], [34.28, -118.08]],
  };
  const MILESTONES = [   // year, utopia, label, where to read more
    [1874, "transit", "First horsecar line, Spring and Sixth Streets", "https://metroprimaryresources.info/this-date-in-los-angeles-transportation-history/july/july-1/"],
    [1901, "transit", "Pacific Electric incorporated; Red Cars to Long Beach in 1902", "https://en.wikipedia.org/wiki/Pacific_Electric"],
    [1904, "pastoral", "Residential District Ordinance", "https://en.wikipedia.org/wiki/Zoning_in_the_United_States#Los_Angeles,_1904-1909"],
    [1913, "coop", "Little Landers colony, Tujunga", "https://en.wikipedia.org/wiki/Little_Landers"],
    [1914, "coop", "Llano del Rio founded", "https://en.wikipedia.org/wiki/Llano_del_Rio"],
    [1925, "transit", "Kelker, De Leuw rapid transit plan; Hollywood Subway opens", "https://libraryarchives.metro.net/DPGTL/trafficplans/1925_comprehensive_rapid_transit_plan_los_angeles.pdf"],
    [1930, "pastoral", "Olmsted–Bartholomew regional parks plan", "https://libraryarchives.metro.net/DPGTL/trafficplans/1930_parks_playgrounds_beaches_los_angeles_region.pdf"],
    [1940, "autopia", "Arroyo Seco Parkway, the first freeway, opens", "https://en.wikipedia.org/wiki/Arroyo_Seco_Parkway"],
    [1942, "coop", "Baldwin Hills Village completed", "https://en.wikipedia.org/wiki/Village_Green,_Los_Angeles"],
    [1946, "autopia", "County parkways plan: 613 miles", "https://libraryarchives.metro.net/DPGTL/trafficplans/1946_interregional_regional_metropolitan_parkways.pdf"],
    [1946, "coop", "Crestwood Hills cooperative established", "https://en.wikipedia.org/wiki/Crestwood_Hills,_Los_Angeles"],
    [1949, "autopia", "Four Level Interchange completed", "https://en.wikipedia.org/wiki/Four_Level_Interchange"],
    [1953, "coop", "Elysian Park Heights cancelled", "https://en.wikipedia.org/wiki/Battle_of_Chavez_Ravine"],
    [1961, "transit", "The last Red Car runs, to Long Beach", "https://en.wikipedia.org/wiki/Pacific_Electric"],
    [1962, "coop", "Dodger Stadium opens in Chávez Ravine", "https://en.wikipedia.org/wiki/Dodger_Stadium"],
    [1963, "transit", "The last streetcars (lines J, P, R, S and V) give way to buses", "https://metroprimaryresources.info/this-date-in-los-angeles-transportation-history/march/march-31/"],
    [1966, "autopia", "Santa Monica Freeway completed", "https://en.wikipedia.org/wiki/Santa_Monica_Freeway"],
    [1971, "autopia", "Banham publishes <i>Los Angeles: The Architecture of Four Ecologies</i>", "https://en.wikipedia.org/wiki/Reyner_Banham"],
    [1974, "centers", "Centers Concept adopted, 3 April", "https://libraryarchives.metro.net/dpgtl/lacity/1974-concept-los-angeles-side-1.pdf"],
    [1980, "transit", "Proposition A: voters fund transit, at the fifth attempt", "https://libraryarchives.metro.net/DPGTL/histories/2017-History-BallotInitiatives.xls"],
    [1990, "transit", "Blue Line: first modern rail line opens", "https://en.wikipedia.org/wiki/A_Line_(Los_Angeles_Metro)"],
    [1996, "centers", "General Plan Framework adopted", "https://planning.lacity.gov/plans-policies/framework-element"],
    [2016, "transit", "Measure M passes with 71% of the vote", "https://en.wikipedia.org/wiki/2008_Los_Angeles_County_Measure_R"],
  ];

  async function init() {
    const [S, M, SS, places, centers, towers, rail, stations, fwy, aadt, bott, holc, utop, topoMeta, cities, fwy500, chartPlaces, todayC, metro] = await Promise.all([
      J("data/stats.json"), J("data/morph.json"), J("data/story_stats.json"), J("data/story_places.geojson"),
      J("data/centers.geojson"), J("data/towers.geojson"), J("data/rail.geojson"), J("data/stations.geojson"),
      J("data/freeways.geojson"), J("data/aadt.geojson"), J("data/bottlenecks.geojson"), J("data/holc.geojson"),
      J("data/utopias.geojson"), J("img/topo_meta.json"), J("data/cities.geojson"), J("data/fwy500.geojson"), J("data/chart_places.geojson"), J("data/today_centres.geojson"),
      J("data/metro_lines.geojson"),
    ]);
    const oldnet = await J("data/old_network.geojson").catch(() => ({ type: "FeatureCollection", features: [] }));
    const mobile = window.matchMedia("(max-width: 900px)");

    /* ======================= map & panes ======================= */
    const map = L.map("st-map", { zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100, maxZoom: 17, minZoom: 7 }).fitBounds(VIEWS.basin);
    map.zoomControl.setPosition("topright");
    const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
    const DATA_ATTR = " · data: LA County, City of LA, Caltrans, LA Metro, USGS, US Census, Mapping Inequality";
    const BASES = {
      map: L.tileLayer(ESRI + "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", { maxZoom: 17, maxNativeZoom: 16,
        attribution: 'Tiles &copy; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' + DATA_ATTR }),
      sat: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 17,
        attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics and the GIS User Community" + DATA_ATTR }),
    };
    let baseKind = "map";
    try { if (localStorage.getItem("d8-base") === "sat") baseKind = "sat"; } catch (e) { /* storage blocked: default map */ }
    function setBase(k) {
      if (!BASES[k]) return;
      Object.entries(BASES).forEach(([n, l]) => { if (n !== k && map.hasLayer(l)) map.removeLayer(l); });
      BASES[k].addTo(map); baseKind = k;
      blendOrig();
      map.getContainer().classList.toggle("sat", k === "sat");
      document.querySelectorAll("[data-base]").forEach((b) => { b.classList.toggle("on", b.dataset.base === k); b.setAttribute("aria-pressed", String(b.dataset.base === k)); });
      try { localStorage.setItem("d8-base", k); } catch (e) { /* not remembered */ }
    }
    const pane = (name, z, cls) => { const p = map.createPane(name); p.style.zIndex = z; if (cls) p.classList.add(cls); return p; };
    pane("morph", 250);
    const origPane = pane("orig", 280);
    origPane.style.mixBlendMode = "multiply";
    const GP = {};
    GROUPS.forEach((g, i) => { GP[g] = pane("g-" + g, 400 + i * 10, "g-pane"); });
    pane("top", 455);
    // no raster place-name tiles: every word on the map is set in the page's own type (see the label layer below)
    pane("cities", 390).style.pointerEvents = "none";
    L.geoJSON(cities, { pane: "cities", interactive: false,
      style: (f) => (f.properties.la ? { color: INK, weight: 1.8, opacity: 0.9, fill: false } : { color: "#8c8c8c", weight: 0.8, opacity: 0.9, fill: false }) }).addTo(map);
    const cv = Object.fromEntries(GROUPS.map((g) => [g, L.canvas({ pane: "g-" + g, padding: 0.3 })]));

    /* ======================= morphogenesis ======================= */
    const [NX, NY] = M.size, CS = M.cell_m_webmerc, ORIG = Math.PI * 6378137;
    const pSW = L.CRS.EPSG3857.project(L.latLng(M.bounds[0])), pNE = L.CRS.EPSG3857.project(L.latLng(M.bounds[1]));
    const GX0 = Math.round(pSW.x / CS) * CS, GY1 = Math.round(pNE.y / CS) * CS;
    const img = new Image(); img.src = D0 + "img/morph_grid.png"; await img.decode();
    const src = document.createElement("canvas"); src.width = NX; src.height = NY;
    const sctx = src.getContext("2d", { willReadFrequently: true }); sctx.drawImage(img, 0, 0);
    const px = sctx.getImageData(0, 0, NX, NY).data;
    const counts = new Int32Array(178);
    for (let i = 0; i < NX * NY; i++) if (px[4 * i + 3]) counts[px[4 * i]]++;
    const start = new Int32Array(179); for (let k = 0; k < 178; k++) start[k + 1] = start[k] + counts[k];
    const order = new Int32Array(start[178]); const fill = start.slice();
    for (let i = 0; i < NX * NY; i++) if (px[4 * i + 3]) order[fill[px[4 * i]]++] = i;
    const disp = document.createElement("canvas"); disp.width = NX; disp.height = NY;
    const dctx = disp.getContext("2d");
    const dimg = dctx.createImageData(NX, NY), d32 = new Uint32Array(dimg.data.buffer);
    const rgba = (h, a) => { const n = parseInt(h.slice(1), 16); return ((a << 24) | ((n & 255) << 16) | (((n >> 8) & 255) << 8) | (n >> 16)) >>> 0; };
    const FOG = rgba("#ffffff", 244), FRONT = rgba(INK, 185), FRONT_YRS = 5;
    const mips = [disp];
    for (let f = 2; f <= 8; f *= 2) { const m = document.createElement("canvas"); m.width = Math.ceil(NX / f); m.height = Math.ceil(NY / f); mips.push(m); }
    function recolor(Y) {
      d32.fill(0);
      for (let k = 0; k < 178; k++) {
        const y = 1850 + k;
        const c = y > Y ? FOG : (Y < Y1 && Y - y < FRONT_YRS ? FRONT : 0);
        if (!c) continue;
        for (let j = start[k]; j < start[k + 1]; j++) d32[order[j]] = c;
      }
      dctx.putImageData(dimg, 0, 0);
      for (let i = 1; i < mips.length; i++) {
        const m = mips[i], c = m.getContext("2d");
        c.clearRect(0, 0, m.width, m.height); c.imageSmoothingEnabled = true; c.imageSmoothingQuality = "high";
        c.drawImage(mips[i - 1], 0, 0, m.width, m.height);
      }
    }
    function drawTile(c, co) {
      const ctx = c.getContext("2d"); ctx.clearRect(0, 0, 256, 256);
      const res = 2 * ORIG / (256 * 2 ** co.z), X = -ORIG + co.x * 256 * res, Y = ORIG - co.y * 256 * res;
      const sx = (X - GX0) / CS, sy = (GY1 - Y) / CS, s = 256 * res / CS, k = 256 / s;
      const x0 = Math.max(0, sx), y0 = Math.max(0, sy), x1 = Math.min(NX, sx + s), y1 = Math.min(NY, sy + s);
      if (x1 <= x0 || y1 <= y0) return;
      const lvl = Math.max(0, Math.min(mips.length - 1, Math.floor(Math.log2(s / 256)))), f = 2 ** lvl;
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";   // soft edges, never hard squares
      ctx.drawImage(mips[lvl], x0 / f, y0 / f, (x1 - x0) / f, (y1 - y0) / f, (x0 - sx) * k, (y0 - sy) * k, (x1 - x0) * k, (y1 - y0) * k);
    }
    const Morph = L.GridLayer.extend({ createTile(co) { const c = L.DomUtil.create("canvas", "morph-tile"); c.width = c.height = 256; drawTile(c, co); return c; } });
    const morph = new Morph({ pane: "morph", opacity: 1, maxZoom: 17, updateWhenZooming: false,
      bounds: L.latLngBounds(M.bounds) }).addTo(map);
    const redrawMorph = () => { for (const key in morph._tiles) { const t = morph._tiles[key]; drawTile(t.el, t.coords); } };

    /* cumulative share of today's buildings by year */
    const H = M.hist, N = M.parcels, cum = {};
    { let acc = 0; for (let y = 1850; y <= Y1; y++) { acc += H[y] || 0; cum[y] = acc / N; } }

    /* ======================= timeline ======================= */
    const tEl = document.getElementById("t-hist"), tYear = document.getElementById("t-year"), tShare = document.getElementById("t-share");
    const playBtn = document.getElementById("t-play");
    const SVGNS = "http://www.w3.org/2000/svg";
    let year = Y1, bars = [], cursor, cursorT, tw = 0;
    const hmax = Math.max(...Object.entries(H).filter(([y]) => +y >= Y0).map(([, v]) => v));
    function buildHist() {
      const w = tEl.clientWidth, h = tEl.clientHeight; if (!w) return; tw = w;
      const n = Y1 - Y0 + 1, bw = w / n, mr = bw < 2.5 ? 2.5 : 3.2, top = 4 * mr + 5, bot = h - 13;
      const svg = document.createElementNS(SVGNS, "svg"); svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
      bars = [];
      for (let y = Y0; y <= Y1; y++) {
        const v = H[y] || 0, bh = Math.max(v ? 1 : 0, (bot - top) * v / hmax);
        const r = document.createElementNS(SVGNS, "rect");
        r.setAttribute("x", ((y - Y0) * bw).toFixed(2)); r.setAttribute("width", Math.max(0.6, bw - 0.5).toFixed(2));
        r.setAttribute("y", (bot - bh).toFixed(2)); r.setAttribute("height", bh.toFixed(2)); r.setAttribute("rx", Math.min(1, bw / 3));
        svg.appendChild(r); bars.push(r);
      }
      const base = document.createElementNS(SVGNS, "line");
      Object.entries({ x1: 0, x2: w, y1: bot + 0.5, y2: bot + 0.5, stroke: INK }).forEach(([k, v]) => base.setAttribute(k, v)); svg.appendChild(base);
      for (let y = 1900; y <= 2020; y += 20) {
        const t = document.createElementNS(SVGNS, "text"); t.setAttribute("x", (y - Y0 + 0.5) * bw); t.setAttribute("y", h - 1);
        t.setAttribute("text-anchor", "middle"); t.textContent = y; svg.appendChild(t);
      }
      // two rows of milestone dots; a dot drops to the second row when the first is taken
      const rowEnd = [-1e9, -1e9];
      MILESTONES.forEach(([y, ch, label]) => {
        let cx = (y - Y0 + 0.5) * bw, row = rowEnd.findIndex((e) => cx - e >= 2 * mr + 1);
        if (row < 0) { row = rowEnd[0] <= rowEnd[1] ? 0 : 1; cx = rowEnd[row] + 2 * mr + 1; }
        rowEnd[row] = cx;
        const c = document.createElementNS(SVGNS, "rect");   // neutral markers: the utopia colours stay on the utopias
        c.setAttribute("x", cx - mr); c.setAttribute("y", 1 + row * (2 * mr + 1)); c.setAttribute("width", 2 * mr); c.setAttribute("height", 2 * mr);
        c.setAttribute("fill", INK);
        c.classList.add("ms"); c.dataset.year = y;
        const ti = document.createElementNS(SVGNS, "title"); ti.textContent = `${y} · ${NUM[ch]} · ${label.replace(/<[^>]+>/g, "")}`; c.appendChild(ti);
        svg.appendChild(c);
      });
      cursor = document.createElementNS(SVGNS, "line"); cursor.setAttribute("y1", top - 2); cursor.setAttribute("y2", bot + 3);
      cursor.setAttribute("stroke", INK); cursor.setAttribute("stroke-width", 1.5); svg.appendChild(cursor);
      tEl.replaceChildren(svg);
      paintHist();
    }
    function paintHist() {
      if (!bars.length) return;
      for (let y = Y0; y <= Y1; y++) {
        const r = bars[y - Y0];
        r.setAttribute("fill", y > year ? "#e6e6e6" : (year < Y1 && year - y < FRONT_YRS ? INK : "#9b9b9b"));
      }
      const x = (year - Y0 + 0.5) * tw / (Y1 - Y0 + 1);
      cursor.setAttribute("x1", x); cursor.setAttribute("x2", x);
    }
    new ResizeObserver(buildHist).observe(tEl);

    let frame = 0;
    const yearHooks = [];   // layers that follow the year (the Metro network)
    function setYear(y) {
      year = Math.max(Y0, Math.min(Y1, Math.round(y)));
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0; recolor(year); redrawMorph(); paintHist();
        tYear.textContent = year;
        const p = cum[year] * 100;
        tShare.textContent = `${p < 1 ? p.toFixed(1) : Math.round(p)}% of today’s buildings stood`;
        tEl.setAttribute("aria-valuenow", year); tEl.setAttribute("aria-valuetext", `${year}: ${tShare.textContent}`);
        yearHooks.forEach((f) => f(year));
        if (window.__d8year) window.__d8year(year);
      });
    }
    let anim = null, playing = false;
    function stopAnim() { if (anim) cancelAnimationFrame(anim); anim = null; playing = false; playBtn.textContent = "Play"; playBtn.setAttribute("aria-label", "Play the city's growth"); }
    function tweenYear(target, ms = 1100) {
      stopAnim();
      const from = year, t0 = performance.now();
      if (from === target) { setYear(target); return; }
      const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
      const stepF = (now) => { const t = Math.min(1, (now - t0) / ms); setYear(from + (target - from) * ease(t)); anim = t < 1 ? requestAnimationFrame(stepF) : null; };
      anim = requestAnimationFrame(stepF);
    }
    function play(from) {
      stopAnim();
      if (from != null) setYear(from); else if (year >= Y1) setYear(Y0);
      playing = true; playBtn.textContent = "Pause"; playBtn.setAttribute("aria-label", "Pause");
      let last = performance.now(), acc = year;
      const stepF = (now) => {
        acc += (now - last) / 1000 * 11; last = now; setYear(acc);
        if (acc >= Y1) { stopAnim(); setYear(Y1); return; }
        anim = requestAnimationFrame(stepF);
      };
      anim = requestAnimationFrame(stepF);
    }
    playBtn.addEventListener("click", () => (playing ? stopAnim() : play()));
    document.querySelectorAll("[data-play]").forEach((b) => b.addEventListener("click", () => play(Y0)));
    const yearAt = (e) => { const r = tEl.getBoundingClientRect(); return Y0 + Math.floor((e.clientX - r.left) / r.width * (Y1 - Y0 + 1)); };
    let scrub = false;
    tEl.addEventListener("pointerdown", (e) => {
      const ms = e.target.closest(".ms"); stopAnim();
      if (ms) { tweenYear(+ms.dataset.year, 700); return; }
      scrub = true; tEl.setPointerCapture(e.pointerId); setYear(yearAt(e));
    });
    tEl.addEventListener("pointermove", (e) => { if (scrub) setYear(yearAt(e)); });
    tEl.addEventListener("pointerup", () => { scrub = false; });
    tEl.addEventListener("keydown", (e) => {
      const d = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -1, ArrowUp: 1, PageDown: -10, PageUp: 10 }[e.key];
      if (d) { stopAnim(); setYear(year + d); e.preventDefault(); }
      if (e.key === "Home") { stopAnim(); setYear(Y0); e.preventDefault(); }
      if (e.key === "End") { stopAnim(); setYear(Y1); e.preventDefault(); }
    });
    setYear(Y1);

    /* ======================= original maps + swipe ======================= */
    const topoName = (f) => f.split("_").slice(1).filter((s) => !/^\d+$/.test(s) && !s.includes(".")).join(" ");
    const ORIGS = {
      transit1925: { url: "tiles/transit1925/{z}/{x}/{y}.webp", maxN: 13, bounds: [[33.66, -118.69], [34.37, -117.61]], tag: "1925 Plan",
        cap: "Kelker, De Leuw &amp; Co., 1925", href: "https://libraryarchives.metro.net/DPGTL/trafficplans/1925_comprehensive_rapid_transit_plan_los_angeles.pdf",
        win: [[33.72, -118.66], [34.30, -117.80]] },
      parks1930: { url: "tiles/parks1930/{z}/{x}/{y}.webp", maxN: 12, bounds: [[33.73, -118.73], [34.45, -117.52]], tag: "1930 Plan",
        cap: "Olmsted Brothers &amp; Bartholomew, 1930", href: "https://libraryarchives.metro.net/DPGTL/trafficplans/1930_parks_playgrounds_beaches_los_angeles_region.pdf",
        win: [[33.80, -118.81], [34.45, -117.60]] },
      parkways1946: { url: "tiles/parkways1946/{z}/{x}/{y}.webp", maxN: 12, bounds: [[33.66, -118.99], [34.37, -117.61]], tag: "1946 Plan",
        cap: "Los Angeles County Regional Planning Commission, 1946", href: "https://libraryarchives.metro.net/DPGTL/trafficplans/1946_interregional_regional_metropolitan_parkways.pdf",
        win: [[33.70, -118.95], [34.42, -117.65]] },
      plan1974: { url: "tiles/plan1974/{z}/{x}/{y}.webp", maxN: 14, bounds: [[33.67, -118.76], [34.36, -118.04]], tag: "1974 Plan",
        cap: "City of Los Angeles, Concept Los Angeles, 1974", href: "https://libraryarchives.metro.net/dpgtl/lacity/1974-concept-los-angeles-side-1.pdf",
        win: [[33.70, -118.70], [34.34, -118.06]] },
    };
    Object.entries(topoMeta).forEach(([id, t]) => {
      const names = (t.sheets || [t.file]).map(topoName);
      ORIGS["topo:" + id] = { url: `tiles/topo_${t.tiles || id}/{z}/{x}/{y}.webp`, minN: t.zmin, maxN: t.zmax, minZoom: 10, bounds: t.bounds, tag: `${t.year} Map`,
        cap: `U.S. Geological Survey, ${names.length > 1 ? names.join(" and ") + " sheets" : names[0]}, ${t.year}`, win: t.focus || t.bounds,
        href: "https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/PDF/CA/24000/" + t.file.replace("_geo.tif", "_geo.pdf").replace(/^CA_(.*?)_(\d{6})_/, (m, n, id) => `CA_${n.replace(/_/g, "%20")}_${id}_`) };
    });
    // one dated option per survey sheet set (adjacent sheets of the same year are one seamless map)
    const SHEETSETS = {};
    Object.entries(topoMeta).forEach(([id, t]) => {
      const k = t.tiles || id;
      (SHEETSETS[k] = SHEETSETS[k] || { year: t.year, names: (t.sheets || [t.file]).map(topoName), sites: [] }).sites.push(id);
    });
    document.getElementById("o-sheets").innerHTML = Object.entries(SHEETSETS).sort((a, b) => a[1].year - b[1].year)
      .map(([k, v]) => `<option value="sheet:${k}">${v.year} · ${v.names.join(" and ")}</option>`).join("");
    // each original map's own printed legend (colours sampled from the scans)
    const OLEG = {
      transit1925: [["band", "#211916", "Rapid transit, existing"], ["band", "#d8775e", "Rapid transit for immediate construction"], ["bandd", "#d8775e", "Rapid transit for future construction"],
        ["bando", "#d8775e", "Future separation of grades"], ["tdash", "#c88845", "Los Angeles Railway (streetcars)"], ["line", "#ba7c3b", "Pacific Electric Railway (Red Cars)"]],
      parks1930: [["fill", "#659257", "Existing parks"], ["fill", "#ea7669", "Proposed parks, parkways and beaches"], ["line", "#4a4a4a", "Roads, railways and terrain (base map)"]],
      parkways1946: [["line", "#c25843", "U.S. interregional system"], ["dash", "#c25843", "State regional system"], ["dot", "#c25843", "Metropolitan parkway system"], ["thin", "#8c8c8c", "Existing roads (base map)"]],
      plan1974: [["disc", "#f40509", "Centers"], ["node", "#4e462a", "Node or satellite"], ["fillb", "#ffffff", "Suburban residential area"], ["fill", "#dbd6a7", "Industrial district"],
        ["fill", "#84af0c", "Open space"], ["rail", "#4e462a", "Rapid transit line and station"], ["thin", "#4e462a", "Secondary transit line and station"], ["double", "#84af0c", "Freeway"]],
      topo: [["line", "#b0703a", "Contour lines (elevation)"], ["fill", "#f3c0bb", "Built-up area"], ["fill", "#cfe5b4", "Woodland"], ["fill", "#9cc9ec", "Water"], ["line", "#111111", "Roads, railways and buildings"]],
    };
    const swatch = (t, c) => {
      const L_ = (extra) => `<line x1="1" y1="6" x2="21" y2="6" stroke="${c}" ${extra}/>`;
      const body = {
        fill: `<rect x="1" y="1" width="20" height="10" fill="${c}"/>`,
        fillb: `<rect x="1.5" y="1.5" width="19" height="9" fill="${c}" stroke="#9a9a9a"/>`,
        line: L_('stroke-width="2.4"'), thin: L_('stroke-width="1.2"'), dash: L_('stroke-width="2.4" stroke-dasharray="5 3"'),
        dot: L_('stroke-width="2.4" stroke-dasharray="0.1 4" stroke-linecap="round"'),
        double: `<line x1="1" y1="4" x2="21" y2="4" stroke="${c}" stroke-width="1.6"/><line x1="1" y1="8" x2="21" y2="8" stroke="${c}" stroke-width="1.6"/>`,
        disc: `<circle cx="11" cy="6" r="5" fill="${c}"/>`,
        node: `<line x1="4" y1="6" x2="18" y2="6" stroke="${c}" stroke-width="1"/><circle cx="18" cy="6" r="1.8" fill="${c}"/>`,
        rail: `<line x1="1" y1="6" x2="21" y2="6" stroke="${c}" stroke-width="3" stroke-dasharray="1.5 1.5"/><circle cx="11" cy="6" r="3" fill="#fff" stroke="${c}" stroke-width="1.5"/>`,
        veil: `<rect x="1" y="1" width="20" height="10" fill="#fff" stroke="#8c8c8c"/><path d="M4 11 L10 1 M10 11 L16 1 M16 11 L21 3" stroke="#c4c4c4" stroke-width="1"/>`,
        ink: `<rect x="1" y="1" width="20" height="10" fill="${c}" fill-opacity="0.6"/>`,
        ring: `<circle cx="11" cy="6" r="4.6" fill="#fff" stroke="${c}" stroke-width="2"/>`,
        ringd: `<circle cx="11" cy="6" r="4.6" fill="none" stroke="${c}" stroke-width="1.2" stroke-dasharray="2 1.6"/>`,
        dotf: `<circle cx="11" cy="6" r="4.6" fill="${c}" stroke="#fff" stroke-width="1"/>`,
        pin: `<rect x="5" y="0.5" width="11" height="11" fill="${c}" stroke="#111" stroke-width="1.2"/>`,
        sq: `<rect x="7" y="2" width="8" height="8" fill="${c}"/>`,
        band: `<rect x="1" y="3" width="20" height="6" fill="${c}"/>`,
        bandd: `<rect x="1" y="3" width="8" height="6" fill="${c}"/><rect x="13" y="3" width="8" height="6" fill="${c}"/>`,
        bando: `<rect x="1" y="3" width="6" height="6" fill="${c}"/><circle cx="11" cy="6" r="2.6" fill="${c}"/><rect x="15" y="3" width="6" height="6" fill="${c}"/>`,
        tdash: L_('stroke-width="1.6" stroke-dasharray="3 2.4"'),
      }[t];
      return `<svg viewBox="0 0 22 12" aria-hidden="true">${body}</svg>`;
    };
    const lgRow = (t, c, label) => `<div class="lg">${swatch(t, c)}<span>${label}</span></div>`;
    const oLeg = document.getElementById("o-legend");
    const origLayers = {};
    const HD = L.Browser.retina ? 1 : 0;   // on high-density screens, request the next zoom level's tiles at half size
    const getOrig = (k) => origLayers[k] || (origLayers[k] = L.tileLayer(D0 + ORIGS[k].url, {
      pane: "orig", minZoom: ORIGS[k].minZoom || 7, maxZoom: 17, tileSize: 256 >> HD, zoomOffset: HD,
      minNativeZoom: (ORIGS[k].minN || 9) - HD, maxNativeZoom: ORIGS[k].maxN - HD,
      bounds: L.latLngBounds(ORIGS[k].bounds), opacity: opFor(k),
    }));
    let origOpacity = 0.85, userOpacity = false, curOrig = "none", userOrig = false;
    // printed survey sheets are full maps on their own paper: shown opaque, not multiplied into today's map
    const isSheet = (k) => k.startsWith("topo:");
    const opFor = (k) => (isSheet(k) && !userOpacity ? 1 : origOpacity);
    // survey sheets, and every scan over satellite imagery, are drawn as printed; plans on the grey map are multiplied in
    function blendOrig() { origPane.style.mixBlendMode = isSheet(curOrig) || baseKind === "sat" ? "normal" : "multiply"; }
    setBase(baseKind);
    const swipe = { on: true, x: 0.5 };
    const divider = L.DomUtil.create("div", "swipe-divider", map.getContainer());
    divider.innerHTML = '<span class="swipe-tag l"></span><span class="swipe-tag r">Today</span><button class="swipe-handle" type="button" aria-label="Drag to compare the original map with today"></button>';
    L.DomEvent.disableClickPropagation(divider); L.DomEvent.disableScrollPropagation(divider);
    const oPanel = document.getElementById("st-orig"), oSel = document.getElementById("o-select"), oCap = document.getElementById("o-cap");
    L.DomEvent.disableClickPropagation(oPanel); L.DomEvent.disableScrollPropagation(oPanel);
    function clipOrig() {
      const size = map.getSize();
      const nw = map.containerPointToLayerPoint([0, 0]), se = map.containerPointToLayerPoint(size);
      const x = swipe.on ? Math.round(size.x * swipe.x) : size.x;
      origPane.style.clip = swipe.on ? `rect(${nw.y}px, ${nw.x + x}px, ${se.y}px, ${nw.x}px)` : "";
      divider.style.left = `${x}px`;
      divider.style.display = swipe.on && curOrig !== "none" ? "" : "none";
      // The handle must always be visible and draggable. Search down the divider for a spot clear of every panel and
      // control, preferring just below the original-map panel; if none is clear, lift the handle above the panels.
      const mc = map.getContainer(), r0 = mc.getBoundingClientRect(), H = r0.height;
      const boxes = [...mc.closest(".st-mapbox").querySelectorAll(".st-orig, .st-key, .st-time, .leaflet-control-zoom, .st-back, .leaflet-control-attribution")]
        .filter((e) => e.offsetParent && getComputedStyle(e).display !== "none" && getComputedStyle(e).visibility !== "hidden")
        .map((e) => { const r = e.getBoundingClientRect(); return { x: r.left - r0.left - 6, y: r.top - r0.top - 6, w: r.width + 12, h: r.height + 12 }; });
      const clear = (x0, x1, y0, y1) => y0 >= 4 && y1 <= H - 4 && !boxes.some((o) => x1 > o.x && x0 < o.x + o.w && y1 > o.y && y0 < o.y + o.h);
      const handleOk = (y) => clear(x - 18, x + 18, y - 26, y + 26);
      const tagsOk = (y) => clear(x - 100, x + 100, y + 28, y + 50);
      const ob = oPanel.getBoundingClientRect(), top0 = ob.bottom - r0.top + 46;
      const ys = [top0];
      for (let y = 30; y <= H - 30; y += 12) ys.push(y);
      ys.sort((p, q) => Math.abs(p - top0) - Math.abs(q - top0));
      let hy = ys.find((y) => handleOk(y) && tagsOk(y));
      const tags = hy !== undefined;
      if (hy === undefined) hy = ys.find(handleOk);
      divider.classList.toggle("lift", hy === undefined);      // nowhere clear: draw the handle over the panels
      divider.classList.toggle("no-tags", !tags);
      divider.style.setProperty("--hy", `${Math.round(hy ?? Math.min(Math.max(top0, 40), H - 40))}px`);
    }
    map.on("move zoom resize viewreset", clipOrig);
    let swAnim = null;
    function setSwipe(x, animate = true) {
      if (swAnim) cancelAnimationFrame(swAnim);
      if (!animate) { swipe.x = x; clipOrig(); return; }
      const from = swipe.x, t0 = performance.now();
      const f = (now) => { const t = Math.min(1, (now - t0) / 700); swipe.x = from + (x - from) * (1 - (1 - t) ** 3); clipOrig(); swAnim = t < 1 ? requestAnimationFrame(f) : null; };
      swAnim = requestAnimationFrame(f);
    }
    const handle = divider.querySelector(".swipe-handle");
    let drag = false;
    handle.addEventListener("pointerdown", (e) => { drag = true; map.dragging.disable(); handle.setPointerCapture(e.pointerId); if (swAnim) cancelAnimationFrame(swAnim); });
    handle.addEventListener("pointermove", (e) => {
      if (!drag) return; const r = map.getContainer().getBoundingClientRect();
      swipe.x = Math.min(0.98, Math.max(0.02, (e.clientX - r.left) / r.width)); clipOrig();
    });
    const endDrag = () => { if (drag) { drag = false; map.dragging.enable(); } };
    handle.addEventListener("pointerup", endDrag); handle.addEventListener("pointercancel", endDrag);
    handle.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") { setSwipe(Math.min(0.98, Math.max(0.02, swipe.x + (e.key === "ArrowLeft" ? -0.04 : 0.04))), false); e.preventDefault(); }
    });
    function nearestTopo(set) {
      const c = map.getCenter(); let best = null, bd = Infinity;
      Object.entries(topoMeta).filter(([id, t]) => !set || (t.tiles || id) === set).forEach(([id, t]) => { const d = c.distanceTo(L.latLngBounds(t.focus || t.bounds).getCenter()); if (d < bd) { bd = d; best = id; } });
      return "topo:" + best;
    }
    function setOriginal(k, user = false) {
      if (!user && userOrig) return;
      if (user) userOrig = true;
      if (k === "topo") k = nearestTopo();
      if (k.startsWith("sheet:")) k = nearestTopo(k.slice(6));
      if (k === curOrig && oSel.dataset.init) return;
      oSel.dataset.init = 1;
      if (curOrig !== "none") map.removeLayer(getOrig(curOrig));
      curOrig = k;
      blendOrig();
      if (k !== "none") { const l = getOrig(k); l.setOpacity(opFor(k)); l.addTo(map); document.getElementById("o-op").value = Math.round(opFor(k) * 100); }
      oSel.value = k.startsWith("topo:") ? "sheet:" + (topoMeta[k.slice(5)].tiles || k.slice(5)) : k;
      oPanel.classList.toggle("is-none", k === "none");
      oCap.innerHTML = k === "none" ? "" : `Source: ${ORIGS[k].cap} · <a href="${ORIGS[k].href}" target="_blank" rel="noopener">Open the original (PDF)</a>`;
      oLeg.innerHTML = k === "none" ? "" : OLEG[k.startsWith("topo:") ? "topo" : k].map(([t, c, l]) => lgRow(t, c, l)).join("");
      divider.querySelector(".swipe-tag.l").textContent = k === "none" ? "" : ORIGS[k].tag;
      clipOrig();
    }
    oSel.addEventListener("change", () => {
      setOriginal(oSel.value, true);
      // a survey sheet chosen from afar: go to it
      if (isSheet(curOrig) && !map.getBounds().intersects(L.latLngBounds(ORIGS[curOrig].bounds)))
        map.flyToBounds(L.latLngBounds(ORIGS[curOrig].win), { ...pad(), maxZoom: 15, duration: 1.0 });
    });
    document.getElementById("o-op").addEventListener("input", (e) => { origOpacity = e.target.value / 100; userOpacity = true; if (curOrig !== "none") getOrig(curOrig).setOpacity(origOpacity); });
    document.getElementById("o-swipe").addEventListener("change", (e) => { swipe.on = e.target.checked; clipOrig(); });

    /* ======================= utopia layers ======================= */
    const PL = {};   // place registry: id -> { ch, name, bounds, layer, maxZoom, topo }
    const reg = (id, o) => { PL[id] = o; };
    const pop = (h, meta, body) => `<div class="st-pop"><p class="meta">${meta}</p><h4>${h}</h4>${body}</div>`;
    const placeById = Object.fromEntries(places.features.map((f) => [f.properties.id, f]));

    // II · pastoral — named suburbs (official outlines), with year-built profile
    const pastoralIds = ["valley", "pasadena", "hollywood", "hancock", "windsor"];
    const pastoralLayer = L.featureGroup(pastoralIds.map((id) => {
      const f = placeById[id], p = f.properties;
      const l = L.geoJSON(f, { pane: "g-pastoral", style: { color: LINE.pastoral, weight: id === "valley" ? 1.6 : 2, fillColor: COL.pastoral, fillOpacity: id === "valley" ? 0.1 : 0.2 } })
        .bindPopup(pop(p.name, "The Pastoral Suburb", `<p>Typical year built: <b>${p.median_year}</b><br>${Math.round(p.pre1930_pct)}% of its buildings date from before 1930</p>`));
      reg(id, { ch: "pastoral", name: p.name, bounds: l.getBounds(), layer: l, maxZoom: 13.5 });
      return l;
    })).addTo(map);
    const HOLC_OP = { A: 0.05, B: 0.16, C: 0.3, D: 0.5 };
    const holcLayer = L.geoJSON(holc, { pane: "g-pastoral",
      style: (f) => ({ color: INK, weight: 0.8, opacity: 0.7, fillColor: INK, fillOpacity: HOLC_OP[f.properties.grade] }),
      onEachFeature: (f, l) => { const g = f.properties.grade, h = S.holc[g];
        l.bindPopup(pop(`Grade ${g} — “${{ A: "Best", B: "Still desirable", C: "Declining", D: "Hazardous" }[g]}”`, "1939 Federal Mortgage-Risk Map",
          `<p>Today ${Math.round(h.zoned_sf_pct)}% of the City’s grade-${g} land is zoned for detached houses.</p>`)); } });
    const zonedLayer = L.tileLayer(D0 + "tiles/zonedsf/{z}/{x}/{y}.webp", { pane: "g-pastoral", minNativeZoom: 10, maxNativeZoom: 14, maxZoom: 17, opacity: 0.9,
      bounds: L.latLngBounds([33.70, -118.68], [34.34, -118.15]) });

    // III · Autopia — freeways, named freeways & interchanges, Boyle Heights
    const fwyLayer = L.geoJSON(fwy, { pane: "g-autopia", interactive: false, style: { color: LINE.autopia, weight: 1.7, opacity: 0.85 } }).addTo(map);
    const boyle = placeById.boyle;
    const boyleLayer = L.geoJSON(boyle, { pane: "g-autopia", style: { color: LINE.autopia, weight: 2.6, fillColor: COL.autopia, fillOpacity: 0.16 } })
      .bindPopup(pop("Boyle Heights", "Autopia", `<p>Typical year built: <b>${boyle.properties.median_year}</b><br>
        ${Math.round(SS.boyle.bh.within_500ft_pct)}% of its homes stand within 500 ft of a freeway, the highest share of ${SS.boyle.places.length} places in the County (City of Los Angeles: ${Math.round(SS.boyle.city.within_500ft_pct)}%)</p>`)).addTo(map);
    reg("boyle", { ch: "autopia", name: "Boyle Heights", bounds: boyleLayer.getBounds(), layer: boyleLayer, maxZoom: 14 });
    ["smfwy", "santaana"].forEach((id) => {
      const f = placeById[id];
      const l = L.geoJSON(f, { pane: "g-autopia", style: { color: LINE.autopia, weight: 5.5, opacity: 0.95, lineCap: "round" } })
        .bindPopup(pop(f.properties.name, "Autopia", "")).addTo(map);
      const cs = f.geometry.type === "LineString" ? f.geometry.coordinates : f.geometry.coordinates.reduce((a, b) => (b.length > a.length ? b : a));
      const mid = cs[Math.floor(cs.length / 2)];
      reg(id, { ch: "autopia", name: f.properties.name, bounds: l.getBounds(), layer: l, maxZoom: 14, labelAt: [mid[1], mid[0]] });
    });
    ["fourlevel", "ela", "smsd"].forEach((id) => {
      const f = placeById[id], [lng, lat] = f.geometry.coordinates;
      const l = L.circleMarker([lat, lng], { pane: "g-autopia", radius: 8, color: INK, weight: 2, fillColor: COL.autopia, fillOpacity: 1 })
        .bindPopup(pop(f.properties.name, "Autopia", "")).addTo(map);
      reg(id, { ch: "autopia", name: id === "smsd" ? "Santa Monica × San Diego freeways" : f.properties.name, short: id === "smsd" ? "I-10 × I-405" : null, bounds: L.latLngBounds([[lat, lng], [lat, lng]]), layer: l, maxZoom: 14, ll: [lat, lng] });
    });
    const bh500 = L.geoJSON(fwy500, { pane: "g-autopia", interactive: false, style: { stroke: false, fillColor: COL.autopia, fillOpacity: 0.45 } });
    const maxV = S.aadt.max.v, MINV = 100000;
    const aR = (v) => 1.6 + 8 * Math.sqrt(Math.max(0, v - MINV) / (maxV - MINV));
    const aadtLayer = L.layerGroup(aadt.features.filter((f) => f.properties.v >= MINV).sort((a, b) => a.properties.v - b.properties.v).map((f) => {
      const p = f.properties, [lng, lat] = f.geometry.coordinates;
      return L.circleMarker([lat, lng], { pane: "g-autopia", renderer: cv.autopia, radius: aR(p.v), color: "#fff", weight: 0.7, fillColor: COL.autopia, fillOpacity: 0.8 })
        .bindPopup(pop(`${fmt(p.v)} vehicles a day`, "Freeway Traffic, 2024", `<p>${p.at}</p>`));
    }));
    const bottLayer = L.geoJSON(bott, { pane: "g-autopia",
      style: (f) => ({ color: "#6b4a00", weight: f.properties.rank <= 5 ? 6 : 4, opacity: 0.9, lineCap: "round" }),
      onEachFeature: (f, l) => { const p = f.properties;
        l.bindPopup(pop(`${p.fwy.replace(/^I(\d)/, "I-$1").replace(/-([NSEW])$/, " ($1)")} at ${p.at}`, `Worst Traffic Jams of 2024 · #${p.rank}`, "")); } });

    // IV · Centers — the 56 discs (½ mile), coloured by what each became
    const OUT = {
      realised: { fill: COL.centers, op: 0.6, stroke: LINE.centers, w: 1.2, label: "Towers and rail" },
      towers: { fill: "#86b6ef", op: 0.55, stroke: LINE.centers, w: 1.2, label: "Towers, no rail" },
      rail: { fill: "#ffffff", op: 0.65, stroke: LINE.centers, w: 2.6, label: "Rail, no towers" },
      neither: { fill: "#ffffff", op: 0.05, stroke: "#8b877e", w: 1.2, dash: "3 3", label: "Neither" },
    };
    const NB = {
      jobs: { label: "A job centre built low", rule: "10,000 or more jobs", fill: "#6f6b63" },
      transit: { label: "Rail or a busway nearby, or coming", rule: "Metro within a mile, a line being built, or a busway or Metrolink stop", fill: "#cddaf2", stroke: LINE.centers, dash: "4 2.5" },   // rail in waiting: next to "Rail only", dashed like a line under construction
      urban: { label: "A dense low-rise neighbourhood", rule: "4,000 or more homes", fill: "#c4bfb4" },
      suburban: { label: "Still suburban", rule: "none of these", fill: "#e8e4dc" },
    };
    const ALIAS = { "Canoga Park–Woodland Hills": "Warner Center" };
    // where the jobs are today (Giuliano & Small: 10+ jobs per acre, 10,000+ jobs), under the planned circles
    const todayLayer = L.geoJSON(todayC, { pane: "g-centers",
      style: { color: LINE.centers, weight: 1.6, opacity: 0.9, fillColor: COL.centers, fillOpacity: 0.1 },
      onEachFeature: (f, l) => { const p = f.properties;
        l.bindPopup(pop(p.name, "A Job Centre Today", `<p><b>${fmt(p.jobs)} jobs</b> over ${p.km2} km² (at least 10 jobs per acre throughout)</p>
          <p>${p.planned.length ? `The 1974 plan drew ${p.planned.length === 1 ? "a centre" : p.planned.length + " centres"} here: ${p.planned.map((n) => ALIAS[n] || n).join(", ")}.` : "The 1974 plan drew no centre here."}</p>`)); } }).addTo(map);
    const centerLayer = L.geoJSON(centers, { pane: "g-centers",
      pointToLayer: (f, ll) => { const o = OUT[f.properties.oc];
        return L.circle(ll, { pane: "g-centers", radius: 804.7, color: o.stroke, weight: o.w, dashArray: o.dash, fillColor: o.fill, fillOpacity: o.op }); },
      onEachFeature: (f, l) => { const p = f.properties, nm = ALIAS[p.name] || p.name;
        l.bindPopup(pop(nm, "A Centre of the 1974 Plan", `<p><b>${{ realised: "Got tall buildings and a rail station", towers: "Got tall buildings, no rail station", rail: "Got a rail station, no tall buildings", neither: "Got neither tall buildings nor a rail station" }[p.oc]}</b> within half a mile of where the plan drew it.</p>${p.today_id ? `<p>Today it lies ${p.today_in ? "in" : "beside"} a job centre of ${fmt(p.today_jobs)} jobs over ${p.today_km2} km².</p>` : `<p>No job centre today within 800 m.</p>`}${p.oc === "neither" && NB[p.nb] ? `<p>What it became instead: ${NB[p.nb].label.toLowerCase()}. Within half a mile of its core: ${fmt(p.jobs)} jobs, ${fmt(p.homes)} homes.</p>` : ""}`)); } }).addTo(map);
    const circleByName = {};
    centerLayer.eachLayer((l) => { circleByName[l.feature.properties.name] = l; });
    const cIdx = Object.fromEntries(centers.features.map((f) => [f.properties.name, f]));
    [["centurycity", "Century City"], ["westwood", "Westwood"], ["warner", "Canoga Park–Woodland Hills"]].forEach(([id, nm]) => {
      const [lng, lat] = cIdx[nm].geometry.coordinates, ll = L.latLng(lat, lng);
      reg(id, { ch: "centers", name: ALIAS[nm] || nm, bounds: ll.toBounds(1700), maxZoom: 14, ll: [lat, lng], layer: circleByName[nm] });
    });
    const towerLayer = L.layerGroup(towers.features.map((f) => { const p = f.properties, [lng, lat] = f.geometry.coordinates;
      return L.circleMarker([lat, lng], { pane: "g-centers", renderer: cv.centers, radius: 1.6 + (p.h || p.st * 12.5) / 450, stroke: false, fillColor: INK, fillOpacity: 0.85 })
        .bindTooltip(p.h ? `${fmt(p.h)} ft` : `${p.st} storeys`, { direction: "top" }); }));
    const openStations = new Set(stations.features.filter((f) => f.properties.k === "open").map((f) => f.properties.name));
    const railLayer = L.layerGroup([
      L.geoJSON(rail, { pane: "g-centers", interactive: false, style: { color: INK, weight: 2.4, opacity: 0.85 } }),
      L.geoJSON(stations, { pane: "g-centers", filter: (f) => f.properties.k === "open" || (f.properties.k === "uc" && !openStations.has(f.properties.name)),
        pointToLayer: (f, ll) => L.circleMarker(ll, { pane: "g-centers", radius: f.properties.k === "uc" ? 4 : 2.8, color: INK, weight: 1.3, dashArray: f.properties.k === "uc" ? "2 2" : null, fillColor: f.properties.k === "uc" ? "#fbeede" : "#fff", fillOpacity: 1 }),
        onEachFeature: (f, l) => l.bindTooltip(`${f.properties.name}${f.properties.k === "uc" ? ` — under construction (${f.properties.line})` : ""}`, { direction: "top" }) }),
    ]);

    // I · Transit — today's Metro, section by section as it opened (rail solid, busway dashed), and its stations
    const LN = { A: "A Line (Blue, then Gold)", B: "B Line (Red)", C: "C Line (Green)", D: "D Line (Purple)", E: "E Line (Expo, then Gold)", K: "K Line (Crenshaw)", G: "G Line busway (Orange)", J: "J Line busway (Silver)" };
    const metroLayer = L.layerGroup().addTo(map);
    const metroItems = metro.features.map((f) => {
      const p = f.properties;
      const l = p.kind === "station"
        ? L.circleMarker([f.geometry.coordinates[1], f.geometry.coordinates[0]], { pane: "g-transit", radius: 2.6, color: LINE.transit, weight: 1.3, fillColor: "#fff", fillOpacity: 1 })
            .bindTooltip(`${p.name} · ${p.year}`, { direction: "top" })
        : L.geoJSON(f, { pane: "g-transit", style: p.kind === "bus" ? { color: LINE.transit, weight: 2.2, opacity: 0.95, dashArray: "5 4" } : { color: LINE.transit, weight: 3, opacity: 0.95 } })
            .bindPopup(pop(LN[p.line] || p.line + " Line", "The Transit Metropolis", `<p>This section opened in <b>${p.year}</b>${p.kind === "bus" ? " as a busway" : ""}.</p>`));
      return [p.year, p.kind === "station", l];
    });
    let metroY = null;
    const metroYear = (Y) => {
      if (Y === metroY) return; metroY = Y;
      metroItems.forEach(([y, st, l]) => { const on = y <= Y; if (on !== metroLayer.hasLayer(l)) { if (on) { metroLayer.addLayer(l); if (st) l.bringToFront(); } else metroLayer.removeLayer(l); } });
    };
    yearHooks.push(metroYear); metroYear(year);
    // sections named in the text: outlined on click, never drawn twice
    [["blueline", "Blue Line, 1990", (p) => p.line === "A" && p.year <= 1991, 11.5], ["redline", "Red Line, 1993", (p) => p.line === "B" && p.year === 1993, 14],
     ["expo", "Expo Line to Santa Monica, 2016", (p) => p.line === "E" && p.year === 2016, 12.5], ["connector", "Regional Connector, 2023", (p) => p.line === "A" && p.year === 2023, 15],
     ["pomona", "A Line to Pomona, 2025", (p) => p.line === "A" && p.year === 2025, 12.5], ["dline", "D Line to La Cienega, 2026", (p) => p.line === "D" && p.year === 2026, 14]].forEach(([id, name, test, z]) => {
      const fs = metro.features.filter((f) => f.properties.kind !== "station" && test(f.properties));
      const l = L.geoJSON({ type: "FeatureCollection", features: fs });
      const cs = fs.map((f) => (f.geometry.type === "LineString" ? f.geometry.coordinates : f.geometry.coordinates.flat())).reduce((a, b) => (b.length > a.length ? b : a));
      const mid = cs[Math.floor(cs.length / 2)];
      reg(id, { ch: "transit", name, bounds: l.getBounds(), layer: l, maxZoom: z, labelAt: [mid[1], mid[0]] });
    });

    // the Hollywood Subway, 1925 to 1955: Subway Terminal Building (417 S Hill St) to the Belmont Tunnel portal (1304 W 2nd St),
    // both City Historic-Cultural Monuments; drawn straight between them (0.82 mi, the tunnel's recorded 4,325 ft)
    const HS = [[34.05017, -118.25129], [34.05999, -118.25934]];
    const hsub = L.featureGroup([
      L.polyline(HS, { pane: "g-transit", color: "#fff", weight: 7, opacity: 0.9 }),
      L.polyline(HS, { pane: "g-transit", color: INK, weight: 3.2, dashArray: "7 4", lineCap: "butt" }),
      ...HS.map((ll) => L.circleMarker(ll, { pane: "g-transit", radius: 4.5, color: INK, weight: 2, fillColor: "#fff", fillOpacity: 1 })),
    ]).bindPopup(pop("The Hollywood Subway", "Pacific Electric, 1925 to 1955", `<p>Just under a mile of tunnel beneath Bunker Hill, from the Subway Terminal Building on Hill Street to the Belmont Tunnel portal near Glendale Boulevard, where the Red Cars came up for Hollywood, Glendale and the Valley. Opened in 1925, closed in 1955; drawn here straight between its two ends, both City Historic-Cultural Monuments.</p><p><a href="https://en.wikipedia.org/wiki/Hollywood_Subway" target="_blank" rel="noopener">Read more (Wikipedia)</a></p>`));
    yearHooks.push((Y) => { const on = Y >= 1925 && Y <= 1955; if (on !== map.hasLayer(hsub)) on ? hsub.addTo(map) : map.removeLayer(hsub); });
    if (year >= 1925 && year <= 1955) hsub.addTo(map);
    reg("hsubway", { ch: "transit", name: "Hollywood Subway, 1925", bounds: L.latLngBounds(HS).pad(0.35), layer: L.polyline(HS), maxZoom: 15, labelAt: [34.0551, -118.2553] });

    // the rail network Los Angeles dismantled: Red Cars (Pacific Electric) and Yellow Cars (Los Angeles Railway) in 1925, traced from
    // the Kelker, De Leuw plate (and line maps where they are more precise), in the plate's own browns; the last lines drawn heavier
    const OLDC = { PE: "#a8743a", LARy: "#c88845" };
    const oldStyle = (p, faded) => (p.op === "PE" ? { color: OLDC.PE, weight: 2.6, opacity: faded ? 0.35 : 0.95 } : { color: OLDC.LARy, weight: 1.9, opacity: faded ? 0.35 : 1, dashArray: "4 3" });
    const oldName = (p) => (p.op === "PE" ? "Red Cars (Pacific Electric)" : "Yellow Cars (Los Angeles Railway)");
    const lineName = (p) => (!p.name ? oldName(p) : /Line|Railway/.test(p.name) ? p.name : `Line ${p.name}`);
    const HOW = { plate: "Traced from the Kelker, De Leuw plan of 1925.", wiki: "Route as mapped for the line’s Wikipedia article from historical maps.",
      ohm: "Track as mapped on OpenHistoricalMap, kept where the 1925 plan shows it.", streets: "Routed on today’s streets from the line’s 1920s route." };
    const oldnetLayer = L.geoJSON({ type: "FeatureCollection", features: oldnet.features.filter((f) => !f.properties.last) }, { pane: "g-transit", style: (f) => oldStyle(f.properties),
      onEachFeature: (f, l) => l.bindPopup(pop(lineName(f.properties), `${oldName(f.properties)}, about 1925`, `<p>${HOW[f.properties.src] || ""}</p>`)) });
    const lastF = (yr) => oldnet.features.filter((f) => f.properties.last === yr);
    const lastLayer = L.featureGroup();
    ["1961", "1963"].forEach((yr) => lastF(yr).forEach((f) => {
      L.geoJSON(f, { pane: "g-transit", interactive: false, style: { color: INK, weight: 6, opacity: 0.85 } }).addTo(lastLayer);
      L.geoJSON(f, { pane: "g-transit", style: { color: OLDC[f.properties.op], weight: 3.4, opacity: 1 } })
        .bindPopup(pop(lineName(f.properties), yr === "1961" ? "The Last Red Car, April 1961" : "The Last Streetcars, 31 March 1963",
          `<p>${yr === "1961" ? "The Pacific Electric’s line between Los Angeles and Long Beach, the last Red Car route, closed by the Metropolitan Transit Authority." : "One of the five Yellow Car lines (J, P, R, S, V) the Metropolitan Transit Authority replaced with buses, the last streetcars in Los Angeles."}</p>`)).addTo(lastLayer);
    }));
    [["lastredcar", "The last Red Car, 1961", "1961"], ["laststreetcars", "The last streetcars, 1963", "1963"]].forEach(([id, name, yr]) => {
      const fs = lastF(yr); if (!fs.length) return;
      const l = L.geoJSON({ type: "FeatureCollection", features: fs });
      reg(id, { ch: "transit", name, bounds: l.getBounds(), layer: l, maxZoom: yr === "1961" ? 11.5 : 12.5 });
    });

    // V · Cooperative — footprints + numbered pins
    const pins = utop.features.filter((f) => !f.properties.shape);
    const shapes = Object.fromEntries(utop.features.filter((f) => f.properties.shape).map((f) => [f.properties.id, f]));
    const coopLayer = L.featureGroup();
    L.geoJSON({ type: "FeatureCollection", features: Object.values(shapes) }, { pane: "g-coop", interactive: false,
      style: { color: LINE.coop, weight: 2, fillColor: COL.coop, fillOpacity: 0.3 } }).addTo(coopLayer);
    const READ = { llano: "https://en.wikipedia.org/wiki/Llano_del_Rio", landers: "https://en.wikipedia.org/wiki/Little_Landers", village: "https://en.wikipedia.org/wiki/Village_Green,_Los_Angeles",
      crestwood: "https://en.wikipedia.org/wiki/Crestwood_Hills,_Los_Angeles", elysian: "https://en.wikipedia.org/wiki/Battle_of_Chavez_Ravine" };
    pins.forEach((f, i) => {
      const p = f.properties, [lng, lat] = f.geometry.coordinates;
      const m = L.marker([lat, lng], { pane: "g-coop", icon: L.divIcon({ className: "", html: `<span class="u-pin">${i + 1}</span>`, iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12] }) })
        .bindPopup(pop(p.name, p.years, `<p>${{ abandoned: "Abandoned; the plans were never built", absorbed: "Absorbed into the suburb", built: "Built; still standing", privatised: "Built; the cooperative later dissolved", replaced: "Never built; the site became Dodger Stadium" }[p.fate]}</p>
          ${ORIGS["topo:" + p.id] ? `<p><a href="${ORIGS["topo:" + p.id].href}" target="_blank" rel="noopener">Open the ${topoMeta[p.id].year} survey map (PDF)</a></p>` : ""}
          ${p.id === "llano" ? `<p><a href="https://ohp.parks.ca.gov/ListedResources/Detail/933" target="_blank" rel="noopener">California Historical Landmark No. 933</a></p>` : ""}
          ${READ[p.id] ? `<p><a href="${READ[p.id]}" target="_blank" rel="noopener">Read more (Wikipedia)</a></p>` : ""}`), { maxWidth: 300 });
      m.addTo(coopLayer);
      const b = shapes[p.id] ? L.geoJSON(shapes[p.id]).getBounds() : L.latLng(lat, lng).toBounds(400);
      const SHORT = { llano: "Llano del Rio", landers: "Little Landers · Bolton Hall", village: "Village Green", crestwood: "Crestwood Hills", elysian: "Chávez Ravine" };
      reg(p.id, { ch: "coop", name: p.name, short: SHORT[p.id], bounds: b, layer: m, maxZoom: 15, topo: topoMeta[p.id] ? "topo:" + p.id : null, ll: [lat, lng], n: i + 1 });
    });
    coopLayer.addTo(map);

    const EXTRAS = { holc: holcLayer, zoned: zonedLayer, aadt: aadtLayer, bott: bottLayer, bh500, towers: towerLayer, rail: railLayer, oldnet: oldnetLayer, lastrail: lastLayer };
    let extras = [];
    // the year layer is a 120 m grid: it reads at city scale and turns into blocks at street scale, so it fades out from zoom 12 to 13
    function morphOpacity() {
      const z = map.getZoom();
      let o = z >= 13 ? 0 : z > 12 ? 13 - z : 1;
      if (extras.some((k) => k === "holc" || k === "zoned" || k === "bh500")) o *= 0.6;
      morph.setOpacity(o);
      if (window.__d8year) window.__d8year(year);
    }
    map.on("zoomend", morphOpacity);
    function setExtras(list) {
      extras = list;
      morphOpacity();
      Object.entries(EXTRAS).forEach(([k, l]) => { const on = list.includes(k); if (on && !map.hasLayer(l)) l.addTo(map); if (!on && map.hasLayer(l)) map.removeLayer(l); });
      oldnetLayer.setStyle((f) => oldStyle(f.properties, list.includes("lastrail")));   // the survivors stand out against the faded 1925 network
    }

    /* ======================= focus, labels, key ======================= */
    const mapEl = document.getElementById("st-map");
    let focus = "all";
    function setFocus(ch) {
      focus = ch; mapEl.dataset.focus = ch;
      GROUPS.forEach((g) => { GP[g].classList.toggle("dim", ch !== "all" && ch !== "none" && ch !== g); GP[g].classList.toggle("off", ch === "none"); });
      document.querySelectorAll("#st-focus li").forEach((li) => li.classList.toggle("on", ch === "all" || li.dataset.ch === ch));
      updateKey();
    }
    // Labels live in one absolutely positioned layer and are placed greedily: each tries a few anchor positions and
    // takes the first that clears the map edge, the panels, the swipe handle and every label already placed;
    // a label that fits nowhere is hidden rather than drawn over something else.
    // orientation names, set in the page's type (replacing the basemap's raster labels); shown from a zoom level up
    const baseLayer = L.DomUtil.create("div", "lbl-layer", map.getContainer());
    const BASE = [
      ["San Fernando Valley", 34.215, -118.47, 9, "big"], ["San Gabriel Valley", 34.075, -118.04, 9, "big"], ["Downtown", 34.049, -118.25, 9, "big"],
      ["Hollywood", 34.098, -118.327, 9.5, ""], ["Santa Monica", 34.019, -118.491, 9, "big"], ["Pasadena", 34.148, -118.144, 9, "big"], ["Long Beach", 33.772, -118.19, 9, "big"],
      ["Pacific Ocean", 33.84, -118.62, 8, "water"], ["Santa Monica Bay", 33.93, -118.53, 10.5, "water"],
      ["Burbank", 34.181, -118.309, 10.5, ""], ["Glendale", 34.142, -118.255, 10.5, ""], ["Inglewood", 33.962, -118.353, 10.5, ""], ["Torrance", 33.836, -118.341, 10.5, ""],
      ["Compton", 33.896, -118.22, 10.5, ""], ["East Los Angeles", 34.024, -118.172, 10.5, ""], ["Beverly Hills", 34.073, -118.4, 10.5, ""], ["Culver City", 34.021, -118.396, 10.5, ""],
      ["Venice", 33.985, -118.469, 11, ""], ["San Pedro", 33.736, -118.292, 10.5, ""], ["Van Nuys", 34.186, -118.449, 11, ""], ["Northridge", 34.228, -118.536, 11, ""],
      ["Whittier", 33.979, -118.033, 10.5, ""], ["Downey", 33.94, -118.13, 10.5, ""], ["El Monte", 34.069, -118.028, 10.5, ""], ["Malibu", 34.035, -118.69, 10.5, ""],
      ["LAX", 33.942, -118.408, 10.5, ""], ["Westwood", 34.061, -118.445, 12, ""], ["Koreatown", 34.058, -118.3, 12, ""], ["South Los Angeles", 33.99, -118.28, 11.5, ""],
      ["Silver Lake", 34.087, -118.27, 12, ""], ["Echo Park", 34.078, -118.26, 12.5, ""], ["Highland Park", 34.112, -118.192, 12, ""], ["Watts", 33.94, -118.243, 12, ""],
      ["Sylmar", 34.307, -118.449, 11, ""], ["Chatsworth", 34.257, -118.601, 11.5, ""], ["Sherman Oaks", 34.151, -118.449, 12, ""], ["Studio City", 34.14, -118.39, 12, ""],
      ["Griffith Park", 34.136, -118.294, 11.5, "water"],
    ].map(([t, lat, lng, z, cls]) => { const el = L.DomUtil.create("div", "base-label " + cls, baseLayer); el.textContent = t; return { t, ll: L.latLng(lat, lng), z, el }; });
    BASE[BASE.length - 1].el.className = "base-label";   // Griffith Park is land
    const lblLayer = L.DomUtil.create("div", "lbl-layer", map.getContainer());
    let lbls = [];
    function showLabels(ids, extra = []) {
      lblLayer.replaceChildren();
      lbls = ids.filter((id) => PL[id]).map((id) => {
        const P = PL[id], el = L.DomUtil.create("div", "pl-label", lblLayer); el.textContent = P.short || P.name;
        return { ll: L.latLng(P.labelAt || P.ll || P.bounds.getCenter()), pt: !!P.ll && !P.labelAt, el, b: P.ll ? null : P.bounds };
      }).concat(extra.map(([ll, text]) => { const el = L.DomUtil.create("div", "pl-label", lblLayer); el.textContent = text; return { ll: L.latLng(ll), pt: true, el }; }));
      placeLabels();
    }
    const box = map.getContainer().closest(".st-mapbox");
    function obstacles() {
      const r0 = map.getContainer().getBoundingClientRect();
      return [...box.querySelectorAll(".st-orig, .st-focus, .st-key, .st-time, .leaflet-control-zoom, .swipe-handle, .swipe-tag, .st-back, .leaflet-control-attribution")]
        .filter((e) => e.offsetParent && getComputedStyle(e).display !== "none" && e.textContent !== "")
        .map((e) => { const r = e.getBoundingClientRect(); return { x: r.left - r0.left - 4, y: r.top - r0.top - 4, w: r.width + 8, h: r.height + 8 }; })
        .filter((o) => o.w > 8 && o.h > 8);
    }
    const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
    function placeLabels() {
      const size = map.getSize(), obs = obstacles(), placed = [];
      // points first (their anchor is exact), then areas (they can slide inside their outline)
      [...lbls].sort((a, b) => b.pt - a.pt).forEach((L_) => {
        const w = L_.el.offsetWidth, h = L_.el.offsetHeight, p = map.latLngToContainerPoint(L_.ll);
        const cand = L_.pt
          ? [[14, -h / 2], [-w - 14, -h / 2], [-w / 2, -h - 14], [-w / 2, 14], [12, -h - 8], [12, 8], [-w - 12, -h - 8], [-w - 12, 8], [-w / 2, -h - 30], [-w / 2, 30]]
          : [[-w / 2, -h / 2], [-w / 2, -h - 10], [-w / 2, 10], [12, -h / 2], [-w - 12, -h / 2], [-w / 2, -h - 32], [-w / 2, 32], [16, -h - 16], [-w - 16, 16], [16, 16], [-w - 16, -h - 16]];
        if (L_.b) {   // an area label may also sit anywhere well inside its own outline's box
          const a = map.latLngToContainerPoint(L_.b.getNorthWest()), z = map.latLngToContainerPoint(L_.b.getSouthEast());
          for (const fx of [0.3, 0.7, 0.5]) for (const fy of [0.3, 0.7, 0.5]) cand.push([a.x + (z.x - a.x) * fx - p.x - w / 2, a.y + (z.y - a.y) * fy - p.y - h / 2]);
        }
        let ok = null;
        for (const [dx, dy] of cand) {
          const r = { x: p.x + dx, y: p.y + dy, w, h };
          if (r.x < 4 || r.y < 4 || r.x + w > size.x - 4 || r.y + h > size.y - 4) continue;
          if (obs.some((o) => hit(o, r)) || placed.some((o) => hit(o, r))) continue;
          ok = r; break;
        }
        if (ok) { L_.el.style.transform = `translate(${Math.round(ok.x)}px, ${Math.round(ok.y)}px)`; L_.el.style.visibility = ""; placed.push({ x: ok.x - 3, y: ok.y - 3, w: w + 6, h: h + 6 }); }
        else L_.el.style.visibility = "hidden";
      });
      // orientation names last: they never push an essay label away, and skip a name the essay is already showing
      const z = map.getZoom(), shown = new Set(lbls.map((l) => l.el.textContent.toLowerCase()));
      Object.values(PL).forEach((P) => { if (P.ll && P.layer && P.ch !== "centers") { const q = map.latLngToContainerPoint(P.ll); placed.push({ x: q.x - 14, y: q.y - 14, w: 28, h: 28 }); } });
      BASE.forEach((b) => {
        if (z < b.z || shown.has(b.t.toLowerCase())) { b.el.style.visibility = "hidden"; return; }
        const w = b.el.offsetWidth, h = b.el.offsetHeight, p = map.latLngToContainerPoint(b.ll), r = { x: p.x - w / 2, y: p.y - h / 2, w, h };
        if (r.x < 4 || r.y < 4 || r.x + w > size.x - 4 || r.y + h > size.y - 4 || obs.some((o) => hit(o, r)) || placed.some((o) => hit(o, r))) { b.el.style.visibility = "hidden"; return; }
        b.el.style.transform = `translate(${Math.round(r.x)}px, ${Math.round(r.y)}px)`; b.el.style.visibility = ""; placed.push({ x: r.x - 4, y: r.y - 3, w: w + 8, h: h + 6 });
      });
    }
    map.on("move zoomend resize", placeLabels);
    map.on("zoomanim", () => { lblLayer.classList.add("hide"); baseLayer.classList.add("hide"); });
    map.on("zoomend", () => { lblLayer.classList.remove("hide"); baseLayer.classList.remove("hide"); });
    // an open popup owns the screen: labels and the swipe chips step aside so nothing is written over it
    map.on("popupopen", () => { lblLayer.classList.add("hide"); baseLayer.classList.add("hide"); map.getContainer().classList.add("popup-open"); });
    map.on("popupclose", () => { lblLayer.classList.remove("hide"); baseLayer.classList.remove("hide"); map.getContainer().classList.remove("popup-open"); });
    // the Valley's polygon centre lands in the hills; label it where the subdivisions are
    PL.valley.labelAt = [34.205, -118.47];
    const keyEl = document.getElementById("st-key");
    const sw = (style) => `<i style="${style}"></i>`;
    let hasPhotos = false;
    // retractable panels: the header stays, the body folds away; the choice is remembered on this device
    const remember = (k, v) => { try { localStorage.setItem(k, v ? "1" : "0"); } catch (e) {} };
    const recall = (k) => { try { return localStorage.getItem(k) === "1"; } catch (e) { return false; } };
    let keyClosed = recall("d8-key-closed");
    keyEl.addEventListener("click", (e) => {
      const bb = e.target.closest("[data-base]");
      if (bb) { setBase(bb.dataset.base); return; }
      if (!e.target.closest(".panel-t")) return;
      keyClosed = !keyClosed; remember("d8-key-closed", keyClosed);
      keyEl.classList.toggle("closed", keyClosed); keyEl.querySelector(".panel-t").setAttribute("aria-expanded", String(!keyClosed)); placeLabels(); clipOrig();
    });
    {
      const t = oPanel.querySelector(".panel-t"); let closed = recall("d8-orig-closed");
      const apply = () => { oPanel.classList.toggle("closed", closed); t.setAttribute("aria-expanded", String(!closed)); placeLabels(); clipOrig(); };
      t.addEventListener("click", () => { closed = !closed; remember("d8-orig-closed", closed); apply(); });
      apply();
    }
    L.DomEvent.disableClickPropagation(keyEl); L.DomEvent.disableScrollPropagation(keyEl);
    function updateKey() {
      const RN = Object.fromEntries(GROUPS.map((g) => [g, [NUM[g], { pastoral: "Pastoral", autopia: "Autopia", centers: "Polycentric", transit: "Transit", coop: "Cooperative" }[g]]]));
      let h = `<button type="button" class="panel-t" aria-expanded="${!keyClosed}"><span class="panel-h">Now <b>Today’s Map</b></span><span class="chev" aria-hidden="true"></span></button>
        <div class="panel-b"><div class="k-base" role="group" aria-label="Base map">${[["map", "Map"], ["sat", "Satellite"]].map(([k, t]) => `<button type="button" data-base="${k}" class="${baseKind === k ? "on" : ""}" aria-pressed="${baseKind === k}">${t}</button>`).join("")}</div><div class="k-u">${GROUPS.map((g) => `<a href="#${g}" class="${focus === g ? "on" : focus === "all" ? "all" : ""}" style="--c:${COL[g]}" title="${RN[g][1]}"><i></i>${RN[g][0]}${focus === g ? ` ${RN[g][1]}` : ""}</a>`).join("")}</div>
        <h5>Year on the Map</h5><p class="k-year" id="k-year"></p><div id="k-yrrows"></div>`;
      const g = focus;
      if (g === "pastoral") {
        h += `<h5>${NUM.pastoral} · Pastoral Suburb</h5>` + lgRow("fill", COL.pastoral + "55", "Neighbourhoods named in the text");
        if (extras.includes("zoned")) h += lgRow("fill", "#3f8a2e", "Zoned for detached houses (2026)");
      } else if (g === "autopia") {
        h += `<h5>${NUM.autopia} · Autopia</h5>` + lgRow("line", LINE.autopia, "Freeways") + lgRow("dotf", COL.autopia, "Interchanges named in the text") + lgRow("fill", COL.autopia + "55", "Boyle Heights");
        if (extras.includes("aadt")) h += lgRow("disc", COL.autopia, "Traffic: vehicles a day (bigger = busier)");
        if (extras.includes("bott")) h += lgRow("line", "#6b4a00", "Worst traffic jams, 2024");
        if (extras.includes("bh500")) h += lgRow("fill", COL.autopia + "88", "Within 500 ft of a freeway");
      } else if (g === "centers") {
        h += `<h5>${NUM.centers} · The 56 Centres of 1974, Where the Plan Drew Them</h5>` + lgRow("dotf", COL.centers, `Got tall buildings and rail · ${S.centers.outcomes_half_mile.realised}`) +
          lgRow("dotf", "#86b6ef", `Tall buildings, no rail · ${S.centers.outcomes_half_mile.towers}`) + lgRow("ring", LINE.centers, `Rail, no tall buildings · ${S.centers.outcomes_half_mile.rail}`) +
          lgRow("ringd", "#8b877e", `Neither · ${S.centers.outcomes_half_mile.neither}`) +
          `<h5>Job Centres Today</h5>` + lgRow("fill", COL.centers + "33", `10+ jobs per acre, 10,000+ jobs · ${S.today.n}`);
        if (extras.includes("towers")) h += lgRow("sq", INK, "Tall buildings (150 ft and up)");
        if (extras.includes("rail")) h += lgRow("line", INK, "Metro rail");
      } else if (g === "transit") {
        h += `<h5>${NUM.transit} · The Transit Metropolis</h5>` + lgRow("line", LINE.transit, "Metro rail, as open in the year on the map") + lgRow("dash", LINE.transit, "Metro busway") + lgRow("ring", LINE.transit, "Rail station");
        if (extras.includes("oldnet") && oldnet.features.length) h += `<h5>The Network of About 1925</h5>` + lgRow("line", OLDC.PE, "Red Cars (Pacific Electric)") + lgRow("tdash", OLDC.LARy, "Yellow Cars (Los Angeles Railway)");
        if (extras.includes("lastrail") && oldnet.features.length) h += lgRow("line", INK, "The last lines: Red Car 1961, streetcars 1963");
      } else if (g === "coop") {
        h += `<h5>${NUM.coop} · Cooperative Experiments</h5>` + lgRow("pin", COL.coop, "Experiment sites (numbered)") + lgRow("fill", COL.coop + "55", "Site outlines");
      }
      if (extras.includes("holc")) h += `<h5>1939 Mortgage-Risk Grades</h5>` + ["A", "B", "C", "D"].map((k) => lgRow("fill", `rgba(17,17,17,${HOLC_OP[k] + 0.04})`,
        `${k} · “${{ A: "Best", B: "Still desirable", C: "Declining", D: "Hazardous" }[k]}”`)).join("");
      h += `<h5>Boundaries</h5>` + lgRow("line", INK, "City of Los Angeles") + lgRow("thin", "#8c8c8c", "Other cities");
      if (hasPhotos) h += `<h5>Photographs</h5>` + lgRow("pin", "#ffffff", "Photo taken here (click to open)");
      keyEl.innerHTML = h + "</div>";
      keyEl.classList.toggle("closed", keyClosed);
      window.__d8year(year);
    }
    window.__d8year = (Y) => {
      const ky = document.getElementById("k-year"), rows = document.getElementById("k-yrrows"); if (!ky) return;
      if (map.getZoom() >= 13) { ky.textContent = Y >= Y1 ? "Today (2026)" : String(Y); rows.innerHTML = `<div class="lg"><span>Zoom out to see what stood in ${Y >= Y1 ? "each year" : Y}</span></div>`; }
      else if (Y >= Y1) { ky.textContent = "Today (2026)"; rows.innerHTML = lgRow("fillb", "#ffffff", "No veil: the city as it stands today"); }
      else { ky.textContent = String(Y); rows.innerHTML = lgRow("veil", "", `Not yet built in ${Y} (faded)`) + lgRow("ink", INK, `Built ${Y - FRONT_YRS + 1} to ${Y}`); }
    };

    /* ======================= camera ======================= */
    // camera padding = the panels actually on screen, so a target never lands under the legend or the timeline
    const tEl2 = document.getElementById("st-time");
    const pad = () => {
      const o = oPanel.getBoundingClientRect(), t = tEl2.getBoundingClientRect();
      const k = keyEl.offsetParent && getComputedStyle(keyEl).display !== "none" ? keyEl.getBoundingClientRect() : null;
      if (mobile.matches) {
        const mb = map.getContainer().getBoundingClientRect().bottom;
        return { paddingTopLeft: [16, o.height + 14], paddingBottomRight: [16, Math.max(t.height + 26, k ? mb - k.top + 10 : 0)] };
      }
      return { paddingTopLeft: [28, o.height + 26], paddingBottomRight: [k ? k.width + 34 : 28, t.height + 44] };
    };
    function boundsFor(v) {
      if (v === "region" && mobile.matches) v = "basin";   // the Antelope Valley view is too small to read on a phone
      if (VIEWS[v]) return { b: L.latLngBounds(VIEWS[v]), z: 13 };
      if (v === "pastoral") return { b: L.latLngBounds(pastoralIds.map((id) => PL[id].bounds)), z: 13 };
      if (v === "plate") return { b: L.latLngBounds((ORIGS[curOrig] || ORIGS.parks1930).win), z: 13 };
      if (v === "sites") return { b: coopLayer.getBounds().pad(0.08), z: 13 };
      if (v.startsWith("topo:")) { const t = topoMeta[v.slice(5)]; return { b: L.latLngBounds(t.focus || t.bounds), z: 15 }; }
      const ids = v.split(",").filter((id) => PL[id]);
      if (!ids.length) return null;
      const b = L.latLngBounds(ids.map((id) => PL[id].bounds));
      return { b, z: Math.min(...ids.map((id) => PL[id].maxZoom || 14)) };
    }
    let lastView = "";
    function flyView(v, force = false) {
      if (!force && v === lastView) return; lastView = v;
      const t = boundsFor(v); if (!t) return;
      map.flyToBounds(t.b, { ...pad(), maxZoom: t.z, duration: 1.1 });
    }
    // after a place click or a manual pan/zoom, offer the way back to the paragraph's own view
    const back = L.DomUtil.create("button", "st-back", box);
    back.type = "button"; back.textContent = "Back to this paragraph’s map"; back.hidden = true;
    const showBack = () => { back.hidden = false; placeLabels(); };
    function goBack() {
      back.hidden = true; map.closePopup(); halo.clearLayers(); areaHL.clearLayers(); resetCentres();
      if (!active) return;
      const s = active._s; setFocus(s.ch); setOriginal(s.o, true); userOrig = false; setExtras(s.x);
      flyView(s.v, true); showLabels(s.v.split(",").map((v) => v.replace(/^topo:/, "")));
    }
    back.addEventListener("click", goBack);
    const home = L.DomUtil.create("a", "leaflet-control-zoom-home", map.zoomControl.getContainer());
    home.href = "#"; home.title = "Back"; home.setAttribute("role", "button"); home.setAttribute("aria-label", home.title); home.textContent = "Back";
    L.DomEvent.on(home, "click", (e) => { L.DomEvent.preventDefault(e); L.DomEvent.stopPropagation(e); goBack(); });
    map.on("dragstart", showBack);
    const mc = map.getContainer();
    mc.addEventListener("wheel", showBack, { passive: true });
    mc.addEventListener("dblclick", showBack);
    mc.addEventListener("touchstart", (e) => { if (e.touches.length > 1) showBack(); }, { passive: true });
    map.zoomControl.getContainer().querySelectorAll(".leaflet-control-zoom-in, .leaflet-control-zoom-out").forEach((a) => a.addEventListener("click", showBack));

    /* ======================= halo for clicked places ======================= */
    const halo = L.layerGroup().addTo(map);
    // chart rows name places that are not story places (plan areas, cities): outline one and fly there
    const areaHL = L.layerGroup().addTo(map);
    const cpIdx = Object.fromEntries(chartPlaces.features.map((f) => [f.properties.id, f]));
    function focusArea(id, name, ch) {
      const f = cpIdx[id]; if (!f) return;
      areaHL.clearLayers(); halo.clearLayers(); map.closePopup();
      const col = LINE[ch] || INK;
      L.geoJSON(f, { pane: "top", interactive: false, style: { color: "#fff", weight: 7, opacity: 0.9, fill: false } }).addTo(areaHL);
      const lyr = L.geoJSON(f, { pane: "top", interactive: false, style: { color: col, weight: 3, fillColor: COL[ch] || INK, fillOpacity: 0.12 } }).addTo(areaHL);
      const b = lyr.getBounds();
      lastView = "";
      map.flyToBounds(b, { ...pad(), maxZoom: 14, duration: 1.0 });
      showLabels([], [[b.getCenter(), name]]); showBack();
    }
    function flash(P) {
      halo.clearLayers();
      const col = COL[P.ch];
      if (P.layer && P.layer.toGeoJSON && !P.ll) {
        L.geoJSON(P.layer.toGeoJSON(), { pane: "top", interactive: false, style: { color: "#fff", weight: 7, opacity: 0.9, fill: false } }).addTo(halo);
        L.geoJSON(P.layer.toGeoJSON(), { pane: "top", interactive: false, style: { color: col, weight: 3.5, fill: false, className: "halo" } }).addTo(halo);
      } else {
        L.circleMarker(P.ll || P.bounds.getCenter(), { pane: "top", radius: 18, color: col, weight: 3, fill: false, className: "halo", interactive: false }).addTo(halo);
      }
      setTimeout(() => halo.clearLayers(), 3600);
    }
    function focusPlace(id) {
      const P = PL[id]; if (!P) return;
      setFocus(P.ch);
      const t = { b: P.bounds, z: P.maxZoom || 14 };
      if (P.topo) { setOriginal(P.topo, true); t.b = L.latLngBounds(topoMeta[id].focus || topoMeta[id].bounds); }
      lastView = "";
      map.flyToBounds(t.b, { ...pad(), maxZoom: t.z, duration: 1.0 });
      showLabels([id]); flash(P); showBack();
      map.once("moveend", () => {
        // points open their popup; areas keep their name label and outline in view (a popup would hide the label)
        if (P.ll && P.layer && P.layer.openPopup) P.layer.openPopup();
      });
    }
    document.querySelectorAll(".pl[data-place]").forEach((b) => b.addEventListener("click", () => {
      focusPlace(b.dataset.place); b.classList.add("pulse"); setTimeout(() => b.classList.remove("pulse"), 1200);
    }));

    function resetCentres() {
      centerLayer.eachLayer((l) => { const o = OUT[l.feature.properties.oc];
        l.setStyle({ color: o.stroke, weight: o.w, dashArray: o.dash || null, fillColor: o.fill, fillOpacity: o.op, opacity: 1 }); });
      document.querySelectorAll(".nb-row.on").forEach((r) => r.classList.remove("on"));
    }

    /* ======================= evidence cards ======================= */
    const C = S.centers, G = S.garden, B = SS.boyle, PW = SS.parkways1946;
    const tile = (big, txt) => `<div class="tile"><b>${big}</b><span>${txt}</span></div>`;
    const svgEl = (w, h, inner) => `<svg viewBox="0 0 ${w} ${h}" role="img">${inner}</svg>`;
    const cardW = () => { const e = document.querySelector(".evid"); return Math.round(Math.max(300, Math.min(560, (e ? e.clientWidth : 520) - 38))); };

    const KIND = { la: "City of Los Angeles", city: "City", unincorporated: "Unincorporated" };
    const placeName = (p) => (p.kind === "la" ? p.name.split(" - ").slice(0, 2).join(" – ")
      : p.name.toLowerCase().replace(/(^|[\s-])\w/g, (c) => c.toUpperCase()).replace(/ - /g, " – "));
    // two measures per place, each on its own scale: the chapter's measure (filled bar) and median household income (outlined bar)
    const money = (v) => (v == null ? "n/a" : v >= 200000 ? "$200k+" : "$" + Math.round(v / 1000) + "k");
    function twoBars({ rows, refs, head1, fmt1, max1, cap1, ch, gapAfter, head2 = "Median household income", fmt2 = money, max2 = 200000, head1s, head2s }) {
      const W = cardW(), narrow = W < 420, LW = narrow ? 136 : 178;
      if (narrow) { head1 = head1s || head1; head2 = head2s || head2; }
      const RH = 30, GAP = 14, imax = max2;
      const pw = (W - LW - GAP) * 0.5, X1 = LW, X2 = LW + pw + GAP, bw = pw - (narrow ? 34 : 40);
      const PX = (v) => X1 + Math.min(v, cap1 || max1) / max1 * bw, IX = (v) => X2 + Math.min(v, imax) / imax * bw;
      let s = `<text x="${X1}" y="9" style="font-size:9.5px;font-weight:600;fill:#111">${head1}</text>
        <text x="${X2}" y="9" style="font-size:9.5px;font-weight:600;fill:#111">${head2}</text>`;
      const T0 = 18;
      const row = ({ n, k, v, inc, hi, id }, y) => {
        y += T0;
        if (id) s += `<g class="row" data-area="${id}" data-name="${n}" data-ch="${ch}" tabindex="0" role="button" aria-label="Show ${n} on the map"><rect class="hit" x="0" y="${y}" width="${W}" height="${RH - 2}" fill="transparent"/>`;
        s += `<text class="lbl" x="0" y="${y + 11}" style="${hi ? "font-weight:700;" : ""}${narrow ? "font-size:10px" : ""}">${n}</text><text x="0" y="${y + 23}" style="font-size:9.5px;fill:#6b6b6b">${narrow ? k.replace(/^the whole \w+, /, "") : k}</text>
          <rect x="${X1}" y="${y + 3}" width="${Math.max(hi ? 4 : 1, PX(v) - X1)}" height="16" rx="3" fill="${hi ? COL[ch] : "#c9c3b6"}"/>`;
        if (cap1 && v > cap1) s += `<path d="M${PX(v) - 12} ${y + 1}l-5 20M${PX(v) - 7} ${y + 1}l-5 20" stroke="#fff" stroke-width="2.5"/>`;   // broken bar: off the scale
        s += `<text x="${PX(v) + 5}" y="${y + 15}" style="font-weight:600;fill:#111">${fmt1(v)}</text>
          <rect x="${X2}" y="${y + 3}" width="${Math.max(1, IX(inc || 0) - X2)}" height="16" rx="3" fill="#fff" stroke="#6f6b63" stroke-width="1.4"/>
          <text x="${IX(inc || 0) + 5}" y="${y + 15}" style="font-weight:600;fill:#111">${fmt2(inc)}</text>`;
        if (id) s += `</g>`;
      };
      rows.forEach((r, i) => row(r, i * RH + (gapAfter && i >= gapAfter ? 10 : 0)));
      if (gapAfter) s += `<text x="${X1}" y="${T0 + gapAfter * RH + 7}" style="font-size:9.5px;fill:#6b6b6b">${rows.between}</text>`;
      const y0 = rows.length * RH + (gapAfter ? 18 : 8);
      s += `<line x1="0" x2="${W}" y1="${T0 + y0 - 4}" y2="${T0 + y0 - 4}" stroke="#d6d6d6"/>`;
      refs.forEach((r, i) => row(r, y0 + i * RH));
      return svgEl(W, T0 + y0 + refs.length * RH, s);
    }
    const INCOME_NOTE = "Median household income: U.S. Census Bureau, American Community Survey 2020–2024 (5-year estimates); a city’s or community’s own published median where the Bureau publishes one, otherwise its census tracts pooled; the top bracket is $200,000 or more.";
    function parkBars() {
      const PK = SS.parks, all = PK.la.slice();
      const short = (n) => ({ "Arleta - Pacoima": "Arleta – Pacoima", "Bel Air - Beverly Crest": "Bel Air", "Brentwood - Pacific Palisades": "Brentwood" }[n] || n.split(" - ")[0]
        .replace("Southeast Los Angeles", "Southeast LA").replace("South Los Angeles", "South LA").replace("Northeast Los Angeles", "Northeast LA").replace("West Los Angeles", "West LA"));
      const poorest = new Set(all.slice().sort((a, b) => a.median_income - b.median_income).slice(0, 10).map((d) => d.name));
      const tone = (n) => (n === "Wilshire" ? COL.pastoral : poorest.has(n) ? "#3b3934" : "#c9c3b6");
      const byPark = all.slice().sort((a, b) => b.per_1000_homes - a.per_1000_homes), byInc = all.slice().sort((a, b) => b.median_income - a.median_income);
      const pick = (L) => L.slice(0, 10).concat([null], L.slice(-10));
      const W = cardW(), narrow = W < 420, G = narrow ? 18 : 30, Lw = (W - G) / 2, NW = narrow ? 70 : 92, RH = 17, T0 = 30, BH = 11;
      const BW = Lw - NW - 6 - (narrow ? 36 : 44), cap = 150;
      const PX = (v) => Math.max(2, Math.min(v, cap) / cap * BW), IX = (v) => Math.max(2, Math.min(v, 200000) / 200000 * BW);
      const f1 = (v) => (v < 10 ? v.toFixed(1) : Math.round(v).toLocaleString("en-US"));
      const rowY = (i) => T0 + i * RH + (i > 10 ? 4 : 0);
      let s = `<text x="0" y="10" style="font-size:9.5px;font-weight:600;fill:#111">Park acres per 1,000 homes</text>
        <text x="${Lw + G}" y="10" style="font-size:9.5px;font-weight:600;fill:#111">Median household income</text>
        <text x="0" y="22" style="font-size:9px;fill:#6b6b6b">most to least</text><text x="${Lw + G}" y="22" style="font-size:9px;fill:#6b6b6b">highest to lowest</text>`;
      const left = pick(byPark), right = pick(byInc), yL = {}, yR = {};
      left.forEach((d, i) => { if (d) yL[d.name] = rowY(i) + RH / 2; });
      right.forEach((d, i) => { if (d) yR[d.name] = rowY(i) + RH / 2; });
      // lines first, under the rows: a plan area on both sides
      Object.keys(yL).filter((n) => n in yR).sort((a, b) => (tone(a) === "#c9c3b6") - (tone(b) === "#c9c3b6")).reverse().forEach((n) => {
        const c = tone(n) === "#c9c3b6" ? "#b9b4a9" : tone(n);
        s += `<line x1="${Lw - 2}" y1="${yL[n]}" x2="${Lw + G + 2}" y2="${yR[n]}" stroke="${c}" stroke-width="${n === "Wilshire" ? 2.4 : c === "#b9b4a9" ? 1 : 1.8}"/>`;
      });
      const side = (L, x0, val, fmt, broken) => L.forEach((d, i) => {
        const y = rowY(i);
        if (!d) { s += `<text x="${x0 + NW + 6}" y="${y + 11}" style="font-size:9px;fill:#6b6b6b">… 14 plan areas between …</text>`; return; }
        const n = short(d.name), w = val(d), hi = d.name === "Wilshire" || poorest.has(d.name);
        s += `<g class="row" data-area="la:${d.name}" data-name="${n}" data-ch="pastoral" tabindex="0" role="button" aria-label="Show ${n} on the map"><rect class="hit" x="${x0}" y="${y}" width="${Lw}" height="${RH - 1}" fill="transparent"/>
          <text x="${x0 + NW}" y="${y + 12}" text-anchor="end" style="font-size:9.5px;fill:#111;font-weight:${hi ? 600 : 400}">${n}</text>
          <rect x="${x0 + NW + 6}" y="${y + 3}" width="${w}" height="${BH}" fill="${tone(d.name)}"/>`;
        if (broken && broken(d)) s += `<path d="M${x0 + NW + 6 + w - 12} ${y + 1}l-4 15M${x0 + NW + 6 + w - 8} ${y + 1}l-4 15" stroke="#fff" stroke-width="2"/>`;
        s += `<text x="${x0 + NW + 6 + w + 4}" y="${y + 12}" style="font-size:9.5px;font-weight:600;fill:#111">${fmt(d)}</text></g>`;
      });
      side(left, 0, (d) => PX(d.per_1000_homes), (d) => f1(d.per_1000_homes), (d) => d.per_1000_homes > cap);
      side(right, Lw + G, (d) => IX(d.median_income), (d) => money(d.median_income));
      const y0 = rowY(21) + 10;
      s += `<line x1="0" x2="${W}" y1="${y0 - 5}" y2="${y0 - 5}" stroke="#d6d6d6"/>`;
      [["City of Los Angeles", PK.city], ["Los Angeles County", PK.county]].forEach(([n, d], k) => {
        const y = y0 + k * RH, nm = narrow ? n.replace("City of Los Angeles", "City of LA").replace("Los Angeles County", "LA County") : n;
        s += `<text x="${NW}" y="${y + 12}" text-anchor="end" style="font-size:9.5px;font-weight:600;fill:#111">${nm}</text>
          <rect x="${NW + 6}" y="${y + 3}" width="${PX(d.per_1000_homes)}" height="${BH}" fill="#fff" stroke="#6f6b63" stroke-width="1.2"/>
          <text x="${NW + 6 + PX(d.per_1000_homes) + 4}" y="${y + 12}" style="font-size:9.5px;font-weight:600;fill:#111">${f1(d.per_1000_homes)}</text>
          <text x="${Lw + G + NW}" y="${y + 12}" text-anchor="end" style="font-size:9.5px;font-weight:600;fill:#111">${nm}</text>
          <rect x="${Lw + G + NW + 6}" y="${y + 3}" width="${IX(d.median_income)}" height="${BH}" fill="#fff" stroke="#6f6b63" stroke-width="1.2"/>
          <text x="${Lw + G + NW + 6 + IX(d.median_income) + 4}" y="${y + 12}" style="font-size:9.5px;font-weight:600;fill:#111">${money(d.median_income)}</text>`;
      });
      const key = `<div class="rank-key"><span><i style="background:#3b3934"></i>the ten lowest-income plan areas</span><span><i style="background:${COL.pastoral}"></i>Wilshire, with Hancock Park and Windsor Square</span><span><i style="background:#c9c3b6"></i>the others</span><span><i style="background:#fff;border:1.2px solid #6f6b63"></i>City and County, for comparison</span></div>`;
      return svgEl(W, y0 + 2 * RH + 2, s) + key +
        `<p class="mini-note">Click a plan area to see it on the map. The City of Los Angeles’s ${all.length} community plan areas with at least 5,000 homes: the ten with the most and the ten with the least of each, bars to scale (park bars beyond ${cap} acres are cut); a line joins a plan area that appears on both sides. Public park: open-access land in the California Protected Areas Database (GreenInfo Network, current release), federal forest excluded; homes on the 2026 Assessor roll. ${INCOME_NOTE}</p>`;
    }
    function proxBars() {
      const rows = B.places.slice(0, 10).map((p) => ({ n: placeName(p), k: KIND[p.kind], v: p.within_500ft_pct, inc: p.transit_pct,
        hi: p.name === "Boyle Heights", id: (p.kind === "la" ? "la:" : "cc:") + p.name }));
      const refs = [{ n: "City of Los Angeles", k: "the whole city, for comparison", v: B.city.within_500ft_pct, inc: B.city.transit_pct },
                    { n: "Los Angeles County", k: "the whole county, for comparison", v: B.county.within_500ft_pct, inc: B.county.transit_pct }];
      const tmax = Math.ceil(Math.max(...rows.map((r) => r.inc || 0), B.city.transit_pct) / 5) * 5;
      return twoBars({ rows, refs, head1: "Homes within 500 ft of a freeway", fmt1: (v) => Math.round(v) + "%", max1: Math.ceil(rows[0].v / 5) * 5, ch: "autopia",
                       head2: "Commute by transit", head1s: "Within 500 ft", head2s: "By transit", fmt2: (v) => (v == null ? "n/a" : v.toFixed(1) + "%"), max2: tmax }) +
        `<p class="mini-note">Click a place to see it on the map. Ranked among the ${B.places.length} places with at least 5,000 homes: the City of Los Angeles’s ${B.places.filter((p) => p.kind === "la").length} community plan areas, the County’s other cities and its unincorporated communities. Homes on the 2026 Assessor roll; freeways from Caltrans. Commuting by transit: workers 16 and over who get to work by public transportation (taxis excluded), U.S. Census Bureau, American Community Survey 2020–2024; a city’s or community’s own published figure where the Bureau publishes one, otherwise its census tracts pooled.</p>`;
    }
    // does living by a freeway go with less transit? block groups compared within income fifths
    function fwyTransit() {
      const F = SS.fwy_transit, Q = F.by_income_quintile, W = cardW(), narrow = W < 420, LW = narrow ? 96 : 120, RH = 36, T0 = 18, BH = 12;
      const max = Math.ceil(Math.max(...Q.flatMap((q) => [q.near_pct, q.none_pct])) / 2) * 2, bw = W - LW - 44, X = (v) => LW + v / max * bw;
      const kk = (v) => "$" + Math.round(v / 1000) + "k";
      const band = (i) => (i === 0 ? `under ${kk(Q[1].inc_lo)}` : i === 4 ? `${kk(Q[4].inc_lo)} and up` : `${kk(Q[i].inc_lo)} to ${kk(Q[i + 1].inc_lo)}`);
      let s = `<text x="${LW}" y="9" style="font-size:9.5px;font-weight:600;fill:#111">Workers commuting by transit</text>`;
      Q.forEach((q, i) => {
        const y = T0 + i * RH;
        s += `<text class="lbl" x="0" y="${y + 12}">${["Lowest", "Second", "Middle", "Fourth", "Highest"][i]} fifth</text>
          <text x="0" y="${y + 25}" style="font-size:9.5px;fill:#6b6b6b">${band(i)}</text>
          <g><title>${band(i)}: ${q.near_pct}% in ${q.near_n} block groups by a freeway</title><rect x="${LW}" y="${y + 2}" width="${Math.max(2, X(q.near_pct) - LW)}" height="${BH}" fill="${COL.autopia}"/>
          <text x="${X(q.near_pct) + 4}" y="${y + 12}" style="font-weight:600;fill:#111">${q.near_pct.toFixed(1)}%</text></g>
          <g><title>${band(i)}: ${q.none_pct}% in ${q.none_n} block groups with no home within 500 ft</title><rect x="${LW}" y="${y + 16}" width="${Math.max(2, X(q.none_pct) - LW)}" height="${BH}" fill="#c9c3b6"/>
          <text x="${X(q.none_pct) + 4}" y="${y + 26}" style="font-weight:600;fill:#111">${q.none_pct.toFixed(1)}%</text></g>`;
      });
      const c = F.ols_controlled_per10pts, d = F.ols_controlled_drive_alone_per10pts, sgn = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(2);
      return svgEl(W, T0 + 5 * RH, s) + key([[`background:${COL.autopia}`, "by a freeway: a quarter or more of homes within 500 ft"], ["background:#c9c3b6", "no home within 500 ft"]]) +
        `<p class="mini-note">Within each fifth of household income, block groups by a freeway and block groups away from one send almost the same share of workers to work by transit; across the fifths, the share falls more than fivefold as income rises. Across all ${fmt(F.n_block_groups)} block groups in the County, with income, housing density, rail and bus service and distance to Downtown held equal, ten more points of homes within 500 ft of a freeway change the transit share by ${sgn(c.b)} points (95% range ${sgn(c.lo)} to ${sgn(c.hi)}): no measurable effect. Living by a freeway goes with slightly more driving alone (${sgn(d.b)} points per ten), not with less transit. Census block groups with 200 or more workers (ACS 2020–2024, B08301 and B19013); homes and the 500 ft band as above; Metro rail stations and bus stops (GTFS 2026); errors clustered by tract.</p>`;
    }
    function outcomeBar() {
      const o = C.outcomes_half_mile, keys = ["realised", "towers", "rail", "neither"], W = cardW(), h = 22;
      const LBL = { realised: "Tall buildings and rail", towers: "Tall buildings only", rail: "Rail only", neither: "Neither" };
      let x = 0, s = "";
      const NT = C.neither_types, nbKeys = ["transit", "jobs", "urban", "suburban"];   // the rail-in-waiting group sits beside "Rail only"
      keys.forEach((k) => {
        const w = o[k] / C.n * W, st = OUT[k];
        if (k === "neither") {   // split into what those centres became instead
          let xx = x;
          nbKeys.forEach((t) => {
            const ww = NT[t].n / C.n * W;
            s += NB[t].stroke
              ? `<rect x="${xx + 2}" y="1" width="${Math.max(0, ww - 4)}" height="${h - 2}" fill="${NB[t].fill}" stroke="${NB[t].stroke}" stroke-width="2" stroke-dasharray="${NB[t].dash}"/>`
              : `<rect x="${xx + 1}" y="0" width="${Math.max(0, ww - 2)}" height="${h}" fill="${NB[t].fill}"/>`;
            s += `
              <text x="${xx + ww / 2}" y="${h + 14}" text-anchor="middle" class="lbl">${NT[t].n}</text>`;
            xx += ww;
          });
          s += `<rect x="${x + 0.5}" y="0.5" width="${w - 1}" height="${h - 1}" fill="none" stroke="${st.stroke}" stroke-width="1.2" stroke-dasharray="3 3"/>
            <path d="M${x + 2} ${h + 20}v5h${w - 4}v-5" fill="none" stroke="#8b877e"/><text x="${x + w / 2}" y="${h + 38}" text-anchor="middle" class="lbl">Neither · ${o[k]}</text>`;
          x += w; return;
        }
        s += `<rect x="${x + 1}" y="0" width="${Math.max(0, w - 2)}" height="${h}" fill="${st.fill}" fill-opacity="${Math.max(st.op, 0.85)}" stroke="${st.stroke}" stroke-width="${k === "rail" ? 2.4 : 1}" ${st.dash ? `stroke-dasharray="${st.dash}"` : ""}/>
          <text x="${x + w / 2}" y="${h + 14}" text-anchor="middle" class="lbl">${o[k]}</text>`;
        x += w;
      });
      // one legend format for all seven groups: the bar's own swatch, label · count, the rule, the centres' names
      const sw = (fill, stroke, w, dash) => `<svg viewBox="0 0 22 12" aria-hidden="true"><rect x="1" y="1" width="20" height="10" fill="${fill}" stroke="${stroke}" stroke-width="${w}"${dash ? ` stroke-dasharray="${dash}"` : ""}/></svg>`;
      const namesOf = (oc) => centers.features.filter((f) => f.properties.oc === oc).map((f) => ALIAS[f.properties.name] || f.properties.name).sort();
      const RULE = { realised: "a building of 150 ft or more and a rail station within half a mile", towers: "buildings of 150 ft or more, no rail station", rail: "a rail station, no building of 150 ft or more" };
      const SWB = { realised: sw(COL.centers, LINE.centers, 1), towers: sw("#86b6ef", LINE.centers, 1), rail: sw("#fff", LINE.centers, 2.4) };
      const item = (swh, label, n, rule, names) => `<div class="lg">${swh}<span><b>${label} · ${n}</b> <span class="nb-rule">(${rule})</span><br>${names.join(", ")}</span></div>`;
      return svgEl(W, h + 42, s) + `<div class="nb-key">${keys.slice(0, 3).map((k) => item(SWB[k], LBL[k], o[k], RULE[k], namesOf(k))).join("")}</div>
        <p class="nb-h">Neither · ${o.neither}: What They Became Instead</p>
        <div class="nb-key">${nbKeys.map((t) => item(sw(NB[t].fill, NB[t].stroke || "#8b877e", NB[t].stroke ? 2 : 1, "3 2"), NB[t].label, NT[t].n, NB[t].rule, NT[t].names)).join("")}</div>
        <p class="nb-h">Today: ${S.today.n} Job Centres</p>
        <p class="mini-note">Areas with at least 10 jobs per acre and 10,000 jobs in all (the definition of Giuliano and Small’s study of Los Angeles, 1991), from the Census Bureau’s 2023 workplace counts, hold ${fmt(Math.round(S.today.jobs / 1e5) * 1e5)} of the County’s ${fmt(Math.round(S.today.county_jobs / 1e5) * 1e5)} jobs. ${S.today.planned_matched} of the 56 planned centres lie in or beside one; one continuous core now runs from Downtown to Santa Monica and takes in ${todayC.features[0].properties.planned.length} of them. ${S.today.n - S.today.with_planned} job centres grew where the plan drew none, among them ${[...new Set(S.today.unplanned)].slice(0, 8).join(", ")}.</p>
        <p class="mini-note">The plan gave each centre “a ‘core’ of about one-quarter mile radius containing a rapid transit station, high-rise office structures, department stores, hotels, theaters, restaurants and government offices”, with apartments nearby. The bar tests the two most visible of those, buildings of 150 ft and up and a rail station, within half a mile of each centre as the plan drew it (the diagram, placed without distortion); jobs and homes are counted within the same half mile.</p>`;
    }
    const SPANS = [
      ["landers", 1913, 1917, "gone"], ["llano", 1914, 1918, "gone"], ["village", 1941, 1942, "survives"],
      ["crestwood", 1946, 1955, "survives"], ["elysian", 1950, 1953, "stadium"],
    ];
    function gantt() {
      const W = cardW(), LW = W < 420 ? 140 : 170, RH = 24, ya = 1910, yb = 2026, X = (y) => LW + (y - ya) / (yb - ya) * (W - LW - 6);
      let s = "";
      (W < 420 ? [1910, 1950, 1990] : [1910, 1930, 1950, 1970, 1990, 2010]).forEach((y) => { s += `<line class="ax" x1="${X(y)}" x2="${X(y)}" y1="0" y2="${SPANS.length * RH}"/><text x="${X(y)}" y="${SPANS.length * RH + 14}" text-anchor="middle">${y}</text>`; });
      SPANS.forEach(([id, a, b, fate], i) => {
        const y = i * RH + 5, P = PL[id];
        const short = { landers: "Little Landers", llano: "Llano del Rio", village: "Baldwin Hills Village", crestwood: "Crestwood Hills", elysian: "Chávez Ravine" }[id];
        s += `<g class="row" data-place="${id}"><rect class="hit" x="0" y="${i * RH}" width="${W}" height="${RH}" fill="transparent"/>
          <text class="lbl" x="0" y="${y + 11}">${short}</text>`;
        if (fate === "stadium") {
          s += `<rect x="${X(a)}" y="${y}" width="${X(b) - X(a)}" height="14" rx="3" fill="#fff" stroke="${COL.coop}" stroke-width="1.6" stroke-dasharray="3 2"/>
            <rect x="${X(1962)}" y="${y + 3}" width="${X(yb) - X(1962)}" height="8" rx="2" fill="#b9b3a6"/>`;
        } else {
          s += `<rect x="${X(a)}" y="${y}" width="${Math.max(4, X(b) - X(a))}" height="14" rx="3" fill="${COL.coop}"/>`;
          if (fate === "survives") s += `<rect x="${X(b)}" y="${y + 4}" width="${X(yb) - X(b)}" height="6" rx="2" fill="${COL.coop}" fill-opacity=".3"/>`;
        }
        s += `</g>`;
      });
      return svgEl(W, SPANS.length * RH + 22, s);
    }
    // I · the votes that paid for the network, and the miles they bought
    const T = SS.transit;
    const BDESC = { "1968 Measure A": "Bonds for 62 miles of rapid transit", "1974 Proposition A": "One-cent sales tax", "1976 Measure R": "Half-cent sales tax to build 232 miles of rail",
      "1976 Measure T": "Half-cent sales tax to run the system", "1980 Proposition A": "Half-cent sales tax, no end date", "1990 Proposition C": "A second half-cent, no end date",
      "2008 Measure R": "Half-cent sales tax for 30 years", "2012 Measure J": "Extending Measure R’s tax by 30 years", "2016 Measure M": "A further half-cent; Measure R’s tax made permanent" };
    const key = (items) => `<div class="rank-key">${items.map(([st, t]) => `<span><i style="${st}"></i>${t}</span>`).join("")}</div>`;
    function ballotBars() {
      const W = cardW(), narrow = W < 420, LW = narrow ? 122 : 132, RH = 34, T0 = 16, max = 80, n = T.ballots.length;
      const bw = W - LW - (narrow ? 84 : 96), X = (v) => LW + v / max * bw;
      let s = `<text x="${LW}" y="9" style="font-size:9.5px;font-weight:600;fill:#111">Share voting yes</text>`;
      [0, 25, 50, 75].forEach((v) => { s += `<line x1="${X(v)}" x2="${X(v)}" y1="${T0}" y2="${T0 + n * RH - 8}" stroke="#ececec"/>
        <text x="${X(v)}" y="${T0 + n * RH + 9}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">${v}%</text>`; });
      T.ballots.forEach((b, i) => {
        const y = T0 + i * RH, d = BDESC[`${b.year} ${b.measure}`] || "", end = X(Math.max(b.pct_yes, b.pct_needed));
        s += `<g><title>${b.year} ${b.measure}: ${b.pct_yes.toFixed(1)}% yes, ${b.pct_needed}% needed, ${b.passed ? "passed" : "failed"}</title>
          <text class="lbl" x="0" y="${y + 12}">${b.year} · ${b.measure.replace("Proposition", "Prop.")}</text>
          <rect x="${LW}" y="${y + 2}" width="${X(b.pct_yes) - LW}" height="14" fill="${b.passed ? COL.transit : "#fff"}" stroke="${LINE.transit}" stroke-width="${b.passed ? 0 : 1.4}"/>
          <line x1="${X(b.pct_needed)}" x2="${X(b.pct_needed)}" y1="${y - 1}" y2="${y + 19}" stroke="${INK}" stroke-width="1.8"/>
          <text x="${end + 5}" y="${y + 13}" style="font-weight:600;fill:#111">${b.pct_yes.toFixed(1)}%<tspan style="font-weight:400;fill:#6b6b6b"> ${b.passed ? "passed" : "failed"}</tspan></text>
          <text x="0" y="${y + 26}" style="font-size:9.5px;fill:#6b6b6b">${d}</text></g>`;
      });
      return svgEl(W, T0 + n * RH + 13, s) + key([[`background:${COL.transit}`, "passed"], [`background:#fff;border:1.4px solid ${LINE.transit}`, "failed"],
        [`width:2px;height:12px;background:${INK}`, "share required: a majority until 1990, two-thirds since"]]);
    }
    function milesChart() {
      const W = cardW(), narrow = W < 420, H = 160, L0 = 38, R0 = narrow ? 46 : 78, T0 = 22, B0 = 20, ya = 1980, yb = 2027, vmax = 140, MB = T.miles_by_year;
      const X = (y) => L0 + (y - ya) / (yb - ya) * (W - L0 - R0), Y = (v) => T0 + (1 - v / vmax) * (H - T0 - B0);
      const at = (y, k) => MB.reduce((v, r) => (r[0] <= y ? r[k] : v), 0);
      const path = (k) => { let d = `M${X(ya)} ${Y(0)}`, prev = 0; for (let y = ya; y < yb; y++) { const v = at(y, k); if (v !== prev) { d += `H${X(y)}V${Y(v)}`; prev = v; } } return d + `H${X(yb)}`; };
      let s = "";
      [50, 100].forEach((v) => { s += `<line x1="${L0}" x2="${X(yb)}" y1="${Y(v)}" y2="${Y(v)}" stroke="#ececec"/><text x="${L0 - 4}" y="${Y(v) + 3}" text-anchor="end" style="font-size:9px;fill:#6b6b6b">${v}${v === 100 ? " mi" : ""}</text>`; });
      [[1980, "Prop. A", "A"], [1990, "Prop. C", "C"], [2008, "Measure R", "R"], [2016, "Measure M", "M"]].forEach(([y, t, sh]) => {
        s += `<line x1="${X(y)}" x2="${X(y)}" y1="${T0 - 6}" y2="${Y(0)}" stroke="#a9a49a" stroke-dasharray="2 2"/>
          <text x="${X(y) + 3}" y="${T0 - 9}" style="font-size:9px;fill:#6b6b6b">${narrow ? sh : t}</text>`; });
      s += `<path d="${path(1)}V${Y(0)}Z" fill="${COL.transit}" fill-opacity="0.14"/>
        <path d="${path(1)}" fill="none" stroke="${LINE.transit}" stroke-width="2"/>
        <path d="${path(2)}" fill="none" stroke="${LINE.transit}" stroke-width="2" stroke-dasharray="5 3"/>
        <line x1="${L0}" x2="${X(yb)}" y1="${Y(0)}" y2="${Y(0)}" stroke="${INK}"/>`;
      [1980, 1990, 2000, 2010, 2020].forEach((y) => { s += `<text x="${X(y)}" y="${H - 6}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">${y}</text>`; });
      const r1 = at(2026, 1), r2 = at(2026, 2);
      s += `<text x="${X(yb) + 5}" y="${Y(r1) + 4}" style="font-weight:600;fill:#111">${Math.round(r1)} mi${narrow ? "" : " rail"}</text>
        <text x="${X(yb) + 5}" y="${Y(r2) + 4}" style="font-weight:600;fill:#111">${Math.round(r2)} mi${narrow ? "" : " busway"}</text>`;
      for (let y = ya; y < yb; y++) s += `<rect x="${X(y)}" y="${T0}" width="${X(y + 1) - X(y)}" height="${Y(0) - T0}" fill="transparent"><title>${y}: ${at(y, 1)} miles of rail, ${at(y, 2)} of busway</title></rect>`;
      return svgEl(W, H, s) + key([[`height:0;border-top:2px solid ${LINE.transit}`, "rail"], [`height:0;border-top:2px dashed ${LINE.transit}`, "busway"],
        ["height:12px;width:0;border-left:1px dashed #a9a49a", "a transit tax passes"]]) +
        `<p class="mini-note">Route miles of today’s network by the year each section opened, shared track counted once (LA Metro rail and bus GTFS, November 2026); lines since closed are not counted. The marked votes are those that passed (see the chart of all nine in the text).</p>`;
    }
    const CARDS = {
      pastoral: () => `<p class="orig-link">Original map: <a href="${ORIGS.parks1930.href}" target="_blank" rel="noopener">1930 · Olmsted Brothers and Bartholomew, <i>Parks, Playgrounds and Beaches for the Los Angeles Region</i></a></p>
        <div class="tiles">
          ${tile(`${Math.round(G.sf_share_of_residential_zoned_land)}%`, "of the City’s residential land is zoned for detached houses")}
          ${tile(`${Math.round(G.sfr_share_of_all_units)}%`, "of its homes are detached houses")}
        </div>
        <div class="mini"><h4>Public Park and Household Income, Ranked</h4>${parkBars()}</div>`,
      autopia: () => `<p class="orig-link">Original map: <a href="${ORIGS.parkways1946.href}" target="_blank" rel="noopener">1946 · County Regional Planning Commission, <i>Interregional, Regional and Metropolitan Parkways</i></a></p>
        <div class="tiles">
          ${tile(fmt(S.aadt.max.v), "vehicles a day on the Santa Monica Freeway")}
          ${tile(`${Math.round(B.bh.within_500ft_pct)}%`, `of Boyle Heights homes stand within 500 ft of a freeway, the highest share of ${B.places.length} places in the County`)}
        </div>
        <div class="mini"><h4>The Ten Places with the Most Homes within 500 ft of a Freeway</h4>${proxBars()}</div>
        <div class="mini"><h4>Transit Use Follows Income, Not the Freeway</h4>${fwyTransit()}</div>`,
      centers: () => `<p class="orig-link">Original map: <a href="${ORIGS.plan1974.href}" target="_blank" rel="noopener">1974 · City of Los Angeles, <i>Concept Los Angeles</i>, adopted centers map</a></p>
        <div class="tiles">
          ${tile(`${C.outcomes_half_mile.realised} of ${C.n}`, "planned centres got both tall buildings and a rail station")}
          ${tile(`${Math.round(C.city_towers_in_half / C.city_towers * 100)}%`, "of the City’s tall buildings stand in the planned centres")}
        </div>
        <div class="mini"><h4>What the 56 Planned Centres Became</h4>${outcomeBar()}</div>`,
      transit: () => `<p class="orig-link">Original map: <a href="${ORIGS.transit1925.href}" target="_blank" rel="noopener">1925 · Kelker, De Leuw &amp; Co., <i>Comprehensive Rapid Transit Plan for the City and County of Los Angeles</i>, Plate 1</a></p>
        <div class="tiles">
          ${tile(Math.round(T.rail_miles_2026), `miles of Metro rail in 2026, with ${T.stations_open} stations, and ${Math.round(T.busway_miles_2026)} miles of busway`)}
          ${tile(`${T.ballots.find((b) => b.measure === "Measure M").pct_yes}%`, "voted for Measure M in 2016, where a transit tax needs two-thirds")}
        </div>
        <div class="mini"><h4>Metro Route Miles Open, 1980 to 2026</h4>${milesChart()}</div>`,
      coop: () => `<p class="orig-link">Original maps: U.S. Geological Survey sheets, ${Object.entries(topoMeta).map(([id, t]) => `<a href="${ORIGS["topo:" + id].href}" target="_blank" rel="noopener">${topoName(t.file)} ${t.year}</a>`).join(", ")}</p>
        <div class="mini"><h4>The Experiments</h4>${gantt()}
          <p class="glegend"><span class="g1"></span>Community <span class="g2"></span>Buildings still standing <span class="g3"></span>Never built</p></div>`,
    };
    // who ran what, when: each rail or busway system, private company years light, public agency years full ink
    function systemsChart() {
      const ROWS = [
        ["Horsecars", [[1874, 1897, "p"]]],
        ["Cable cars", [[1885, 1902, "p"]]],
        ["Yellow Cars (streetcars)", [[1895, 1945, "p", "LA Railway"], [1945, 1958, "p", "LATL"], [1958, 1963, "g", ""]]],
        ["Red Cars (interurbans)", [[1901, 1953, "p", "Pacific Electric"], [1953, 1958, "p", "MCL"], [1958, 1961, "g", ""]]],
        ["Hollywood Subway", [[1925, 1955, "p"]]],
        ["Busways", [[1973, 2026, "g", "El Monte 1973; Orange Line 2005"]]],
        ["Metro Rail", [[1990, 2026, "g", "Blue Line 1990"]]],
        ["Metrolink", [[1992, 2026, "g"]]],
      ];
      const W = cardW(), narrow = W < 420, LW = narrow ? 104 : 150, RH = 24, T0 = 6, ya = 1870, yb = 2026, X = (y) => LW + (y - ya) / (yb - ya) * (W - LW - 4);
      const mx = (X(1963) + X(1990)) / 2;   // 31 March 1963 to 14 July 1990: no streetcar, interurban or metro line ran
      let s = `<rect x="${X(1963)}" y="${T0}" width="${X(1990) - X(1963)}" height="${ROWS.length * RH}" fill="#f3f2ee"/>
        <text x="${mx}" y="${T0 + 14}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">27 years</text>
        <text x="${mx}" y="${T0 + 25}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">with no</text>
        <text x="${mx}" y="${T0 + 36}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">streetcar</text>
        <text x="${mx}" y="${T0 + 47}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">or metro</text>`;
      (narrow ? [1880, 1920, 1960, 2000] : [1880, 1900, 1920, 1940, 1960, 1980, 2000, 2020]).forEach((y) => { s += `<line class="ax" x1="${X(y)}" x2="${X(y)}" y1="${T0}" y2="${T0 + ROWS.length * RH}"/><text x="${X(y)}" y="${T0 + ROWS.length * RH + 12}" text-anchor="middle" style="font-size:9px;fill:#6b6b6b">${y}</text>`; });
      ROWS.forEach(([name, segs], i) => {
        const y = T0 + i * RH + 4;
        s += `<text class="lbl" x="0" y="${y + 11}" style="font-size:${narrow ? 10 : 11}px">${name}</text>`;
        segs.forEach(([a, b, k, t]) => {
          const w = Math.max(3, X(b) - X(a));
          s += `<g><title>${name}: ${a} to ${b === 2026 ? "today" : b}${t ? ` (${t})` : ""}, ${k === "g" ? "public agency" : "private company"}</title>
            <rect x="${X(a) + 0.5}" y="${y}" width="${w - 1}" height="15" fill="${k === "g" ? COL.transit : "#e7c9c4"}" stroke="${LINE.transit}" stroke-width="${k === "g" ? 0 : 1}"/></g>`;
          if (t && w > t.length * 5.6 + 8) s += `<text x="${X(a) + 5}" y="${y + 11}" style="font-size:9.5px;fill:${k === "g" ? "#fff" : "#111"};stroke:none">${t}</text>`;
        });
      });
      return `<h4>Who Ran Los Angeles’s Rail Transit, 1874 to 2026</h4>` + svgEl(W, T0 + ROWS.length * RH + 16, s) +
        key([["background:#e7c9c4;border:1px solid " + LINE.transit, "private company"], [`background:${COL.transit}`, "public agency"]]) +
        `<p class="mini-note">LATL: Los Angeles Transit Lines (National City Lines), 1945 to 1958. MCL: Metropolitan Coach Lines, which took over the Pacific Electric’s passenger services in 1953. From 1958 the public Los Angeles Metropolitan Transit Authority ran both until their last lines closed; Metro rail and busways are run today by the Los Angeles County Metropolitan Transportation Authority (1993), Metrolink by the Southern California Regional Rail Authority. Sources: LA Metro Research Library (“This Date in Los Angeles Transportation History” and its record of rail openings); Kelker, De Leuw &amp; Co. (1925).</p>`;
    }
    // charts set in the essay itself, beside the paragraph they illustrate
    const INLINE = {
      systems: systemsChart,
      ballots: () => `<h4>Nine Countywide Votes on Transit, 1968 to 2016</h4>${ballotBars()}
        <p class="mini-note">LA Metro Research Library, Los Angeles County Mass Transit Ballot Initiative Vote History (2017), with the share each measure required: the 1980 and 1990 taxes were held exempt from Proposition 13, while those of the merged agency since 1993 need two-thirds.</p>`,
    };
    document.querySelectorAll("[data-inline]").forEach((el) => { el.innerHTML = INLINE[el.dataset.inline](); });
    document.querySelectorAll(".evid[data-card]").forEach((el) => {
      el.innerHTML = CARDS[el.dataset.card]();
      el.querySelectorAll("[data-orig]").forEach((b) => b.addEventListener("click", () => setOriginal(b.dataset.orig, true)));
      el.querySelectorAll(".row[data-place]").forEach((r) => r.addEventListener("click", () => focusPlace(r.dataset.place)));
      el.querySelectorAll(".row[data-area]").forEach((r) => {
        const go = () => focusArea(r.dataset.area, r.dataset.name, r.dataset.ch);
        r.addEventListener("click", go);
        r.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
      });
    });

    /* chronology interlude */
    const msList = document.getElementById("milestones");
    msList.innerHTML = MILESTONES.map(([y, ch, t, u]) => `<li data-year="${y}"><b>${y}</b><span><a class="ms-link" href="${u}" target="_blank" rel="noopener" title="Read more">${t}</a></span><i title="${UNAME[ch]}">${NUM[ch]}</i></li>`).join("");
    msList.querySelectorAll("li").forEach((li) => li.addEventListener("click", () => tweenYear(+li.dataset.year, 900)));
    msList.querySelectorAll(".ms-link").forEach((a_) => a_.addEventListener("click", (e) => e.stopPropagation()));

    /* ======================= your photographs (photos/photos.json) ======================= */
    const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    fetch(D0 + "photos/photos.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : [])).then((list) => {
      if (!Array.isArray(list)) return;
      list = list.filter((ph) => ph && ph.file);
      if (!list.length) return;
      const fig = (ph) => `<figure class="photo"><img src="photos/${encodeURI(ph.file)}" alt="${esc(ph.caption || ph.place || "Photograph")}" loading="lazy">
        <figcaption>${ph.place ? `<b>${esc(ph.place)}</b>` : ""}${ph.place && ph.caption ? " · " : ""}${esc(ph.caption || "")}</figcaption></figure>`;
      const groups = {};
      list.forEach((ph) => { const ch = ph.chapter && document.getElementById(ph.chapter) && ph.chapter !== "references" ? ph.chapter : "photos"; (groups[ch] = groups[ch] || []).push(ph); });
      Object.entries(groups).forEach(([ch, phs]) => {
        if (ch === "photos") { document.getElementById("photos").hidden = false; document.getElementById("photos-grid").innerHTML = phs.map(fig).join(""); }
        else { const g = document.createElement("div"); g.className = "photos-grid"; g.innerHTML = phs.map(fig).join(""); document.getElementById(ch).appendChild(g); }
      });
      const pp = map.createPane("photos"); pp.style.zIndex = 452;
      list.filter((ph) => isFinite(ph.lat) && isFinite(ph.lng)).forEach((ph) => {
        L.marker([ph.lat, ph.lng], { pane: "photos", icon: L.divIcon({ className: "", html: '<span class="photo-pin"></span>', iconSize: [14, 14], iconAnchor: [7, 7] }) })
          .bindPopup(`<div class="st-pop"><p class="meta">Photograph</p>${ph.place ? `<h4>${esc(ph.place)}</h4>` : ""}<img src="photos/${encodeURI(ph.file)}" alt="" style="width:240px;display:block;border:1.5px solid #111">
            ${ph.caption ? `<p>${esc(ph.caption)}</p>` : ""}</div>`, { maxWidth: 270 }).addTo(map);
      });
      hasPhotos = list.some((ph) => isFinite(ph.lat) && isFinite(ph.lng)); updateKey();
    }).catch(() => {});

    /* ======================= scroll steps ======================= */
    const steps = [...document.querySelectorAll("[data-s]")];
    const lastO = {};
    steps.forEach((el) => {
      const sec = el.closest(".ch"), s = {};
      el.dataset.s.split(";").forEach((kv) => { const [k, v] = kv.split("="); s[k.trim()] = v.trim(); });
      if (s.o == null) s.o = lastO[sec.id] || "none"; else lastO[sec.id] = s.o;
      s.x = s.x ? s.x.split(",") : [];
      s.ch = sec.dataset.ch; s.sec = sec.id;
      el._s = s;
      if (s.ch && s.ch !== "none") el.style.setProperty("--c", COL[s.ch]);
    });
    document.querySelectorAll(".st-chips a, #st-focus li, .milestones li, .verdict .u").forEach((a) => { const ch = a.dataset.ch; if (COL[ch]) a.style.setProperty("--c", COL[ch]); });
    let active = null, section = null, autoplayed = false;
    function activate(el) {
      if (el === active) return;
      active?.classList.remove("is-active"); el.classList.add("is-active"); active = el;
      const s = el._s;
      if (s.sec !== section) {
        section = s.sec; userOrig = false;
        document.querySelectorAll(".st-chips a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + section));
        const on = document.querySelector(`.st-chips a[href="#${section}"]`), bar = on && on.closest(".st-chips");
        if (on && bar.scrollWidth > bar.clientWidth) bar.scrollTo({ left: on.offsetLeft - (bar.clientWidth - on.clientWidth) / 2, behavior: "smooth" });
      }
      setFocus(s.ch);
      setOriginal(s.o);
      setExtras(s.x);
      if (s.y === "play") { if (!autoplayed) { autoplayed = true; play(Y0); } else if (!playing) tweenYear(Y1); }
      else if (s.y) tweenYear(+s.y);
      if (s.w) setSwipe(+s.w); else if (s.o !== "none" && (swipe.x > 0.85 || swipe.x < 0.15)) setSwipe(0.5);
      halo.clearLayers(); areaHL.clearLayers(); resetCentres(); back.hidden = true; map.closePopup();
      flyView(s.v);
      showLabels(s.v.split(",").map((v) => v.replace(/^topo:/, "")));
      updateKey();
    }
    let io;
    function observe() {
      io?.disconnect();
      const rm = mobile.matches ? "-62% 0px -30% 0px" : "-36% 0px -58% 0px";
      io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && activate(e.target)), { rootMargin: rm });
      steps.forEach((el) => io.observe(el));
    }
    observe();
    mobile.addEventListener("change", () => { observe(); map.invalidateSize(); });
    let settle = 0;
    function resync() {
      const line = innerHeight * (mobile.matches ? 0.66 : 0.4);
      let best = null;
      for (const el of steps) { const r = el.getBoundingClientRect(); if (r.top <= line) best = el; else break; }
      if (best) activate(best);
    }
    addEventListener("scroll", () => { clearTimeout(settle); settle = setTimeout(resync, 160); }, { passive: true });
    const prog = document.querySelector(".st-progress span");
    addEventListener("scroll", () => {
      const h = document.documentElement.scrollHeight - innerHeight;
      prog.style.width = `${Math.min(100, scrollY / Math.max(1, h) * 100)}%`;
    }, { passive: true });
    activate(steps[0]);
    clipOrig();
  }

  document.addEventListener("DOMContentLoaded", () => init().catch((e) => {
    console.error(e);
    const m = document.getElementById("st-map");
    if (m) m.insertAdjacentHTML("beforeend", `<p style="position:absolute;inset:auto 12px 100px;z-index:900;background:#fff;padding:8px;border-radius:6px">Map data failed to load: ${e.message}</p>`);
  }));
})();
