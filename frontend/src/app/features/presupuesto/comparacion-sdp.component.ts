import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

type Estado = 'cumplida' | 'en_curso' | 'atrasada' | 'sin_reporte' | 'sin_oficial';

interface MetaComparada {
  proyecto: string;
  codigo_meta: string;
  meta: string;
  magnitud_interna: number;
  oficial_programado: number;
  oficial_entregado: number;
  avance_oficial_pct: number;
  tipo_anualizacion: string | null;
  estado: Estado;
}

/** De dónde salen las cifras y qué tan completa viene la fuente. */
interface Fuente {
  nombre: string;
  filas: number;
  filas_con_avance: number;
  sincronizado: string | null;
  nota: string;
}

interface Stats {
  total: number; cumplida: number; en_curso: number; atrasada: number;
  sin_reporte: number; sin_oficial: number;
}

const ESTADO_META: Record<Estado, { label: string; clase: string }> = {
  cumplida:    { label: 'Cumplida',        clase: 'e-ok' },
  en_curso:    { label: 'En curso',        clase: 'e-mid' },
  atrasada:    { label: 'Atrasada',        clase: 'e-bad' },
  // Gris, NO rojo. Un 0% acá dice que el Distrito no ha cargado la ejecución,
  // no que el área incumplió: pintarlo de rojo sería acusar por el silencio
  // de una fuente ajena.
  sin_reporte: { label: 'Sin reporte oficial', clase: 'e-gray' },
  sin_oficial: { label: 'Sin dato oficial', clase: 'e-gray' },
};

/**
 * Comparación innovaK ↔ Planeación (SDP-PDL). Cruza cada meta interna enganchada
 * (metas.codigo_meta) contra lo oficial del Distrito. Consume
 * `/dashboard/api/v2/presupuesto/comparacion-sdp/` (JWT-first).
 */
@Component({
  standalone: true,
  selector: 'app-comparacion-sdp',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-scale-balanced" aria-hidden="true"></i> Comparación con Planeación (SDP)</h1>
        <p class="page__subtitle">
          Cada meta de innovaK enganchada a su código oficial SEGPLAN, contra lo que
          reporta el Distrito (Visor SDP-PDL 2025-2028). El total oficial es del cuatrienio.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!metas().length) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>Ninguna meta enganchada aún. Corre la ingesta y el mapeo de código de meta.</p>
        </div>
      } @else {
        <div class="tiles">
          <div class="tile"><span class="tile__n">{{ metas().length }}</span><span class="tile__l">metas enganchadas a SEGPLAN</span></div>
          <div class="tile"><span class="tile__n">{{ proyectos() }}</span><span class="tile__l">proyectos conectados</span></div>
          <div class="tile"><span class="tile__n">{{ pctEntregadoGlobal() }}%</span><span class="tile__l">avance oficial (entregado/programado)</span></div>
        </div>

        <!-- Sin esto, 18 metas en gris se leen como culpa del area. Con esto se
             ve que quien no ha cargado la ejecucion es el Distrito. -->
        @if (fuente(); as f) {
          <div class="ui-info-bar ui-info-bar--info" role="note">
            <strong>{{ f.nombre }}.</strong> {{ f.nota }}
            <small>
              {{ f.filas_con_avance }} de {{ f.filas }} filas con ejecucion cargada
              @if (f.sincronizado) { · sincronizado {{ f.sincronizado.slice(0, 10) }} }
            </small>
          </div>
        }

        <div class="barra">
          <div class="chips" role="tablist" aria-label="Filtrar por estado">
            <button class="chip" [class.chip--on]="filtro() === 'todos'" (click)="setFiltro('todos')">
              Todas <span class="chip__n">{{ metas().length }}</span>
            </button>
            <button class="chip chip--ok" [class.chip--on]="filtro() === 'cumplida'" (click)="setFiltro('cumplida')">
              Cumplidas <span class="chip__n">{{ conteo('cumplida') }}</span>
            </button>
            <button class="chip chip--mid" [class.chip--on]="filtro() === 'en_curso'" (click)="setFiltro('en_curso')">
              En curso <span class="chip__n">{{ conteo('en_curso') }}</span>
            </button>
            <button class="chip chip--bad" [class.chip--on]="filtro() === 'atrasada'" (click)="setFiltro('atrasada')">
              Atrasadas <span class="chip__n">{{ conteo('atrasada') }}</span>
            </button>
            <button class="chip chip--gray" [class.chip--on]="filtro() === 'sin_reporte'" (click)="setFiltro('sin_reporte')">
              Sin reporte oficial <span class="chip__n">{{ conteo('sin_reporte') }}</span>
            </button>
            <button class="chip chip--gray" [class.chip--on]="filtro() === 'sin_oficial'" (click)="setFiltro('sin_oficial')">
              Sin dato oficial <span class="chip__n">{{ conteo('sin_oficial') }}</span>
            </button>
          </div>
          <button class="btn-export" (click)="exportarCsv()">
            <i class="fa fa-file-csv" aria-hidden="true"></i> Exportar CSV
          </button>
        </div>

        <div class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th>Estado</th>
                <th>Proyecto</th>
                <th>SEGPLAN</th>
                <th>Meta</th>
                <th class="num">Magnitud interna</th>
                <th class="num">Meta programada (oficial)</th>
                <th class="num">Entregado oficial</th>
                <th class="num">% oficial</th>
                <th>Anualización</th>
              </tr>
            </thead>
            <tbody>
              @for (m of visibles(); track m.codigo_meta) {
                <tr>
                  <td><span class="sem" [class]="claseEstado(m.estado)">{{ labelEstado(m.estado) }}</span></td>
                  <td>{{ m.proyecto }}</td>
                  <td><span class="chip-seg">{{ m.codigo_meta }}</span></td>
                  <td class="meta">{{ m.meta }}</td>
                  <td class="num">{{ m.magnitud_interna | number:'1.0-0' }}</td>
                  <td class="num">{{ m.oficial_programado | number:'1.0-0' }}</td>
                  <td class="num">{{ m.oficial_entregado | number:'1.0-0' }}</td>
                  <td class="num">
                    <div class="pctcell">
                      <strong>{{ m.avance_oficial_pct }}%</strong>
                      <div class="pctbar"><span [class]="claseEstado(m.estado)" [style.width.%]="min100(m.avance_oficial_pct)"></span></div>
                    </div>
                  </td>
                  <td>{{ m.tipo_anualizacion || '—' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <p class="nota">
          La magnitud interna suele ser el <strong>aporte de la vigencia</strong>; el
          programado oficial es el <strong>total del cuatrienio</strong> (25% × 4 años).
        </p>
      }

      <a routerLink="/presupuesto" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1150px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .tiles { display: flex; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; }
    .tile { background: rgba(0,0,0,.04); border-radius: 10px; padding: $space-3 $space-4; min-width: 160px; }
    .tile__n { display: block; font-size: 1.7rem; font-weight: 700; color: $color-primary; }
    .tile__l { color: $color-text-muted; font-size: $font-size-sm; }
    .barra { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-3; flex-wrap: wrap; justify-content: space-between; }
    .chips { display: inline-flex; gap: $space-1; flex-wrap: wrap; }
    .chip { border: 1px solid rgba(0,0,0,.12); background: #fff; padding: $space-1 $space-3; border-radius: 999px; cursor: pointer; font-size: $font-size-sm; color: $color-text-muted; display: inline-flex; align-items: center; gap: 6px; }
    .chip__n { background: rgba(0,0,0,.08); border-radius: 999px; padding: 0 7px; font-size: .72rem; font-weight: 700; }
    .chip--on { color: $color-text; font-weight: 700; border-color: $color-primary; box-shadow: inset 0 0 0 1px $color-primary; }
    .chip--ok.chip--on { border-color: #16a34a; box-shadow: inset 0 0 0 1px #16a34a; color: #166534; }
    .chip--mid.chip--on { border-color: #d97706; box-shadow: inset 0 0 0 1px #d97706; color: #92400e; }
    .chip--bad.chip--on { border-color: #dc2626; box-shadow: inset 0 0 0 1px #dc2626; color: #991b1b; }
    .chip--gray.chip--on { border-color: #6b7280; box-shadow: inset 0 0 0 1px #6b7280; color: #374151; }
    .btn-export { border: 1px solid $color-primary; background: #fff; color: $color-primary; padding: $space-1 $space-3; border-radius: 8px; cursor: pointer; font-size: $font-size-sm; white-space: nowrap; i { margin-right: 5px; } }
    .btn-export:hover { background: $color-primary; color: #fff; }
    .sem { border-radius: 999px; padding: 1px 9px; font-size: .72rem; font-weight: 700; white-space: nowrap; }
    .sem.e-ok, .pctbar span.e-ok { background: #16a34a; }
    .sem.e-mid, .pctbar span.e-mid { background: #d97706; }
    .sem.e-bad, .pctbar span.e-bad { background: #dc2626; }
    .sem.e-gray, .pctbar span.e-gray { background: #9ca3af; }
    .sem.e-ok, .sem.e-mid, .sem.e-bad, .sem.e-gray { color: #fff; }
    .pctcell { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
    .pctbar { width: 72px; height: 5px; border-radius: 999px; background: rgba(0,0,0,.08); overflow: hidden; }
    .pctbar span { display: block; height: 100%; border-radius: 999px; transition: width .4s ease; }
    .chip-seg { background: $color-primary; color: #fff; border-radius: 999px; padding: 1px 8px; font-variant-numeric: tabular-nums; }
    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08); text-align: left; vertical-align: top; }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .tabla td.meta { max-width: 320px; color: $color-text-muted; }
    .chip { background: $color-primary; color: #fff; border-radius: 999px; padding: 1px 8px; font-variant-numeric: tabular-nums; }
    .nota { color: $color-text-muted; font-size: $font-size-sm; margin-top: $space-3; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class ComparacionSdpComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  metas = signal<MetaComparada[]>([]);
  cargando = signal<boolean>(true);
  filtro = signal<Estado | 'todos'>('todos');

  proyectos = computed(() => new Set(this.metas().map((m) => m.proyecto)).size);

  /** Filas que pasan el filtro de estado activo. */
  visibles = computed(() => {
    const f = this.filtro();
    return f === 'todos' ? this.metas() : this.metas().filter((m) => m.estado === f);
  });

  setFiltro(valor: Estado | 'todos'): void {
    this.filtro.set(valor);
  }

  conteo(estado: Estado): number {
    return this.metas().filter((m) => m.estado === estado).length;
  }

  labelEstado(estado: Estado): string {
    return ESTADO_META[estado]?.label ?? estado;
  }

  claseEstado(estado: Estado): string {
    return ESTADO_META[estado]?.clase ?? 'e-gray';
  }

  /** Acota la barra de progreso: un 340 % oficial no puede desbordar la celda. */
  min100(pct: number): number {
    return Math.max(0, Math.min(100, Number(pct) || 0));
  }

  /** Descarga las filas visibles como CSV, sin dependencias externas. */
  exportarCsv(): void {
    const cabecera = [
      'estado', 'proyecto', 'codigo_meta', 'meta', 'magnitud_interna',
      'oficial_programado', 'oficial_entregado', 'avance_oficial_pct',
      'tipo_anualizacion',
    ];
    const escapar = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const filas = this.visibles().map((m) => [
      this.labelEstado(m.estado), m.proyecto, m.codigo_meta, m.meta,
      m.magnitud_interna, m.oficial_programado, m.oficial_entregado,
      m.avance_oficial_pct, m.tipo_anualizacion ?? '',
    ].map(escapar).join(','));
    // BOM para que Excel en Windows abra las tildes bien.
    const csv = '﻿' + [cabecera.join(','), ...filas].join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparacion_sdp_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
  fuente = signal<Fuente | null>(null);
  pctEntregadoGlobal = computed(() => {
    const prog = this.metas().reduce((s, m) => s + m.oficial_programado, 0);
    const ent = this.metas().reduce((s, m) => s + m.oficial_entregado, 0);
    return prog ? Math.round((ent / prog) * 1000) / 10 : 0;
  });

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Comparación SDP' },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url('/dashboard/api/v2/presupuesto/comparacion-sdp/')),
      );
      this.metas.set(r?.metas ?? []);
      this.fuente.set(r?.fuente ?? null);
    } catch {
      this.metas.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
