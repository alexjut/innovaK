import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

/** Una fila de avance por sector = subgrupo (Inversión Local). */
interface SectorAvance {
  subgrupo_id: number;
  sector: string;
  n_proyectos: number;
  n_kpis: number;
  n_eventos: number;
  avance: number;
  meta: number;
  porcentaje: number;
}

/**
 * Avance por SECTOR (subgrupo) — alineación con el Visor SDP-PDL.
 * Consume `/dashboard/api/v2/presupuesto/avance-por-sector/` (JWT-first).
 * El sector es el subgrupo del proyecto, NO `metas.sector` (vacío).
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
          Proyectos, indicadores y ejecución por sector (subgrupo de Inversión Local),
          alineado con el Visor SDP-PDL.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!sectores().length) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle"></i>
          <p>No hay sectores con proyectos o actividades registradas.</p>
        </div>
      } @else {
        <section class="hub-section">
          <div class="barras">
            @for (s of sectores(); track s.subgrupo_id) {
              <div class="barra-row">
                <div class="barra-label">
                  <strong>{{ s.sector }}</strong>
                  <small>{{ s.n_proyectos }} proy · {{ s.n_kpis }} KPIs · {{ s.n_eventos }} act.</small>
                </div>
                <div class="barra-track" [attr.title]="s.porcentaje + '% de cumplimiento'">
                  <div class="barra-fill"
                       [style.width.%]="clamp(s.porcentaje)"
                       [class]="'barra-fill--' + nivel(s.porcentaje)"></div>
                </div>
                <div class="barra-pct">{{ s.porcentaje }}%</div>
              </div>
            }
          </div>
        </section>

        <section class="hub-section">
          <h2 class="hub-section__title">Detalle</h2>
          <div class="tabla-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th>Sector</th>
                  <th class="num">Proyectos</th>
                  <th class="num">KPIs</th>
                  <th class="num">Actividades</th>
                  <th class="num">Avance</th>
                  <th class="num">Meta</th>
                  <th class="num">%</th>
                </tr>
              </thead>
              <tbody>
                @for (s of sectores(); track s.subgrupo_id) {
                  <tr>
                    <td>{{ s.sector }}</td>
                    <td class="num">{{ s.n_proyectos }}</td>
                    <td class="num">{{ s.n_kpis }}</td>
                    <td class="num">{{ s.n_eventos }}</td>
                    <td class="num">{{ s.avance | number:'1.0-0' }}</td>
                    <td class="num">{{ s.meta | number:'1.0-0' }}</td>
                    <td class="num"><strong>{{ s.porcentaje }}%</strong></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      <a routerLink="/presupuesto" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .hub-section { margin-top: $space-5; }
    .hub-section__title { margin: 0 0 $space-3; font-size: $font-size-lg; color: $color-text; }
    .barras { display: flex; flex-direction: column; gap: $space-3; }
    .barra-row { display: grid; grid-template-columns: minmax(160px, 1fr) 3fr auto; align-items: center; gap: $space-3; }
    .barra-label strong { display: block; color: $color-text; }
    .barra-label small { color: $color-text-muted; }
    .barra-track { background: rgba(0,0,0,.08); border-radius: 999px; height: 14px; overflow: hidden; }
    .barra-fill { height: 100%; border-radius: 999px; transition: width .4s ease; min-width: 2px; }
    .barra-fill--alto { background: #16a34a; }
    .barra-fill--medio { background: #f59e0b; }
    .barra-fill--bajo { background: #dc2626; }
    .barra-pct { font-variant-numeric: tabular-nums; color: $color-text; min-width: 46px; text-align: right; }
    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08); text-align: left; }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class PresupuestoSectoresComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  sectores = signal<SectorAvance[]>([]);
  cargando = signal<boolean>(true);

  clamp(pct: number): number { return Math.max(0, Math.min(100, pct)); }
  nivel(pct: number): 'alto' | 'medio' | 'bajo' {
    return pct >= 80 ? 'alto' : pct >= 50 ? 'medio' : 'bajo';
  }

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Avance por sector' },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url('/dashboard/api/v2/presupuesto/avance-por-sector/')),
      );
      this.sectores.set(r?.sectores ?? []);
    } catch {
      this.sectores.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
