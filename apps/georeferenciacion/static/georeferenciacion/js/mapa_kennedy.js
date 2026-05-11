// static/georeferenciacion/js/mapa_kennedy.js

// =====================
// Config API
// =====================
const APP_PREFIX = "/geo";
const API = {
  lugares: `${APP_PREFIX}/api/lugares`,
  crearLugar: `${APP_PREFIX}/api/lugares/crear`,
  estadisticas: `${APP_PREFIX}/api/estadisticas`,
  choropleth: `${APP_PREFIX}/api/choropleth`,
  lugaresCSV: `${APP_PREFIX}/api/lugares.csv`,
  // Capas de polígonos: apuntan a los endpoints que leen GeoJSON del disco.
  // Los endpoints originales (/api/barrios, /api/upz, /api/localidad/kennedy)
  // dependen de GeoDjango no instalado y devuelven FeatureCollection vacío.
  // Los /api/kennedy/* son fuente canónica mientras esa deuda no se cierre.
  barrios: `${APP_PREFIX}/api/kennedy/barrios/`,
  upz: `${APP_PREFIX}/api/kennedy/upz/`,
  localidad: (cod) => `${APP_PREFIX}/api/localidad/${cod}/`,
  localidadKennedy: `${APP_PREFIX}/api/kennedy/contorno/`,
  parques: `${APP_PREFIX}/api/kennedy/parques/`,
  escuelas: `${APP_PREFIX}/api/kennedy/escuelas/`,
};

// =====================
// CSRF
// =====================
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
}
const CSRF_TOKEN = getCookie("csrftoken");

// =====================
// Helpers UI
// =====================
function getBadgeClass(t) {
  return t === "deporte"
    ? "bg-success"
    : t === "cultura"
    ? "bg-primary"
    : t === "educacion"
    ? "bg-warning"
    : "bg-secondary";
}

function setKPI(id, val) {
  const v = String(val ?? 0);
  document.querySelectorAll('#' + id).forEach((el) => {
    el.textContent = v;
  });
}

function buildQuery() {
  const ids = (id) => document.getElementById(id);
  const pick = (sel) =>
    sel ? [...sel.selectedOptions].map((o) => o.value).filter(Boolean) : [];

  const upz = pick(ids("f-upz"));
  const barrio = pick(ids("f-barrio"));
  const tipo = pick(ids("f-tipo"));
  const subg = pick(ids("f-subgrupo"));
  const q = (ids("q")?.value || "").trim();

  const p = new URLSearchParams();
  upz.forEach((v) => p.append("upz", v));
  barrio.forEach((v) => p.append("barrio", v));
  tipo.forEach((v) => p.append("tipo", v));
  subg.forEach((v) => p.append("subgrupo", v)); // backend puede mapear sub1/sub2/...
  if (q) p.set("q", q);

  return p.toString();
}

// ==========================
//  Inicializador
// ==========================
function initKennedy() {
  if (window.__kennedyInited) return;
  window.__kennedyInited = true;

  // ===== Mapa base =====
  const map = L.map("map").setView([4.626, -74.17], 12);

  L.tileLayer("https://tile.openstreetmap.bzh/br/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
    crossOrigin: true,
  }).addTo(map);

  // Dibujo
  const drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);
  map.addControl(
    new L.Control.Draw({
      draw: {
        polygon: true,
        rectangle: true,
        polyline: false,
        circle: false,
        marker: false,
        circlemarker: false,
      },
      edit: { featureGroup: drawnItems },
    })
  );

  let cluster = L.markerClusterGroup();
  let heatLayer = null;
  let addMode = false;
  let tempMarker = null;
  let currentMarkers = [];

  // ---------- Tabla ----------
  function getTableBodyEl() {
    // Soporta ambos ids (según el template que tengas cargado)
    return (
      document.getElementById("tbody-lugares") ||
      document.getElementById("tbody-demo")
    );
  }

  function renderTableFromFeatures(features) {
    const tbody = getTableBodyEl();
    if (!tbody) return;

    const rows = features.map((f, i) => {
      const p = f.properties || {};
      const [lon, lat] = Array.isArray(f.geometry?.coordinates)
        ? f.geometry.coordinates
        : [null, null];

      const nombre = p.nombre || p.nombre_punto || "—";
      const dir = p.direccion || p.direccion_texto || p.formatted_address || "—";
      const upz = p.upz_nombre || p.upz || "—";
      const barrio = p.barrio_nombre || p.barrio || "—";
      const tipo = p.tipo || "otro";
      const coord =
        typeof lat === "number" && typeof lon === "number"
          ? `${lat.toFixed(6)}, ${lon.toFixed(6)}`
          : "—";

      return `
        <tr>
          <td>${i + 1}</td>
          <td>${nombre}</td>
          <td>${dir}</td>
          <td>${upz}</td>
          <td>${barrio}</td>
          <td><span class="badge ${getBadgeClass(tipo)}">${String(
        tipo
      ).toUpperCase()}</span></td>
          <td>${coord}</td>
        </tr>`;
    });

    tbody.innerHTML = rows.join("") || `
      <tr><td colspan="7" class="text-center text-muted">Sin resultados.</td></tr>
    `;

    const countEl = document.getElementById("tabla-count");
    if (countEl) {
      countEl.textContent = "Mostrando " + features.length + " registros";
    }
  }

  // ---------- Mapa ----------
  function renderMapFromFeatures(features) {
    const total = features.length;
    setKPI("kpi-total", total);
    setKPI("total-lugares", total);
    setKPI("kpi-hoy", Math.floor(total * 0.05));
    setKPI("kpi-pend", Math.floor(total * 0.03));

    if (cluster) map.removeLayer(cluster);
    if (heatLayer) map.removeLayer(heatLayer);
    cluster = L.markerClusterGroup();
    currentMarkers = [];
    const heat = [];

    features.forEach((f) => {
      if (!f?.geometry?.coordinates || f.geometry.coordinates.length < 2) return;
      const [lon, lat] = f.geometry.coordinates;
      if (typeof lat !== "number" || typeof lon !== "number") return;

      heat.push([lat, lon, 0.7]);
      const p = f.properties || {};
      const html = `
        <div class="marker-popup">
          <h6>${p.nombre || p.nombre_punto || ""}</h6>
          <div><strong>Dirección:</strong> ${p.direccion || p.direccion_texto || p.formatted_address || ""}</div>
          <div><strong>UPZ:</strong> ${p.upz_nombre || p.upz || ""}</div>
          <div><strong>Barrio:</strong> ${p.barrio_nombre || p.barrio || ""}</div>
          <div><strong>Tipo:</strong> <span class="badge ${getBadgeClass(
            p.tipo
          )}">${(p.tipo || "").toUpperCase()}</span></div>
          <div><strong>Coordenadas:</strong> ${lat.toFixed(6)}, ${lon.toFixed(6)}</div>
        </div>`;
      const m = L.marker([lat, lon]).bindPopup(html);
      cluster.addLayer(m);
      currentMarkers.push(m);
    });

    // Capa "Lugares (históricos)" eliminada del UI por solicitud (era
    // duplicado de Escuelas Cultura). El cluster se sigue construyendo
    // internamente porque los KPIs (total, hoy, pendientes) dependen de
    // `features.length`, pero ya no se agrega al mapa.
    if (currentMarkers.length) {
      try {
        map.fitBounds(cluster.getBounds(), { padding: [20, 20] });
      } catch {}
    }

    // heat (solo si el toggle está activo)
    const heatToggle = document.getElementById("heatmap-toggle");
    const wantsHeat = !!heatToggle?.checked;
    if (wantsHeat && heat.length) {
      heatLayer = L.heatLayer(heat, { radius: 20, blur: 15 });
      map.addLayer(heatLayer);
    } else {
      heatLayer = null;
    }
  }

  async function updateKPIsFromAPI() {
    try {
      const qs = buildQuery();
      const url = `${API.estadisticas}${qs ? `?${qs}` : ""}`;
      const res = await fetch(url, { credentials: "include" });
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) return;
      const j = await res.json();
      setKPI("kpi-total", j.total ?? 0);
      setKPI("total-lugares", j.total ?? 0);
      setKPI("kpi-hoy", j.actualizados_hoy ?? 0);
      setKPI("kpi-pend", j.pendientes ?? 0);
    } catch {}
  }

  async function cargar() {
    try {
      const qs = buildQuery();
      const url = `${API.lugares}${qs ? `?${qs}` : ""}`;
      const res = await fetch(url, { credentials: "include" });
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        const txt = await res.text();
        console.error("[kennedy] /lugares no JSON", res.status, txt.slice(0, 300));
        alert("La API de lugares no devolvió JSON. Revisa autenticación.");
        return;
      }
      const geo = await res.json();
      const features = Array.isArray(geo?.features) ? geo.features : [];
      renderMapFromFeatures(features);
      renderTableFromFeatures(features);
      updateKPIsFromAPI();
    } catch (e) {
      console.error("Error cargando lugares:", e);
      alert("No se pudieron cargar los lugares.");
    }
  }

  window.cargar = cargar;

  // ---------- Filtros ----------
  document.getElementById("btn-aplicar")?.addEventListener("click", () => {
    cargar();
    refreshBarriosPolygons({ fit: false });
  });

  document.getElementById("btn-limpiar")?.addEventListener("click", () => {
    document.querySelectorAll(".sidebar select").forEach((s) => (s.selectedIndex = -1));
    const q = document.getElementById("q");
    if (q) q.value = "";
    cargar();
    refreshBarriosPolygons({ fit: false });
  });

  // Dependencia barrio (modal)
  document.getElementById("f-upz-new")?.addEventListener("change", () => {
    const upzSel = document.getElementById("f-upz-new").value;
    const $b = document.getElementById("f-barrio-new");
    if (!$b) return;
    [...$b.options].forEach((o) => {
      if (!o.value) {
        o.hidden = false;
        return;
      }
      const u = o.getAttribute("data-upz") || "";
      o.hidden = upzSel && u && u !== upzSel;
    });
    if ($b.selectedOptions[0] && $b.selectedOptions[0].hidden) $b.value = "";
  });

  // Controles extra
  document.getElementById("zoom-in")?.addEventListener("click", () => map.zoomIn());
  document.getElementById("zoom-out")?.addEventListener("click", () => map.zoomOut());

  // heatmap toggle
  document.getElementById("heatmap-toggle")?.addEventListener("change", () => {
    cargar(); // recarga y aplica el estado del heatmap
  });

  // Agregar lugar
  const posRel = document.querySelector(".position-relative");
  if (posRel) {
    const btnAdd = document.createElement("button");
    btnAdd.id = "btn-agregar";
    btnAdd.className = "btn btn-success btn-sm position-absolute";
    btnAdd.style.top = "10px";
    btnAdd.style.left = "60px";
    btnAdd.textContent = "Agregar lugar";
    posRel.appendChild(btnAdd);
    btnAdd.addEventListener("click", () => {
      addMode = !addMode;
      btnAdd.classList.toggle("btn-outline-success", !addMode);
      btnAdd.classList.toggle("btn-success", addMode);
    });
  }

  map.on("click", (ev) => {
    if (!addMode) return;
    const { lat, lng } = ev.latlng;
    if (tempMarker) map.removeLayer(tempMarker);
    tempMarker = L.marker([lat, lng]).addTo(map).bindPopup("Nueva ubicación").openPopup();
    const latEl = document.getElementById("f-lat");
    const lonEl = document.getElementById("f-lon");
    if (latEl) latEl.value = lat.toFixed(6);
    if (lonEl) lonEl.value = lng.toFixed(6);
    const modalEl = document.getElementById("modalLugar");
    if (modalEl) new bootstrap.Modal(modalEl).show();
  });

  document.getElementById("form-lugar")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      nombre: document.getElementById("f-nombre").value.trim(),
      direccion: document.getElementById("f-direccion").value.trim(),
      upz_codigo: document.getElementById("f-upz-new").value || null,
      barrio_codigo: document.getElementById("f-barrio-new").value || null,
      tipo: document.getElementById("f-tipo-new").value || "otro",
      latitud: parseFloat(document.getElementById("f-lat").value),
      longitud: parseFloat(document.getElementById("f-lon").value),
      desc: document.getElementById("f-desc").value.trim(),
    };

    try {
      const res = await fetch(API.crearLugar, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": CSRF_TOKEN,
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      const ct = res.headers.get("content-type") || "";
      const j = ct.includes("application/json") ? await res.json() : { ok: res.ok };
      if (!res.ok || j.ok === false) {
        alert("Error al guardar: " + (j.error || res.status));
        return;
      }
      const modal = bootstrap.Modal.getInstance(document.getElementById("modalLugar"));
      if (modal) modal.hide();
      e.target.reset();
      addMode = false;
      if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
      }
      await cargar();
    } catch (err) {
      console.error("Error creando lugar:", err);
      alert("No se pudo crear el lugar");
    }
  });

  // ===== Capas de polígonos =====
  function styleUPZ() {
    return { color: "#198754", weight: 1, fillColor: "#198754", fillOpacity: 0.08 };
  }
  function styleBarrios() {
    return { color: "#0d6efd", weight: 1, fillColor: "#0d6efd", fillOpacity: 0.08 };
  }
  function styleLocalidad() {
    return { color: "#dc3545", weight: 2, dashArray: "4 2", fillOpacity: 0 };
  }
  function styleParques() {
    return { color: "#16a34a", weight: 1, fillColor: "#22c55e", fillOpacity: 0.25 };
  }

  // Colores de markers de escuelas por tipo (rosa/cultura, teal/deporte)
  const COLOR_ESCUELA = {
    'Cultura': '#ec4899',
    'Deporte': '#14b8a6',
  };
  function iconoEscuela(tipo) {
    const color = COLOR_ESCUELA[tipo] || '#6b7280';
    return L.divIcon({
      className: 'marker-escuela',
      html: '<div style="width:18px;height:18px;background:' + color +
            ';border:2px solid white;border-radius:3px;box-shadow:0 1px 4px rgba(0,0,0,0.3);"></div>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
      popupAnchor: [0, -9],
    });
  }

  function styleFor(kind) {
    if (kind === "upz") return styleUPZ();
    if (kind === "barrios") return styleBarrios();
    if (kind === "parques") return styleParques();
    return styleLocalidad();
  }
  function layerFor(kind) {
    if (kind === "upz") return upzLayer;
    if (kind === "barrios") return barriosLayer;
    if (kind === "parques") return parquesLayer;
    return localidadLayer;
  }

  function withInteractions(kind, nameField = "nombre") {
    return {
      style: styleFor(kind),
      onEachFeature: (feature, l) => {
        const p = feature.properties || {};
        const title = p[nameField] || p.nombre || p.codigo || "Sin nombre";
        const extra = (kind === "parques" && p.tipo)
          ? `<div style="font-size:12px;color:#6b7280;">${p.tipo}</div>`
          : "";
        l.bindPopup(`<strong>${title}</strong>${extra}`);
        l.on("mouseover", (e) => {
          e.target.setStyle({ weight: 3, fillOpacity: 0.35 });
          e.target.bringToFront();
        });
        l.on("mouseout", (e) => {
          layerFor(kind).resetStyle(e.target);
        });
      },
    };
  }

  const upzLayer = L.geoJSON(null, withInteractions("upz"));
  const barriosLayer = L.geoJSON(null, withInteractions("barrios"));
  const localidadLayer = L.geoJSON(null, withInteractions("localidad"));
  const parquesLayer = L.geoJSON(null, withInteractions("parques"));

  // Escuelas: puntos con markers coloreados por tipo (Cultura/Deporte)
  const escuelasLayer = L.geoJSON(null, {
    pointToLayer: (feature, latlng) => L.marker(latlng, {
      icon: iconoEscuela(feature.properties?.tipo),
    }),
    onEachFeature: (feature, l) => {
      const p = feature.properties || {};
      const color = COLOR_ESCUELA[p.tipo] || '#6b7280';
      const html =
        `<div style="min-width:180px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">` +
          `<div style="font-weight:700;font-size:14px;color:#1f2937;margin-bottom:4px;">${p.nombre || '—'}</div>` +
          (p.tipo ? `<div><span style="background:${color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">${p.tipo}</span></div>` : '') +
          (p.direccion ? `<div style="font-size:12px;color:#6b7280;margin-top:4px;">📍 ${p.direccion}</div>` : '') +
        `</div>`;
      l.bindPopup(html);
    },
  });

  // Cache del GeoJSON de escuelas para permitir filtrado por tipo sin
  // volver a hacer fetch. Los checkboxes .layer-escuela-tipo (Cultura /
  // Deporte) llaman renderEscuelasLayer() que filtra sobre este cache.
  let escuelasData = null;

  // Filtro de escuelas controlado por las pestañas de subgrupo N18.
  // Valores:
  //   '*'      -> todas las escuelas visibles (default)
  //   'Cultura' / 'Deporte' -> solo ese tipo
  //   'none'   -> oculta la capa por completo
  let escuelaFiltro = '*';

  function renderEscuelasLayer() {
    if (!escuelasData) return;
    if (escuelaFiltro === 'none') {
      escuelasLayer.clearLayers();
      if (map.hasLayer(escuelasLayer)) map.removeLayer(escuelasLayer);
      return;
    }
    const features = (escuelasData.features || []).filter(f => {
      if (escuelaFiltro === '*') return true;
      return f.properties?.tipo === escuelaFiltro;
    });
    escuelasLayer.clearLayers();
    escuelasLayer.addData({ type: 'FeatureCollection', features: features });
    if (!map.hasLayer(escuelasLayer)) map.addLayer(escuelasLayer);
  }

  // Expuesto para que las pestañas de subgrupo N18 controlen la capa.
  function filtrarEscuelas(tipo) {
    escuelaFiltro = tipo || '*';
    renderEscuelasLayer();
  }

  async function cargarEscuelas() {
    try {
      const res = await fetch(API.escuelas, { credentials: "include" });
      escuelasData = await res.json();
      renderEscuelasLayer();
    } catch (e) {
      console.error("Error cargando escuelas:", e);
    }
  }

  async function toggleGeoLayer(url, layerObj, { bringToBack = false, fit = false } = {}) {
    try {
      const res = await fetch(url, { credentials: "include" });
      const gj = await res.json();
      layerObj.clearLayers().addData(gj);
      if (bringToBack) layerObj.bringToBack();
      else layerObj.bringToFront();
      map.addLayer(layerObj);
      if (fit && layerObj.getLayers().length) {
        try {
          map.fitBounds(layerObj.getBounds(), { padding: [20, 20] });
        } catch {}
      }
      return layerObj;
    } catch (e) {
      console.error("Error cargando capa:", e);
      return layerObj;
    }
  }

  const cbBarrios = document.getElementById("layer-barrios");
  const cbUPZ = document.getElementById("layer-upz");
  const cbLocalidad = document.getElementById("layer-localidad");
  const cbParques = document.getElementById("layer-parques");
  // Capa "Lugares históricos" y checkboxes de Escuelas (Cultura/Deporte)
  // retirados del UI. Las escuelas siguen siempre visibles en el mapa.
  // El cluster de lugares se construye internamente para KPIs pero no se
  // agrega al mapa (ver renderMapFromFeatures arriba).

  cbBarrios?.addEventListener("change", async function () {
    if (this.checked) {
      const upzSel = [...(document.getElementById("f-upz")?.selectedOptions || [])]
        .map((o) => o.value)
        .filter(Boolean);
      const u = new URL(API.barrios, window.location.origin);
      upzSel.forEach((code) => u.searchParams.append("upz", code));
      await toggleGeoLayer(u.toString(), barriosLayer, { bringToBack: true, fit: false });
    } else {
      map.removeLayer(barriosLayer);
    }
  });

  cbUPZ?.addEventListener("change", async function () {
    if (this.checked) {
      await toggleGeoLayer(API.upz, upzLayer, { bringToBack: true, fit: false });
    } else {
      map.removeLayer(upzLayer);
    }
  });

  // Localidad Kennedy
  cbLocalidad?.addEventListener("change", async function () {
    if (this.checked) {
      await toggleGeoLayer(API.localidadKennedy, localidadLayer, { bringToBack: false, fit: true });
    } else {
      map.removeLayer(localidadLayer);
    }
  });

  // Parques
  cbParques?.addEventListener("change", async function () {
    if (this.checked) {
      await toggleGeoLayer(API.parques, parquesLayer, { bringToBack: true, fit: false });
    } else {
      map.removeLayer(parquesLayer);
    }
  });

  // (Escuelas: el toggle por tipo vive más arriba con
  //  document.querySelectorAll('.layer-escuela-tipo'). La carga inicial
  //  la hace cargarEscuelas() al final de initKennedy.)

  document.getElementById("f-upz")?.addEventListener("change", () => {
    if (cbBarrios?.checked) refreshBarriosPolygons({ fit: false });
  });

  async function refreshBarriosPolygons({ fit = false } = {}) {
    const upzSel = [...(document.getElementById("f-upz")?.selectedOptions || [])]
      .map((o) => o.value)
      .filter(Boolean);
    const u = new URL(API.barrios, window.location.origin);
    upzSel.forEach((code) => u.searchParams.append("upz", code));
    try {
      const res = await fetch(u.toString(), { credentials: "include" });
      const gj = await res.json();
      barriosLayer.clearLayers().addData(gj).bringToBack();
      if (fit && barriosLayer.getLayers().length) {
        try {
          map.fitBounds(barriosLayer.getBounds(), { padding: [20, 20] });
        } catch {}
      }
      if (cbBarrios?.checked) map.addLayer(barriosLayer);
    } catch (e) {
      console.warn("No se pudieron cargar Barrios:", e);
    }
  }

  // Primera carga y capas iniciales
  cargar();
  cargarEscuelas();  // cache + render inicial respetando checkboxes por tipo
  if (cbUPZ?.checked) toggleGeoLayer(API.upz, upzLayer, { bringToBack: true, fit: false });
  if (cbBarrios?.checked) refreshBarriosPolygons({ fit: false });
  if (cbLocalidad?.checked) toggleGeoLayer(API.localidadKennedy, localidadLayer, { bringToBack: false, fit: true });
  if (cbParques?.checked) toggleGeoLayer(API.parques, parquesLayer, { bringToBack: true, fit: false });

  // Exponer para depuración
  window.__kennedy = {
    map,
    layers: { upzLayer, barriosLayer, localidadLayer, parquesLayer, escuelasLayer },
    cargar,
    filtrarEscuelas,
  };
}

// ==============================
// Arreglo de navegación forzada
// ==============================
function forceAnchorNavById(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const clone = el.cloneNode(true); // limpia listeners previos
  el.parentNode.replaceChild(clone, el);
  clone.addEventListener(
    "click",
    function (e) {
      e.preventDefault();
      e.stopPropagation();
      const href = clone.getAttribute("href");
      if (href) window.location.assign(href);
    },
    true
  );
  clone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      const href = clone.getAttribute("href");
      if (href) window.location.assign(href);
    }
  });
  clone.style.pointerEvents = "auto";
}

window.initKennedy = initKennedy;

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    () => {
      initKennedy();
    },
    { once: true }
  );
} else {
  initKennedy();
}
