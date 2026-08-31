import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild,
  computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { LucideAngularModule } from 'lucide-angular';
import { LayoutService } from '../../core/layout/layout.service';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { StatGridComponent, StatItem } from '../../shared/ui/stat-grid.component';
import { ActionNoticeComponent } from '../../shared/ui/action-notice.component';

interface Institucion {
  id: number;
  codigo_snies: string;
  nombre: string;
  tipo_registro: 'SNIES' | 'SIET';
  ciudad: string | null;
  latitud: number | null;
  longitud: number | null;
  ubicada: boolean;
  origen: 'CARGUE' | 'MANUAL';
  activa: boolean;
  observacion: string | null;
  personas: number;
  matriculas: number;
  programas: number;
}

interface Programa {
  id: number;
  codigo_snies: string;
  nombre: string;
  nivel_formacion: string | null;
  nivel_etiqueta: string | null;
  personas: number;
  matriculas: number;
}

interface Detalle extends Institucion {
  programas_lista?: Programa[];
  por_vigencia: Record<string, number>;
}

interface Listado {
  instituciones: Institucion[];
  vigencia: number | null;
  vigencias: number[];
  sin_ubicar: number;
  precision: string;
  desglose_nivel: {
    niveles: { nivel: string; etiqueta: string; es_superior: boolean;
               matriculas: number; personas: number }[];
    personas_total: number;
    superior: { matriculas: number; personas: number };
    etdh: { matriculas: number; personas: number };
    personas_en_ambos_grupos: number;
  };
}

/**
 * Instituciones de educación posmedia — mapa y panel en una sola pantalla.
 *
 * Backend: `apps/educacion/api/instituciones.py`.
 *
 * ## Por qué acá y no dentro de `/app/mapa`
 *
 * El mapa general es de la LOCALIDAD y tiene pestañas por subgrupo; estas
 * instituciones están mayormente fuera de Kennedy —La Sabana está en Chía— y un
 * CRUD adentro desvirtuaría esa pantalla. La pestaña de Educación del mapa
 * general consume el MISMO endpoint para pintar su capa y enlaza acá para
 * gestionar: un solo desarrollo, una sola fuente.
 *
 * ## Encuadre
 *
 * Arranca en Kennedy —que es donde está el área y donde quedan los institutos
 * de ETDH— y ofrece «ver todas», que hace `fitBounds` sobre los puntos
 * cargados. Es lo más barato que respeta las dos naturalezas: las universitarias
 * están en el norte y el centro, y forzar un encuadre que las abarque siempre
 * dejaría Kennedy como un punto diminuto.
 *
 * ## Habeas data
 *
 * Solo agregados. Ni esta pantalla ni su backend devuelven listados de personas
 * identificadas: un mapa se proyecta en reuniones y se captura en pantalla.
 *
 * ## Diseño
 *
 * Reusa el sistema existente: `.page`, `.ui-card`, `.ui-table`, `.ui-badge`,
 * `.ui-empty-state`, `.ui-filter-bar` y el vocabulario `.mapa-*` del mapa
 * general. Los iconos son lucide (Font Awesome no carga en este proyecto).
 */
@Component({
  standalone: true,
  selector: 'app-educacion-instituciones',
  imports: [
    CommonModule, FormsModule, RouterLink, LucideAngularModule,
    PageHeaderComponent, StatGridComponent, ActionNoticeComponent,
  ],
  template: `
    <div class="page">
      <app-page-header title="Instituciones de educación posmedia"
                       description="Dónde estudian los beneficiarios del proyecto, y qué programas cursan.">
        <a header-actions routerLink="/educacion" class="ui-btn ui-btn--ghost">
          Ver colegios distritales
        </a>
      </app-page-header>

      @if (error()) { <p class="ui-info-bar ui-info-bar--danger">{{ error() }}</p> }

      @if (data(); as d) {
        <!-- Cifras: siempre las dos lecturas -->
        <app-stat-grid [stats]="kpiStats(d)" />

        @if (d.desglose_nivel.personas_en_ambos_grupos > 0) {
          <p class="ui-info-bar ui-info-bar--warning">
            {{ d.desglose_nivel.personas_en_ambos_grupos }} persona(s) tienen matrícula
            en educación superior y en ETDH: aparecen contadas en los dos grupos, por eso
            la suma da más que el total.
          </p>
        }

        <!-- Filtros -->
        <div class="ui-filter-bar">
          <label class="ui-field">
            <span class="ui-field__label">Vigencia</span>
            <select class="ui-input" [(ngModel)]="vigencia" (change)="cargar()">
              <option [ngValue]="null">Acumulado</option>
              @for (v of d.vigencias; track v) { <option [ngValue]="v">{{ v }}</option> }
            </select>
          </label>
          <label class="ui-field">
            <span class="ui-field__label">Tipo</span>
            <select class="ui-input" [(ngModel)]="tipo" (change)="cargar()">
              <option value="">Todas</option>
              <option value="SNIES">Superior (SNIES)</option>
              <option value="SIET">ETDH (SIET)</option>
            </select>
          </label>
          <label class="ui-field">
            <span class="ui-field__label">Buscar</span>
            <input class="ui-input" [(ngModel)]="query" placeholder="Nombre o código">
          </label>
          <label class="ui-field">
            <span class="ui-field__label">&nbsp;</span>
            <label class="ui-check">
              <input type="checkbox" [(ngModel)]="soloSinUbicar"> Solo sin ubicar
            </label>
          </label>
          <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" (click)="verTodas()">
            <lucide-icon name="map-pin" size="16"></lucide-icon> Ver todas en el mapa
          </button>
          <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" (click)="sincronizar()">
            <lucide-icon name="rotate-ccw" size="16"></lucide-icon> Traer las de los cargues
          </button>
        </div>

        @if (vigencia === null) {
          <app-action-notice variant="info" title="Acumulado"
            description="Personas distintas en todo el período. No es la suma de las vigencias — quien recibe beneficio dos años es una persona, no dos." />
        }

        <!-- Mapa + panel -->
        <div class="edu-split">
          <article class="ui-card edu-split__mapa">
            <div class="ui-card__body">
              <div #mapEl class="mapa-leaflet" role="application"
                   aria-label="Mapa de las instituciones donde estudian los beneficiarios."></div>
              <p class="page__subtitle">{{ d.precision }}</p>
            </div>
          </article>

          <article class="ui-card edu-split__panel">
            <div class="ui-card__body">
              @if (!visibles().length) {
                <div class="ui-empty-state">
                  <p class="ui-empty-state__title">Sin instituciones</p>
                  <p class="ui-empty-state__text">
                    El catálogo se llena solo con cada cargue de beneficiarios.
                    Use «Traer las de los cargues» si ya cargó y no aparecen.
                  </p>
                </div>
              } @else {
                <div class="ui-table-responsive">
                  <table class="ui-table">
                    <thead>
                      <tr>
                        <th>Institución</th><th>Ciudad</th><th>Tipo</th>
                        <th class="num">Progr.</th><th class="num">Benef.</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (i of visibles(); track i.id) {
                        <tr [class.edu-row--sel]="seleccion()?.id === i.id"
                            (click)="seleccionar(i)">
                          <td>
                            {{ i.nombre }}
                            @if (!i.ubicada) {
                              <span class="ui-badge ui-badge--muted">sin ubicar</span>
                            }
                          </td>
                          <td>{{ i.ciudad || '—' }}</td>
                          <td>
                            <span class="ui-badge" [class.ui-badge--info]="i.tipo_registro === 'SNIES'">
                              {{ i.tipo_registro === 'SNIES' ? 'Superior' : 'ETDH' }}
                            </span>
                          </td>
                          <td class="num">{{ i.programas }}</td>
                          <td class="num">{{ i.personas }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            </div>
          </article>
        </div>

        <!-- Detalle -->
        @if (detalle(); as det) {
          <article class="ui-card ui-card--accent">
            <div class="ui-card__body">
              <h2>{{ det.nombre }} <span class="ui-badge ui-badge--muted">{{ det.codigo_snies }}</span></h2>

              <div class="ui-filter-bar">
                <label class="ui-field">
                  <span class="ui-field__label">Nombre</span>
                  <input class="ui-input" [(ngModel)]="edicion.nombre">
                </label>
                <label class="ui-field">
                  <span class="ui-field__label">Ciudad</span>
                  <input class="ui-input" [(ngModel)]="edicion.ciudad">
                </label>
                <label class="ui-field">
                  <span class="ui-field__label">Latitud</span>
                  <input class="ui-input" type="number" step="0.000001" [(ngModel)]="edicion.latitud">
                </label>
                <label class="ui-field">
                  <span class="ui-field__label">Longitud</span>
                  <input class="ui-input" type="number" step="0.000001" [(ngModel)]="edicion.longitud">
                </label>
                <button type="button" class="ui-btn ui-btn--primary ui-btn--sm" (click)="guardar()">
                  Guardar
                </button>
              </div>
              <p class="page__subtitle">
                Las coordenadas van juntas. Si no las tiene, déjelas vacías: queda
                «sin ubicar» y se puede completar después.
              </p>

              @if (det.programas_lista?.length) {
                <div class="ui-table-responsive">
                  <table class="ui-table">
                    <thead>
                      <tr><th>Programa</th><th>Nivel</th><th class="num">Alumnos</th></tr>
                    </thead>
                    <tbody>
                      @for (p of det.programas_lista; track p.id) {
                        <tr>
                          <td>{{ p.nombre }} <span class="ui-badge ui-badge--muted">{{ p.codigo_snies }}</span></td>
                          <td>{{ p.nivel_etiqueta || '—' }}</td>
                          <td class="num">{{ p.personas }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            </div>
          </article>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    /* Composición, no estilos nuevos: el split y la fila seleccionada son lo
       único que el sistema no tiene, y se apoyan en sus tokens. */
    .edu-split { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
    @media (max-width: 900px) { .edu-split { grid-template-columns: 1fr; } }
    .edu-split__mapa .mapa-leaflet { height: 460px; border-radius: 8px; }
    .edu-split__panel .ui-table tbody tr { cursor: pointer; }
    .edu-row--sel td { background: $color-primary-bg; }
    .ui-table .num { text-align: right; }
  `],
})
export class EducacionInstitucionesComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('mapEl') mapEl?: ElementRef<HTMLDivElement>;
  private http = inject(HttpClient);
  private layout = inject(LayoutService);
  private readonly base = '/educacion/api/instituciones';

  kpiStats(d: Listado): StatItem[] {
    return [
      { value: d.desglose_nivel.personas_total, label: 'Beneficiarios' },
      { value: d.desglose_nivel.superior.personas, label: 'Educación superior' },
      { value: d.desglose_nivel.etdh.personas, label: 'ETDH' },
      { value: d.instituciones.length, label: 'Instituciones' },
      { value: d.sin_ubicar, label: 'Sin ubicar', variant: d.sin_ubicar > 0 ? 'warn' : undefined },
    ];
  }

  data = signal<Listado | null>(null);
  detalle = signal<Detalle | null>(null);
  seleccion = signal<Institucion | null>(null);
  error = signal<string | null>(null);

  vigencia: number | null = null;
  tipo = '';
  query = '';
  soloSinUbicar = false;
  edicion: any = {};

  private map?: L.Map;
  private capa?: L.LayerGroup;
  private marcadores = new Map<number, L.CircleMarker>();

  visibles = computed(() => {
    const d = this.data();
    if (!d) return [];
    const q = this.query.trim().toLowerCase();
    return d.instituciones.filter((i) => {
      if (this.soloSinUbicar && i.ubicada) return false;
      if (!q) return true;
      return `${i.nombre} ${i.codigo_snies}`.toLowerCase().includes(q);
    });
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Educación', url: '/educacion' },
      { label: 'Instituciones posmedia' },
    ]);
    this.cargar();
  }

  ngAfterViewInit(): void {
    if (!this.mapEl) return;
    // Arranca en Kennedy: es donde está el área y donde quedan los institutos
    // de ETDH. Las universitarias se alcanzan con «ver todas».
    this.map = L.map(this.mapEl.nativeElement).setView([4.628, -74.16], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
                { maxZoom: 19, attribution: '© OpenStreetMap © CARTO' }).addTo(this.map);
    this.pintar();
  }

  ngOnDestroy(): void { this.map?.remove(); }

  cargar(): void {
    const params: string[] = [];
    if (this.vigencia) params.push(`vigencia=${this.vigencia}`);
    if (this.tipo) params.push(`tipo=${this.tipo}`);
    const qs = params.length ? `?${params.join('&')}` : '';
    this.http.get<Listado>(`${this.base}/${qs}`).subscribe({
      next: (d) => { this.data.set(d); this.error.set(null); this.pintar(); },
      error: (e) => this.error.set(
        e?.error?.detail || 'No se pudo cargar el catálogo de instituciones.'),
    });
  }

  private pintar(): void {
    if (!this.map || !this.data()) return;
    this.capa?.remove();
    this.marcadores.clear();
    const grupo = L.layerGroup();
    for (const i of this.data()!.instituciones) {
      if (!i.ubicada) continue;
      const m = L.circleMarker([i.latitud!, i.longitud!], {
        radius: Math.min(6 + i.personas / 3, 18),
        // Categoría de dato, no marca: mismo azul que ya usa el badge "Superior"
        // de la tabla ($color-info) / mismo verde que $color-success para ETDH.
        // Antes usaba rojo/amarillo institucional — reservados para identidad.
        color: i.tipo_registro === 'SIET' ? '#16A34A' : '#3B82F6',
        fillColor: i.tipo_registro === 'SIET' ? '#4ADE80' : '#60A5FA',
        fillOpacity: 0.75, weight: 2,
      }).bindPopup(
        `<strong>${i.nombre}</strong><br>${i.ciudad || 'ciudad sin registrar'}<br>` +
        `${i.personas} beneficiario(s) · ${i.programas} programa(s)`);
      m.on('click', () => this.seleccionar(i));
      m.addTo(grupo);
      this.marcadores.set(i.id, m);
    }
    grupo.addTo(this.map);
    this.capa = grupo;
  }

  seleccionar(i: Institucion): void {
    this.seleccion.set(i);
    this.edicion = { nombre: i.nombre, ciudad: i.ciudad,
                     latitud: i.latitud, longitud: i.longitud };
    const m = this.marcadores.get(i.id);
    if (m && this.map) { this.map.panTo(m.getLatLng()); m.openPopup(); }
    const q = this.vigencia ? `?vigencia=${this.vigencia}` : '';
    this.http.get<any>(`${this.base}/${i.id}/${q}`).subscribe({
      next: (d) => this.detalle.set({ ...d, programas_lista: d.programas }),
      error: () => this.detalle.set(null),
    });
  }

  verTodas(): void {
    const puntos = [...this.marcadores.values()].map((m) => m.getLatLng());
    if (this.map && puntos.length) this.map.fitBounds(L.latLngBounds(puntos).pad(0.15));
  }

  guardar(): void {
    const sel = this.seleccion();
    if (!sel) return;
    this.http.patch<Institucion>(`${this.base}/${sel.id}/`, this.edicion).subscribe({
      next: () => { this.cargar(); this.seleccionar(sel); },
      error: (e) => this.error.set(e?.error?.detail || 'No se pudo guardar.'),
    });
  }

  sincronizar(): void {
    this.http.post<any>(`${this.base}/sincronizar/`, { aplicar: true }).subscribe({
      next: (r) => {
        this.cargar();
        if (r.avisos?.length) this.error.set(r.avisos.join(' · '));
      },
      error: (e) => this.error.set(e?.error?.detail || 'No se pudo sincronizar.'),
    });
  }
}
