/* The Cyclades Coupled-Systems Explorer.
 * Coordinated multiple views (brushing-and-linking) over ONE shared dataset,
 * keyed on `lithology` + system `type`. Vanilla JS + inline SVG, no build step,
 * no external libraries: the scale-break axis and flow ribbons are hand-rolled.
 * Ships reduced-motion, keyboard, and data-table fallbacks. */

const SVGNS = "http://www.w3.org/2000/svg";
const $ = (s) => document.querySelector(s);
function svg(tag, attrs = {}, kids = []) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  (Array.isArray(kids) ? kids : [kids]).forEach((c) => c != null && e.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
  return e;
}
const LITH_COLOR = { metamorphic: "#2a6f97", granitic: "#b08a4f", volcanic: "#b5413b" };
const LITH_LABEL = { metamorphic: "Metamorphic", granitic: "Granitic", volcanic: "Volcanic" };

/* ---------------- shared state (single source of truth) ---------------- */
const state = { lithology: "all", island: "syros", hover: null, tourStep: 0, tourActive: true, reduce: false };
const subs = [];
function subscribe(fn) { subs.push(fn); }
function setState(patch) { Object.assign(state, patch); subs.forEach((fn) => fn(state)); }

let ISLANDS, STRATA, SUB, SYSTEMS, TEX;
let islandById = {}, stratumById = {};

/* ---------------- textures / patterns ---------------- */
function buildDefs() {
  const defs = svg("defs");
  const hatch = (id, color, content) => {
    const p = svg("pattern", { id, patternUnits: "userSpaceOnUse", width: 6, height: 6 });
    p.appendChild(svg("rect", { width: 6, height: 6, fill: color, "fill-opacity": 0.16 }));
    content(p, color);
    return p;
  };
  defs.appendChild(hatch("pat-metamorphic", LITH_COLOR.metamorphic, (p, c) =>
    p.appendChild(svg("path", { d: "M0,6 L6,0 M-1,1 L1,-1 M5,7 L7,5", stroke: c, "stroke-width": 0.8, "stroke-opacity": 0.7 }))));
  defs.appendChild(hatch("pat-granitic", LITH_COLOR.granitic, (p, c) => {
    p.appendChild(svg("circle", { cx: 1.5, cy: 1.5, r: 0.9, fill: c, "fill-opacity": 0.75 }));
    p.appendChild(svg("circle", { cx: 4.5, cy: 4.5, r: 0.9, fill: c, "fill-opacity": 0.75 }));
  }));
  defs.appendChild(hatch("pat-volcanic", LITH_COLOR.volcanic, (p, c) =>
    p.appendChild(svg("path", { d: "M0,0 L6,6 M6,0 L0,6", stroke: c, "stroke-width": 0.7, "stroke-opacity": 0.6 }))));
  const neu = svg("pattern", { id: "pat-neutral", patternUnits: "userSpaceOnUse", width: 5, height: 5 });
  neu.appendChild(svg("rect", { width: 5, height: 5, fill: "#9aa3ab", "fill-opacity": 0.10 }));
  neu.appendChild(svg("circle", { cx: 1, cy: 1, r: 0.6, fill: "#7c8791", "fill-opacity": 0.5 }));
  defs.appendChild(neu);
  // real photo slots (when manifest src is set)
  (TEX.slots || []).forEach((s) => {
    if (!s.src) return;
    const p = svg("pattern", { id: "img-" + s.id, patternContentUnits: "objectBoundingBox", width: 1, height: 1 });
    p.appendChild(svg("image", { href: s.src, width: 1, height: 1, preserveAspectRatio: s.fit === "meet" ? "xMidYMid meet" : "xMidYMid slice" }));
    defs.appendChild(p);
  });
  return defs;
}
function slotSrc(id) { const s = (TEX.slots || []).find((x) => x.id === id); return s && s.src; }
function fillFor(slotId, lith) {
  if (slotId && slotSrc(slotId)) return `url(#img-${slotId})`;
  if (lith && LITH_COLOR[lith]) return `url(#pat-${lith})`;
  return "url(#pat-neutral)";
}
function attachDefs(el) { el.appendChild(buildDefs()); }

/* ---------------- scale-break vertical axis ---------------- */
function scaleY(subId, v) {
  const s = SUB[subId];
  const [d0, d1] = s.domain, [b0, b1] = s.band;
  return (b0 + ((v - d0) / (d1 - d0)) * (b1 - b0)) * 100;
}

/* ---------------- MAP (horizontal schematic) ---------------- */
function renderMap() {
  const el = $("#map-svg"); el.innerHTML = ""; attachDefs(el);
  const zones = [
    { lith: "metamorphic", x: 5, w: 37 }, { lith: "granitic", x: 45, w: 21 }, { lith: "volcanic", x: 69, w: 26 },
  ];
  zones.forEach((z) => {
    const active = state.lithology === "all" || state.lithology === z.lith;
    el.appendChild(svg("rect", { x: z.x, y: 4, width: z.w, height: 66, rx: 3, fill: LITH_COLOR[z.lith], "fill-opacity": active ? 0.06 : 0.02, stroke: LITH_COLOR[z.lith], "stroke-opacity": active ? 0.35 : 0.12, "stroke-dasharray": "1.5 1.5" }));
    el.appendChild(svg("text", { x: z.x + z.w / 2, y: 10, "text-anchor": "middle", class: "zone-label", "fill-opacity": active ? 0.8 : 0.3 }, LITH_LABEL[z.lith]));
  });
  ISLANDS.forEach((isl) => {
    const r = Math.sqrt(isl.areaKm2) / 2.4;
    const on = state.lithology === "all" || state.lithology === isl.lithology;
    const g = svg("g", { class: "island", "data-id": isl.id, tabindex: 0, role: "button",
      "aria-label": `${isl.name}: ${isl.lithology}, ${isl.areaKm2} km², water from ${isl.waterSource.join(", ")}`,
      opacity: on ? 1 : 0.22 });
    g.appendChild(svg("circle", { cx: isl.x, cy: isl.y, r, fill: fillFor(isl.textureSlot, isl.lithology), stroke: LITH_COLOR[isl.lithology], "stroke-width": isl.id === state.island ? 1.6 : 0.8, class: "island-shape" }));
    g.appendChild(svg("text", { x: isl.x, y: isl.y + r + 3.4, "text-anchor": "middle", class: "island-label" }, isl.name));
    el.appendChild(g);
  });
}

/* ---------------- CROSS-SECTION (vertical, scale-break) ---------------- */
function renderSection() {
  const el = $("#section-svg"); el.innerHTML = ""; attachDefs(el);
  const isl = islandById[state.island];
  const LX = 26, RX = 97;
  // sub-scale bands + axis labels + seams
  const order = ["atmosphere", "depth", "crust", "deeptime"];
  order.forEach((id, i) => {
    const s = SUB[id]; const y0 = s.band[0] * 100, y1 = s.band[1] * 100;
    el.appendChild(svg("rect", { x: LX, y: y0, width: RX - LX, height: y1 - y0, fill: "#ffffff", "fill-opacity": 0.5, stroke: "#e3d9c8", "stroke-width": 0.3 }));
    el.appendChild(svg("text", { x: 2, y: y0 + 3, class: "axis-unit", "data-idx": i }, s.label));
    el.appendChild(svg("text", { x: 24, y: y0 + 3, class: "axis-tick", "text-anchor": "end" }, String(s.domain[0])));
    el.appendChild(svg("text", { x: 24, y: y1 - 0.5, class: "axis-tick", "text-anchor": "end" }, String(s.domain[1])));
    if (i < order.length - 1) {
      const ny = SUB[order[i + 1]].band[0] * 100; const my = (y1 + ny) / 2;
      let d = `M${LX},${my}`; for (let x = LX; x <= RX; x += 3) d += ` L${x + 1.5},${my - 1.1} L${x + 3},${my}`;
      el.appendChild(svg("path", { d, class: "seam", fill: "none" }));
    }
  });
  // strata that apply to this island's lithology
  const strat = STRATA.filter((s) => s.appliesTo.includes("*") || s.appliesTo.includes(isl.lithology));
  strat.forEach((s) => {
    const ya = scaleY(s.subscale, s.from), yb = scaleY(s.subscale, s.to);
    const y = Math.min(ya, yb), h = Math.max(1.3, Math.abs(yb - ya));
    const lith = s.appliesTo.includes("*") ? null : (s.appliesTo[0]);
    const g = svg("g", { class: "stratum", "data-id": s.id, tabindex: 0, role: "button", "aria-label": `${s.label}: ${s.note}` });
    g.appendChild(svg("rect", { x: LX, y, width: RX - LX, height: h, fill: fillFor(s.textureSlot, lith), stroke: lith ? LITH_COLOR[lith] : "#b9c0c6", "stroke-width": 0.4, class: "stratum-shape" }));
    if (h > 3.2) g.appendChild(svg("text", { x: LX + 2, y: y + Math.min(h - 1.4, 4), class: "stratum-label" }, s.label));
    // placeholder slot id (only when no real photo yet)
    if (s.textureSlot && !slotSrc(s.textureSlot) && h > 6) g.appendChild(svg("text", { x: RX - 1, y: y + h - 1.4, "text-anchor": "end", class: "slot-tag" }, `▢ ${s.textureSlot}`));
    el.appendChild(g);
  });
  el.appendChild(svg("text", { x: (LX + RX) / 2, y: 100, "text-anchor": "middle", class: "section-title" }, `${isl.name} · ${LITH_LABEL[isl.lithology]}`));
}

/* ---------------- CAUSAL (master flow + feedback loop) ---------------- */
function nodeType(id) { return (SYSTEMS.nodes[id] || {}).type; }
function edgeInto(id) { return SYSTEMS.edges.find((e) => e.target === id); }

function renderCausal() {
  const el = $("#causal-svg"); el.innerHTML = "";
  const isl = islandById[state.island];
  const chain = SYSTEMS.chains[isl.lithology] || SYSTEMS.chains.granitic;
  const TC = SYSTEMS.typeColors;
  const NW = 15, NH = 8;
  // master chain row
  const n = chain.length, gap = (100 - NW) / Math.max(1, n - 1);
  const cx = (i) => (n === 1 ? 50 : 4 + i * ((92 - NW) / (n - 1)));
  const cy = 12;
  el.appendChild(svg("text", { x: 2, y: 4, class: "causal-cap" }, `Master chain · ${LITH_LABEL[isl.lithology]}`));
  for (let i = 0; i < n - 1; i++) {
    const x1 = cx(i) + NW, x2 = cx(i + 1);
    el.appendChild(svg("path", { d: `M${x1},${cy + NH / 2} C${(x1 + x2) / 2},${cy + NH / 2} ${(x1 + x2) / 2},${cy + NH / 2} ${x2},${cy + NH / 2}`, class: "ribbon", "marker-end": "url(#arrow)", fill: "none" }));
  }
  chain.forEach((id, i) => causalNode(el, id, cx(i), cy, NW, NH, TC));
  // feedback loop
  el.appendChild(svg("text", { x: 2, y: 32, class: "causal-cap" }, "Dominant feedback loop"));
  const loop = SYSTEMS.loop, L = loop.length;
  const ccx = 50, ccy = 46, rx = 40, ry = 12;
  const lx = (i) => ccx + rx * Math.cos(-Math.PI / 2 + (i / L) * 2 * Math.PI);
  const ly = (i) => ccy + ry * Math.sin(-Math.PI / 2 + (i / L) * 2 * Math.PI);
  for (let i = 0; i < L; i++) {
    const a = i, b = (i + 1) % L;
    el.appendChild(svg("path", { d: `M${lx(a)},${ly(a)} Q${ccx},${ccy} ${lx(b)},${ly(b)}`, class: "loop-edge", "marker-end": "url(#arrow-bold)", fill: "none" }));
  }
  loop.forEach((id, i) => causalNode(el, id, lx(i) - NW / 2, ly(i) - NH / 2, NW, NH, TC, true));
  // arrow markers
  const defs = svg("defs");
  ["arrow", "arrow-bold"].forEach((id, k) => {
    const m = svg("marker", { id, markerWidth: 6, markerHeight: 6, refX: 4.5, refY: 2, orient: "auto", markerUnits: "strokeWidth" });
    m.appendChild(svg("path", { d: "M0,0 L5,2 L0,4 Z", fill: k ? "#c1632e" : "#8a949e" }));
    defs.appendChild(m);
  });
  el.appendChild(defs);
}
function causalNode(el, id, x, y, w, h, TC, loop) {
  const nd = SYSTEMS.nodes[id]; if (!nd) return;
  const g = svg("g", { class: "cnode" + (loop ? " cnode-loop" : ""), "data-id": id, tabindex: 0, role: "button", "aria-label": nd.label });
  g.appendChild(svg("rect", { x, y, width: w, height: h, rx: 2, fill: TC[nd.type] || "#888", "fill-opacity": 0.9, stroke: "#fff", "stroke-width": 0.6 }));
  const words = nd.label.split(" "); const mid = Math.ceil(words.length / 2);
  const l1 = words.slice(0, mid).join(" "), l2 = words.slice(mid).join(" ");
  g.appendChild(svg("text", { x: x + w / 2, y: y + (l2 ? h / 2 - 0.6 : h / 2 + 1.4), "text-anchor": "middle", class: "cnode-label" }, l1));
  if (l2) g.appendChild(svg("text", { x: x + w / 2, y: y + h / 2 + 2.6, "text-anchor": "middle", class: "cnode-label" }, l2));
  el.appendChild(g);
}

/* ---------------- brushing-and-linking ---------------- */
function highlightSets(hover) {
  const S = { islands: new Set(), strata: new Set(), nodes: new Set() };
  if (!hover) return null;
  if (hover.kind === "island") {
    const isl = islandById[hover.id]; if (!isl) return null;
    S.islands.add(isl.id);
    STRATA.forEach((s) => { if (!s.appliesTo.includes("*") && s.appliesTo.includes(isl.lithology)) S.strata.add(s.id); });
    Object.keys(SYSTEMS.nodes).forEach((k) => {
      const nn = SYSTEMS.nodes[k];
      if ((nn.linksTo && nn.linksTo.lithology === isl.lithology) || (nn.hazardKey && isl.hazards.includes(nn.hazardKey))) S.nodes.add(k);
    });
  } else if (hover.kind === "stratum") {
    const st = stratumById[hover.id]; if (!st) return null;
    S.strata.add(st.id);
    const lith = st.appliesTo.includes("*") ? null : st.appliesTo[0];
    if (lith) ISLANDS.forEach((i) => i.lithology === lith && S.islands.add(i.id));
    Object.keys(SYSTEMS.nodes).forEach((k) => { const nn = SYSTEMS.nodes[k]; if (nn.linksTo && nn.linksTo.stratum === st.id) S.nodes.add(k); });
  } else if (hover.kind === "node") {
    const nn = SYSTEMS.nodes[hover.id]; if (!nn) return null;
    S.nodes.add(hover.id);
    if (nn.linksTo && nn.linksTo.lithology) { ISLANDS.forEach((i) => i.lithology === nn.linksTo.lithology && S.islands.add(i.id));
      STRATA.forEach((s) => { if (!s.appliesTo.includes("*") && s.appliesTo.includes(nn.linksTo.lithology)) S.strata.add(s.id); }); }
    if (nn.linksTo && nn.linksTo.stratum) S.strata.add(nn.linksTo.stratum);
    if (nn.hazardKey) ISLANDS.forEach((i) => i.hazards.includes(nn.hazardKey) && S.islands.add(i.id));
  }
  return S;
}
function applyHighlight() {
  const S = highlightSets(state.hover);
  const mark = (sel, setName) => document.querySelectorAll(sel).forEach((n) => {
    if (!S) { n.classList.remove("is-hi", "is-dim"); return; }
    const on = S[setName].has(n.getAttribute("data-id"));
    n.classList.toggle("is-hi", on); n.classList.toggle("is-dim", !on);
  });
  mark("#map-svg .island", "islands");
  mark("#section-svg .stratum", "strata");
  mark("#causal-svg .cnode", "nodes");
  drawLinks(S);
  // mechanism readout
  if (state.hover && state.hover.kind === "node") {
    const e = edgeInto(state.hover.id);
    $("#mech").textContent = e ? `${SYSTEMS.nodes[e.source].label} ${e.relation} → ${SYSTEMS.nodes[e.target].label}  ·  ${e.mechanism} → ${e.effect}` : SYSTEMS.nodes[state.hover.id].label;
  }
}
/* explicit connecting cue across panels (link layer) */
function centerOf(node) { if (!node) return null; const r = node.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }
function drawLinks(S) {
  const layer = $("#link-layer"); layer.innerHTML = "";
  if (!S || state.reduce || !state.hover) return;
  layer.setAttribute("viewBox", `0 0 ${window.innerWidth} ${window.innerHeight}`);
  layer.setAttribute("width", window.innerWidth); layer.setAttribute("height", window.innerHeight);
  const srcSel = state.hover.kind === "island" ? `#map-svg .island[data-id="${state.hover.id}"]`
    : state.hover.kind === "stratum" ? `#section-svg .stratum[data-id="${state.hover.id}"]`
    : `#causal-svg .cnode[data-id="${state.hover.id}"]`;
  const src = centerOf($(srcSel)); if (!src) return;
  const targets = [];
  S.strata.forEach((id) => { if (!(state.hover.kind === "stratum" && id === state.hover.id)) targets.push(`#section-svg .stratum[data-id="${id}"]`); });
  S.nodes.forEach((id) => { if (!(state.hover.kind === "node" && id === state.hover.id)) targets.push(`#causal-svg .cnode[data-id="${id}"]`); });
  if (state.hover.kind !== "island") S.islands.forEach((id) => targets.push(`#map-svg .island[data-id="${id}"]`));
  targets.slice(0, 4).forEach((sel) => {
    const t = centerOf($(sel)); if (!t) return;
    layer.appendChild(svg("path", { d: `M${src.x},${src.y} C${(src.x + t.x) / 2},${src.y} ${(src.x + t.x) / 2},${t.y} ${t.x},${t.y}`, class: "link-cue", fill: "none" }));
  });
}

/* ---------------- legend + data tables ---------------- */
function renderLegend() {
  const el = $("#legend"); el.innerHTML = "";
  const box = (title, items) => {
    const d = document.createElement("div"); d.className = "legend-box";
    d.innerHTML = `<h4>${title}</h4>` + items.map((i) => `<span class="lg-item"><span class="lg-sw" style="background:${i.c}"></span>${i.l}</span>`).join("");
    return d;
  };
  el.appendChild(box("Lithology", Object.keys(LITH_COLOR).map((k) => ({ c: LITH_COLOR[k], l: LITH_LABEL[k] }))));
  el.appendChild(box("System type (causal)", Object.keys(SYSTEMS.typeColors).map((k) => ({ c: SYSTEMS.typeColors[k], l: k }))));
}
function renderDetails() {
  const isl = ISLANDS.map((i) => `<tr><th scope="row">${i.name}</th><td>${i.lithology}</td><td>${i.areaKm2}</td><td>${i.population.toLocaleString()}</td><td>${i.waterSource.join(", ")}</td><td>${i.hazards.join(", ")}</td></tr>`).join("");
  const str = STRATA.map((s) => `<tr><th scope="row">${s.label}</th><td>${s.regime}</td><td>${s.from}→${s.to} ${SUB[s.subscale].unit}</td><td>${s.appliesTo.join(", ")}</td><td>${s.note}</td></tr>`).join("");
  $("#data-tables").innerHTML =
    `<h4>Islands</h4><table><thead><tr><th>Island</th><th>Lithology</th><th>Area km²</th><th>Pop.</th><th>Water source</th><th>Hazards</th></tr></thead><tbody>${isl}</tbody></table>` +
    `<h4>Strata</h4><table><thead><tr><th>Stratum</th><th>Regime</th><th>Extent</th><th>Applies to</th><th>Mechanism</th></tr></thead><tbody>${str}</tbody></table>`;
}

/* ---------------- interaction wiring ---------------- */
function wire() {
  const hoverFrom = (e, kind) => { const g = e.target.closest(`[data-id]`); if (g && g.parentNode.closest) setState({ hover: { kind, id: g.getAttribute("data-id") } }); };
  const clear = () => setState({ hover: null });
  $("#map-svg").addEventListener("mouseover", (e) => { const g = e.target.closest(".island"); if (g) setState({ hover: { kind: "island", id: g.dataset.id } }); });
  $("#map-svg").addEventListener("mouseout", clear);
  $("#map-svg").addEventListener("focusin", (e) => { const g = e.target.closest(".island"); if (g) setState({ hover: { kind: "island", id: g.dataset.id } }); });
  $("#map-svg").addEventListener("click", (e) => { const g = e.target.closest(".island"); if (g) setState({ island: g.dataset.id }); });
  $("#map-svg").addEventListener("keydown", (e) => { const g = e.target.closest(".island"); if (g && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); setState({ island: g.dataset.id }); } });

  const sec = $("#section-svg");
  sec.addEventListener("mouseover", (e) => { const g = e.target.closest(".stratum"); if (g) setState({ hover: { kind: "stratum", id: g.dataset.id } }); });
  sec.addEventListener("mouseout", clear);
  sec.addEventListener("focusin", (e) => { const g = e.target.closest(".stratum"); if (g) setState({ hover: { kind: "stratum", id: g.dataset.id } }); });

  const cau = $("#causal-svg");
  const nodeHover = (e) => { const g = e.target.closest(".cnode"); if (g) setState({ hover: { kind: "node", id: g.dataset.id } }); };
  cau.addEventListener("mouseover", nodeHover);
  cau.addEventListener("mouseout", clear);
  cau.addEventListener("focusin", nodeHover);

  document.querySelectorAll(".seg-btn").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".seg-btn").forEach((x) => x.classList.remove("is-active"));
    b.classList.add("is-active");
    const lith = b.dataset.lith;
    let island = state.island;
    if (lith !== "all" && islandById[island].lithology !== lith) island = ISLANDS.find((i) => i.lithology === lith).id;
    setState({ lithology: lith, island });
  }));

  const mt = $("#motion-toggle");
  mt.addEventListener("change", () => { setState({ reduce: mt.checked }); document.body.classList.toggle("reduce-motion", mt.checked); });

  window.addEventListener("resize", () => drawLinks(highlightSets(state.hover)));
}

/* ---------------- guided tour (guided → free) ---------------- */
const TOUR = [
  { t: "Two islands, one question", x: "Syros and Mykonos are neighbours of almost the same size — yet one catches rain and one must desalinate. Why? The answer is in the rock.", s: { island: "syros", lithology: "all", hover: null } },
  { t: "Mykonos is granite", x: "Select Mykonos. Its bedrock is a granite pluton — and granite has a fatal flaw for a dry island.", s: { island: "mykonos", lithology: "all", hover: { kind: "node", id: "granite" } } },
  { t: "Granite → grus", x: "Granite weathers grain-by-grain into 'grus' — a permeable sand. Rain sinks straight through instead of running into cisterns.", s: { island: "mykonos", hover: { kind: "node", id: "grus" } } },
  { t: "…→ desalination → energy", x: "Poor capture forces desalination, which is energy-hungry. Water security becomes energy fragility. Follow the master chain.", s: { island: "mykonos", hover: { kind: "node", id: "desal" } } },
  { t: "Syros holds its water", x: "Now Syros: impermeable blueschist retains surface water for cisterns and modest springs — less desalination, but faults bring seismic and slope hazard.", s: { island: "syros", hover: { kind: "node", id: "blueschist" } } },
  { t: "The loop that ties it together", x: "Tourism spikes summer demand → more desalination → more emissions → warming & drying → more pressure. Watch the bold feedback loop.", s: { island: "mykonos", hover: { kind: "node", id: "desal" } } },
  { t: "Now explore freely", x: "Filter by lithology, brush any island, stratum, or node — each lights up its partners in the other views. A data table sits below for full detail.", s: { hover: null } },
];
function renderTour() {
  const tour = $("#tour");
  if (!state.tourActive) { tour.hidden = true; $("#controls").classList.add("free"); return; }
  const step = TOUR[state.tourStep];
  $("#tour-step").textContent = `${state.tourStep + 1} / ${TOUR.length}`;
  $("#tour-title").textContent = step.t;
  $("#tour-text").textContent = step.x;
  $("#tour-prev").disabled = state.tourStep === 0;
  $("#tour-next").textContent = state.tourStep === TOUR.length - 1 ? "Finish" : "Next ›";
}
function gotoStep(i) {
  if (i < 0) return;
  if (i >= TOUR.length) { setState({ tourActive: false, hover: null }); return; }
  const step = TOUR[i];
  // reflect the step's lithology on the segmented control
  const lith = step.s.lithology || state.lithology;
  document.querySelectorAll(".seg-btn").forEach((x) => x.classList.toggle("is-active", x.dataset.lith === lith));
  setState(Object.assign({ tourStep: i, lithology: lith }, step.s));
}

/* ---------------- boot ---------------- */
async function init() {
  const base = "data/";
  [ISLANDS, STRATA, SYSTEMS, TEX] = await Promise.all([
    fetch(base + "islands.json").then((r) => r.json()).then((d) => d.islands),
    fetch(base + "strata.json").then((r) => r.json()),
    fetch(base + "systems.json").then((r) => r.json()),
    fetch(base + "textures.json").then((r) => r.json()),
  ]);
  const strataDoc = STRATA;
  SUB = {}; strataDoc.subscales.forEach((s) => (SUB[s.id] = s));
  STRATA = strataDoc.strata;
  ISLANDS.forEach((i) => (islandById[i.id] = i));
  STRATA.forEach((s) => (stratumById[s.id] = s));

  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    state.reduce = true; document.body.classList.add("reduce-motion"); $("#motion-toggle").checked = true;
  }

  subscribe(renderMap); subscribe(renderSection); subscribe(renderCausal);
  subscribe(applyHighlight); subscribe(renderTour);

  renderMap(); renderSection(); renderCausal(); renderLegend(); renderDetails(); renderTour();
  wire();
  $("#tour-next").addEventListener("click", () => gotoStep(state.tourStep + 1));
  $("#tour-prev").addEventListener("click", () => gotoStep(state.tourStep - 1));
  $("#tour-skip").addEventListener("click", () => setState({ tourActive: false, hover: null }));
  gotoStep(0);
}
document.addEventListener("DOMContentLoaded", init);
