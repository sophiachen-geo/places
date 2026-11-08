/* #30DayMapChallenge · Day 8 · Utopia — "Los Angeles and the Afterlife of Utopia", illustrated.
 * The essay scrolls; the map follows it. Each paragraph carries a step (data-s):
 *   v = view (basin | city | region | centers | pastoral | plate | sites | topo:<site> | place ids)
 *   y = year shown by the morphogenesis layer (or "play")
 *   o = original map under the swipe (parks1930 | parkways1946 | plan1974 | topo:<site> | none) — inherited within a chapter
 *   x = extra evidence layers (holc, zoned, aadt, bott, bh500, towers, rail)
 *   w = swipe divider position (0–1)
 * The chapter (section[data-ch]) decides which utopia is lit; the other three are dimmed. */
(() => {
  "use strict";
  const COL = { pastoral: "#1baf7a", autopia: "#eda100", centers: "#2a78d6", coop: "#e34948", all: "#14304a" };
  const LINE = { pastoral: "#12865c", autopia: "#a87400", centers: "#1c5cab", coop: "#bf2f2e" }; // darker steps of the same hues, for strokes
  const GROUPS = ["pastoral", "autopia", "centers", "coop"];
  const INK = "#14304a";
  const D0 = "../";
  const Y0 = 1880, Y1 = 2026;
  const fmt = (n) => Number(n).toLocaleString("en-US");
  const J = (p) => fetch(D0 + p).then((r) => { if (!r.ok) throw new Error(p); return r.json(); });
  const VIEWS = {
    basin: [[33.70, -118.70], [34.34, -118.06]],
    city: [[33.72, -118.67], [34.34, -118.15]],
    region: [[33.66, -118.80], [34.56, -117.70]],
    centers: [[33.74, -118.62], [34.28, -118.08]],
  };
  const MILESTONES = [
    [1904, "pastoral", "Residential District Ordinance"],
    [1913, "coop", "Little Landers colony, Tujunga"],
    [1914, "coop", "Llano del Rio founded"],
    [1930, "pastoral", "Olmsted–Bartholomew regional parks plan"],
    [1940, "autopia", "Arroyo Seco Parkway, the first freeway, opens"],
    [1942, "coop", "Baldwin Hills Village completed"],
    [1946, "autopia", "County parkways plan: 613 miles"],
    [1946, "coop", "Crestwood Hills cooperative established"],
    [1949, "autopia", "Four Level Interchange completed"],
    [1953, "coop", "Elysian Park Heights cancelled"],
    [1962, "coop", "Dodger Stadium opens in Chávez Ravine"],
    [1966, "autopia", "Santa Monica Freeway completed"],
    [1971, "autopia", "Banham, The Architecture of Four Ecologies"],
    [1974, "centers", "Centers Concept adopted, 3 April"],
    [1990, "centers", "Blue Line: first modern rail line opens"],
    [1996, "centers", "General Plan Framework adopted"],
  ];

  async function init() {
    const [S, M, SS, places, centers, towers, rail, stations, fwy, aadt, bott, holc, utop, topoMeta, reg30, reg46, warp] = await Promise.all([
      J("data/stats.json"), J("data/morph.json"), J("data/story_stats.json"), J("data/story_places.geojson"),
      J("data/centers.geojson"), J("data/towers.geojson"), J("data/rail.geojson"), J("data/stations.geojson"),
      J("data/freeways.geojson"), J("data/aadt.geojson"), J("data/bottlenecks.geojson"), J("data/holc.geojson"),
      J("data/utopias.geojson"), J("img/topo_meta.json"), J("img/parks1930_registration.json"),
      J("img/parkways1946_registration.json"), J("img/concept1974_warped.json"),
    ]);
    const mobile = window.matchMedia("(max-width: 900px)");

    /* ======================= map & panes ======================= */
    const map = L.map("st-map", { zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 100, maxZoom: 17, minZoom: 7 }).fitBounds(VIEWS.basin);
    map.zoomControl.setPosition("topright");
    const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
    L.tileLayer(ESRI + "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 17, maxNativeZoom: 16,
      attribution: 'Tiles &copy; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · data: LA County Assessor, LA City, Caltrans, LA Metro, USGS, Mapping Inequality',
    }).addTo(map);
    const pane = (name, z, cls) => { const p = map.createPane(name); p.style.zIndex = z; if (cls) p.classList.add(cls); return p; };
    pane("morph", 250);
    const origPane = pane("orig", 280);
    origPane.style.mixBlendMode = "multiply";
    const GP = {};
    GROUPS.forEach((g, i) => { GP[g] = pane("g-" + g, 400 + i * 10, "g-pane"); });
    pane("top", 455);
    const lab = pane("labels", 470); lab.style.pointerEvents = "none"; lab.style.opacity = "0.7";
    L.tileLayer(ESRI + "World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", { maxZoom: 17, maxNativeZoom: 16, pane: "labels" }).addTo(map);
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
    const STOPS = [[1890, [93, 87, 77]], [1950, [155, 149, 138]], [2015, [217, 211, 199]]];
    const LUT = new Uint32Array(178);
    for (let k = 0; k < 178; k++) {
      const y = 1850 + k; let c;
      if (y <= STOPS[0][0]) c = STOPS[0][1]; else if (y >= STOPS[2][0]) c = STOPS[2][1];
      else { const [a, b] = y < STOPS[1][0] ? [STOPS[0], STOPS[1]] : [STOPS[1], STOPS[2]]; const t = (y - a[0]) / (b[0] - a[0]); c = a[1].map((v, j) => Math.round(v + (b[1][j] - v) * t)); }
      LUT[k] = ((205 << 24) | (c[2] << 16) | (c[1] << 8) | c[0]) >>> 0;
    }
    const FRONT = rgba(INK, 240), FRONT_YRS = 5;
    const mips = [disp];
    for (let f = 2; f <= 8; f *= 2) { const m = document.createElement("canvas"); m.width = Math.ceil(NX / f); m.height = Math.ceil(NY / f); mips.push(m); }
    function recolor(Y) {
      d32.fill(0);
      const kmax = Math.min(177, Y - 1850);
      for (let k = 0; k <= kmax; k++) {
        const c = (Y - (1850 + k) < FRONT_YRS) ? FRONT : LUT[k];
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
      ctx.imageSmoothingEnabled = s > 256; ctx.imageSmoothingQuality = "high";
      ctx.drawImage(mips[lvl], x0 / f, y0 / f, (x1 - x0) / f, (y1 - y0) / f, (x0 - sx) * k, (y0 - sy) * k, (x1 - x0) * k, (y1 - y0) * k);
    }
    const Morph = L.GridLayer.extend({ createTile(co) { const c = L.DomUtil.create("canvas", "morph-tile"); c.width = c.height = 256; drawTile(c, co); return c; } });
    const morph = new Morph({ pane: "morph", opacity: 0.92, maxZoom: 17, updateWhenZooming: false,
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
      const top = 13, bot = h - 13, n = Y1 - Y0 + 1, bw = w / n;
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
      Object.entries({ x1: 0, x2: w, y1: bot + 0.5, y2: bot + 0.5, stroke: "#cfc7b6" }).forEach(([k, v]) => base.setAttribute(k, v)); svg.appendChild(base);
      for (let y = 1900; y <= 2020; y += 20) {
        const t = document.createElementNS(SVGNS, "text"); t.setAttribute("x", (y - Y0 + 0.5) * bw); t.setAttribute("y", h - 1);
        t.setAttribute("text-anchor", "middle"); t.textContent = y; svg.appendChild(t);
      }
      const seen = {};
      MILESTONES.forEach(([y, ch, label]) => {
        const k = seen[y] = (seen[y] || 0) + 1;
        const c = document.createElementNS(SVGNS, "circle");
        c.setAttribute("cx", (y - Y0 + 0.5) * bw); c.setAttribute("cy", 5 + (k - 1) * 0); c.setAttribute("r", 3.6);
        c.setAttribute("fill", COL[ch]); c.setAttribute("stroke", "#fff"); c.setAttribute("stroke-width", 1.2);
        if (k > 1) c.setAttribute("cx", (y - Y0 + 0.5) * bw + 5);
        c.classList.add("ms"); c.dataset.year = y;
        const ti = document.createElementNS(SVGNS, "title"); ti.textContent = `${y} · ${label}`; c.appendChild(ti);
        svg.appendChild(c);
      });
      cursor = document.createElementNS(SVGNS, "line"); cursor.setAttribute("y1", 9); cursor.setAttribute("y2", bot + 3);
      cursor.setAttribute("stroke", INK); cursor.setAttribute("stroke-width", 1.5); svg.appendChild(cursor);
      tEl.replaceChildren(svg);
      paintHist();
    }
    function paintHist() {
      if (!bars.length) return;
      for (let y = Y0; y <= Y1; y++) {
        const r = bars[y - Y0];
        r.setAttribute("fill", y > year ? "#e4ded2" : (year - y < FRONT_YRS ? INK : `rgb(${[0, 1, 2].map((j) => (LUT[y - 1850] >> (8 * j)) & 255).join(",")})`));
      }
      const x = (year - Y0 + 0.5) * tw / (Y1 - Y0 + 1);
      cursor.setAttribute("x1", x); cursor.setAttribute("x2", x);
    }
    new ResizeObserver(buildHist).observe(tEl);

    let frame = 0;
    function setYear(y) {
      year = Math.max(Y0, Math.min(Y1, Math.round(y)));
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0; recolor(year); redrawMorph(); paintHist();
        tYear.textContent = year;
        const p = cum[year] * 100;
        tShare.textContent = `${p < 1 ? p.toFixed(1) : Math.round(p)}% of today’s buildings stood`;
        tEl.setAttribute("aria-valuenow", year); tEl.setAttribute("aria-valuetext", `${year}: ${tShare.textContent}`);
      });
    }
    let anim = null, playing = false;
    function stopAnim() { if (anim) cancelAnimationFrame(anim); anim = null; playing = false; playBtn.textContent = "▶"; playBtn.setAttribute("aria-label", "Play the city's growth"); }
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
      playing = true; playBtn.textContent = "❚❚"; playBtn.setAttribute("aria-label", "Pause");
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
      parks1930: { url: "tiles/parks1930/{z}/{x}/{y}.webp", maxN: 12, bounds: [[33.62, -118.98], [34.62, -117.42]], tag: "1930 plan",
        cap: `Olmsted Brothers &amp; Bartholomew and Associates, 1930. Registered to the County’s surveyed outline on ${reg30.control_points} points (median ${reg30.median_m} m).`,
        win: [[33.80, -118.81], [34.45, -117.60]] },
      parkways1946: { url: "tiles/parkways1946/{z}/{x}/{y}.webp", maxN: 12, bounds: [[33.52, -119.12], [34.60, -117.48]], tag: "1946 plan",
        cap: `LA County Regional Planning Commission, 1946. Registered on ${reg46.control_points} points of the County outline (median ${reg46.median_m} m).`,
        win: [[33.70, -118.95], [34.42, -117.65]] },
      plan1974: { url: "tiles/plan1974/{z}/{x}/{y}.webp", maxN: 13, bounds: [[33.64, -118.78], [34.39, -118.02]], tag: "1974 plan",
        cap: `LA City Planning Dept., Concept Los Angeles, 1974. Warped on ${warp.gcps.inland_centers + warp.gcps.shoreline} points (centre error, leave-one-out: median ${warp.loo_center_error_m.median} m).`,
        win: [[33.70, -118.70], [34.34, -118.06]] },
    };
    Object.entries(topoMeta).forEach(([id, t]) => {
      ORIGS["topo:" + id] = { url: `tiles/topo_${id}/{z}/{x}/{y}.webp`, minN: t.zmin, maxN: t.zmax, minZoom: 10, bounds: t.bounds, tag: `${t.year} USGS`,
        cap: `USGS 1:24,000 topographic sheet “${topoName(t.file)}”, ${t.year} edition (public domain). NAD27 shifted to WGS84 with NADCON.`, win: t.bounds };
    });
    const origLayers = {};
    const getOrig = (k) => origLayers[k] || (origLayers[k] = L.tileLayer(D0 + ORIGS[k].url, {
      pane: "orig", minZoom: ORIGS[k].minZoom || 7, maxZoom: 17, minNativeZoom: ORIGS[k].minN || 9, maxNativeZoom: ORIGS[k].maxN,
      bounds: L.latLngBounds(ORIGS[k].bounds), opacity: origOpacity,
    }));
    let origOpacity = 0.85, curOrig = "none", userOrig = false;
    const swipe = { on: true, x: 0.5 };
    const divider = L.DomUtil.create("div", "swipe-divider", map.getContainer());
    divider.innerHTML = '<span class="swipe-tag l"></span><span class="swipe-tag r">today</span><button class="swipe-handle" type="button" aria-label="Drag to compare the original map with today">⟷</button>';
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
    function nearestTopo() {
      const c = map.getCenter(); let best = null, bd = Infinity;
      Object.entries(topoMeta).forEach(([id, t]) => { const d = c.distanceTo(L.latLngBounds(t.bounds).getCenter()); if (d < bd) { bd = d; best = id; } });
      return "topo:" + best;
    }
    function setOriginal(k, user = false) {
      if (!user && userOrig) return;
      if (user) userOrig = true;
      if (k === "topo") k = nearestTopo();
      if (k === curOrig && oSel.dataset.init) return;
      oSel.dataset.init = 1;
      if (curOrig !== "none") map.removeLayer(getOrig(curOrig));
      curOrig = k;
      if (k !== "none") { const l = getOrig(k); l.setOpacity(origOpacity); l.addTo(map); }
      oSel.value = k.startsWith("topo:") ? "topo" : k;
      oPanel.classList.toggle("is-none", k === "none");
      oCap.innerHTML = k === "none" ? "" : ORIGS[k].cap;
      divider.querySelector(".swipe-tag.l").textContent = k === "none" ? "" : ORIGS[k].tag;
      clipOrig();
    }
    oSel.addEventListener("change", () => setOriginal(oSel.value, true));
    document.getElementById("o-op").addEventListener("input", (e) => { origOpacity = e.target.value / 100; if (curOrig !== "none") getOrig(curOrig).setOpacity(origOpacity); });
    document.getElementById("o-swipe").addEventListener("change", (e) => { swipe.on = e.target.checked; clipOrig(); });

    /* ======================= utopia layers ======================= */
    const PL = {};   // place registry: id -> { ch, name, bounds, layer, maxZoom, topo }
    const reg = (id, o) => { PL[id] = o; };
    const pop = (h, meta, body) => `<div class="st-pop"><p class="meta">${meta}</p><h4>${h}</h4>${body}</div>`;
    const placeById = Object.fromEntries(places.features.map((f) => [f.properties.id, f]));

    // I · pastoral — named suburbs (official outlines), with year-built profile
    const pastoralIds = ["valley", "pasadena", "hollywood", "hancock", "windsor"];
    const pastoralLayer = L.featureGroup(pastoralIds.map((id) => {
      const f = placeById[id], p = f.properties;
      const l = L.geoJSON(f, { pane: "g-pastoral", style: { color: LINE.pastoral, weight: id === "valley" ? 1.6 : 2, fillColor: COL.pastoral, fillOpacity: id === "valley" ? 0.1 : 0.2 } })
        .bindPopup(pop(p.name, p.src, `<p>${fmt(p.parcels)} parcels today · median year built <b>${p.median_year}</b><br>${p.pre1930_pct}% built before 1930 · ${p.b1946_1970_pct}% built 1946–70</p>`));
      reg(id, { ch: "pastoral", name: p.name, bounds: l.getBounds(), layer: l, maxZoom: 13.5 });
      return l;
    })).addTo(map);
    const HOLC_OP = { A: 0.05, B: 0.16, C: 0.3, D: 0.5 };
    const holcLayer = L.geoJSON(holc, { pane: "g-pastoral",
      style: (f) => ({ color: INK, weight: 0.8, opacity: 0.7, fillColor: INK, fillOpacity: HOLC_OP[f.properties.grade] }),
      onEachFeature: (f, l) => { const g = f.properties.grade, h = S.holc[g];
        l.bindPopup(pop(`Grade ${g}`, `HOLC 1939 · area ${f.properties.id} · Mapping Inequality`,
          `<p>All ${g}-graded land in the City today: <b>${h.zoned_sf_pct}%</b> zoned single-family; <b>${h.sfr_units_pct}%</b> of its homes are single-family houses.</p>`)); } });
    const zonedLayer = L.tileLayer(D0 + "tiles/zonedsf/{z}/{x}/{y}.webp", { pane: "g-pastoral", minNativeZoom: 10, maxNativeZoom: 14, maxZoom: 17, opacity: 0.9,
      bounds: L.latLngBounds([33.70, -118.68], [34.34, -118.15]) });

    // II · Autopia — freeways, named freeways & interchanges, Boyle Heights
    const fwyLayer = L.geoJSON(fwy, { pane: "g-autopia", interactive: false, style: { color: LINE.autopia, weight: 1.7, opacity: 0.85 } }).addTo(map);
    const boyle = placeById.boyle;
    const boyleLayer = L.geoJSON(boyle, { pane: "g-autopia", style: { color: LINE.autopia, weight: 2, dashArray: "5 4", fillColor: COL.autopia, fillOpacity: 0.08 } })
      .bindPopup(pop("Boyle Heights", boyle.properties.src, `<p>${fmt(boyle.properties.parcels)} parcels · median year built <b>${boyle.properties.median_year}</b> · ${boyle.properties.pre1930_pct}% built before 1930.<br>
        Crossed by I-5, I-10, SR-60 and US-101: <b>${SS.boyle.bh.within_500ft_pct}%</b> of its homes lie within 500 ft of a freeway (City: ${SS.boyle.city.within_500ft_pct}%).</p>`)).addTo(map);
    reg("boyle", { ch: "autopia", name: "Boyle Heights", bounds: boyleLayer.getBounds(), layer: boyleLayer, maxZoom: 14 });
    ["smfwy", "santaana"].forEach((id) => {
      const f = placeById[id];
      const l = L.geoJSON(f, { pane: "g-autopia", style: { color: LINE.autopia, weight: 5.5, opacity: 0.95, lineCap: "round" } })
        .bindPopup(pop(f.properties.name, "Caltrans linear referencing system", `<p>${f.properties.src}</p>`)).addTo(map);
      const cs = f.geometry.type === "LineString" ? f.geometry.coordinates : f.geometry.coordinates.reduce((a, b) => (b.length > a.length ? b : a));
      const mid = cs[Math.floor(cs.length / 2)];
      reg(id, { ch: "autopia", name: f.properties.name, bounds: l.getBounds(), layer: l, maxZoom: 14, labelAt: [mid[1], mid[0]] });
    });
    ["fourlevel", "ela", "smsd"].forEach((id) => {
      const f = placeById[id], [lng, lat] = f.geometry.coordinates;
      const l = L.circleMarker([lat, lng], { pane: "g-autopia", radius: 8, color: INK, weight: 2, fillColor: COL.autopia, fillOpacity: 1 })
        .bindPopup(pop(f.properties.name, "Interchange · Caltrans LRS", `<p>${f.properties.src}</p>`)).addTo(map);
      reg(id, { ch: "autopia", name: id === "smsd" ? "Santa Monica × San Diego freeways" : f.properties.name, bounds: L.latLngBounds([[lat, lng], [lat, lng]]), layer: l, maxZoom: 14, ll: [lat, lng] });
    });
    const bh500 = L.geoJSON(placeById.bh500, { pane: "g-autopia", interactive: false, style: { stroke: false, fillColor: COL.autopia, fillOpacity: 0.45 } });
    const maxV = S.aadt.max.v, MINV = 100000;
    const aR = (v) => 1.6 + 8 * Math.sqrt(Math.max(0, v - MINV) / (maxV - MINV));
    const aadtLayer = L.layerGroup(aadt.features.filter((f) => f.properties.v >= MINV).sort((a, b) => a.properties.v - b.properties.v).map((f) => {
      const p = f.properties, [lng, lat] = f.geometry.coordinates;
      return L.circleMarker([lat, lng], { pane: "g-autopia", renderer: cv.autopia, radius: aR(p.v), color: "#fff", weight: 0.7, fillColor: COL.autopia, fillOpacity: 0.8 })
        .bindPopup(pop(`${fmt(p.v)} vehicles / day`, `Caltrans AADT 2024 · Route ${p.rte} · PM ${p.pm}`, `<p>${p.at}</p>`));
    }));
    const bottLayer = L.geoJSON(bott, { pane: "g-autopia",
      style: (f) => ({ color: "#6b4a00", weight: f.properties.rank <= 5 ? 6 : 4, opacity: 0.9, lineCap: "round" }),
      onEachFeature: (f, l) => { const p = f.properties;
        l.bindPopup(pop(`${p.fwy} at ${p.at}`, `Caltrans D7 bottleneck #${p.rank}, calendar 2024 · ${p.shift} peak`,
          `<p><b>${fmt(p.delay)}</b> vehicle-hours of delay on ${p.days} days · queue ≈ ${p.mi} mi${p.q2_2025 ? `<br>Still #${p.q2_2025} in 2025 Q2` : ""}</p>`)); } });

    // III · Centers — the 56 discs (½ mile), coloured by what each became
    const OUT = {
      realised: { fill: COL.centers, op: 0.6, stroke: LINE.centers, w: 1.2, label: "Realised: ≥5 high-rises + open rail" },
      towers: { fill: "#86b6ef", op: 0.55, stroke: LINE.centers, w: 1.2, label: "High-rises, no rail" },
      rail: { fill: "#ffffff", op: 0.65, stroke: LINE.centers, w: 2.6, label: "Rail, no high-rises" },
      neither: { fill: "#ffffff", op: 0.05, stroke: "#8b877e", w: 1.2, dash: "3 3", label: "Neither: still suburban" },
    };
    const ALIAS = { "Canoga Park–Woodland Hills": "Warner Center" };
    const centerLayer = L.geoJSON(centers, { pane: "g-centers",
      pointToLayer: (f, ll) => { const o = OUT[f.properties.oc];
        return L.circle(ll, { pane: "g-centers", radius: 804.7, color: o.stroke, weight: o.w, dashArray: o.dash, fillColor: o.fill, fillOpacity: o.op }); },
      onEachFeature: (f, l) => { const p = f.properties, nm = ALIAS[p.name] ? `${ALIAS[p.name]} <small>(plan: ${p.name})</small>` : p.name;
        l.bindPopup(pop(nm, `1974 Concept centre · ${p.in_city ? "City of LA" : "outside the City"}`,
          `<p>Core: ${p.core}<br><b>${OUT[p.oc].label}</b> (within ½ mile)</p><p>${p.tw} high-rises within ½ mile${p.hmax ? ` · tallest ${fmt(p.hmax)} ft` : ""}<br>
           Nearest open rail: ${p.near}, ${fmt(p.near_m)} m${p.uc ? `<br>Under construction: ${p.uc}` : ""}</p>`)); } }).addTo(map);
    const cIdx = Object.fromEntries(centers.features.map((f) => [f.properties.name, f]));
    [["centurycity", "Century City"], ["westwood", "Westwood"], ["warner", "Canoga Park–Woodland Hills"]].forEach(([id, nm]) => {
      const [lng, lat] = cIdx[nm].geometry.coordinates, ll = L.latLng(lat, lng);
      reg(id, { ch: "centers", name: ALIAS[nm] || nm, bounds: ll.toBounds(1700), maxZoom: 14, ll: [lat, lng] });
    });
    const towerLayer = L.layerGroup(towers.features.map((f) => { const p = f.properties, [lng, lat] = f.geometry.coordinates;
      return L.circleMarker([lat, lng], { pane: "g-centers", renderer: cv.centers, radius: 1.6 + (p.h || p.st * 12.5) / 450, stroke: false, fillColor: INK, fillOpacity: 0.85 })
        .bindTooltip(p.src === "LADBS CofO" ? `${p.addr} · ${p.st} storeys · completed ${p.cofo}` : `${fmt(p.h)} ft (LARIAC 2020)`, { direction: "top" }); }));
    const railLayer = L.layerGroup([
      L.geoJSON(rail, { pane: "g-centers", interactive: false, style: { color: INK, weight: 2.4, opacity: 0.85 } }),
      L.geoJSON(stations, { pane: "g-centers", filter: (f) => f.properties.k === "open" || f.properties.k === "uc",
        pointToLayer: (f, ll) => L.circleMarker(ll, { pane: "g-centers", radius: f.properties.k === "uc" ? 4 : 2.8, color: INK, weight: 1.3, dashArray: f.properties.k === "uc" ? "2 2" : null, fillColor: f.properties.k === "uc" ? "#fbeede" : "#fff", fillOpacity: 1 }),
        onEachFeature: (f, l) => l.bindTooltip(`${f.properties.name}${f.properties.k === "uc" ? ` — under construction (${f.properties.line})` : ""}`, { direction: "top" }) }),
    ]);

    // IV · Cooperative — footprints + numbered pins
    const pins = utop.features.filter((f) => !f.properties.shape);
    const shapes = Object.fromEntries(utop.features.filter((f) => f.properties.shape).map((f) => [f.properties.id, f]));
    const coopLayer = L.featureGroup();
    L.geoJSON({ type: "FeatureCollection", features: Object.values(shapes) }, { pane: "g-coop", interactive: false,
      style: { color: LINE.coop, weight: 2, fillColor: COL.coop, fillOpacity: 0.3 } }).addTo(coopLayer);
    pins.forEach((f, i) => {
      const p = f.properties, [lng, lat] = f.geometry.coordinates;
      const m = L.marker([lat, lng], { pane: "g-coop", icon: L.divIcon({ className: "", html: `<span class="u-pin">${i + 1}</span>`, iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12] }) })
        .bindPopup(pop(p.name, `${p.years}`, `${p.ideal ? `<p><b>Ideal.</b> ${p.ideal}</p>` : ""}${p.reality ? `<p><b>Reality.</b> ${p.reality}</p>` : ""}<p class="meta">${p.geomnote}</p>`), { maxWidth: 320 });
      m.addTo(coopLayer);
      const b = shapes[p.id] ? L.geoJSON(shapes[p.id]).getBounds() : L.latLng(lat, lng).toBounds(400);
      reg(p.id, { ch: "coop", name: p.name, bounds: b, layer: m, maxZoom: 15, topo: topoMeta[p.id] ? "topo:" + p.id : null, ll: [lat, lng], n: i + 1 });
    });
    coopLayer.addTo(map);

    const EXTRAS = { holc: holcLayer, zoned: zonedLayer, aadt: aadtLayer, bott: bottLayer, bh500, towers: towerLayer, rail: railLayer };
    let extras = [];
    function morphOpacity() {
      let o = extras.some((k) => k === "holc" || k === "zoned" || k === "bh500") ? 0.5 : 0.92;
      if (map.getZoom() >= 13.5) o *= 0.55;   // at site scale the 120 m cells would drown the sheet and the streets
      morph.setOpacity(o);
    }
    map.on("zoomend", morphOpacity);
    function setExtras(list) {
      extras = list;
      morphOpacity();
      Object.entries(EXTRAS).forEach(([k, l]) => { const on = list.includes(k); if (on && !map.hasLayer(l)) l.addTo(map); if (!on && map.hasLayer(l)) map.removeLayer(l); });
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
    const labels = L.layerGroup().addTo(map);
    function showLabels(ids) {
      labels.clearLayers();
      ids.filter((id) => PL[id]).forEach((id) => {
        const P = PL[id], pt = !!P.ll && !P.labelAt, ll = P.labelAt || P.ll || P.bounds.getCenter();
        const t = L.tooltip({ permanent: true, direction: pt ? "right" : "center", offset: pt ? [12, 0] : [0, 0], className: "pl-label", interactive: false })
          .setLatLng(ll).setContent(P.name);
        labels.addLayer(t);
      });
    }
    // the Valley's polygon centre lands in the hills; label it where the subdivisions are
    PL.valley.labelAt = [34.205, -118.47];
    const keyEl = document.getElementById("st-key");
    const sw = (style) => `<i style="${style}"></i>`;
    function updateKey() {
      let h = `<h5>Built fabric · year built</h5><div class="ramp"></div><div class="ramp-l"><span>1890</span><span>1950</span><span>2015</span></div>
        <div class="k">${sw(`width:12px;height:8px;background:${INK}`)}Built in the last ${FRONT_YRS} years</div>`;
      const g = focus;
      if (g === "pastoral") {
        h += `<h5>Pastoral suburb</h5><div class="k">${sw(`width:14px;height:10px;border:2px solid ${LINE.pastoral};background:${COL.pastoral}33`)}Named suburbs (official outlines)</div>`;
        if (extras.includes("zoned")) h += `<div class="k">${sw("width:14px;height:10px;background:#3f8a2e;opacity:.6")}Zoned single-family, Nov 2026</div>`;
      } else if (g === "autopia") {
        h += `<h5>Autopia</h5><div class="k">${sw(`width:16px;height:0;border-top:2px solid ${LINE.autopia}`)}Freeways</div>
          <div class="k">${sw(`width:12px;height:12px;border-radius:50%;background:${COL.autopia};border:2px solid ${INK}`)}Interchanges named in the text</div>`;
        if (extras.includes("aadt")) h += `<div class="k">${sw(`width:14px;height:14px;border-radius:50%;background:${COL.autopia}`)}Vehicles/day 2024, ≥100k (max ${fmt(maxV)})</div>`;
        if (extras.includes("bott")) h += `<div class="k">${sw("width:16px;height:0;border-top:5px solid #6b4a00")}20 worst bottlenecks, 2024</div>`;
        if (extras.includes("bh500")) h += `<div class="k">${sw(`width:14px;height:10px;background:${COL.autopia};opacity:.6`)}Within 500 ft of a freeway</div>`;
      } else if (g === "centers") {
        h += `<h5>1974 centres, ½-mile discs</h5>` + Object.entries(OUT).map(([k, o]) =>
          `<div class="k">${sw(`width:12px;height:12px;border-radius:50%;background:${o.fill};opacity:${Math.max(o.op, 0.9)};border:${Math.max(1.5, o.w)}px ${o.dash ? "dashed" : "solid"} ${o.stroke}`)}${o.label} · ${S.centers.outcomes_half_mile[k]}</div>`).join("");
        if (extras.includes("towers")) h += `<div class="k">${sw(`width:6px;height:6px;border-radius:50%;background:${INK}`)}High-rise ≥150 ft / ≥12 storeys</div>`;
        if (extras.includes("rail")) h += `<div class="k">${sw(`width:16px;height:0;border-top:2.5px solid ${INK}`)}Metro rail (dashed stop: being built)</div>`;
      } else if (g === "coop") {
        h += `<h5>Cooperative experiments</h5><div class="k">${sw(`width:14px;height:14px;border-radius:50%;background:${COL.coop};border:2px solid #fff;box-shadow:0 0 0 1px #ccc`)}Site · footprint in red</div>`;
      }
      if (extras.includes("holc")) h += `<h5>HOLC grades, 1939</h5>` + ["A", "B", "C", "D"].map((k) => `<div class="k">${sw(`width:14px;height:10px;border:1px solid ${INK};background:rgba(20,48,74,${HOLC_OP[k]})`)}${k} · today ${S.holc[k].zoned_sf_pct}% zoned single-family</div>`).join("");
      keyEl.innerHTML = h;
    }

    /* ======================= camera ======================= */
    const pad = () => (mobile.matches ? { paddingTopLeft: [20, 56], paddingBottomRight: [20, 72] } : { paddingTopLeft: [50, 120], paddingBottomRight: [60, 150] });
    function boundsFor(v) {
      if (v === "region" && mobile.matches) v = "basin";   // the Antelope Valley view is too small to read on a phone
      if (VIEWS[v]) return { b: L.latLngBounds(VIEWS[v]), z: 13 };
      if (v === "pastoral") return { b: L.latLngBounds(pastoralIds.map((id) => PL[id].bounds)), z: 13 };
      if (v === "plate") return { b: L.latLngBounds((ORIGS[curOrig] || ORIGS.parks1930).win), z: 13 };
      if (v === "sites") return { b: coopLayer.getBounds().pad(0.08), z: 13 };
      if (v.startsWith("topo:")) return { b: L.latLngBounds(topoMeta[v.slice(5)].bounds), z: 15 };
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

    /* ======================= halo for clicked places ======================= */
    const halo = L.layerGroup().addTo(map);
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
      if (P.topo) { setOriginal(P.topo, true); t.b = L.latLngBounds(topoMeta[id].bounds); }
      lastView = "";
      map.flyToBounds(t.b, { ...pad(), maxZoom: t.z, duration: 1.0 });
      showLabels([id]); flash(P);
      map.once("moveend", () => { if (P.layer && P.layer.openPopup && P.ll) P.layer.openPopup(); });
    }
    document.querySelectorAll(".pl[data-place]").forEach((b) => b.addEventListener("click", () => {
      focusPlace(b.dataset.place); b.classList.add("pulse"); setTimeout(() => b.classList.remove("pulse"), 1200);
    }));

    /* ======================= evidence cards ======================= */
    const C = S.centers, G = S.garden, B = SS.boyle, PW = SS.parkways1946;
    const tile = (big, txt) => `<div class="tile"><b>${big}</b><span>${txt}</span></div>`;
    const origLine = (k, html) => `<div class="orig"><span class="oi" aria-hidden="true">⟷</span><span><b>Under the swipe:</b> ${html} <button type="button" data-orig="${k}">Show it</button></span></div>`;
    const svgEl = (w, h, inner) => `<svg viewBox="0 0 ${w} ${h}" role="img">${inner}</svg>`;
    const cardW = () => { const e = document.querySelector(".evid"); return Math.round(Math.max(300, Math.min(560, (e ? e.clientWidth : 520) - 38))); };

    function dotStrip() {
      const rows = ["windsor", "hancock", "hollywood", "pasadena", "valley"].map((id) => placeById[id].properties);
      const W = cardW(), LW = W < 420 ? 112 : 132, RH = 24, x0 = LW, x1 = W - 16, ya = 1900, yb = 1980, T = 14, H2 = rows.length * RH + 22 + T;
      const X = (y) => x0 + (y - ya) / (yb - ya) * (x1 - x0);
      let s = "";
      for (let y = ya; y <= yb; y += 20) s += `<line class="ax" x1="${X(y)}" x2="${X(y)}" y1="${T}" y2="${T + rows.length * RH}"/><text x="${X(y)}" y="${T + rows.length * RH + 15}" text-anchor="middle">${y}</text>`;
      s += `<line x1="${X(M.median_year)}" x2="${X(M.median_year)}" y1="${T - 4}" y2="${T + rows.length * RH}" stroke="${INK}" stroke-dasharray="3 3"/><text x="${X(M.median_year)}" y="${T - 7}" text-anchor="middle" style="font-size:10px">all of LA County: ${M.median_year}</text>`;
      rows.forEach((p, i) => {
        const y = T + i * RH + RH / 2;
        s += `<g class="row" data-place="${p.id}"><rect class="hit" x="0" y="${T + i * RH}" width="${W}" height="${RH}" fill="transparent"/>
          <text class="lbl" x="0" y="${y + 4}">${p.name}</text>
          <line x1="${X(ya)}" x2="${X(p.median_year)}" y1="${y}" y2="${y}" stroke="${COL.pastoral}" stroke-opacity=".35" stroke-width="2"/>
          <circle cx="${X(p.median_year)}" cy="${y}" r="5.5" fill="${COL.pastoral}" stroke="${LINE.pastoral}" stroke-width="1.2"/>
          <text x="${X(p.median_year) + 9}" y="${y + 4}">${p.median_year}</text></g>`;
      });
      return svgEl(W, H2, s);
    }
    function proxBars() {
      const rows = [["Boyle Heights", B.bh.within_500ft_pct, true], ["City of Los Angeles", B.city.within_500ft_pct], ["Los Angeles County", B.county.within_500ft_pct]];
      const W = cardW(), LW = W < 420 ? 112 : 132, RH = 24, max = 25, X = (v) => LW + v / max * (W - LW - 46);
      let s = "";
      rows.forEach(([n, v, hi], i) => {
        const y = i * RH + 4;
        s += `<text class="lbl" x="0" y="${y + 12}">${n}</text><rect x="${LW}" y="${y}" width="${X(v) - LW}" height="16" rx="3" fill="${hi ? COL.autopia : "#c9c3b6"}"/>
          <text x="${X(v) + 6}" y="${y + 12}" style="font-weight:600;fill:#1b2a3a">${v}%</text>`;
      });
      return svgEl(W, rows.length * RH + 4, s);
    }
    function outcomeBar() {
      const o = C.outcomes_half_mile, keys = ["realised", "towers", "rail", "neither"], W = cardW(), h = 22;
      let x = 0, s = "";
      keys.forEach((k) => {
        const w = o[k] / C.n * W, st = OUT[k];
        s += `<rect x="${x + 1}" y="0" width="${Math.max(0, w - 2)}" height="${h}" rx="3" fill="${st.fill}" fill-opacity="${Math.max(st.op, 0.85)}" stroke="${st.stroke}" stroke-width="${k === "rail" ? 2.4 : 1}" ${st.dash ? `stroke-dasharray="${st.dash}"` : ""}/>
          <text x="${x + w / 2}" y="${h + 14}" text-anchor="middle" class="lbl">${o[k]}</text>
          <text x="${x + w / 2}" y="${h + 27}" text-anchor="middle">${(W < 420 ? { realised: "both", towers: "towers", rail: "rail", neither: "neither" } : { realised: "towers + rail", towers: "towers only", rail: "rail only", neither: "neither" })[k]}</text>`;
        x += w;
      });
      return svgEl(W, h + 32, s);
    }
    const SPANS = [
      ["landers", 1913, 1917, "gone"], ["llano", 1914, 1918, "gone"], ["village", 1941, 1942, "survives"],
      ["crestwood", 1946, 1955, "survives"], ["elysian", 1950, 1953, "stadium"],
    ];
    function gantt() {
      const W = cardW(), LW = W < 420 ? 150 : 206, RH = 24, ya = 1910, yb = 2026, X = (y) => LW + (y - ya) / (yb - ya) * (W - LW - 6);
      let s = "";
      (W < 420 ? [1910, 1950, 1990] : [1910, 1930, 1950, 1970, 1990, 2010]).forEach((y) => { s += `<line class="ax" x1="${X(y)}" x2="${X(y)}" y1="0" y2="${SPANS.length * RH}"/><text x="${X(y)}" y="${SPANS.length * RH + 14}" text-anchor="middle">${y}</text>`; });
      SPANS.forEach(([id, a, b, fate], i) => {
        const y = i * RH + 5, P = PL[id];
        const short = { landers: "Little Landers", llano: "Llano del Rio", village: "Baldwin Hills Village", crestwood: "Crestwood Hills", elysian: W < 420 ? "Elysian Pk Hts → stadium" : "Elysian Park Heights → Dodger Stadium" }[id];
        s += `<g class="row" data-place="${id}"><rect class="hit" x="0" y="${i * RH}" width="${W}" height="${RH}" fill="transparent"/>
          <text class="lbl" x="0" y="${y + 11}">${P ? P.n + ". " : ""}${short}</text>`;
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
    const CARDS = {
      pastoral: () => `<h3>Read with the map</h3>
        ${origLine("parks1930", "the 1930 Olmsted–Bartholomew plan — the regional parks, parkways and beaches the region did not adopt.")}
        <div class="tiles">
          ${tile(`${G.sf_share_of_residential_zoned_land}%`, "of the City’s residential-zoned land is reserved for single-family houses (zoning, Nov 2026)")}
          ${tile(`${G.sfr_share_of_all_units}%`, `of the City’s ${fmt(G.units_total)} homes are in those houses (2026 Assessor roll)`)}
          ${tile(`${S.holc.A.zoned_sf_pct}% · ${S.holc.D.zoned_sf_pct}%`, "zoned single-family today inside 1939 HOLC grade A vs grade D areas")}
          ${tile(`${placeById.valley.properties.b1946_1970_pct}%`, `of the San Fernando Valley’s ${fmt(placeById.valley.properties.parcels)} parcels were built 1946–70`)}
        </div>
        <div class="mini"><h4>Successive expressions — median year built of the buildings standing today</h4>${dotStrip()}
          <p class="note">Official outlines: HPOZs (Hancock Park, Windsor Square), Community Plan Area (Hollywood), Valley planning commissions, City of Pasadena. Click a row to fly there.</p></div>`,
      autopia: () => `<h3>Read with the map</h3>
        ${origLine("parkways1946", `the County’s 1946 parkway plan — ${PW.miles.total} miles of interregional, regional and metropolitan parkways, estimated at $${(PW.cost_usd_1946 / 1e6).toFixed(1)} million.`)}
        <div class="tiles">
          ${tile(fmt(S.aadt.max.v), "vehicles a day on the Santa Monica Freeway at Vermont Ave — the region’s highest 2024 count")}
          ${tile(S.aadt.ge_300k, "freeway count points above 300,000 vehicles a day (2024)")}
          ${tile(B.routes.length, `freeways cross Boyle Heights: ${B.routes.map((r) => ({ 5: "I-5", 10: "I-10", 60: "SR-60", 101: "US-101" }[r] || r)).join(", ")}`)}
          ${tile(`${(S.bottlenecks.delay_2024_top20_veh_hrs / 1e6).toFixed(1)} M`, "vehicle-hours of delay at the 20 worst bottlenecks, 2024")}
        </div>
        <div class="mini"><h4>Homes within 500 ft of a freeway</h4>${proxBars()}
          <p class="note">${boyle.properties.pre1930_pct}% of Boyle Heights’ surviving buildings predate 1930: the freeways were driven through a finished neighbourhood. 500 ft is CARB’s siting distance for homes near freeways; homes from the 2026 Assessor roll.</p></div>`,
      centers: () => `<h3>Read with the map</h3>
        ${origLine("plan1974", "the adopted 1974 Concept Los Angeles diagram, warped onto today’s map.")}
        <div class="tiles">
          ${tile(`${C.outcomes_half_mile.realised} of ${C.n}`, "centres got both ≥5 high-rises and an open rail station within ½ mile")}
          ${tile(`${Math.round(C.city_towers_in_half / C.city_towers * 100)}%`, `of the City’s ${C.city_towers} high-rises stand within ½ mile of a centre — on ${C.half_share_of_city_land}% of its land`)}
          ${tile(`${C.rail_open_half}`, `centres have an open rail station within ½ mile; ${C.rail_building_half} more are being built`)}
          ${tile(`${cIdx["Century City"].properties.tw} · ${cIdx.Westwood.properties.tw} · ${cIdx["Canoga Park–Woodland Hills"].properties.tw}`, "high-rises within ½ mile of Century City · Westwood · Warner Center; none yet on open rail")}
        </div>
        <div class="mini"><h4>What the 56 centres became (within ½ mile of each core)</h4>${outcomeBar()}</div>`,
      coop: () => `<h3>Read with the map</h3>
        ${origLine("topo", "USGS topographic sheets from each experiment’s own years — they change as you read, site by site.")}
        <div class="mini"><h4>The experiments, 1910–2026</h4>${gantt()}
          <p class="note">Solid: the experiment as a working community. Faint: the buildings survive, the cooperative form does not. Dashed: planned, never built; grey: the stadium, from 1962. Click a row to fly there with its topographic sheet.</p></div>
        <div class="tiles">
          ${tile("627", "residences around the shared greens of Village Green")}
          ${tile(`${S.dodger_site_acres} ac`, "the Dodger Stadium parcels on Chávez Ravine today (2025 roll)")}
        </div>`,
      afterlife: () => `<h3>Read with the map</h3>
        <div class="tiles">
          ${tile(`${M.standing_by["1946"]}%`, "of today’s buildings already stood in 1946")}
          ${tile(`${M.built_1946_1971_pct}%`, "were built 1946–71, between the parkway plan and Banham")}
          ${tile(`${M.built_since_1974_pct}%`, "were built after the Centers Concept was adopted in 1974")}
          ${tile(M.median_year, `median year built of ${(M.parcels / 1e6).toFixed(1)} million parcels`)}
        </div>
        <div class="mini"><h4>Form and promise, in the essay’s words</h4>
          <div class="verdict"><div>Utopia</div><div>Form</div><div>Promise</div>
            <div class="u" data-ch="pastoral">Pastoral</div><div><q>substantial physical realization</q></div><div><q>remained incomplete</q></div>
            <div class="u" data-ch="autopia">Autopia</div><div><q>realized to a remarkable degree</q></div><div><q>remained compromised</q></div>
            <div class="u" data-ch="centers">Polycentric</div><div><q>partial physical realization</q></div><div><q>largely unrealized</q></div>
            <div class="u" data-ch="coop">Cooperative</div><div><q>geographically limited</q></div><div><q>frequently constrained</q></div>
          </div></div>`,
    };
    document.querySelectorAll(".evid[data-card]").forEach((el) => {
      el.innerHTML = CARDS[el.dataset.card]();
      el.querySelectorAll("[data-orig]").forEach((b) => b.addEventListener("click", () => setOriginal(b.dataset.orig, true)));
      el.querySelectorAll(".row[data-place]").forEach((r) => r.addEventListener("click", () => focusPlace(r.dataset.place)));
    });

    /* chronology interlude */
    const iStats = document.getElementById("int-stats");
    iStats.innerHTML = [[1914, "Llano founded"], [1930, "Olmsted plan"], [1946, "parkway plan"], [1974, "Centers adopted"]]
      .map(([y, t]) => `<div data-year="${y}"><b>${M.standing_by[y]}%</b><span>of today’s buildings stood by ${y} · ${t}</span></div>`).join("");
    iStats.querySelectorAll("[data-year]").forEach((d) => d.addEventListener("click", () => tweenYear(+d.dataset.year, 900)));
    document.getElementById("reg-note").textContent = `1930 plate: ${reg30.control_points} control points, median ${reg30.median_m} m, p90 ${reg30.p90_m} m; 1946 plate: ${reg46.control_points} points, median ${reg46.median_m} m, p90 ${reg46.p90_m} m`;
    document.getElementById("int-n").textContent = `${(M.parcels / 1e6).toFixed(1)} million`;
    const msList = document.getElementById("milestones");
    msList.innerHTML = MILESTONES.map(([y, ch, t]) => `<li data-ch="${ch}" data-year="${y}"><b>${y}</b><span>${t}</span></li>`).join("");
    msList.querySelectorAll("li").forEach((li) => li.addEventListener("click", () => tweenYear(+li.dataset.year, 900)));

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
      halo.clearLayers();
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
