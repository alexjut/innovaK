import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface MetaComparada {
  proyecto: string;
  codigo_meta: string;
  meta: string;
  magnitud_interna: number;
  oficial_programado: number;
  oficial_entregado: number;
  avance_oficial_pct: number;
  tipo_anualizacion: string | null;
}

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
          <i class="fa fa-info-circle"></i>
          <p>Ninguna meta enganchada aún. Corre la ingesta y el mapeo de código de meta.</p>
        </div>
      } @else {
        <div class="tiles">
          <div class="tile"><span class="tile__n">{{ metas().length }}</span><span class="tile__l">metas enganchadas a SEGPLAN</span></div>
          <div class="tile"><span class="tile__n">{{ proyectos() }}</span><span class="tile__l">proyectos conectados</span></div>
          <div class="tile"><span class="tile__n">{{ pctEntregadoGlobal() }}%</span><span class="tile__l">avance oficial (entregado/programado)</span></div>
        </div>

        <div class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th>Proyecto</th>
                <th>SEGPLAN</th>
                <th>Meta</th>
                <th class="num">Magnitud interna</th>
                <th class="num">Programado oficial</th>
                <th class="num">Entregado oficial</th>
                <th class="num">% oficial</th>
                <th>Anualización</th>
              </tr>
            </thead>
            <tbody>
              @for (m of metas(); track m.codigo_meta) {
                <tr>
                  <td>{{ m.proyecto }}</td>
                  <td><span class="chip">{{ m.codigo_meta }}</span></td>
                  <td class="meta">{{ m.meta }}</td>
                  <td class="num">{{ m.magnitud_interna | number:'1.0-0' }}</td>
                  <td class="num">{{ m.oficial_programado | number:'1.0-0' }}</td>
                  <td class="num">{{ m.oficial_entregado | number:'1.0-0' }}</td>
                  <td class="num"><strong>{{ m.avance_oficial_pct }}%</strong></td>
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

  proyectos = computed(() => new Set(this.metas().map((m) => m.proyecto)).size);
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
    } catch {
      this.metas.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
