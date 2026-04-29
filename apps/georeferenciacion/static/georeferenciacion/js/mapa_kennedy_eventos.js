/**
 * Mapa Kennedy — Layer de eventos georreferenciados
 *
 * Consume /geo/api/eventos/ (endpoint creado en Fase A, commit bbc358c)
 * y renderiza cada evento como marker coloreado por tipo_evento con popup
 * completo (fecha, dependencia, funcionario, dirección, KPI impactado).
 *
 * Dependencias:
 *   - Leaflet 1.9+ (global L)
 *   - mapa_kennedy.js (expone window.__kennedy.map al terminar initKennedy)
 *
 * Expone:
 *   - window.cargarEventos(params) para recargar con filtros querystring
 *     (la Fase C3 la consumirá desde los selects del sidebar).
 *
 * Extraído del template en Fase C2.
 */
(function () {
  // --- Constantes ---------------------------------------------------------
  // Los colores los inyecta el template desde TipoEvento.color_hex (property
  // determinística en apps/login/models/evento.py). Cuando se cree un tipo
  // nuevo en BD aparece aquí sin tocar JS. Fallback a paleta interna por si
  // el bootstrap del template no se ejecutó.
  const COLORES_TIPO = (window && window.__COLORES_TIPO_EVENTO) || {
    'ENTREGA':           '#10b981',
    'CAPACITACION':      '#3b82f6',
    'CURSO':             '#f59e0b',
    'INFO_TERRENO':      '#a855f7',
    'BANCO_INICIATIVAS': '#ef4444',
  };
  const COLOR_DEFAULT = '#6b7280'; // gris

  // Tiles CartoDB Voyager — reemplaza el mirror openstreetmap.bzh del JS core.
  const TILE_VOYAGER = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

  // --- Helpers ------------------------------------------------------------

  // Ícono SVG circular con color por tipo.
  function iconoEvento(tipoCodigo) {
    const color = COLORES_TIPO[tipoCodigo] || COLOR_DEFAULT;
    return L.divIcon({
      className: 'marker-evento',
      html: '<div style="width:24px;height:24px;background:' + color +
            ';border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>',
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12],
    });
  }

  // YYYY-MM-DD → "23 abr 2026"
  function fmtFecha(isoStr) {
    if (!isoStr) return '—';
    const meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
    const [y, m, d] = isoStr.split('-').map(Number);
    return d + ' ' + meses[m - 1] + ' ' + y;
  }

  // Escape HTML defensivo para los campos interpolados en popups.
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // HTML del popup con la cadena completa de datos del evento.
  function popupEventoHtml(props) {
    const fechaStr = (props.fecha_fin && props.fecha_fin !== props.fecha_inicio)
      ? (fmtFecha(props.fecha_inicio) + ' — ' + fmtFecha(props.fecha_fin))
      : fmtFecha(props.fecha_inicio);

    const colorTipo = COLORES_TIPO[props.tipo_evento_codigo] || COLOR_DEFAULT;

    const magnitud = (props.magnitud_aportada !== null && props.magnitud_aportada !== undefined)
      ? props.magnitud_aportada : '—';

    const indicadorHtml = props.indicador
      ? '<div style="margin-top:8px;padding-top:8px;border-top:1px solid #e5e7eb;">' +
          '<div style="color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;">Aporta al KPI</div>' +
          '<div style="font-weight:600;color:#1f2937;">' + escapeHtml(props.indicador) + '</div>' +
          '<div style="color:#3b82f6;font-weight:700;font-size:18px;">' +
            magnitud +
            ' <span style="font-size:12px;color:#6b7280;font-weight:400;">impactados</span>' +
          '</div>' +
        '</div>'
      : '';

    return '<div style="min-width:240px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;">' +
      '<div style="font-weight:700;font-size:15px;color:#1f2937;margin-bottom:8px;line-height:1.3;">' +
        escapeHtml(props.nombre) +
      '</div>' +
      '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:13px;color:#4b5563;">' +
        '🗓 ' + fechaStr +
      '</div>' +
      '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:13px;">' +
        '<span style="background:' + colorTipo + ';color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">' +
          (props.tipo_evento_codigo || '—') +
        '</span>' +
      '</div>' +
      '<div style="font-size:13px;color:#4b5563;margin-bottom:4px;">' +
        '🏢 ' + escapeHtml(props.dependencia || '—') +
      '</div>' +
      (props.funcionario
        ? '<div style="font-size:12px;color:#6b7280;margin-bottom:4px;">👤 ' + escapeHtml(props.funcionario) + '</div>'
        : '') +
      (props.direccion
        ? '<div style="font-size:12px;color:#6b7280;">📍 ' + escapeHtml(props.direccion) + '</div>'
        : '') +
      indicadorHtml +
    '</div>';
  }

  // --- Funciones principales ----------------------------------------------

  // Sobrescribe los tiles del JS core (openstreetmap.bzh → CartoDB Voyager).
  // El JS core ya agregó su tileLayer; lo removemos y añadimos Voyager.
  function overrideTiles(map) {
    map.eachLayer(function (layer) {
      if (layer instanceof L.TileLayer) map.removeLayer(layer);
    });
    L.tileLayer(TILE_VOYAGER, {
      attribution: '© OpenStreetMap contributors © CARTO',
      subdomains: 'abcd',
      maxZoom: 20,
    }).addTo(map);
  }

  let eventosLayer = null;
  let eventosData = null;  // cache del JSON crudo para re-filtrar sin fetch

  // Lee los checkboxes .layer-evento-tipo y devuelve el Set de tipos activos.
  // Si no hay checkboxes (sidebar aún no carga), asume todos activos.
  function tiposEventoActivos() {
    const boxes = document.querySelectorAll('.layer-evento-tipo');
    if (boxes.length === 0) return null;  // null = "no filtrar"
    const activos = new Set();
    boxes.forEach(function (b) {
      if (b.checked) activos.add(b.getAttribute('data-tipo'));
    });
    return activos;
  }

  // Reconstruye eventosLayer con el filtro de tipos activos.
  // Siempre hay que llamar esto después de cargar o de cambiar checkboxes.
  function renderEventosLayer() {
    const kennedy = window.__kennedy;
    if (!kennedy || !kennedy.map || !eventosData) return;
    const map = kennedy.map;

    if (eventosLayer) {
      map.removeLayer(eventosLayer);
      eventosLayer = null;
    }

    const activos = tiposEventoActivos();
    const features = (eventosData.features || []).filter(function (f) {
      if (activos === null) return true;
      return activos.has(f.properties?.tipo_evento_codigo);
    });

    eventosLayer = L.geoJSON({ type: 'FeatureCollection', features: features }, {
      pointToLayer: function (feature, latlng) {
        return L.marker(latlng, {
          icon: iconoEvento(feature.properties.tipo_evento_codigo),
        });
      },
      onEachFeature: function (feature, layer) {
        layer.bindPopup(popupEventoHtml(feature.properties), {
          maxWidth: 320,
          className: 'popup-evento',
        });
      },
    }).addTo(map);
  }

  // Carga el endpoint /geo/api/eventos/, cachea el JSON y renderiza.
  // `params` es el querystring (sin '?') para filtrar server-side (fecha,
  // dependencia, etc.); los toggles de tipo filtran client-side sobre el cache.
  function cargarEventos(params) {
    const kennedy = window.__kennedy;
    if (!kennedy || !kennedy.map) return;
    const qs = params ? ('?' + params) : '';
    fetch('/geo/api/eventos/' + qs)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.features) return;
        eventosData = data;
        console.log('Cargando ' + data.features.length + ' eventos en el mapa');
        renderEventosLayer();
      })
      .catch(function (err) { console.error('Error cargando eventos:', err); });
  }

  // --- Cascadas del sidebar -----------------------------------------------
  // Helper genérico: al cambiar `padreSel`, filtra los options de `hijoSel`
  // por el atributo data-* coincidente. `hijoSel` puede ser un <select> single
  // o multiple (ambos funcionan).

  function setupCascada(padreId, hijoId, dataAttr) {
    const padreSel = document.getElementById(padreId);
    const hijoSel = document.getElementById(hijoId);
    if (!padreSel || !hijoSel) return;

    const allHijoOptions = Array.from(hijoSel.options).map(function (opt) {
      return {
        value: opt.value,
        text: opt.textContent,
        padreKey: opt.getAttribute('data-' + dataAttr),
      };
    });

    function filtrar() {
      // padreSel puede ser single o multiple; recogemos todos los valores activos.
      const activos = padreSel.multiple
        ? Array.from(padreSel.selectedOptions).map(function (o) { return o.value; }).filter(Boolean)
        : (padreSel.value ? [padreSel.value] : []);

      hijoSel.innerHTML = '';
      allHijoOptions.forEach(function (opt) {
        const keep = activos.length === 0 || activos.indexOf(opt.padreKey) !== -1;
        if (!keep) return;
        const o = document.createElement('option');
        o.value = opt.value;
        o.textContent = opt.text;
        o.setAttribute('data-' + dataAttr, opt.padreKey);
        hijoSel.appendChild(o);
      });
    }

    padreSel.addEventListener('change', filtrar);
  }

  function setupCascadaDependencia() {
    setupCascada('f-dependencia', 'f-subgrupo', 'dependencia');
  }

  function setupCascadaUpzBarrio() {
    setupCascada('f-upz', 'f-barrio', 'upz');
  }

  // --- Toggles por TIPO de evento (4 checkboxes: ENTREGA / CAPACITACION /
  // CURSO / INFO_TERRENO). Cada click re-renderiza la capa filtrando
  // sobre el cache eventosData, sin nuevo fetch al servidor.
  function setupToggleEventos() {
    document.querySelectorAll('.layer-evento-tipo').forEach(function (chk) {
      chk.addEventListener('change', renderEventosLayer);
    });
  }

  // --- Aplicar / Limpiar filtros ------------------------------------------

  function construirQueryString() {
    const params = new URLSearchParams();

    // Tipo evento (multiselect). El endpoint acepta solo un código por
    // ahora; mandamos el primero seleccionado.
    const tipoSel = document.getElementById('f-tipo');
    if (tipoSel) {
      const tipos = Array.from(tipoSel.selectedOptions)
        .map(function (o) { return o.value; })
        .filter(Boolean);
      if (tipos.length > 0) params.set('tipo_evento', tipos[0]);
    }

    // Dependencia (single).
    const depSel = document.getElementById('f-dependencia');
    if (depSel && depSel.value) {
      params.set('dependencia_id', depSel.value);
    }

    // Subgrupo (multiselect). Mismo compromiso: primer valor.
    const subSel = document.getElementById('f-subgrupo');
    if (subSel) {
      const subs = Array.from(subSel.selectedOptions)
        .map(function (o) { return o.value; })
        .filter(Boolean);
      if (subs.length > 0) params.set('subgrupo_id', subs[0]);
    }

    return params.toString();
  }

  function setupBotonesFiltro() {
    const btnAplicar = document.getElementById('btn-aplicar');
    const btnLimpiar = document.getElementById('btn-limpiar');

    if (btnAplicar) {
      btnAplicar.addEventListener('click', function (e) {
        e.preventDefault();
        const qs = construirQueryString();
        console.log('Aplicando filtros:', qs || '(sin filtros)');
        cargarEventos(qs);
      });
    }

    if (btnLimpiar) {
      btnLimpiar.addEventListener('click', function (e) {
        e.preventDefault();
        ['f-tipo', 'f-subgrupo', 'f-dependencia', 'f-upz', 'f-barrio'].forEach(function (id) {
          const el = document.getElementById(id);
          if (!el) return;
          if (el.multiple) {
            Array.from(el.options).forEach(function (o) { o.selected = false; });
          } else {
            el.value = '';
          }
        });
        const q = document.getElementById('q');
        if (q) q.value = '';
        cargarEventos();
        // Restaurar cascadas al reset (opciones vuelven a aparecer todas).
        setupCascadaDependencia();
        setupCascadaUpzBarrio();
      });
    }
  }

  // --- Bootstrap ----------------------------------------------------------

  // Espera a que initKennedy haya corrido y expuesto window.__kennedy.map.
  function arrancar() {
    let intentos = 0;
    const intv = setInterval(function () {
      intentos++;
      if (window.__kennedy && window.__kennedy.map) {
        clearInterval(intv);
        overrideTiles(window.__kennedy.map);
        cargarEventos();
        setupCascadaDependencia();
        setupCascadaUpzBarrio();
        setupBotonesFiltro();
        setupToggleEventos();
      } else if (intentos > 100) {
        // 10s sin __kennedy listo: abortar silenciosamente
        clearInterval(intv);
        console.warn('cargarEventos: window.__kennedy no disponible tras 10s');
      }
    }, 100);
  }

  window.addEventListener('load', arrancar);
  // Expuesto para recargas con filtros (Fase C3).
  window.cargarEventos = cargarEventos;
})();
