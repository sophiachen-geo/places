/* Mykonos — interactive map of the sites named in the text and research notes.
   Places are grouped into thematic layers; each pin carries a short note. */

(function () {
  "use strict";

  var CATS = {
    town:      { label: "Chora & the town core",        color: "#14304a" },
    coast:     { label: "Harbours, bays & beaches",     color: "#2a6f97" },
    inland:    { label: "Villages & monasteries",       color: "#c1632e" },
    ancient:   { label: "Ancient & fortified sites",    color: "#7a5c3e" },
    landscape: { label: "Capes & heights",              color: "#6a7b53" }
  };

  /* [name, lat, lng, category, note].
     Coordinates for the small town-core sites and a few inland spots are
     approximate; the map is a reading of the text, not a survey. */
  var PLACES = [
    // --- Chora & the town core ---
    ["Chora (Mykonos Town)", 37.4456, 25.3287, "town",
      "The island's only settlement of any size: a labyrinthine white mass on flat ground between two rises."],
    ["Kastro", 37.4452, 25.3253, "town",
      "The earliest medieval core at the northwestern edge. Defence came from the strengthened outer walls of the houses themselves, not a true castle."],
    ["Panagia Paraportiani", 37.4452, 25.3253, "town",
      "The cluster of churches around which the Kastro's open spaces now spread."],
    ["Venetia (Little Venice)", 37.4453, 25.3250, "town",
      "The captains' quarter on the south side of the Kastro, with sea-facing doors said to lead to underground stores for hidden loot."],
    ["Alefkandra", 37.4455, 25.3252, "town",
      "Waterfront edge where the sense of enclosed interior space finally opens to the sea."],
    ["Kato Mili (the Lower Mills)", 37.4441, 25.3266, "town",
      "The southern rise of windmills that milled imported grain into flour, bread and ship's biscuit for foreign fleets."],
    ["Paralia (Old Port waterfront)", 37.4466, 25.3290, "town",
      "The small, north-wind-exposed harbour of Chora, used for loading only in fair weather."],
    ["Matogianni", 37.4459, 25.3284, "town",
      "A newer nineteenth-century neighbourhood with a more orthogonal street grid."],

    // --- Harbours, bays & beaches ---
    ["Tourlos", 37.4560, 25.3312, "coast",
      "The best anchorage for large ships, sheltered from the north winds; boats fled here when the meltemi rose."],
    ["Agios Stefanos", 37.4610, 25.3268, "coast",
      "Bay to the north of Chora that helps frame the western gulf."],
    ["Korfos", 37.4270, 25.3245, "coast",
      "A particularly safe southern anchorage; with Tourlos it gave Chora its central hinge position."],
    ["Ornos", 37.4247, 25.3210, "coast",
      "Anchorage on the southern isthmus, exposed to the rarer but stronger southerly winds."],
    ["Agios Ioannis / Diakoftis (Kanalia)", 37.4180, 25.3150, "coast",
      "Cove on the Diakoftis peninsula used mainly for loading grain during the age of sail and milling."],
    ["Platis Gialos", 37.4104, 25.3436, "coast",
      "A denser concentration of scattered dwellings on the south coast."],
    ["Bay of Panormos", 37.4780, 25.3540, "coast",
      "Northern bay dominated by the height of Palaiokastro."],
    ["Kalo Livadi", 37.4360, 25.3960, "coast",
      "Eastern bay near the core of the Ano Mera rural community."],
    ["Elia", 37.4270, 25.3960, "coast",
      "Bay on the south-eastern coast."],

    // --- Villages & monasteries ---
    ["Ano Mera", 37.4497, 25.3820, "inland",
      "The one true concentration of rural life inland, a second focus of the island's road network."],
    ["Panagia Tourliani Monastery", 37.4494, 25.3806, "inland",
      "The monastery at the heart of Ano Mera."],
    ["Palaiokastro Monastery", 37.4720, 25.3560, "inland",
      "Stands on the fortified height east of Panormos, where the medieval mansion of the Ghizi family once dominated the bay."],
    ["Monastery of Panteleimon", 37.4650, 25.3600, "inland",
      "One of the inland monasteries named among the island's landmarks."],

    // --- Ancient & fortified sites ---
    ["Delos", 37.3936, 25.2686, "ancient",
      "The sacred neighbouring island: for eighteen centuries the Mykonians sold its marble, farmed its land and grazed it, and much of Chora's marble comes from here."],
    ["Rhenia", 37.4030, 25.2400, "ancient",
      "The larger island beside Delos, part of the same archaeological group."],
    ["Palaiokastro (fortified site)", 37.4720, 25.3560, "ancient",
      "The island's second fortified place, an inland height above Panormos with the ruins of the Ghizi palace."],
    ["Towers of Lino", 37.4600, 25.3550, "ancient",
      "Ruins of two Classical-period towers, probably watchtowers, with sections of wall (location approximate)."],

    // --- Capes & heights ---
    ["Cape Armenistis (lighthouse)", 37.4869, 25.3179, "landscape",
      "The northern cape whose lighthouse marks the shipping approach past the island."],
    ["Kouvounas (275 m)", 37.4550, 25.3600, "landscape",
      "One of the island's heights; the footpath network grows denser around such peaks (location approximate)."]
  ];

  function makeIcon(color) {
    return L.divIcon({
      className: "myk-pin",
      html: '<span style="background:' + color + '"></span>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
      popupAnchor: [0, -10]
    });
  }

  function init() {
    var el = document.getElementById("mykonos-map");
    if (!el || typeof L === "undefined") return;

    var map = L.map(el, { scrollWheelZoom: true }).setView([37.44, 25.32], 12);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    var bounds = [];
    PLACES.forEach(function (p) {
      var cat = CATS[p[3]];
      var m = L.marker([p[1], p[2]], { icon: makeIcon(cat.color) }).addTo(map);
      m.bindPopup(
        '<strong>' + p[0] + '</strong>' +
        '<span class="myk-pop-cat" style="color:' + cat.color + '">' + cat.label + '</span>' +
        '<span class="myk-pop-note">' + p[4] + '</span>'
      );
      bounds.push([p[1], p[2]]);
    });

    if (bounds.length) map.fitBounds(bounds, { padding: [40, 40] });

    // Legend
    var legend = L.control({ position: "bottomright" });
    legend.onAdd = function () {
      var div = L.DomUtil.create("div", "myk-legend");
      var html = "<strong>Layers</strong>";
      Object.keys(CATS).forEach(function (k) {
        html += '<div class="lg-row"><span class="lg-sw" style="background:' +
          CATS[k].color + '"></span>' + CATS[k].label + "</div>";
      });
      div.innerHTML = html;
      return div;
    };
    legend.addTo(map);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
