import { CommonModule } from '@angular/common';
import {
  AfterViewInit, ChangeDetectionStrategy, Component, ElementRef,
  OnDestroy, OnInit, ViewChild, computed, effect, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Chart, registerables } from 'chart.js';
import * as L from 'leaflet';
import { forkJoin } from 'rxjs';

Chart.register(...registerables);
import { LayoutService } from '../../core/layout/layout.service';
import {
  ConteoSubgrupo, EventoFiltros, FeatureCollection, GeoFeature, GeoService,
  SubgrupoLite, TipoEventoLite,
} from '../../core/geo/geo.service';

/**
 * Mapa Kennedy en Angular nativo con Leaflet.
 *
 * Reemplaza el iframe al Django legacy. Consume:
 *   GET /geo/api/mapa/catalogos/   — UPZ, Barrios, Tipos, Dep, Subgrupo, N18
 *   GET /geo/api/eventos/?...      — FeatureCollection eventos
 *   GET /geo/api/kennedy/contorno/ — polígono localidad
 *   GET /geo/api/kennedy/upz/      — polígonos UPZ
 *   GET /geo/api/kennedy/barrios/  — polígonos barrios
 *   GET /geo/api/kennedy/parques/  — polígonos parques
 */
@Component({
  standalone: true,
  selector: 'app-mapa-kennedy',
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mapa">
      <header class="mapa__header">
        <div>
          <h1>
            <i class="fa fa-map-marked-alt" aria-hidden="true"></i>
            Mapa de Kennedy
          </h1>
          <p class="mapa__subtitle">
            Eventos, parques, escuelas y barrios georreferenciados.
            <span class="mapa__count">{{ eventos().features.length }} eventos visibles</span>
          </p>
        </div>
        <div class="mapa__kpis">
          <div class="mapa-kpi">
            <span class="mapa-kpi__value">{{ eventos().features.length }}</span>
            <span class="mapa-kpi__label">Eventos</span>
          </div>
          <div class="mapa-kpi">
            <span class="mapa-kpi__value">{{ kpiHoy() }}</span>
            <span class="mapa-kpi__label">Hoy</span>
          </div>
          <div class="mapa-kpi">
            <span class="mapa-kpi__value">{{ kpiProximos() }}</span>
            <span class="mapa-kpi__label">Próximos</span>
          </div>
        </div>
      </header>

      <div class="mapa__body">
        <aside class="mapa-side">
          <section class="mapa-side__section">
            <h2>Filtros</h2>

            <div class="mapa-field">
              <span class="mapa-field__label">Tipo de evento</span>
              <div class="mapa-chips" role="group" aria-label="Tipo de evento">
                @for (t of catalogos()?.tipos_evento ?? []; track t.codigo) {
                  <button type="button" class="mapa-chip"
                          [class.mapa-chip--on]="selectedTipos.includes(t.codigo)"
                          [attr.aria-pressed]="selectedTipos.includes(t.codigo)"
                          (click)="toggleTipo(t.codigo)">
                    <span class="mapa-chip__dot" [style.background]="t.color_hex"></span>
                    {{ t.nombre }}
                  </button>
                } @empty {
                  <span class="mapa-field__hint">Sin tipos.</span>
                }
              </div>
            </div>

            <label class="mapa-field">
              <span>Dependencia</span>
              <select [(ngModel)]="selectedDependencia" (change)="onDependenciaChange()">
                <option [ngValue]="null">— Todas —</option>
                @for (d of catalogos()?.dependencias ?? []; track d.id) {
                  <option [ngValue]="d.id">{{ d.nombre }}</option>
                }
              </select>
            </label>

            <div class="mapa-field">
              <span class="mapa-field__label">Subgrupo</span>
              <div class="mapa-chips" role="group" aria-label="Subgrupo">
                @for (s of subgruposFiltrados(); track s.id) {
                  <button type="button" class="mapa-chip"
                          [class.mapa-chip--on]="selectedSubgrupos.includes(s.id)"
                          [attr.aria-pressed]="selectedSubgrupos.includes(s.id)"
                          (click)="toggleSubgrupo(s.id)">
                    {{ s.nombre }}
                  </button>
                } @empty {
                  <span class="mapa-field__hint">Sin subgrupos.</span>
                }
              </div>
            </div>

            <label class="mapa-field">
              <span>Buscar</span>
              <input type="search" [(ngModel)]="query" (input)="onBuscar()"
                     placeholder="Nombre, dirección, dependencia…">
            </label>

            <div class="mapa-side__actions">
              <button class="ui-btn ui-btn--sm ui-btn--ghost" type="button"
                      (click)="limpiarFiltros()">Limpiar</button>
            </div>
          </section>

          <section class="mapa-side__section">
            <h2>Capas</h2>
            @for (t of catalogos()?.tipos_evento ?? []; track t.codigo) {
              <label class="mapa-layer">
                <input type="checkbox" [(ngModel)]="layerVisible[t.codigo]"
                       (change)="renderEventos()">
                <span class="mapa-dot" [style.background]="t.color_hex"></span>
                {{ t.nombre }}
              </label>
            }
            <hr>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.parques" (change)="toggleCapa('parques')">
              <span class="mapa-poly mapa-poly--parque"></span> Parques
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.barrios" (change)="toggleCapa('barrios')">
              <span class="mapa-poly mapa-poly--barrio"></span> Barrios
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.upz" (change)="toggleCapa('upz')">
              <span class="mapa-poly mapa-poly--upz"></span> UPZ
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.estratificacion" (change)="toggleCapa('estratificacion')">
              <span class="mapa-poly mapa-poly--estrato"></span> Estratificación (IDECA)
              @if (estratificacionCargando) {
                <span class="mapa-cargando" role="status">cargando…</span>
              }
            </label>
            @if (capas.estratificacion && !estratificacionCargando) {
              <div class="mapa-estrato-leyenda" aria-label="Leyenda por estrato socioeconómico">
                @for (it of estratoLeyenda; track it.e) {
                  <span class="mapa-estrato-chip">
                    <span class="mapa-estrato-dot" [style.background]="colorEstrato(it.e)"></span>
                    {{ it.label }}
                  </span>
                }
                <span class="mapa-estrato-fuente">Fuente: Catastro/IDECA (2019)</span>
              </div>
            }
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.localidad" (change)="toggleCapa('localidad')">
              <span class="mapa-line mapa-line--localidad"></span> Localidad
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.ofertaFormativa" (change)="toggleCapa('ofertaFormativa')">
              <span class="mapa-bubble"></span> Oferta formativa (cursos por sede)
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.festivales" (change)="toggleCapa('festivales')">
              <span class="mapa-festival-dot">★</span> Festivales
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.tramosViales" (change)="toggleCapa('tramosViales')">
              <span class="mapa-line mapa-line--obra"></span> Malla vial / obras
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.parquesObras" (change)="toggleCapa('parquesObras')">
              <span class="mapa-obra-dot">🌳</span> Parques (obras)
            </label>

            @if (capas.tramosViales || capas.parquesObras) {
              <div class="mapa-avance-leyenda" aria-label="Leyenda por porcentaje de avance">
                <span class="mapa-avance-chip">
                  <span class="mapa-avance-dot mapa-avance-dot--rojo"></span> 0% (sin iniciar)
                </span>
                <span class="mapa-avance-chip">
                  <span class="mapa-avance-dot mapa-avance-dot--ambar"></span> Parcial
                </span>
                <span class="mapa-avance-chip">
                  <span class="mapa-avance-dot mapa-avance-dot--verde"></span> 100% (terminado)
                </span>
              </div>
            }
            <hr>
            <small class="mapa-side__hint">
              <i class="fa fa-info-circle"></i> El equipamiento (escenarios de
              Cultura y Deporte) se muestra según el subgrupo seleccionado
              arriba del mapa.
            </small>
          </section>
        </aside>

        <div class="mapa-canvas">
          @if (subgruposInversion().length) {
            <div class="mapa-tabs" role="tablist" aria-label="Subgrupo Inversión Local">
              <button class="mapa-tab" type="button"
                      [class.mapa-tab--active]="!subgrupoTab()"
                      (click)="setSubgrupoTab(null)">Todos</button>
              @for (s of subgruposInversion(); track s.id) {
                <button class="mapa-tab" type="button"
                        [class.mapa-tab--active]="subgrupoTab() === s.id"
                        (click)="setSubgrupoTab(s.id)"
                        [title]="s.nombre">
                  {{ s.nombre }}
                  @if (conteosSubgrupo()[s.id]; as c) {
                    <span class="mapa-tab__count">{{ c.total }}</span>
                  }
                </button>
              }
            </div>
          }
          <div #mapEl class="mapa-leaflet"></div>
          @if (loading()) {
            <div class="mapa-loading">Cargando datos…</div>
          }
          @if (errorMsg()) {
            <div class="mapa-error">⚠ {{ errorMsg() }}</div>
          }
        </div>
      </div>

      <section class="mapa-stats">
        <header class="mapa-stats__head" (click)="statsAbierto.set(!statsAbierto())">
          <h2><i class="fa fa-chart-pie"></i> Análisis de actividades
            <small>· {{ eventosFiltrados().length }} en vista</small></h2>
          <i class="fa" [class.fa-chevron-down]="!statsAbierto()"
             [class.fa-chevron-up]="statsAbierto()"></i>
        </header>
        @if (statsAbierto()) {
          <div class="mapa-stats__kpis">
            <article class="stat-card stat-card--total">
              <span class="stat-card__value">{{ eventosFiltrados().length }}</span>
              <span class="stat-card__label">En vista</span>
            </article>
            <article class="stat-card stat-card--ok">
              <span class="stat-card__value">{{ statKpis().ejecutados }}</span>
              <span class="stat-card__label">Ejecutados</span>
            </article>
            <article class="stat-card stat-card--soon">
              <span class="stat-card__value">{{ statKpis().proximos }}</span>
              <span class="stat-card__label">Próximos</span>
            </article>
            <article class="stat-card stat-card--carac">
              <span class="stat-card__value">{{ statKpis().conKpi }}</span>
              <span class="stat-card__label">Con KPI</span>
            </article>
          </div>
          <div class="mapa-stats__charts">
            <div class="chart-box">
              <h3>Por tipo de actividad</h3>
              <canvas #chartTipo></canvas>
            </div>
            <div class="chart-box">
              <h3>Por subgrupo (top 8)</h3>
              <canvas #chartSub></canvas>
            </div>
            <div class="chart-box chart-box--wide">
              <h3>Evolución mensual</h3>
              <canvas #chartMes></canvas>
            </div>
          </div>
        }
      </section>

      <section class="mapa-table">
        <h2>Eventos en el mapa
          <span class="mapa-table__count">({{ eventosFiltrados().length }})</span>
        </h2>
        <div class="mapa-table__wrap">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Dependencia</th>
                <th>Dirección</th>
              </tr>
            </thead>
            <tbody>
              @for (f of eventosFiltrados(); track f.properties.id) {
                <tr (click)="centrar(f)" class="mapa-table__row">
                  <td>{{ f.properties.nombre || '—' }}</td>
                  <td>{{ f.properties.fecha_inicio || '—' }}</td>
                  <td>
                    <span class="mapa-pill"
                          [style.background]="colorTipo(f.properties.tipo_evento_codigo)">
                      {{ tipoNombre(f.properties.tipo_evento_codigo) }}
                    </span>
                  </td>
                  <td>{{ f.properties.dependencia || '—' }}</td>
                  <td>{{ f.properties.direccion || '—' }}</td>
                </tr>
              } @empty {
                <tr><td colspan="5" class="mapa-table__empty">
                  No hay eventos que coincidan con los filtros.
                </td></tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
  styleUrl: './mapa.component.scss',
})
export class MapaKennedyComponent implements OnInit, AfterViewInit, OnDestroy {
  private geo = inject(GeoService);
  private layout = inject(LayoutService);

  @ViewChild('mapEl', { static: false }) mapEl!: ElementRef<HTMLDivElement>;
  @ViewChild('chartTipo') private chartTipoRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSub') private chartSubRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartMes') private chartMesRef?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];
  statsAbierto = signal<boolean>(true);

  constructor() {
    // Redibuja los gráficos cuando cambian los eventos filtrados o se abre
    // el panel. Reactivo a TODOS los filtros (signals + query).
    effect(() => {
      const feats = this.eventosFiltrados();
      if (this.statsAbierto()) {
        queueMicrotask(() => this.dibujarCharts(feats));
      }
    });
  }

  // ── Estado reactivo ─────────────────────────────────────────────
  catalogos = signal<MapaCatalogosLocal | null>(null);
  eventos = signal<FeatureCollection>({ type: 'FeatureCollection', features: [] });
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  subgrupoTab = signal<number | null>(null);
  query = '';
  selectedTipos: string[] = [];
  selectedSubgrupos: number[] = [];
  selectedDependencia: number | null = null;

  layerVisible: Record<string, boolean> = {};
  capas = {
    parques: true, barrios: false, upz: false, localidad: true,
    escuelasCultura: false, escuelasDeporte: false,
    ofertaFormativa: false, festivales: false,
    tramosViales: false, parquesObras: false,
    estratificacion: false,
  };

  // Paleta de estratos (IDECA). 0/sin dato = gris; 1→6 rojo→morado (convención Bogotá).
  readonly estratoColores: Record<number, string> = {
    0: '#9CA3AF', 1: '#E4572E', 2: '#F3A712', 3: '#F4D35E',
    4: '#59A14F', 5: '#4E79A7', 6: '#7B4FA3',
  };
  readonly estratoLeyenda = [
    { e: 1, label: 'Estrato 1' }, { e: 2, label: 'Estrato 2' }, { e: 3, label: 'Estrato 3' },
    { e: 4, label: 'Estrato 4' }, { e: 5, label: 'Estrato 5' }, { e: 6, label: 'Estrato 6' },
    { e: 0, label: 'Sin estrato' },
  ];
  colorEstrato(e: number | null | undefined): string {
    return this.estratoColores[e ?? 0] ?? this.estratoColores[0];
  }

  // ── Estado Leaflet ──────────────────────────────────────────────
  private map?: L.Map;
  private eventoLayer?: L.LayerGroup;
  private contornoLayer?: L.GeoJSON;
  private upzLayer?: L.GeoJSON;
  private barriosLayer?: L.GeoJSON;
  private parquesLayer?: L.GeoJSON;
  private escuelasCulturaLayer?: L.LayerGroup;
  private escuelasDeporteLayer?: L.LayerGroup;
  private festivalesLayer?: L.LayerGroup;
  private tramosLayer?: L.GeoJSON;
  private parquesObrasLayer?: L.LayerGroup;
  private estratificacionLayer?: L.GeoJSON;
  /** La capa pesa ~1 MB y tarda: sin esto el check parece muerto mientras baja. */
  estratificacionCargando = false;

  // ── Derivados ───────────────────────────────────────────────────
  subgruposFiltrados = computed<SubgrupoLite[]>(() => {
    const cat = this.catalogos();
    if (!cat) return [];
    if (this.selectedDependencia == null) return cat.subgrupos;
    return cat.subgrupos.filter(s => s.dependencia_id === this.selectedDependencia);
  });

  subgruposInversion = computed<SubgrupoLite[]>(() =>
    this.catalogos()?.subgrupos_inversion_local ?? []);

  conteosSubgrupo = computed<Record<number, ConteoSubgrupo>>(() =>
    this.catalogos()?.conteos_subgrupo ?? {});

  eventosFiltrados = computed<GeoFeature[]>(() => {
    const q = this.query.trim().toLowerCase();
    return this.eventos().features.filter((f) => {
      const p = f.properties;
      const visible = this.layerVisible[p.tipo_evento_codigo] !== false;
      if (!visible) return false;
      if (!q) return true;
      const hay = [p.nombre, p.direccion, p.dependencia, p.funcionario]
        .filter(Boolean).map(String).join(' ').toLowerCase();
      return hay.includes(q);
    });
  });

  kpiHoy = computed<number>(() => {
    const today = new Date().toISOString().slice(0, 10);
    return this.eventos().features.filter(f =>
      (f.properties.fecha_inicio || '').slice(0, 10) === today).length;
  });

  kpiProximos = computed<number>(() => {
    const today = new Date().toISOString().slice(0, 10);
    return this.eventos().features.filter(f =>
      (f.properties.fecha_inicio || '') >= today).length;
  });

  /** KPIs del panel de análisis, sobre los eventos filtrados (en vista). */
  statKpis = computed(() => {
    const today = new Date().toISOString().slice(0, 10);
    const feats = this.eventosFiltrados();
    let proximos = 0, conKpi = 0;
    for (const f of feats) {
      if ((f.properties.fecha_inicio || '') >= today) proximos++;
      if (f.properties['indicador']) conKpi++;
    }
    return { proximos, ejecutados: feats.length - proximos, conKpi };
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mapa de Kennedy' },
    ]);
  }

  ngAfterViewInit(): void {
    this.initMap();
    this.cargarCatalogos();
  }

  ngOnDestroy(): void {
    this.map?.remove();
    this.charts.forEach(c => c.destroy());
  }

  /** Dibuja/actualiza los 3 gráficos con los eventos en vista. */
  private dibujarCharts(feats: GeoFeature[]): void {
    const cTipo = this.chartTipoRef?.nativeElement;
    const cSub = this.chartSubRef?.nativeElement;
    const cMes = this.chartMesRef?.nativeElement;
    if (!cTipo || !cSub || !cMes) return;
    this.charts.forEach(c => c.destroy());
    this.charts = [];

    // Por tipo (con color del catálogo).
    const porTipo = new Map<string, number>();
    const porSub = new Map<string, number>();
    const porMes = new Map<string, number>();
    for (const f of feats) {
      const t = f.properties.tipo_evento_codigo || '—';
      porTipo.set(t, (porTipo.get(t) || 0) + 1);
      const s = (f.properties['subgrupo'] as string) || 'Sin subgrupo';
      porSub.set(s, (porSub.get(s) || 0) + 1);
      const m = (f.properties.fecha_inicio || '').slice(0, 7);
      if (m) porMes.set(m, (porMes.get(m) || 0) + 1);
    }

    const tipoLabels = [...porTipo.keys()];
    this.charts.push(new Chart(cTipo, {
      type: 'doughnut',
      data: {
        labels: tipoLabels.map(c => this.tipoNombre(c)),
        datasets: [{
          data: tipoLabels.map(c => porTipo.get(c)!),
          backgroundColor: tipoLabels.map(c => this.colorTipo(c)),
          borderWidth: 2, borderColor: '#fff',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
      },
    }));

    const subTop = [...porSub.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    this.charts.push(new Chart(cSub, {
      type: 'bar',
      data: {
        labels: subTop.map(([k]) => k),
        datasets: [{
          data: subTop.map(([, v]) => v),
          backgroundColor: '#0D9488', borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    }));

    const meses = [...porMes.keys()].sort();
    this.charts.push(new Chart(cMes, {
      type: 'line',
      data: {
        labels: meses,
        datasets: [{
          data: meses.map(m => porMes.get(m)!),
          borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)',
          fill: true, tension: 0.3, pointRadius: 3,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    }));
  }

  // ── Inicialización ──────────────────────────────────────────────
  private initMap(): void {
    this.map = L.map(this.mapEl.nativeElement, {
      center: [4.6280, -74.1530],  // Kennedy aprox.
      zoom: 13,
      zoomControl: true,
    });

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      },
    ).addTo(this.map);

    this.eventoLayer = L.layerGroup().addTo(this.map);
  }

  private cargarCatalogos(): void {
    this.loading.set(true);
    forkJoin({
      cat: this.geo.catalogos(),
      contorno: this.geo.contornoKennedy(),
    }).subscribe({
      next: ({ cat, contorno }) => {
        this.catalogos.set(cat as MapaCatalogosLocal);
        // Todas las capas de tipo evento visibles por default.
        const layer: Record<string, boolean> = {};
        for (const t of cat.tipos_evento) layer[t.codigo] = true;
        this.layerVisible = layer;

        this.drawContorno(contorno);
        this.cargarParques();
        this.cargarEscuelas();
        this.cargarEventos();
      },
      error: (err) => {
        this.errorMsg.set('No se pudieron cargar los catálogos. Verifica tu sesión.');
        this.loading.set(false);
        console.error(err);
      },
    });
  }

  private drawContorno(fc: FeatureCollection): void {
    if (!this.map) return;
    this.contornoLayer?.remove();
    this.contornoLayer = L.geoJSON(fc as any, {
      style: { color: '#D6001C', weight: 3, fill: false, dashArray: '6 6' },
    });
    if (this.capas.localidad) this.contornoLayer.addTo(this.map);
    try {
      const bb = this.contornoLayer.getBounds();
      if (bb.isValid()) this.map.fitBounds(bb, { padding: [20, 20] });
    } catch { /* sin bounds, ignorar */ }
  }

  private cargarParques(): void {
    this.geo.parquesKennedy().subscribe({
      next: (fc) => {
        if (!this.map) return;
        this.parquesLayer = L.geoJSON(fc as any, {
          style: { color: '#10B981', weight: 1, fillColor: '#10B981', fillOpacity: 0.25 },
        });
        if (this.capas.parques) this.parquesLayer.addTo(this.map);
      },
      error: () => {},
    });
  }

  private escuelaIcon(tipo: 'Cultura' | 'Deporte'): L.DivIcon {
    const color = tipo === 'Cultura' ? '#EC4899' : '#14B8A6';
    return L.divIcon({
      className: 'mapa-escuela-marker',
      html: `<div style="background:${color};width:11px;height:11px;border:2px solid #fff;
              box-shadow:0 0 0 1px ${color};"></div>`,
      iconSize: [13, 13],
      iconAnchor: [7, 7],
    });
  }

  private cargarEscuelas(): void {
    this.geo.escuelasKennedy().subscribe({
      next: (fc) => {
        if (!this.map) return;
        const culLayer = L.layerGroup();
        const depLayer = L.layerGroup();
        for (const f of fc.features) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const tipo = (f.properties?.tipo || '').trim();
          const target = tipo === 'Cultura' ? culLayer : (tipo === 'Deporte' ? depLayer : null);
          if (!target) continue;
          const m = L.marker([lat, lng], {
            icon: this.escuelaIcon(tipo as 'Cultura' | 'Deporte'),
          });
          m.bindPopup(`
            <div class="mapa-popup">
              <h4>${f.properties?.nombre || 'Escuela'}</h4>
              <div><strong>Tipo:</strong> ${tipo}</div>
              ${f.properties?.direccion ? `<div><strong>Dirección:</strong> ${f.properties.direccion}</div>` : ''}
            </div>`);
          m.addTo(target);
        }
        this.escuelasCulturaLayer = culLayer;
        this.escuelasDeporteLayer = depLayer;
        if (this.capas.escuelasCultura) culLayer.addTo(this.map);
        if (this.capas.escuelasDeporte) depLayer.addTo(this.map);
      },
      error: () => { /* sin escuelas, no rompe el mapa */ },
    });
  }

  private ofertaLayer?: L.LayerGroup;

  /** Mapa de calor de oferta formativa: burbujas por escuela según nº de cursos. */
  private cargarOfertaFormativa(): void {
    if (this.ofertaLayer) return;  // lazy, una vez
    this.geo.ofertaFormativa().subscribe({
      next: (r) => {
        if (!this.map) return;
        const layer = L.layerGroup();
        const maxCursos = Math.max(1, ...r.items.map((i) => i.cursos));
        for (const i of r.items) {
          // Radio y opacidad proporcionales a la densidad de cursos.
          const radio = 8 + 22 * (i.cursos / maxCursos);
          const c = L.circleMarker([i.lat, i.lng], {
            radius: radio,
            color: '#7C3AED', weight: 1,
            fillColor: '#A855F7', fillOpacity: 0.45,
          });
          c.bindPopup(`
            <div class="mapa-popup">
              <h4>${i.nombre}</h4>
              <div><strong>${i.cursos}</strong> curso(s) activos${i.tipo ? ' · ' + i.tipo : ''}</div>
            </div>`);
          c.addTo(layer);
        }
        this.ofertaLayer = layer;
        if (this.capas.ofertaFormativa) layer.addTo(this.map);
      },
      error: () => { /* sin oferta, no rompe el mapa */ },
    });
  }

  /** Ícono diferenciado de festival: estrella en burbuja morada. */
  private festivalIcon(): L.DivIcon {
    return L.divIcon({
      className: 'mapa-festival-marker',
      html: `<div style="background:#8B5CF6;color:#fff;width:24px;height:24px;
              border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);
              display:flex;align-items:center;justify-content:center;
              font-size:13px;line-height:1;">★</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      popupAnchor: [0, -13],
    });
  }

  /** Capa de festivales con punto (FEST-F-11). Lazy: se carga una vez. */
  private cargarFestivales(): void {
    if (this.festivalesLayer) return;
    this.geo.festivalesGeojson().subscribe({
      next: (fc) => {
        if (!this.map) return;
        const layer = L.layerGroup();
        for (const f of fc.features || []) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const m = L.marker([lat, lng], { icon: this.festivalIcon() });
          m.bindPopup(this.festivalPopup(f.properties || {}));
          m.addTo(layer);
        }
        this.festivalesLayer = layer;
        if (this.capas.festivales) layer.addTo(this.map);
      },
      error: () => { /* sin festivales, no rompe el mapa */ },
    });
  }

  private festivalPopup(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    const fechas = [p['fecha_inicio'], p['fecha_fin']].filter(Boolean).join(' → ');
    return `
      <div class="mapa-popup">
        <h4>★ ${p['nombre'] || 'Festival'}</h4>
        ${fila('Tipo', p['tipo_festival'])}
        ${fila('Vigencia', p['vigencia'])}
        ${fila('Estado', p['estado'])}
        ${fila('Fechas', fechas)}
        ${fila('Lugar', p['lugar'])}
        ${fila('Actos', p['n_eventos'])}
      </div>`;
  }

  /** Color por % avance, reutilizable para tramos viales y parques con obra. */
  private colorAvance(pct: number): string {
    if (pct >= 100) return '#16a34a';  // terminado
    if (pct <= 0) return '#dc2626';    // sin iniciar
    return '#f59e0b';                  // parcial
  }

  private fmtMiles(valor: any): string {
    const n = Number(valor);
    if (valor == null || isNaN(n)) return '—';
    return n.toLocaleString('es-CO');
  }

  /** Capa de tramos viales (LineStrings) coloreados por % avance. Lazy. */
  private cargarTramos(): void {
    if (this.tramosLayer) return;
    this.geo.tramosViales().subscribe({
      next: (fc) => {
        if (!this.map) return;
        this.tramosLayer = L.geoJSON(fc as any, {
          style: (feat: any) => ({
            color: this.colorAvance(Number(feat?.properties?.pct_avance) || 0),
            weight: 5,
            opacity: 0.9,
          }),
          onEachFeature: (feat: any, lyr) => {
            lyr.bindPopup(this.tramoPopup(feat?.properties || {}));
          },
        });
        if (this.capas.tramosViales) this.tramosLayer.addTo(this.map);
      },
      error: () => { /* sin tramos, no rompe el mapa */ },
    });
  }

  private tramoPopup(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value || value === 0 ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    const tramo = [p['desde'], p['hasta']].filter(Boolean).join(' → ');
    return `
      <div class="mapa-popup">
        <h4>${p['eje_vial'] || 'Tramo vial'}</h4>
        ${fila('Tramo', tramo)}
        ${fila('CIV', p['civ'])}
        ${fila('Contrato', p['contrato'])}
        ${fila('Valor intervención', '$' + this.fmtMiles(p['valor_intervencion']))}
        ${fila('% avance', (Number(p['pct_avance']) || 0) + '%')}
      </div>`;
  }

  /** Ícono diferenciado de parque con obra: árbol coloreado por % avance. */
  private parqueObraIcon(pct: number): L.DivIcon {
    const color = this.colorAvance(pct);
    return L.divIcon({
      className: 'mapa-obra-marker',
      html: `<div style="background:${color};width:24px;height:24px;border-radius:50%;
              border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);
              display:flex;align-items:center;justify-content:center;
              font-size:13px;line-height:1;">🌳</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      popupAnchor: [0, -13],
    });
  }

  /** Capa de parques con obra (Points) coloreados por % avance. Lazy. */
  private cargarParquesObras(): void {
    if (this.parquesObrasLayer) return;
    this.geo.parquesObras().subscribe({
      next: (fc) => {
        if (!this.map) return;
        const layer = L.layerGroup();
        for (const f of fc.features || []) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const pct = Number(f.properties?.pct_avance) || 0;
          const m = L.marker([lat, lng], { icon: this.parqueObraIcon(pct) });
          m.bindPopup(this.parqueObraPopup(f.properties || {}));
          m.addTo(layer);
        }
        this.parquesObrasLayer = layer;
        if (this.capas.parquesObras) layer.addTo(this.map);
      },
      error: () => { /* sin parques con obra, no rompe el mapa */ },
    });
  }

  private parqueObraPopup(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value || value === 0 ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    return `
      <div class="mapa-popup">
        <h4>🌳 ${p['nombre'] || 'Parque'}</h4>
        ${fila('Código', p['codigo_parque'])}
        ${fila('Contrato', p['contrato'])}
        ${fila('% avance', (Number(p['pct_avance']) || 0) + '%')}
      </div>`;
  }

  private cargarUpzLazy(): void {
    if (this.upzLayer) return;
    this.geo.upzKennedy().subscribe((fc) => {
      this.upzLayer = L.geoJSON(fc as any, {
        style: { color: '#0EA5E9', weight: 1.5, fill: false },
      });
      if (this.capas.upz && this.map) this.upzLayer.addTo(this.map);
    });
  }

  private cargarBarriosLazy(): void {
    if (this.barriosLayer) return;
    this.geo.barriosKennedy().subscribe((fc) => {
      this.barriosLayer = L.geoJSON(fc as any, {
        style: { color: '#8B5CF6', weight: 0.8, fillOpacity: 0.05, fillColor: '#8B5CF6' },
      });
      if (this.capas.barrios && this.map) this.barriosLayer.addTo(this.map);
    });
  }

  private cargarEstratificacionLazy(): void {
    if (this.estratificacionLayer || this.estratificacionCargando) return;
    // 4.966 manzanas recortadas a Kennedy, ~1 MB gzip: se siente. Sin avisar que
    // está cargando, el usuario prende el check, no ve nada y cree que está roto.
    this.estratificacionCargando = true;
    const renderer = L.canvas({ padding: 0.5 });
    this.geo.estratificacionKennedy().subscribe({
      next: (fc) => {
        this.estratificacionCargando = false;
        if (!this.map) return;
        // Una capa vacía no es un caso normal: la tabla tiene ~19k manzanas y el
        // endpoint recorta a las de Kennedy. Cero features = algo está mal, y hay
        // que decirlo en vez de dejar el check prendido sin dibujar nada.
        if (!fc?.features?.length) {
          this.errorMsg.set('Estratificación: el servidor no devolvió manzanas.');
          this.capas.estratificacion = false;
          return;
        }
        this.estratificacionLayer = L.geoJSON(fc as any, {
          // `renderer` va acá dentro y no como opción de la capa: es parte de
          // PathOptions, y así lo tipa @types/leaflet. Leaflet lo aplica igual
          // (setStyle → options.renderer, que beforeAdd lee para elegir canvas).
          style: (f: any) => {
            const color = this.colorEstrato(f?.properties?.estrato);
            return { renderer, color, weight: 0.3, fillColor: color, fillOpacity: 0.55 };
          },
          onEachFeature: (f: any, layer) => {
            const e = f?.properties?.estrato;
            const cod = f?.properties?.codigo_manzana ?? '—';
            layer.bindPopup(
              `<b>Manzana ${cod}</b><br>Estrato: ${e ?? 'sin estrato'}`,
            );
          },
        });
        if (this.capas.estratificacion) this.estratificacionLayer.addTo(this.map);
      },
      error: (e) => {
        // Antes esto se tragaba el error entero: el check quedaba prendido, el
        // mapa vacío y ni una pista de por qué.
        this.estratificacionCargando = false;
        this.capas.estratificacion = false;
        this.errorMsg.set(
          e?.status === 401
            ? 'Estratificación: la sesión expiró, vuelve a entrar.'
            : 'No se pudo cargar la estratificación. Reintenta en un momento.',
        );
      },
    });
  }

  cargarEventos(): void {
    const filtros: EventoFiltros = {
      tipo_evento: this.selectedTipos.length ? this.selectedTipos : undefined,
      subgrupo_id: this.selectedSubgrupos.length
        ? this.selectedSubgrupos.map(Number) : undefined,
      dependencia_id: this.selectedDependencia ?? undefined,
    };
    this.loading.set(true);
    this.geo.eventos(filtros).subscribe({
      next: (fc) => {
        this.eventos.set(fc);
        this.renderEventos();
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg.set('Error cargando eventos.');
        this.loading.set(false);
      },
    });
  }

  renderEventos(): void {
    if (!this.map || !this.eventoLayer) return;
    this.eventoLayer.clearLayers();

    for (const f of this.eventos().features) {
      const p = f.properties;
      if (this.layerVisible[p.tipo_evento_codigo] === false) continue;

      const geom = f.geometry;
      let lat: number | null = null;
      let lng: number | null = null;
      if (geom?.type === 'Point' && Array.isArray(geom.coordinates)) {
        lng = Number(geom.coordinates[0]);
        lat = Number(geom.coordinates[1]);
      }
      if (lat == null || lng == null || isNaN(lat) || isNaN(lng)) continue;

      const color = this.colorTipo(p.tipo_evento_codigo);
      const marker = L.circleMarker([lat, lng], {
        radius: 7,
        weight: 2,
        color: '#fff',
        fillColor: color,
        fillOpacity: 0.95,
      });
      marker.bindPopup(this.popupHtml(p));
      marker.addTo(this.eventoLayer);
    }
  }

  private popupHtml(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    return `
      <div class="mapa-popup">
        <h4>${p['nombre'] || 'Evento'}</h4>
        ${fila('Tipo', this.tipoNombre(p['tipo_evento_codigo']))}
        ${fila('Fecha', p['fecha_inicio'])}
        ${fila('Dependencia', p['dependencia'])}
        ${fila('Subgrupo', p['subgrupo'])}
        ${fila('Funcionario', p['funcionario'])}
        ${fila('Dirección', p['direccion'])}
        ${fila('KPI', p['indicador'])}
        ${fila('Magnitud aportada', p['magnitud_aportada'])}
        ${p['caracterizaciones'] ? fila('Caracterizaciones', p['caracterizaciones'].total + (p['caracterizaciones'].sector ? ' · ' + p['caracterizaciones'].sector : '')) : ''}
      </div>
    `;
  }

  // ── UI handlers ─────────────────────────────────────────────────
  onFiltrosChange(): void {
    this.cargarEventos();
  }

  /** Multi-selección por clic simple (sin Ctrl) para Tipo de evento. */
  toggleTipo(codigo: string): void {
    const i = this.selectedTipos.indexOf(codigo);
    this.selectedTipos = i === -1
      ? [...this.selectedTipos, codigo]
      : this.selectedTipos.filter(c => c !== codigo);
    this.cargarEventos();
  }

  /** Multi-selección por clic simple (sin Ctrl) para Subgrupo. */
  toggleSubgrupo(id: number): void {
    const i = this.selectedSubgrupos.indexOf(id);
    this.selectedSubgrupos = i === -1
      ? [...this.selectedSubgrupos, id]
      : this.selectedSubgrupos.filter(s => s !== id);
    this.cargarEventos();
  }
  onDependenciaChange(): void {
    // limpia subgrupos al cambiar dependencia
    this.selectedSubgrupos = [];
    this.cargarEventos();
  }
  onBuscar(): void { /* filtro client-side a través de computed */ }

  limpiarFiltros(): void {
    this.query = '';
    this.selectedTipos = [];
    this.selectedSubgrupos = [];
    this.selectedDependencia = null;
    this.subgrupoTab.set(null);
    this.cargarEventos();
  }

  setSubgrupoTab(id: number | null): void {
    this.subgrupoTab.set(id);
    this.selectedSubgrupos = id ? [id] : [];
    // El equipamiento es propio de cada subgrupo (decisión Alex 2026-06-03):
    //   Cultura → solo Escuelas de Cultura.
    //   Deporte → solo Escuelas de Deporte.
    //   Otros / Todos → sin equipamiento (cada subgrupo es distinto).
    const nombre = id
      ? (this.subgruposInversion().find(s => s.id === id)?.nombre || '').toLowerCase()
      : '';
    this.capas.escuelasCultura = nombre === 'cultura';
    this.capas.escuelasDeporte = nombre === 'deporte';
    this.toggleCapa('escuelasCultura');
    this.toggleCapa('escuelasDeporte');
    this.cargarEventos();
  }

  toggleCapa(
    nombre: 'parques' | 'barrios' | 'upz' | 'localidad'
          | 'escuelasCultura' | 'escuelasDeporte' | 'ofertaFormativa'
          | 'festivales' | 'tramosViales' | 'parquesObras' | 'estratificacion',
  ): void {
    if (!this.map) return;
    const on = (this.capas as any)[nombre];
    if (nombre === 'estratificacion') {
      if (on) { this.cargarEstratificacionLazy(); this.estratificacionLayer?.addTo(this.map); }
      else this.estratificacionLayer?.remove();
      return;
    }
    if (nombre === 'ofertaFormativa') {
      if (on) { this.cargarOfertaFormativa(); this.ofertaLayer?.addTo(this.map); }
      else this.ofertaLayer?.remove();
      return;
    }
    if (nombre === 'festivales') {
      if (on) { this.cargarFestivales(); this.festivalesLayer?.addTo(this.map); }
      else this.festivalesLayer?.remove();
      return;
    }
    if (nombre === 'tramosViales') {
      if (on) { this.cargarTramos(); this.tramosLayer?.addTo(this.map); }
      else this.tramosLayer?.remove();
      return;
    }
    if (nombre === 'parquesObras') {
      if (on) { this.cargarParquesObras(); this.parquesObrasLayer?.addTo(this.map); }
      else this.parquesObrasLayer?.remove();
      return;
    }
    if (nombre === 'parques') {
      if (on && this.parquesLayer) this.parquesLayer.addTo(this.map);
      else this.parquesLayer?.remove();
    } else if (nombre === 'barrios') {
      if (on) {
        this.cargarBarriosLazy();
        this.barriosLayer?.addTo(this.map);
      } else this.barriosLayer?.remove();
    } else if (nombre === 'upz') {
      if (on) {
        this.cargarUpzLazy();
        this.upzLayer?.addTo(this.map);
      } else this.upzLayer?.remove();
    } else if (nombre === 'localidad') {
      if (on && this.contornoLayer) this.contornoLayer.addTo(this.map);
      else this.contornoLayer?.remove();
    } else if (nombre === 'escuelasCultura') {
      if (on && this.escuelasCulturaLayer) this.escuelasCulturaLayer.addTo(this.map);
      else this.escuelasCulturaLayer?.remove();
    } else if (nombre === 'escuelasDeporte') {
      if (on && this.escuelasDeporteLayer) this.escuelasDeporteLayer.addTo(this.map);
      else this.escuelasDeporteLayer?.remove();
    }
  }

  centrar(f: GeoFeature): void {
    if (!this.map) return;
    const g = f.geometry;
    if (g?.type === 'Point' && Array.isArray(g.coordinates)) {
      this.map.setView([Number(g.coordinates[1]), Number(g.coordinates[0])], 16);
    }
  }

  colorTipo(codigo: string): string {
    const t = this.catalogos()?.tipos_evento.find(x => x.codigo === codigo);
    return t?.color_hex || '#6B7280';
  }

  tipoNombre(codigo: string): string {
    const t = this.catalogos()?.tipos_evento.find(x => x.codigo === codigo);
    return t?.nombre || codigo || '—';
  }
}

// Cast local porque el modelo del backend tiene optional fields
type MapaCatalogosLocal = {
  upz: any[];
  barrios: any[];
  tipos_evento: TipoEventoLite[];
  dependencias: any[];
  subgrupos: SubgrupoLite[];
  subgrupos_inversion_local: SubgrupoLite[];
  conteos_subgrupo: Record<number, ConteoSubgrupo>;
};
