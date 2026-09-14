import { CommonModule } from '@angular/common';
import { Component, Input, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';

interface KpiDelEvento {
  indicador_id: number;
  nombre: string;
  unidad_medida: string | null;
  meta_magnitud: number;
  reportado: number | null;
  reportado_en: string | null;
  periodo: string | null;
  acumulado_kpi: number;
  pct_kpi: number | null;
  /** `false` si otro módulo ya reporta este KPI para este evento. */
  editable: boolean;
  dueno: string | null;
  reportado_por_otro: number | null;
}
interface ReporteEvento {
  evento_id: number;
  evento_nombre: string;
  actividad_plan_id: number | null;
  fecha_del_hecho: string;
  puede_reportar: boolean;
  motivo: string | null;
  kpis: KpiDelEvento[];
}

/**
 * «Reportar avance» de un evento ya ejecutado — el puente entre lo que hace el
 * funcionario y lo que miden las metas del Plan.
 *
 * Los KPIs NO se eligen de una lista: salen de la actividad del plan a la que
 * está enganchado el evento. Si el evento no tiene actividad, o la actividad
 * no tiene meta vinculada, el panel lo dice y manda a arreglarlo — no ofrece
 * un select de 77 indicadores, que es exactamente como se llegó a que solo 6
 * de esos 77 tuvieran algo reportado.
 *
 * Un KPI que ya reporta otro módulo (Festivales, Jóvenes, Entregas…) sale en
 * gris y con el nombre de su dueño: escribirlo acá contaría dos veces el mismo
 * hecho. El backend lo rechaza igual; acá se muestra para que no haya que
 * intentarlo para enterarse.
 */
@Component({
  standalone: true,
  selector: 'app-evento-avance',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <button type="button" class="ui-btn ui-btn--sm ui-btn--ghost"
            (click)="alternar()"
            [attr.title]="'Reportar lo que entregó este evento a las metas del Plan'">
      <i class="fa fa-chart-line" aria-hidden="true"></i> Avance
    </button>

    @if (abierto()) {
      <div class="panel" role="dialog" aria-label="Reportar avance del evento">
        @if (!reporte()) {
          <p class="muted"><i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Cargando…</p>
        } @else {
          @let r = reporte()!;
          @if (!r.puede_reportar) {
            <p class="aviso">{{ r.motivo }}</p>
            @if (r.actividad_plan_id) {
              <a routerLink="/plan/actividades" class="ui-btn ui-btn--sm ui-btn--ghost">
                <i class="fa fa-link" aria-hidden="true"></i> Vincular la meta
              </a>
            }
          } @else {
            <p class="panel__nota">
              Se registra con fecha <strong>{{ r.fecha_del_hecho }}</strong> —
              la del hecho, no la de hoy si el evento ya terminó.
            </p>
            <table class="kpis">
              <thead>
                <tr>
                  <th>Meta del Plan</th>
                  <th class="num">Va en</th>
                  <th class="num">Este evento aportó</th>
                </tr>
              </thead>
              <tbody>
                @for (k of r.kpis; track k.indicador_id) {
                  <tr [class.bloqueado]="!k.editable">
                    <td>
                      {{ k.nombre }}
                      @if (k.unidad_medida) { <small>({{ k.unidad_medida }})</small> }
                    </td>
                    <td class="num">
                      {{ k.acumulado_kpi | number:'1.0-0' }}
                      / {{ k.meta_magnitud | number:'1.0-0' }}
                      @if (k.pct_kpi !== null) { <small>· {{ k.pct_kpi }}%</small> }
                    </td>
                    <td class="num">
                      @if (!k.editable) {
                        <span class="dueno"
                              [attr.title]="'Lo reporta ' + k.dueno + '; escribirlo acá lo contaría dos veces'">
                          {{ k.reportado_por_otro | number:'1.0-0' }} · vía {{ k.dueno }}
                        </span>
                      } @else {
                        <input type="number" min="0" step="1" class="mag"
                               [ngModel]="valores()[k.indicador_id]"
                               (ngModelChange)="fijar(k.indicador_id, $event)"
                               [attr.aria-label]="'Magnitud aportada a ' + k.nombre" />
                        @if (k.reportado !== null) {
                          <button type="button" class="retirar"
                                  [disabled]="guardando()"
                                  (click)="retirar(k)"
                                  title="Retirar lo que este evento reportó a esta meta">
                            retirar
                          </button>
                        }
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>

            <div class="panel__pie">
              <button class="ui-btn ui-btn--sm ui-btn--primary"
                      [disabled]="guardando() || !hayCambios()"
                      (click)="guardar()">
                <i class="fa" aria-hidden="true"
                   [class]="guardando() ? 'fa-spinner fa-spin' : 'fa-floppy-disk'"></i>
                Guardar avance
              </button>
              <button class="ui-btn ui-btn--sm ui-btn--ghost" (click)="alternar()">Cerrar</button>
            </div>
          }

          @if (mensaje(); as m) {
            <p class="msg" [class.err]="m.err">{{ m.texto }}</p>
          }
        }
      </div>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: contents; }
    .panel {
      margin-top: $space-2; padding: $space-3; text-align: left;
      border: 1px solid $color-border; border-radius: $radius-sm;
      background: $color-bg; max-width: 720px;
    }
    .panel__nota { margin: 0 0 $space-2; color: $color-text-muted; font-size: $font-size-sm; }
    .panel__pie { display: flex; gap: $space-2; margin-top: $space-2; }
    .muted { color: $color-text-muted; }
    .aviso {
      margin: 0 0 $space-2; padding: $space-2;
      background: rgba(217, 119, 6, .10); color: #b45309;
      border-radius: $radius-sm; font-size: $font-size-sm;
    }
    .kpis { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .kpis th, .kpis td {
      padding: $space-1 $space-2; border-bottom: 1px solid rgba(0,0,0,.08);
      text-align: left; vertical-align: top;
    }
    .kpis th.num, .kpis td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .kpis small { color: $color-text-muted; }
    .bloqueado td { opacity: .7; }
    .dueno { font-size: 0.78rem; color: $color-text-muted; }
    .mag {
      width: 96px; padding: 4px 6px; text-align: right;
      border: 1px solid $color-border; border-radius: $radius-sm;
    }
    .retirar {
      display: block; margin-left: auto; margin-top: 2px;
      border: 0; background: none; cursor: pointer;
      font-size: 0.72rem; color: $color-text-muted; text-decoration: underline;
      &:hover:not(:disabled) { color: $color-primary; }
    }
    .msg {
      margin: $space-2 0 0; padding: $space-1 $space-2; border-radius: $radius-sm;
      font-size: $font-size-sm;
      background: rgba(22, 163, 74, .10); color: #16a34a;
      &.err { background: rgba(214, 0, 28, .08); color: $color-primary; }
    }
  `],
})
export class EventoAvanceComponent {
  @Input({ required: true }) eventoId!: number;

  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  abierto = signal(false);
  reporte = signal<ReporteEvento | null>(null);
  guardando = signal(false);
  mensaje = signal<{ texto: string; err: boolean } | null>(null);
  /** Lo que hay escrito en las casillas, por indicador_id. */
  valores = signal<Record<number, number | null>>({});

  private url(): string {
    return this.cfg.url(`/presupuesto/api/eventos/${this.eventoId}/avance/`);
  }

  async alternar(): Promise<void> {
    if (this.abierto()) {
      this.abierto.set(false);
      return;
    }
    this.abierto.set(true);
    this.mensaje.set(null);
    this.reporte.set(null);
    await this.cargar();
  }

  private async cargar(): Promise<void> {
    try {
      const r = await firstValueFrom(this.http.get<ReporteEvento>(this.url()));
      this.aplicar(r);
    } catch (e: any) {
      this.reporte.set(null);
      this.mensaje.set({
        texto: e?.error?.detail || 'No se pudo cargar el avance del evento.',
        err: true,
      });
      this.abierto.set(true);
    }
  }

  /** Deja las casillas mostrando lo ya reportado, para poder corregirlo. */
  private aplicar(r: ReporteEvento): void {
    this.reporte.set(r);
    const v: Record<number, number | null> = {};
    for (const k of r.kpis) if (k.editable) v[k.indicador_id] = k.reportado;
    this.valores.set(v);
  }

  fijar(indicadorId: number, valor: any): void {
    const n = valor === '' || valor === null ? null : Number(valor);
    this.valores.set({ ...this.valores(), [indicadorId]: n });
  }

  /** Solo se manda lo que cambió. Un `0` SÍ es un cambio si antes no había nada. */
  private cambios(): Record<number, number> {
    const r = this.reporte();
    const out: Record<number, number> = {};
    if (!r) return out;
    for (const k of r.kpis) {
      if (!k.editable) continue;
      const v = this.valores()[k.indicador_id];
      if (v === null || v === undefined || Number.isNaN(v)) continue;
      if (k.reportado !== null && Number(k.reportado) === Number(v)) continue;
      out[k.indicador_id] = Number(v);
    }
    return out;
  }

  hayCambios(): boolean {
    return Object.keys(this.cambios()).length > 0;
  }

  async guardar(): Promise<void> {
    const aportes = this.cambios();
    if (!Object.keys(aportes).length) return;
    this.guardando.set(true);
    this.mensaje.set(null);
    try {
      const r: any = await firstValueFrom(
        this.http.post(this.url(), { aportes }));
      if (r?.reporte) this.aplicar(r.reporte);
      const n = (r?.aportes ?? []).length;
      this.mensaje.set({
        texto: `Avance guardado en ${n} meta${n === 1 ? '' : 's'} (periodo ${r?.periodo}).`,
        err: false,
      });
    } catch (e: any) {
      this.mensaje.set({
        texto: e?.error?.detail || 'No se pudo guardar el avance.',
        err: true,
      });
    } finally {
      this.guardando.set(false);
    }
  }

  async retirar(k: KpiDelEvento): Promise<void> {
    if (!confirm(
      `¿Retirar lo que este evento le reportó a «${k.nombre}»?\n` +
      'La meta deja de contar ese aporte.',
    )) return;
    this.guardando.set(true);
    this.mensaje.set(null);
    try {
      const r: any = await firstValueFrom(this.http.delete(
        `${this.url()}?indicador_id=${k.indicador_id}`));
      if (r?.reporte) this.aplicar(r.reporte);
      this.mensaje.set({ texto: r?.detail || 'Avance retirado.', err: false });
    } catch (e: any) {
      this.mensaje.set({
        texto: e?.error?.detail || 'No se pudo retirar el avance.',
        err: true,
      });
    } finally {
      this.guardando.set(false);
    }
  }
}
