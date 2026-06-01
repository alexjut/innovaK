import { CommonModule } from '@angular/common';
import {
  AfterViewInit, ChangeDetectionStrategy, Component, ElementRef,
  OnDestroy, OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import * as L from 'leaflet';
import { forkJoin } from 'rxjs';
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

            <label class="mapa-field">
              <span>Tipo de evento</span>
              <select multiple size="4" [(ngModel)]="selectedTipos" (change)="onFiltrosChange()">
                @for (t of catalogos()?.tipos_evento ?? []; track t.codigo) {
                  <option [value]="t.codigo">{{ t.nombre }}</option>
                }
              </select>
            </label>

            <label class="mapa-field">
              <span>Dependencia</span>
              <select [(ngModel)]="selectedDependencia" (change)="onDependenciaChange()">
                <option [ngValue]="null">— Todas —</option>
                @for (d of catalogos()?.dependencias ?? []; track d.id) {
                  <option [ngValue]="d.id">{{ d.nombre }}</option>
                }
              </select>
            </label>

            <label class="mapa-field">
              <span>Subgrupo</span>
              <select multiple size="4" [(ngModel)]="selectedSubgrupos"
                      (change)="onFiltrosChange()">
                @for (s of subgruposFiltrados(); track s.id) {
                  <option [value]="s.id">{{ s.nombre }}</option>
                }
              </select>
            </label>

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
              <input type="checkbox" [(ngModel)]="capas.localidad" (change)="toggleCapa('localidad')">
              <span class="mapa-line mapa-line--localidad"></span> Localidad
            </label>
            <hr>
            <small class="mapa-side__hint">Equipamiento</small>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.escuelasCultura"
                     (change)="toggleCapa('escuelasCultura')">
              <span class="mapa-square mapa-square--cultura"></span> Escuelas Cultura
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.escuelasDeporte"
                     (change)="toggleCapa('escuelasDeporte')">
              <span class="mapa-square mapa-square--deporte"></span> Escuelas Deporte
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.lugares"
                     (change)="toggleCapa('lugares')">
              <span class="mapa-dot" style="background:#A855F7"></span> Lugares
            </label>
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
                  <td>{{ f.properties.dependencia_nombre || '—' }}</td>
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
    escuelasCultura: true, escuelasDeporte: true, lugares: false,
  };

  // ── Estado Leaflet ──────────────────────────────────────────────
  private map?: L.Map;
  private eventoLayer?: L.LayerGroup;
  private contornoLayer?: L.GeoJSON;
  private upzLayer?: L.GeoJSON;
  private barriosLayer?: L.GeoJSON;
  private parquesLayer?: L.GeoJSON;
  private escuelasCulturaLayer?: L.LayerGroup;
  private escuelasDeporteLayer?: L.LayerGroup;
  private lugaresLayer?: L.LayerGroup;

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
      const hay = [p.nombre, p.direccion, p.dependencia_nombre, p.funcionario_nombre]
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
        this.cargarLugares();
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

  private cargarLugares(): void {
    if (this.lugaresLayer) return;
    this.geo.lugares().subscribe({
      next: (fc) => {
        if (!this.map) return;
        const grp = L.layerGroup();
        for (const f of fc.features) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const m = L.circleMarker([lat, lng], {
            radius: 4, weight: 1, color: '#A855F7',
            fillColor: '#A855F7', fillOpacity: 0.8,
          });
          m.bindPopup(`
            <div class="mapa-popup">
              <h4>${f.properties?.nombre || 'Lugar'}</h4>
              ${f.properties?.direccion ? `<div>${f.properties.direccion}</div>` : ''}
            </div>`);
          m.addTo(grp);
        }
        this.lugaresLayer = grp;
        if (this.capas.lugares && this.map) grp.addTo(this.map);
      },
      error: () => { /* sin lugares, no rompe el mapa */ },
    });
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
        ${fila('Dependencia', p['dependencia_nombre'])}
        ${fila('Subgrupo', p['subgrupo_nombre'])}
        ${fila('Funcionario', p['funcionario_nombre'])}
        ${fila('Dirección', p['direccion'])}
        ${fila('KPI', p['indicador_nombre'])}
      </div>
    `;
  }

  // ── UI handlers ─────────────────────────────────────────────────
  onFiltrosChange(): void {
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
    // Heurística N18 (subgrupos Inversión Local):
    //   Cultura   → escuelas Cultura + lugares (sitios culturales).
    //   Deporte   → escuelas Deporte (los lugares no aplican).
    //   Educación → escuelas Cultura + Deporte + lugares (se hacen
    //               actividades educativas en ambos tipos de espacio).
    //   Todos / otros → muestra ambas escuelas + lugares.
    const nombre = id
      ? (this.subgruposInversion().find(s => s.id === id)?.nombre || '').toLowerCase()
      : '';
    if (nombre === 'cultura') {
      this.capas.escuelasCultura = true;
      this.capas.escuelasDeporte = false;
      this.capas.lugares = true;
    } else if (nombre === 'deporte') {
      this.capas.escuelasCultura = false;
      this.capas.escuelasDeporte = true;
      this.capas.lugares = false;
    } else if (nombre === 'educación' || nombre === 'educacion') {
      this.capas.escuelasCultura = true;
      this.capas.escuelasDeporte = true;
      this.capas.lugares = true;
    } else {
      this.capas.escuelasCultura = true;
      this.capas.escuelasDeporte = true;
      this.capas.lugares = true;
    }
    this.toggleCapa('escuelasCultura');
    this.toggleCapa('escuelasDeporte');
    this.toggleCapa('lugares');
    this.cargarEventos();
  }

  toggleCapa(
    nombre: 'parques' | 'barrios' | 'upz' | 'localidad'
          | 'escuelasCultura' | 'escuelasDeporte' | 'lugares',
  ): void {
    if (!this.map) return;
    const on = (this.capas as any)[nombre];
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
    } else if (nombre === 'lugares') {
      if (on) {
        this.cargarLugares();
        this.lugaresLayer?.addTo(this.map);
      } else this.lugaresLayer?.remove();
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
