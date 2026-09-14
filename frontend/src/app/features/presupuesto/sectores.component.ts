import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { errorDeCarga, ErrorDeCarga } from './estado-carga';

/** Una fila de avance por sector = subgrupo (Inversión Local). */
interface SectorAvance {
  subgrupo_id: number;
  sector: string;
  n_proyectos: number;
  n_kpis: number;
  /** Actividades DEL PLAN de los proyectos del subgrupo. */
  n_actividades: number;
  /** Eventos ejecutados, agrupados por el subgrupo del EVENTO. Otro eje. */
  n_eventos: number;
  avance: number;
  meta: number;
  porcentaje: number | null;
  /** Cuántos de sus KPIs tienen algo reportado por el área. */
  kpis_cargados: number;
  pct_cargue: number | null;
}

/** Un KPI del sector, con las dos medidas enfrentadas. */
interface KpiComparado {
  kpi_id: number;
  nombre: string;
  unidad_medida: string | null;
  meta_magnitud: number;
  reportado: number;
  n_reportes: number;
  ultimo_reporte: string | null;
  cargado: boolean;
  pct_area: number | null;
  pct_matriz: number | null;
  diferencia: number | null;
  meta_codigo: string | null;
  proyecto_codigo: string | null;
  proyecto_nombre: string | null;
}
interface DetalleSector {
  kpis: KpiComparado[];
  resumen: {
    n_kpis: number;
    n_cargados: number;
    n_comparables: number;
    brecha_media: number | null;
  };
}

/**
 * Avance por SECTOR (subgrupo) — alineación con el Visor SDP-PDL.
 * Consume `/dashboard/api/v2/presupuesto/avance-por-sector/` (JWT-first).
 * El sector es el subgrupo del proyecto, NO `metas.sector` (vacío).
 *
 * LAS DOS MEDIDAS (2026-09-14). La pantalla enseña dos cosas distintas y las
 * llama por su nombre:
 *
 *   · **La Matriz** — el % de cumplimiento oficial, el que sale de las
 *     fuentes. Es el número de cabecera y no lo mueve nadie desde acá.
 *   · **El cargue del área** — cuántos de sus KPIs tienen algo reportado.
 *     NO es un % de cumplimiento: es cobertura. A nivel de sector no se puede
 *     dar otra cosa sin mentir, porque sumar magnitudes de KPIs distintos
 *     mezcla árboles, m² y personas en el mismo denominador.
 *
 * La comparación de verdad —cuánto dice el área contra cuánto dice la
 * Matriz— vive un piso más abajo, al abrir el sector: ahí sí es KPI por KPI,
 * donde numerador y denominador hablan de lo mismo.
 */
@Component({
  standalone: true,
  selector: 'app-presupuesto-sectores',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-layer-group" aria-hidden="true"></i> Avance por sector</h1>
        <p class="page__subtitle">
          Qué dice la Matriz de cada sector, y cuánto ha cargado el área frente a eso.
          El sector es el subgrupo de Inversión Local.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (error()) {
        <div class="ui-empty-state">
          <i class="fa" [class]="error()!.icono" aria-hidden="true"></i>
          <p><strong>{{ error()!.titulo }}</strong></p>
          <p class="muted">{{ error()!.detalle }}</p>
        </div>
      } @else if (!sectores().length) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>No hay sectores con proyectos o actividades registradas.</p>
        </div>
      } @else {
        <!-- Resumen del cargue, arriba del todo: es la pregunta que trae
             a esta pantalla. Sin esto, «6 de 77» hay que contarlo a mano. -->
        <section class="tiles">
          <div class="ui-card tile">
            <span class="tile__num">{{ totalCargados() }} <small>de {{ totalKpis() }}</small></span>
            <span class="tile__label">KPIs con algo reportado por el área</span>
          </div>
          <div class="ui-card tile" [class.tile--warn]="sectoresEnCero() > 0">
            <span class="tile__num">{{ sectoresEnCero() }}</span>
            <span class="tile__label">Sectores sin un solo reporte</span>
          </div>
          <div class="ui-card tile">
            <span class="tile__num">{{ sectoresConKpis() }}</span>
            <span class="tile__label">Sectores con KPIs</span>
          </div>
        </section>

        <section class="hub-section">
          <h2 class="hub-section__title">Cumplimiento según la Matriz</h2>
          <div class="barras">
            @for (s of sectores(); track s.subgrupo_id) {
              <div class="barra-row">
                <div class="barra-label">
                  <strong>{{ s.sector }}</strong>
                  <!--
                    Decía «N act.» y lo que contaba eran EVENTOS:
                    Relacionamiento Interinstitucional mostraba «16 act.» sin
                    tener una sola actividad del plan. Son dos ejes distintos
                    —la actividad cuelga del proyecto, el evento del subgrupo
                    que lo ejecuta— y ahora van separados y con su nombre.
                  -->
                  <small>
                    {{ s.n_proyectos }} proy · {{ s.n_kpis }} KPIs ·
                    {{ s.n_actividades }} act. plan · {{ s.n_eventos }} eventos
                  </small>
                </div>
                <div class="barra-track"
                     [attr.title]="(s.porcentaje ?? '—') + '% según la Matriz'">
                  <div class="barra-fill"
                       [style.width.%]="clamp(s.porcentaje)"
                       [class]="'barra-fill--' + nivel(s.porcentaje)"></div>
                </div>
                <div class="barra-pct">{{ s.porcentaje ?? '—' }}%</div>
              </div>
            }
          </div>
        </section>

        <section class="hub-section">
          <h2 class="hub-section__title">La Matriz frente a lo que cargó el área</h2>
          <p class="hub-section__nota">
            El cumplimiento sale de la Matriz. El cargue es cuántos KPIs tiene el área
            reportados — es cobertura, no cumplimiento. Abra un sector para ver la
            diferencia KPI por KPI, que es donde las unidades sí son comparables.
          </p>
          <div class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th></th>
                  <th>Sector</th>
                  <th class="num">Proyectos</th>
                  <th class="num">KPIs</th>
                  <th class="num">Act. plan</th>
                  <th class="num">Eventos</th>
                  <th class="num">Matriz</th>
                  <th>Cargue del área</th>
                </tr>
              </thead>
              <tbody>
                @for (s of sectores(); track s.subgrupo_id) {
                  <tr class="fila" [class.fila--abierta]="abierto() === s.subgrupo_id">
                    <td>
                      @if (s.n_kpis) {
                        <button type="button" class="expandir"
                                (click)="alternar(s)"
                                [attr.aria-expanded]="abierto() === s.subgrupo_id"
                                [attr.title]="'Ver los KPIs de ' + s.sector">
                          <i class="fa" aria-hidden="true"
                             [class]="abierto() === s.subgrupo_id
                                      ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                        </button>
                      }
                    </td>
                    <td>{{ s.sector }}</td>
                    <td class="num">{{ s.n_proyectos }}</td>
                    <td class="num">{{ s.n_kpis }}</td>
                    <!-- Esta columna decía «Actividades» y traía n_eventos. -->
                    <td class="num">{{ s.n_actividades }}</td>
                    <td class="num">{{ s.n_eventos }}</td>
                    <td class="num"><strong>{{ s.porcentaje ?? '—' }}%</strong></td>
                    <td>
                      @if (!s.n_kpis) {
                        <span class="muted">sin KPIs</span>
                      } @else {
                        <div class="cargue">
                          <div class="cargue__track">
                            <div class="cargue__fill"
                                 [style.width.%]="s.pct_cargue ?? 0"
                                 [class.cargue__fill--cero]="!s.kpis_cargados"></div>
                          </div>
                          <span class="cargue__txt"
                                [class.cargue__txt--cero]="!s.kpis_cargados">
                            {{ s.kpis_cargados }} de {{ s.n_kpis }}
                          </span>
                        </div>
                      }
                    </td>
                  </tr>

                  @if (abierto() === s.subgrupo_id) {
                    <tr class="detalle">
                      <td colspan="8">
                        @if (!detalle()) {
                          <p class="muted">
                            <i class="fa fa-spinner fa-spin" aria-hidden="true"></i>
                            Cargando los KPIs de {{ s.sector }}…
                          </p>
                        } @else {
                          @let d = detalle()!;
                          <p class="resumen">
                            {{ d.resumen.n_cargados }} de {{ d.resumen.n_kpis }} KPIs
                            con reporte del área.
                            @if (d.resumen.brecha_media !== null) {
                              Donde las dos fuentes miden, el área reporta
                              <strong>{{ d.resumen.brecha_media }} puntos</strong>
                              frente a la Matriz ({{ d.resumen.n_comparables }}
                              {{ d.resumen.n_comparables === 1 ? 'KPI' : 'KPIs' }}).
                            } @else {
                              Ningún KPI se puede comparar todavía: hacen falta
                              reportes del área.
                            }
                          </p>
                          <table class="tabla tabla--inner">
                            <thead>
                              <tr>
                                <th>KPI</th>
                                <th>Meta SEGPLAN</th>
                                <th class="num">Meta</th>
                                <th class="num">Reportado</th>
                                <th class="num">% área</th>
                                <th class="num">% Matriz</th>
                                <th class="num">Diferencia</th>
                              </tr>
                            </thead>
                            <tbody>
                              @for (k of d.kpis; track k.kpi_id) {
                                <tr [class.sin-cargar]="!k.cargado">
                                  <td>
                                    {{ k.nombre }}
                                    @if (k.unidad_medida) {
                                      <small class="unidad">({{ k.unidad_medida }})</small>
                                    }
                                  </td>
                                  <td class="mono">{{ k.meta_codigo || '—' }}</td>
                                  <td class="num">{{ k.meta_magnitud | number:'1.0-0' }}</td>
                                  <td class="num">
                                    @if (k.cargado) {
                                      {{ k.reportado | number:'1.0-0' }}
                                    } @else {
                                      <span class="chip-falta">sin cargar</span>
                                    }
                                  </td>
                                  <td class="num">
                                    {{ k.pct_area !== null ? k.pct_area + '%' : '—' }}
                                  </td>
                                  <td class="num">
                                    {{ k.pct_matriz !== null ? k.pct_matriz + '%' : '—' }}
                                  </td>
                                  <td class="num">
                                    @if (k.diferencia === null) {
                                      <span class="muted">—</span>
                                    } @else {
                                      <strong [class]="'dif dif--' + signo(k.diferencia)">
                                        {{ k.diferencia > 0 ? '+' : '' }}{{ k.diferencia }}
                                      </strong>
                                    }
                                  </td>
                                </tr>
                              }
                            </tbody>
                          </table>
                        }
                      </td>
                    </tr>
                  }
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      <a routerLink="/plan" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1240px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .tiles {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: $space-3; margin-bottom: $space-4;
    }
    .tile {
      display: flex; flex-direction: column; align-items: center; padding: $space-3;
      text-align: center;
      &__num {
        font-size: 1.6rem; font-weight: 700; color: $color-primary;
        small { font-size: .9rem; font-weight: 400; color: $color-text-muted; }
      }
      &__label { color: $color-text-muted; font-size: $font-size-sm; }
      &--warn .tile__num { color: $color-warning; }
    }
    .hub-section { margin-top: $space-5; }
    .hub-section__title { margin: 0 0 $space-2; font-size: $font-size-lg; color: $color-text; }
    .hub-section__nota {
      margin: 0 0 $space-3; color: $color-text-muted; font-size: $font-size-sm;
      max-width: 72ch;
    }
    .barras { display: flex; flex-direction: column; gap: $space-3; }
    .barra-row { display: grid; grid-template-columns: minmax(160px, 1fr) 3fr auto; align-items: center; gap: $space-3; }
    .barra-label strong { display: block; color: $color-text; }
    .barra-label small { color: $color-text-muted; }
    .barra-track { background: rgba(0,0,0,.08); border-radius: 999px; height: 14px; overflow: hidden; }
    .barra-fill { height: 100%; border-radius: 999px; transition: width .4s ease; min-width: 2px; }
    .barra-fill--alto { background: #16a34a; }
    .barra-fill--medio { background: #f59e0b; }
    .barra-fill--bajo { background: #dc2626; }
    .barra-fill--nulo { background: rgba(0,0,0,.18); }
    .barra-pct { font-variant-numeric: tabular-nums; color: $color-text; min-width: 46px; text-align: right; }
    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08); text-align: left; }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .fila--abierta { background: $color-bg-subtle; }
    .expandir {
      border: 0; background: none; cursor: pointer; color: $color-text-muted;
      padding: 2px 6px; &:hover { color: $color-primary; }
    }
    .cargue { display: flex; align-items: center; gap: $space-2; min-width: 150px; }
    .cargue__track {
      flex: 1; background: rgba(0,0,0,.08); border-radius: 999px;
      height: 8px; overflow: hidden; min-width: 60px;
    }
    .cargue__fill {
      height: 100%; border-radius: 999px; background: #0D9488;
      transition: width .4s ease;
      &--cero { background: transparent; }
    }
    .cargue__txt {
      font-variant-numeric: tabular-nums; font-size: $font-size-sm; white-space: nowrap;
      &--cero { color: $color-warning; font-weight: 600; }
    }
    .detalle > td { background: $color-bg-subtle; padding: $space-3; }
    .resumen { margin: 0 0 $space-2; font-size: $font-size-sm; color: $color-text; }
    .tabla--inner { background: $color-bg; border-radius: $radius-sm; }
    .tabla--inner th { font-size: 0.78rem; text-transform: uppercase; letter-spacing: .02em; color: $color-text-muted; }
    .unidad { color: $color-text-muted; margin-left: 4px; }
    .mono { font-variant-numeric: tabular-nums; color: $color-text-muted; }
    .sin-cargar td { opacity: .72; }
    .chip-falta {
      display: inline-block; padding: 1px 8px; border-radius: 999px;
      font-size: 0.72rem; font-weight: 600;
      background: rgba(217, 119, 6, .12); color: #d97706;
    }
    .dif {
      font-variant-numeric: tabular-nums;
      &--sobre { color: #16a34a; }
      &--bajo  { color: #dc2626; }
      &--par   { color: $color-text-muted; }
    }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class PresupuestoSectoresComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  sectores = signal<SectorAvance[]>([]);
  cargando = signal<boolean>(true);
  /** `null` = no hubo fallo. Distinto de «no hay sectores». */
  error = signal<ErrorDeCarga | null>(null);
  /** subgrupo_id del sector desplegado; uno a la vez. */
  abierto = signal<number | null>(null);
  detalle = signal<DetalleSector | null>(null);

  clamp(pct: number | null): number {
    return pct === null ? 0 : Math.max(0, Math.min(100, pct));
  }
  nivel(pct: number | null): 'alto' | 'medio' | 'bajo' | 'nulo' {
    // `null` NO es cero: es que ninguna fuente mide ese sector. Pintarlo de
    // rojo como un 0 % decía «va pésimo» donde lo cierto es «no hay dato».
    if (pct === null) return 'nulo';
    return pct >= 80 ? 'alto' : pct >= 50 ? 'medio' : 'bajo';
  }
  signo(dif: number): 'sobre' | 'bajo' | 'par' {
    return dif > 0.05 ? 'sobre' : dif < -0.05 ? 'bajo' : 'par';
  }

  totalKpis(): number {
    return this.sectores().reduce((n, s) => n + s.n_kpis, 0);
  }
  totalCargados(): number {
    return this.sectores().reduce((n, s) => n + s.kpis_cargados, 0);
  }
  sectoresConKpis(): number {
    return this.sectores().filter(s => s.n_kpis > 0).length;
  }
  sectoresEnCero(): number {
    return this.sectores().filter(s => s.n_kpis > 0 && !s.kpis_cargados).length;
  }

  async alternar(s: SectorAvance): Promise<void> {
    if (this.abierto() === s.subgrupo_id) {
      this.abierto.set(null);
      return;
    }
    this.abierto.set(s.subgrupo_id);
    this.detalle.set(null);
    try {
      const r = await firstValueFrom(
        this.http.get<DetalleSector>(this.cfg.url(
          `/dashboard/api/v2/presupuesto/avance-por-sector/${s.subgrupo_id}/kpis/`)),
      );
      // Si mientras respondía se abrió otro sector, esta respuesta ya no va.
      if (this.abierto() === s.subgrupo_id) this.detalle.set(r);
    } catch {
      if (this.abierto() === s.subgrupo_id) {
        this.detalle.set({
          kpis: [],
          resumen: { n_kpis: 0, n_cargados: 0, n_comparables: 0, brecha_media: null },
        });
      }
    }
  }

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Avance por sector' },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url('/dashboard/api/v2/presupuesto/avance-por-sector/')),
      );
      this.sectores.set(r?.sectores ?? []);
    } catch (e: any) {
      this.sectores.set([]);
      // «No hay sectores con proyectos registrados» era una AFIRMACIÓN sobre
      // los datos, y se pintaba también cuando el servidor devolvía 403.
      this.error.set(errorDeCarga(e, 'el avance por sector'));
    } finally {
      this.cargando.set(false);
    }
  }
}
