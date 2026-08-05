import { CommonModule } from '@angular/common';
import {
  AfterViewInit, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { CaiProps, GeoService } from '../../core/geo/geo.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Los CAI de Kennedy, dentro del área de Seguridad.
 *
 * Vive acá y no en `/mapa` a propósito: los CAI son de Seguridad, y mandar su
 * tarjeta al mapa general dejaba al área buscando su capa entre una docena de
 * checkboxes que son de las demás. El mapa público sigue teniendo la capa
 * —es información para el ciudadano— pero la herramienta del área es esta.
 *
 * El mapa de esta pantalla muestra SOLO los CAI: sin parques, sin escuelas,
 * sin festivales.
 */
@Component({
  standalone: true,
  selector: 'app-area-cai',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <a [routerLink]="['/mi-area', areaSlug]" class="ui-back-link">
            <i class="fa fa-arrow-left"></i> Seguridad
          </a>
          <h1><i class="fa fa-shield-halved" aria-hidden="true"></i> CAI de Kennedy</h1>
          <p class="page__sub">
            Fuente: Secretaría Distrital de Seguridad, Convivencia y Justicia.
            @if (corte()) { <span>Corte {{ corte() }}.</span> }
          </p>
        </div>
      </header>

      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }

      <section class="kpis">
        <div class="kpi">
          <span class="kpi__val">{{ fijos().length }}</span>
          <span class="kpi__lbl">CAI fijos</span>
        </div>
        <div class="kpi" [class.kpi--warn]="!moviles().length">
          <span class="kpi__val">{{ moviles().length }}</span>
          <span class="kpi__lbl">CAI móviles</span>
        </div>
      </section>

      @if (!moviles().length && !loading()) {
        <!-- Se dice en vez de callarlo: un cero sin explicación se lee como
             "no hay", y lo que pasa es que la fuente oficial no los publica. -->
        <div class="ui-info-bar ui-info-bar--warn">
          <strong>La fuente oficial no publica CAI móviles.</strong>
          La capa de la Secretaría de Seguridad conoce la distinción (tiene el
          código <code>00 = MOVILES</code>) pero hoy devuelve cero móviles en
          toda Bogotá. Los móviles de Kennedy hay que cargarlos a mano: quedan
          marcados como <code>MANUAL</code> y la sincronización no los pisa.
        </div>
      }

      <div class="split">
        <div #mapEl class="mapa" role="application"
             aria-label="Mapa de los CAI de Kennedy"></div>

        <div class="lista">
          <label class="ui-field">
            <span>Buscar</span>
            <input class="ui-input" type="search" [(ngModel)]="q"
                   placeholder="Nombre, dirección o código…">
          </label>
          <table class="ui-table">
            <thead>
              <tr><th>CAI</th><th>Dirección</th><th>Teléfono</th></tr>
            </thead>
            <tbody>
              @for (c of visibles(); track c.codigo) {
                <tr role="button" tabindex="0"
                    (click)="centrar(c)" (keyup.enter)="centrar(c)">
                  <td>
                    <span class="tipo" [class.tipo--movil]="c.es_movil">
                      {{ c.es_movil ? 'móvil' : 'fijo' }}
                    </span>
                    {{ c.nombre }}
                    <small>{{ c.codigo }}</small>
                  </td>
                  <td>{{ c.direccion || '—' }}</td>
                  <td>{{ c.telefono || '—' }}</td>
                </tr>
              } @empty {
                <tr><td colspan="3" class="muted">Ningún CAI coincide.</td></tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .split { display: grid; grid-template-columns: minmax(280px, 1fr) 1.2fr; gap: 1.5rem; }
    @media (max-width: 900px) { .split { grid-template-columns: 1fr; } }
    .mapa { height: 520px; border-radius: 8px; }
    .tipo {
      font-size: .68rem; padding: .1rem .45rem; border-radius: 999px;
      background: #065F46; color: #fff; margin-right: .35rem;
    }
    .tipo--movil { background: #D97706; }
    td small { display: block; color: var(--color-text-muted,#6b7280); font-size: .72rem; }
    tbody tr { cursor: pointer; }
    .muted { color: var(--color-text-muted,#6b7280); }
  `],
})
export class AreaCaiComponent implements OnInit, AfterViewInit, OnDestroy {
  private geo = inject(GeoService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  @ViewChild('mapEl') mapEl!: ElementRef<HTMLDivElement>;

  areaSlug = '';
  q = '';
  cais = signal<CaiProps[]>([]);
  loading = signal<boolean>(true);
  error = signal<string>('');

  private map?: L.Map;
  private marcadores = new Map<string, L.Marker>();

  fijos = computed(() => this.cais().filter((c) => !c.es_movil));
  moviles = computed(() => this.cais().filter((c) => c.es_movil));
  corte = computed(() => this.cais().find((c) => c.fecha_corte)?.fecha_corte ?? null);

  visibles = computed<CaiProps[]>(() => {
    const t = this.q.trim().toLowerCase();
    if (!t) return this.cais();
    return this.cais().filter((c) =>
      [c.nombre, c.direccion, c.codigo].filter(Boolean).join(' ').toLowerCase().includes(t));
  });

  ngOnInit(): void {
    this.areaSlug = this.route.snapshot.paramMap.get('slug') || '';
    // Inicio › Mi área › Seguridad › CAI  ==  /app/mi-area/seguridad/cai
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mi área', url: '/mi-area' },
      { label: 'Seguridad', url: `/mi-area/${this.areaSlug}` },
      { label: 'CAI' },
    ]);
  }

  ngAfterViewInit(): void {
    this.map = L.map(this.mapEl.nativeElement).setView([4.628, -74.155], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      { attribution: '© OpenStreetMap, © CARTO', maxZoom: 19 }).addTo(this.map);
    this.cargar();
  }

  ngOnDestroy(): void { this.map?.remove(); }

  private cargar(): void {
    this.geo.cai().subscribe({
      next: (r) => {
        this.loading.set(false);
        if (r.disponible === false) {
          this.error.set('Todavía no hay CAI cargados. Se traen de la fuente '
            + 'oficial con manage.py sync_cai.');
          return;
        }
        const props = (r.features || []).map((f) => f.properties as CaiProps);
        this.cais.set(props);
        this.pintar(r.features || []);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('No se pudieron cargar los CAI.');
      },
    });
  }

  private pintar(features: { geometry: any; properties: any }[]): void {
    if (!this.map) return;
    const puntos: L.LatLngExpression[] = [];
    for (const f of features) {
      const g = f.geometry;
      if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
      const lat = Number(g.coordinates[1]);
      const lng = Number(g.coordinates[0]);
      if (isNaN(lat) || isNaN(lng)) continue;
      const p = f.properties as CaiProps;
      const m = L.marker([lat, lng], { icon: this.icono(p.es_movil) })
        .bindPopup(`<div class="mapa-popup"><h4>${p.nombre}</h4>`
          + `<div>${p.es_movil ? 'Móvil' : 'Fijo'} · <small>${p.codigo}</small></div>`
          + (p.direccion ? `<div>${p.direccion}</div>` : '')
          + (p.telefono ? `<div><small>Tel. ${p.telefono}</small></div>` : '')
          + '</div>')
        .addTo(this.map);
      this.marcadores.set(p.codigo, m);
      puntos.push([lat, lng]);
    }
    if (puntos.length) this.map.fitBounds(L.latLngBounds(puntos).pad(0.15));
  }

  /** Mismo criterio que en el mapa general: forma Y color, no solo color. */
  private icono(movil: boolean): L.DivIcon {
    return L.divIcon({
      className: 'mapa-cai-marker',
      html: `<div style="background:${movil ? '#D97706' : '#065F46'};color:#fff;
              width:26px;height:26px;border-radius:${movil ? '50%' : '4px'};
              border:2px solid #fff;${movil ? 'border-style:dashed;' : ''}
              box-shadow:0 1px 4px rgba(0,0,0,.4);display:flex;
              align-items:center;justify-content:center;font-size:13px;
              line-height:1;">${movil ? '🚓' : '🛡'}</div>`,
      iconSize: [28, 28], iconAnchor: [14, 14], popupAnchor: [0, -14],
    });
  }

  centrar(c: CaiProps): void {
    const m = this.marcadores.get(c.codigo);
    if (m && this.map) {
      this.map.setView(m.getLatLng(), 16);
      m.openPopup();
    }
  }
}
