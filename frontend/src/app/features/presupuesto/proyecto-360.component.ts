import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface ContratoLite {
  id: number; numero: string;
  valor: number; fecha_inicio: string | null; fecha_fin: string | null;
}
interface CdpHijo {
  id: number; numero: string; fecha: string | null;
  valor: number; descripcion: string;
  comprometido: number; saldo_libre: number; pct_usado: number;
  contratos: ContratoLite[];
}
interface IndicadorHijo {
  id: number; nombre: string; unidad: string;
  meta_magnitud: number; avance_acumulado: number; avance_pct: number | null;
  meta_codigo: string | null; meta_nombre: string | null;
}
interface ActividadHija {
  id: number; descripcion: string; num_eventos: number;
}
interface Proyecto360 {
  id: number; codigo: string; nombre: string;
  programa: { id: number; nombre: string } | null;
  subgrupo: { id: number; nombre: string } | null;
  dependencia: { id: number; nombre: string } | null;
  cdps: CdpHijo[];
  presupuesto_total_cdps: number;
  actividades_plan: ActividadHija[];
  indicadores: IndicadorHijo[];
}

@Component({
  standalone: true,
  selector: 'app-proyecto-360',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loading()) { <div class="page__loading">Cargando proyecto…</div> }
      @else if (errorMsg()) { <div class="page__error">⚠ {{ errorMsg() }}</div> }
      @else if (data()) {
        @let p = data()!;
        <header class="page__header">
          <h1><i class="fa fa-folder-open"></i> {{ p.nombre }}</h1>
          <p class="page__subtitle">
            <code>{{ p.codigo }}</code>
            @if (p.programa) { · <strong>{{ p.programa.nombre }}</strong> }
            @if (p.subgrupo) { · {{ p.subgrupo.nombre }} }
            @if (p.dependencia) { · {{ p.dependencia.nombre }} }
          </p>
        </header>

        <!-- Tiles superiores -->
        <div class="tiles">
          <div class="tile tile--primary">
            <span class="tile__value">{{ p.cdps.length }}</span>
            <span class="tile__label">CDPs</span>
          </div>
          <div class="tile tile--accent">
            <span class="tile__value">{{ p.indicadores.length }}</span>
            <span class="tile__label">KPIs</span>
          </div>
          <div class="tile tile--info">
            <span class="tile__value">{{ totalContratos() }}</span>
            <span class="tile__label">Contratos</span>
          </div>
          <div class="tile tile--success">
            <span class="tile__value">{{ p.actividades_plan.length }}</span>
            <span class="tile__label">Actividades</span>
          </div>
          <div class="tile tile--money">
            <span class="tile__value">\${{ totalCdp() | number:'1.0-0' }}</span>
            <span class="tile__label">Total CDPs</span>
          </div>
          <div class="tile" [class.tile--danger]="saldoNeto() < 0"
                          [class.tile--success]="saldoNeto() >= 0">
            <span class="tile__value">\${{ saldoNeto() | number:'1.0-0' }}</span>
            <span class="tile__label">Saldo libre</span>
          </div>
        </div>

        <!-- Sección Dinero (CDPs con contratos hijos) -->
        <section class="seccion">
          <div class="seccion__header">
            <h2><i class="fa fa-money-bill"></i> Dinero — CDPs y Contratos</h2>
            <div class="seccion__actions">
              <button class="ui-btn ui-btn--sm ui-btn--ghost"
                      (click)="abrirAsignarCdp()">
                <i class="fa fa-link"></i> Asignar CDP existente
              </button>
              <button class="ui-btn ui-btn--primary"
                      (click)="cdpFormAbierto.set(!cdpFormAbierto())">
                <i class="fa fa-plus-circle"></i> Crear CDP
              </button>
            </div>
          </div>

          @if (asignarCdpAbierto()) {
            <div class="form-crear">
              <h3>Asignar un CDP existente (sin proyecto) a este proyecto</h3>
              @if (cdpsSinProyecto().length) {
                <div class="form-grid">
                  <label class="full">CDP disponible *
                    <select [(ngModel)]="cdpAsignarId">
                      <option [ngValue]="null">— Selecciona un CDP —</option>
                      @for (c of cdpsSinProyecto(); track c.id) {
                        <option [ngValue]="c.id">
                          #{{ c.numero }} · \${{ c.valor | number:'1.0-0' }}
                          {{ c.fecha ? '· ' + c.fecha : '' }}
                        </option>
                      }
                    </select>
                  </label>
                </div>
                <div class="form-actions">
                  <button class="ui-btn ui-btn--ghost"
                          (click)="asignarCdpAbierto.set(false)">Cancelar</button>
                  <button class="ui-btn ui-btn--primary"
                          [disabled]="!cdpAsignarId || guardandoAsignar()"
                          (click)="asignarCdp()">
                    @if (guardandoAsignar()) { Asignando… } @else { Asignar al proyecto }
                  </button>
                </div>
              } @else {
                <p class="muted">No hay CDPs sin proyecto disponibles. Crea uno nuevo arriba.</p>
              }
              @if (asignarMsg()) { <p class="msg" [class.err]="asignarErr()">{{ asignarMsg() }}</p> }
            </div>
          }

          @if (cdpFormAbierto()) {
            <div class="form-crear">
              <h3>Crear CDP</h3>
              <div class="form-grid">
                <label>Número *
                  <input type="text" [(ngModel)]="cdpForm.numero">
                </label>
                <label>Valor *
                  <input type="number" step="0.01" [(ngModel)]="cdpForm.valor">
                </label>
                <label>Fecha
                  <input type="date" [(ngModel)]="cdpForm.fecha">
                </label>
                <label class="full">Descripción
                  <input type="text" [(ngModel)]="cdpForm.descripcion">
                </label>
              </div>
              <div class="form-actions">
                <button class="ui-btn ui-btn--ghost"
                        (click)="cdpFormAbierto.set(false)">Cancelar</button>
                <button class="ui-btn ui-btn--primary"
                        [disabled]="!cdpForm.numero || !cdpForm.valor || guardandoCdp()"
                        (click)="crearCdp()">
                  @if (guardandoCdp()) { Guardando… } @else { Crear CDP }
                </button>
              </div>
              @if (cdpMsg()) { <p class="msg" [class.err]="cdpErr()">{{ cdpMsg() }}</p> }
            </div>
          }

          @if (p.cdps.length) {
            <div class="cdps">
              @for (c of p.cdps; track c.id) {
                <article class="cdp">
                  <header class="cdp__header">
                    <div>
                      <strong>CDP #{{ c.numero }}</strong>
                      @if (c.fecha) { <small> · {{ c.fecha }}</small> }
                      <button class="ui-btn ui-btn--sm ui-btn--ghost cdp__quitar"
                              [disabled]="quitandoCdp() === c.id"
                              (click)="quitarCdp(c)"
                              title="Quitar este CDP del proyecto">
                        <i class="fa fa-unlink"></i>
                      </button>
                    </div>
                    <div class="cdp__amounts">
                      <span>Valor: <strong>\${{ c.valor | number:'1.0-0' }}</strong></span>
                      <span class="muted">
                        Comprometido: \${{ c.comprometido | number:'1.0-0' }}
                      </span>
                      <span [class]="saldoClass(c)">
                        Saldo: \${{ c.saldo_libre | number:'1.0-0' }}
                      </span>
                    </div>
                  </header>
                  <div class="barra">
                    <div class="barra__fill" [class]="barraClass(c)"
                         [style.width.%]="Math.min(c.pct_usado, 100)"></div>
                    <span class="barra__label">{{ c.pct_usado }}% usado</span>
                  </div>
                  @if (c.descripcion) { <p class="muted small">{{ c.descripcion }}</p> }

                  @if (c.contratos.length) {
                    <div class="contratos">
                      <small class="muted">Contratos del CDP:</small>
                      @for (ct of c.contratos; track ct.id) {
                        <div class="contrato">
                          <span><strong>{{ ct.numero }}</strong></span>
                          <span>\${{ ct.valor | number:'1.0-0' }}</span>
                          <small class="muted">
                            {{ ct.fecha_inicio }} → {{ ct.fecha_fin || '—' }}
                          </small>
                        </div>
                      }
                    </div>
                  } @else {
                    <p class="muted small">— Sin contratos asociados al CDP —</p>
                  }

                  <details class="contrato-crear">
                    <summary>+ Agregar contrato al CDP</summary>
                    <div class="form-grid">
                      <label>Número *
                        <input type="text"
                               [ngModel]="ctForms[c.id]?.numero || ''"
                               (ngModelChange)="setCt(c.id, 'numero', $event)">
                      </label>
                      <label>Valor * (máx \${{ c.saldo_libre | number:'1.0-0' }})
                        <input type="number" step="0.01"
                               [ngModel]="ctForms[c.id]?.valor || null"
                               (ngModelChange)="setCt(c.id, 'valor', $event)">
                      </label>
                      <label>Fecha inicio
                        <input type="date"
                               [ngModel]="ctForms[c.id]?.fecha_inicio || ''"
                               (ngModelChange)="setCt(c.id, 'fecha_inicio', $event)">
                      </label>
                      <label>Fecha fin
                        <input type="date"
                               [ngModel]="ctForms[c.id]?.fecha_fin || ''"
                               (ngModelChange)="setCt(c.id, 'fecha_fin', $event)">
                      </label>
                      <label class="full">Objeto
                        <input type="text"
                               [ngModel]="ctForms[c.id]?.objeto || ''"
                               (ngModelChange)="setCt(c.id, 'objeto', $event)">
                      </label>
                    </div>
                    <button class="ui-btn ui-btn--sm ui-btn--primary"
                            [disabled]="!ctValido(c.id) || guardandoCt() === c.id"
                            (click)="crearContrato(c.id)">
                      @if (guardandoCt() === c.id) { Guardando… }
                      @else { Crear contrato }
                    </button>
                    @if (ctMsg()[c.id]) {
                      <p class="msg" [class.err]="ctErr()[c.id]">{{ ctMsg()[c.id] }}</p>
                    }
                  </details>
                </article>
              }
            </div>
          } @else {
            <div class="ui-empty-state">
              <i class="fa fa-folder"></i>
              <p>El proyecto no tiene CDPs registrados.</p>
            </div>
          }
        </section>

        <!-- Sección Metas / KPIs -->
        <section class="seccion">
          <div class="seccion__header">
            <h2><i class="fa fa-bullseye"></i> Metas y KPIs</h2>
            <button class="ui-btn ui-btn--sm ui-btn--primary"
                    (click)="metaFormAbierto.set(!metaFormAbierto())">
              <i class="fa fa-plus-circle"></i> Asociar meta
            </button>
          </div>

          @if (metaFormAbierto()) {
            <div class="form-crear">
              <h3>Asociar Meta del catálogo al proyecto</h3>
              <div class="form-grid">
                <label>Meta del catálogo *
                  <select [(ngModel)]="metaSeleccionada">
                    <option [ngValue]="null">— Selecciona —</option>
                    @for (m of metasCatalogo(); track m.codigo) {
                      <option [ngValue]="m.codigo">[{{ m.codigo }}] {{ m.nombre }}</option>
                    }
                  </select>
                </label>
                <label class="full">¿No está? Crear meta nueva:
                  <input type="text" [(ngModel)]="nuevaMetaNombre"
                         placeholder="Nombre de la nueva meta">
                </label>
              </div>
              <div class="form-actions">
                <button class="ui-btn ui-btn--ghost"
                        (click)="metaFormAbierto.set(false)">Cancelar</button>
                @if (nuevaMetaNombre.trim()) {
                  <button class="ui-btn ui-btn--primary"
                          [disabled]="guardandoMeta()"
                          (click)="crearMetaYAsociar()">
                    @if (guardandoMeta()) { Guardando… } @else { Crear meta + asociar }
                  </button>
                } @else {
                  <button class="ui-btn ui-btn--primary"
                          [disabled]="!metaSeleccionada || guardandoMeta()"
                          (click)="asociarMeta()">
                    @if (guardandoMeta()) { Guardando… } @else { Asociar }
                  </button>
                }
              </div>
              @if (metaMsg()) { <p class="msg" [class.err]="metaErr()">{{ metaMsg() }}</p> }
            </div>
          }

          @if (p.indicadores.length) {
            @for (m of metasAgrupadas(); track m.codigo) {
              <article class="meta">
                <header class="meta__header">
                  <h3>{{ m.codigo }} — {{ m.nombre }}</h3>
                </header>
                @for (k of m.kpis; track k.id) {
                  <div class="kpi-row">
                    <div class="kpi-row__info">
                      <strong>{{ k.nombre }}</strong>
                      <small class="muted">
                        Meta: <strong>{{ k.meta_magnitud }} {{ k.unidad }}</strong> ·
                        Avance: <strong>{{ k.avance_acumulado }}</strong>
                      </small>
                    </div>
                    @if (k.avance_pct != null) {
                      <div class="barra">
                        <div class="barra__fill"
                             [class]="kpiClass(k.avance_pct)"
                             [style.width.%]="Math.min(k.avance_pct, 100)"></div>
                        <span class="barra__label">{{ k.avance_pct }}%</span>
                      </div>
                    }
                  </div>
                  <details class="avance-crear">
                    <summary>+ Registrar avance manual</summary>
                    <div class="form-grid">
                      <label>Magnitud aportada *
                        <input type="number" step="0.01"
                               [ngModel]="avForms[k.id]?.magnitud_aportada || null"
                               (ngModelChange)="setAv(k.id, 'magnitud_aportada', $event)">
                      </label>
                      <label>Fecha
                        <input type="date"
                               [ngModel]="avForms[k.id]?.fecha_aporte || ''"
                               (ngModelChange)="setAv(k.id, 'fecha_aporte', $event)">
                      </label>
                      <label>Periodo
                        <input type="text"
                               [ngModel]="avForms[k.id]?.periodo || ''"
                               (ngModelChange)="setAv(k.id, 'periodo', $event)"
                               placeholder="2026-T2, semestre 1, etc.">
                      </label>
                      <label class="full">Observaciones
                        <input type="text"
                               [ngModel]="avForms[k.id]?.observaciones || ''"
                               (ngModelChange)="setAv(k.id, 'observaciones', $event)">
                      </label>
                    </div>
                    <button class="ui-btn ui-btn--sm ui-btn--primary"
                            [disabled]="!avForms[k.id]?.magnitud_aportada || guardandoAv() === k.id"
                            (click)="crearAvance(k.id)">
                      @if (guardandoAv() === k.id) { Guardando… }
                      @else { Registrar avance }
                    </button>
                    @if (avMsg()[k.id]) {
                      <p class="msg" [class.err]="avErr()[k.id]">{{ avMsg()[k.id] }}</p>
                    }
                  </details>
                }
              </article>
            }
          } @else {
            <div class="ui-empty-state">
              <i class="fa fa-bullseye"></i>
              <p>El proyecto no tiene KPIs registrados.</p>
            </div>
          }
        </section>

        <!-- Sección Actividades del plan -->
        <section class="seccion">
          <div class="seccion__header">
            <h2><i class="fa fa-tasks"></i> Actividades del plan</h2>
            <button class="ui-btn ui-btn--sm ui-btn--primary"
                    (click)="apFormAbierto.set(!apFormAbierto())">
              <i class="fa fa-plus-circle"></i> Crear actividad
            </button>
          </div>

          @if (apFormAbierto()) {
            <div class="form-crear">
              <h3>Crear actividad del plan</h3>
              <label class="full">Descripción *
                <input type="text" [(ngModel)]="apDescripcion">
              </label>
              <div class="form-actions">
                <button class="ui-btn ui-btn--ghost"
                        (click)="apFormAbierto.set(false)">Cancelar</button>
                <button class="ui-btn ui-btn--primary"
                        [disabled]="!apDescripcion.trim() || guardandoAp()"
                        (click)="crearActividadPlan()">
                  @if (guardandoAp()) { Guardando… } @else { Crear }
                </button>
              </div>
              @if (apMsg()) { <p class="msg" [class.err]="apErr()">{{ apMsg() }}</p> }
            </div>
          }

          @if (p.actividades_plan.length) {
            <table class="ui-table">
              <thead>
                <tr><th>#</th><th>Descripción</th><th>Eventos</th><th>Acciones</th></tr>
              </thead>
              <tbody>
                @for (ap of p.actividades_plan; track ap.id) {
                  <tr>
                    <td>{{ ap.id }}</td>
                    <td>
                      @if (renombrandoAp() === ap.id) {
                        <div class="ap-rename">
                          <input type="text" [(ngModel)]="apNuevoNombre">
                          <button class="ui-btn ui-btn--sm ui-btn--primary"
                                  [disabled]="!apNuevoNombre.trim() || guardandoRename()"
                                  (click)="guardarRename(ap)">Guardar</button>
                          <button class="ui-btn ui-btn--sm ui-btn--ghost"
                                  (click)="renombrandoAp.set(null)">Cancelar</button>
                        </div>
                      } @else {
                        {{ ap.descripcion }}
                      }
                    </td>
                    <td>
                      <span class="ui-badge ui-badge--info">{{ ap.num_eventos }}</span>
                    </td>
                    <td>
                      <div class="ap-acciones">
                        <button class="ui-btn ui-btn--sm ui-btn--ghost"
                                (click)="verDetalleAp(ap.id)" title="Ver detalle">
                          <i class="fa fa-eye"></i>
                        </button>
                        <button class="ui-btn ui-btn--sm ui-btn--ghost"
                                (click)="abrirRename(ap)" title="Renombrar">
                          <i class="fa fa-pencil"></i>
                        </button>
                        <button class="ui-btn ui-btn--sm ui-btn--ghost"
                                [disabled]="eliminandoAp() === ap.id"
                                (click)="eliminarAp(ap)" title="Eliminar">
                          <i class="fa fa-trash"></i>
                        </button>
                      </div>
                      <details class="vinc-crear">
                        <summary>+ Vincular contrato</summary>
                        <div class="form-grid">
                          <label>Contrato (ID)
                            <input type="number"
                                   [ngModel]="vincForms[ap.id]?.contrato_id || null"
                                   (ngModelChange)="setVinc(ap.id, 'contrato_id', $event)">
                          </label>
                          <label>Monto
                            <input type="number" step="0.01"
                                   [ngModel]="vincForms[ap.id]?.monto || null"
                                   (ngModelChange)="setVinc(ap.id, 'monto', $event)">
                          </label>
                        </div>
                        <button class="ui-btn ui-btn--sm ui-btn--primary"
                                [disabled]="!vincForms[ap.id]?.contrato_id || guardandoVinc() === ap.id"
                                (click)="vincular(ap.id)">
                          @if (guardandoVinc() === ap.id) { Guardando… } @else { Vincular }
                        </button>
                        @if (vincMsg()[ap.id]) {
                          <p class="msg" [class.err]="vincErr()[ap.id]">{{ vincMsg()[ap.id] }}</p>
                        }
                      </details>
                      @if (apMsgAccion()[ap.id]) {
                        <p class="msg" [class.err]="apErrAccion()[ap.id]">{{ apMsgAccion()[ap.id] }}</p>
                      }
                    </td>
                  </tr>
                  @if (detalleAp()?.id === ap.id) {
                    @let det = detalleAp()!;
                    <tr class="ap-detalle-row">
                      <td colspan="4">
                        <div class="ap-detalle">
                          <div class="ap-detalle__col">
                            <h4><i class="fa fa-bullseye"></i> KPIs ({{ det.indicadores.length }})</h4>
                            @if (det.indicadores.length) {
                              <ul>@for (i of det.indicadores; track i.id) { <li>{{ i.nombre }}</li> }</ul>
                            } @else { <p class="muted small">Sin KPIs vinculados.</p> }
                          </div>
                          <div class="ap-detalle__col">
                            <h4><i class="fa fa-calendar"></i> Eventos ({{ det.eventos_count }})</h4>
                            @if (det.eventos.length) {
                              <ul>@for (e of det.eventos; track e.id) {
                                <li>{{ e.nombre }} <small class="muted">{{ e.fecha_inicio }}</small></li>
                              }</ul>
                            } @else { <p class="muted small">Sin eventos.</p> }
                          </div>
                          <div class="ap-detalle__col">
                            <h4><i class="fa fa-file-contract"></i> Contratos
                              (\${{ det.monto_comprometido | number:'1.0-0' }})</h4>
                            @if (det.contratos.length) {
                              <ul>@for (c of det.contratos; track c.vinculacion_id) {
                                <li>#{{ c.contrato_numero }} · \${{ c.monto | number:'1.0-0' }}</li>
                              }</ul>
                            } @else { <p class="muted small">Sin contratos.</p> }
                          </div>
                        </div>
                      </td>
                    </tr>
                  }
                }
              </tbody>
            </table>
          } @else {
            <div class="ui-empty-state">
              <i class="fa fa-tasks"></i>
              <p>Sin actividades_plan en el proyecto.</p>
            </div>
          }
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    code { background: $color-bg-subtle; padding: 2px 6px; border-radius: 3px; }
    .page__loading, .page__error { padding: $space-4; text-align: center; color: $color-text-muted; }
    .page__error { color: $color-danger; }

    .tiles {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: $space-2;
      margin: $space-3 0;
      @media (max-width: 900px) { grid-template-columns: repeat(3, 1fr); }
      @media (max-width: 600px) { grid-template-columns: repeat(2, 1fr); }
    }
    .tile {
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-lg; padding: $space-2; text-align: center;
      &__value {
        display: block; font-size: $font-size-xl;
        font-weight: $font-weight-bold; color: $color-primary;
      }
      &__label {
        display: block; font-size: $font-size-xs;
        color: $color-text-muted; text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      &--primary .tile__value { color: $color-primary; }
      &--accent .tile__value { color: #0D9488; }
      &--info .tile__value { color: $color-info; }
      &--success .tile__value { color: $color-success; }
      &--money .tile__value { color: #B45309; font-size: $font-size-lg; }
      &--danger .tile__value { color: $color-danger; }
    }

    .seccion {
      margin-top: $space-5;
      h2 {
        margin: 0 0 $space-3;
        font-size: $font-size-lg;
        color: $color-text;
        i { color: $color-primary; margin-right: $space-2; }
      }
    }

    .cdps { display: flex; flex-direction: column; gap: $space-3; }
    .cdp {
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-lg; padding: $space-3;
      &__header {
        display: flex; justify-content: space-between;
        align-items: baseline; gap: $space-3;
        flex-wrap: wrap;
        margin-bottom: $space-2;
      }
      &__amounts {
        display: flex; gap: $space-3; flex-wrap: wrap;
        font-size: $font-size-sm;
      }
    }
    .saldo-ok    { color: $color-success; font-weight: $font-weight-semibold; }
    .saldo-warn  { color: #F59E0B; font-weight: $font-weight-semibold; }
    .saldo-bad   { color: $color-danger; font-weight: $font-weight-semibold; }

    .barra {
      position: relative; height: 16px;
      background: $color-bg-subtle; border-radius: $radius-pill;
      overflow: hidden; margin: $space-2 0;
      &__fill {
        height: 100%; transition: width 0.3s;
        &.green  { background: $color-success; }
        &.yellow { background: #F59E0B; }
        &.red    { background: $color-danger; }
      }
      &__label {
        position: absolute; top: 0; left: 0; right: 0;
        text-align: center; font-size: $font-size-xs; line-height: 16px;
        color: $color-text; mix-blend-mode: difference;
      }
    }

    .contratos {
      border-top: 1px dashed $color-border; margin-top: $space-2;
      padding-top: $space-2;
    }
    .contrato {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: $space-2;
      padding: $space-1 0;
      border-bottom: 1px dotted $color-border;
      font-size: $font-size-sm;
    }
    .muted { color: $color-text-muted; }
    .small { font-size: $font-size-xs; }

    .meta {
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-lg; padding: $space-3;
      margin-bottom: $space-3;
      h3 { margin: 0 0 $space-2; font-size: $font-size-md; color: $color-primary; }
    }
    .kpi-row {
      display: grid; grid-template-columns: 1fr 220px;
      gap: $space-3; align-items: center;
      padding: $space-1 0;
      border-bottom: 1px dashed $color-border;
      &__info strong { display: block; }
      @media (max-width: 720px) { grid-template-columns: 1fr; }
    }

    .seccion__header {
      display: flex; justify-content: space-between; align-items: center;
      gap: $space-2; margin-bottom: $space-3;
      h2 { margin: 0; }
    }
    .form-crear {
      background: $color-bg-subtle;
      padding: $space-3;
      border-radius: $radius-md;
      margin-bottom: $space-3;
      h3 { margin: 0 0 $space-2; font-size: $font-size-md; color: $color-primary; }
    }
    .form-grid {
      display: grid; grid-template-columns: repeat(4, 1fr);
      gap: $space-2;
      @media (max-width: 720px) { grid-template-columns: 1fr 1fr; }
      label {
        display: block; font-size: $font-size-xs; color: $color-text-muted;
        input {
          width: 100%; margin-top: 2px; padding: $space-1 $space-2;
          border: 1px solid $color-border; border-radius: $radius-sm;
        }
      }
      .full { grid-column: 1 / -1; }
    }
    .form-actions {
      margin-top: $space-2; display: flex; gap: $space-2; justify-content: flex-end;
    }
    .msg {
      margin-top: $space-2;
      padding: $space-1 $space-2;
      border-radius: $radius-sm;
      background: rgba(22,163,74,0.10);
      color: $color-success;
      &.err { background: rgba(220,38,38,0.10); color: $color-danger; }
    }
    .contrato-crear, .avance-crear, .vinc-crear {
      margin-top: $space-2;
      padding: $space-2;
      background: $color-bg-subtle;
      border-radius: $radius-sm;
      summary { cursor: pointer; color: $color-primary; font-size: $font-size-sm; }
    }
    .avance-crear { margin-left: 0; }
    .seccion__actions { display: flex; gap: $space-2; align-items: center; }
    .cdp__quitar { margin-left: $space-2; padding: 0 $space-2; color: $color-text-muted;
      &:hover { color: $color-danger; } }
    .ap-acciones { display: flex; gap: $space-1; }
    .ap-rename { display: flex; gap: $space-1; align-items: center;
      input { flex: 1; padding: $space-1 $space-2; border: 1px solid $color-border; border-radius: $radius-sm; } }
    .ap-detalle-row td { background: $color-bg-subtle; }
    .ap-detalle { display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; padding: $space-2;
      @media (max-width: 800px) { grid-template-columns: 1fr; } }
    .ap-detalle__col {
      h4 { margin: 0 0 $space-1; font-size: $font-size-sm; color: $color-text-muted; i { margin-right: $space-1; } }
      ul { margin: 0; padding-left: $space-4; font-size: $font-size-sm; }
      li small { margin-left: $space-1; }
    }
  `],
})
export class Proyecto360Component implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  Math = Math;
  data = signal<Proyecto360 | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      const id = Number(p.get('id') || 0);
      this.cargar(id);
      this.cargarMetasCatalogo();
    });
  }

  cargar(id: number): void {
    this.loading.set(true);
    this.http.get<Proyecto360>(
      this.cfg.url(`/presupuesto/api/proyectos/${id}/`),
    ).subscribe({
      next: r => {
        this.data.set(r);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Presupuesto', url: '/presupuesto' },
          { label: 'Proyectos', url: '/presupuesto/proyectos' },
          { label: r.nombre || `Proyecto #${r.id}` },
        ]);
      },
      error: () => {
        this.errorMsg.set('No se pudo cargar el proyecto.');
        this.loading.set(false);
      },
    });
  }

  totalCdp(): number {
    return this.data()?.presupuesto_total_cdps ?? 0;
  }

  totalContratos(): number {
    const d = this.data();
    if (!d) return 0;
    return d.cdps.reduce((acc, c) => acc + c.contratos.length, 0);
  }

  saldoNeto(): number {
    const d = this.data();
    if (!d) return 0;
    return d.cdps.reduce((acc, c) => acc + c.saldo_libre, 0);
  }

  saldoClass(c: CdpHijo): string {
    if (c.saldo_libre < 0) return 'saldo-bad';
    if (c.pct_usado >= 80) return 'saldo-warn';
    return 'saldo-ok';
  }

  barraClass(c: CdpHijo): string {
    if (c.pct_usado >= 100) return 'red';
    if (c.pct_usado >= 80) return 'yellow';
    return 'green';
  }

  kpiClass(pct: number): string {
    if (pct >= 80) return 'green';
    if (pct >= 50) return 'yellow';
    return 'red';
  }

  metasAgrupadas(): Array<{ codigo: string; nombre: string; kpis: IndicadorHijo[] }> {
    const d = this.data();
    if (!d) return [];
    const m = new Map<string, { codigo: string; nombre: string; kpis: IndicadorHijo[] }>();
    for (const k of d.indicadores) {
      const codigo = k.meta_codigo || 'SIN_META';
      const nombre = k.meta_nombre || 'Sin meta vinculada';
      if (!m.has(codigo)) m.set(codigo, { codigo, nombre, kpis: [] });
      m.get(codigo)!.kpis.push(k);
    }
    return Array.from(m.values());
  }

  // ── Crear CDP ────────────────────────────────────────────────
  cdpFormAbierto = signal<boolean>(false);
  guardandoCdp = signal<boolean>(false);
  cdpMsg = signal<string>('');
  cdpErr = signal<boolean>(false);
  cdpForm: { numero: string; valor: number | null; fecha: string; descripcion: string } = {
    numero: '', valor: null, fecha: '', descripcion: '',
  };

  crearCdp(): void {
    const d = this.data(); if (!d) return;
    if (!this.cdpForm.numero || !this.cdpForm.valor) return;
    this.guardandoCdp.set(true);
    this.cdpMsg.set(''); this.cdpErr.set(false);
    this.http.post(this.cfg.url('/presupuesto/api/cdps/crear/'), {
      numero: this.cdpForm.numero,
      valor: this.cdpForm.valor,
      fecha: this.cdpForm.fecha || null,
      descripcion: this.cdpForm.descripcion,
      proyecto_id: d.id,
    }).subscribe({
      next: () => {
        this.cdpMsg.set('✓ CDP creado.');
        this.guardandoCdp.set(false);
        this.cdpForm = { numero: '', valor: null, fecha: '', descripcion: '' };
        this.cdpFormAbierto.set(false);
        this.cargar(d.id);
      },
      error: e => {
        this.cdpErr.set(true);
        this.cdpMsg.set(e?.error?.detail || 'Error creando CDP.');
        this.guardandoCdp.set(false);
      },
    });
  }

  // ── Asignar / quitar CDP existente ───────────────────────────
  asignarCdpAbierto = signal<boolean>(false);
  cdpsSinProyecto = signal<Array<{ id: number; numero: string; valor: number; fecha: string | null }>>([]);
  cdpAsignarId: number | null = null;
  guardandoAsignar = signal<boolean>(false);
  asignarMsg = signal<string>('');
  asignarErr = signal<boolean>(false);
  quitandoCdp = signal<number | null>(null);

  abrirAsignarCdp(): void {
    this.asignarCdpAbierto.set(!this.asignarCdpAbierto());
    this.asignarMsg.set('');
    if (this.asignarCdpAbierto()) {
      this.http.get<{ results: any[] }>(
        this.cfg.url('/presupuesto/api/cdps/sin-proyecto/'),
      ).subscribe(r => this.cdpsSinProyecto.set(r.results));
    }
  }

  asignarCdp(): void {
    const d = this.data(); if (!d || !this.cdpAsignarId) return;
    this.guardandoAsignar.set(true);
    this.asignarMsg.set(''); this.asignarErr.set(false);
    this.http.patch(this.cfg.url(`/presupuesto/api/cdps/${this.cdpAsignarId}/`),
      { proyecto_id: d.id }).subscribe({
      next: () => {
        this.guardandoAsignar.set(false);
        this.cdpAsignarId = null;
        this.asignarCdpAbierto.set(false);
        this.cargar(d.id);
      },
      error: e => {
        this.guardandoAsignar.set(true);
        this.asignarErr.set(true);
        this.asignarMsg.set(e?.error?.detail || 'Error asignando CDP.');
        this.guardandoAsignar.set(false);
      },
    });
  }

  quitarCdp(c: CdpHijo): void {
    const d = this.data(); if (!d) return;
    if (!confirm(`¿Quitar el CDP #${c.numero} de este proyecto? (no se borra el CDP)`)) return;
    this.quitandoCdp.set(c.id);
    this.http.patch(this.cfg.url(`/presupuesto/api/cdps/${c.id}/`),
      { proyecto_id: null }).subscribe({
      next: () => { this.quitandoCdp.set(null); this.cargar(d.id); },
      error: () => { this.quitandoCdp.set(null); },
    });
  }

  // ── Actividad-plan: renombrar / eliminar / detalle ───────────
  renombrandoAp = signal<number | null>(null);
  apNuevoNombre = '';
  guardandoRename = signal<boolean>(false);
  eliminandoAp = signal<number | null>(null);
  detalleAp = signal<any | null>(null);
  apMsgAccion = signal<Record<number, string>>({});
  apErrAccion = signal<Record<number, boolean>>({});

  private setApMsg(id: number, msg: string, err: boolean): void {
    this.apMsgAccion.set({ ...this.apMsgAccion(), [id]: msg });
    this.apErrAccion.set({ ...this.apErrAccion(), [id]: err });
  }

  abrirRename(ap: { id: number; descripcion: string }): void {
    this.renombrandoAp.set(ap.id);
    this.apNuevoNombre = ap.descripcion;
  }

  guardarRename(ap: { id: number }): void {
    const d = this.data(); if (!d || !this.apNuevoNombre.trim()) return;
    this.guardandoRename.set(true);
    this.http.patch(this.cfg.url(`/presupuesto/api/actividades-plan/${ap.id}/`),
      { descripcion: this.apNuevoNombre.trim() }).subscribe({
      next: () => {
        this.guardandoRename.set(false);
        this.renombrandoAp.set(null);
        this.cargar(d.id);
      },
      error: e => {
        this.guardandoRename.set(false);
        this.setApMsg(ap.id, e?.error?.detail || 'Error renombrando.', true);
      },
    });
  }

  eliminarAp(ap: { id: number; descripcion: string }): void {
    const d = this.data(); if (!d) return;
    if (!confirm(`¿Eliminar la actividad "${ap.descripcion}"? Solo se puede si no tiene eventos/contratos/KPIs.`)) return;
    this.eliminandoAp.set(ap.id);
    this.http.delete(this.cfg.url(`/presupuesto/api/actividades-plan/${ap.id}/`)).subscribe({
      next: () => { this.eliminandoAp.set(null); this.cargar(d.id); },
      error: e => {
        this.eliminandoAp.set(null);
        this.setApMsg(ap.id, e?.error?.detail || 'No se pudo eliminar.', true);
      },
    });
  }

  verDetalleAp(id: number): void {
    if (this.detalleAp()?.id === id) { this.detalleAp.set(null); return; }
    this.detalleAp.set(null);
    this.http.get<any>(this.cfg.url(`/presupuesto/api/actividades-plan/${id}/`))
      .subscribe(r => this.detalleAp.set(r));
  }

  // ── Crear contrato (uno por CDP) ─────────────────────────────
  ctForms: Record<number, any> = {};
  guardandoCt = signal<number | null>(null);
  ctMsg = signal<Record<number, string>>({});
  ctErr = signal<Record<number, boolean>>({});

  setCt(cdpId: number, key: string, value: any): void {
    this.ctForms[cdpId] = { ...(this.ctForms[cdpId] || {}), [key]: value };
  }

  ctValido(cdpId: number): boolean {
    const f = this.ctForms[cdpId];
    return !!(f?.numero && f?.valor);
  }

  // ── Meta-Proyecto (asociar Meta del catálogo) ────────────────
  metaFormAbierto = signal<boolean>(false);
  metasCatalogo = signal<Array<{ codigo: number; nombre: string }>>([]);
  guardandoMeta = signal<boolean>(false);
  metaMsg = signal<string>('');
  metaErr = signal<boolean>(false);
  metaSeleccionada: number | null = null;
  nuevaMetaNombre = '';

  cargarMetasCatalogo(): void {
    if (this.metasCatalogo().length) return;
    this.http.get<{ results: any[] }>(
      this.cfg.url('/presupuesto/api/metas/'),
    ).subscribe(r => this.metasCatalogo.set(r.results));
  }

  asociarMeta(): void {
    const d = this.data(); if (!d || !this.metaSeleccionada) return;
    this.guardandoMeta.set(true);
    this.metaMsg.set(''); this.metaErr.set(false);
    this.http.post(this.cfg.url('/presupuesto/api/metas-proyecto/'), {
      meta_id: this.metaSeleccionada,
      proyecto_id: d.id,
    }).subscribe({
      next: () => {
        this.metaMsg.set('✓ Meta asociada.');
        this.guardandoMeta.set(false);
        this.metaSeleccionada = null;
        this.metaFormAbierto.set(false);
        this.cargar(d.id);
      },
      error: e => {
        this.metaErr.set(true);
        this.metaMsg.set(e?.error?.detail || 'Error asociando.');
        this.guardandoMeta.set(false);
      },
    });
  }

  crearMetaYAsociar(): void {
    if (!this.nuevaMetaNombre.trim()) return;
    this.guardandoMeta.set(true);
    this.metaMsg.set(''); this.metaErr.set(false);
    this.http.post<{ codigo: number }>(
      this.cfg.url('/presupuesto/api/metas/'),
      { nombre: this.nuevaMetaNombre.trim() },
    ).subscribe({
      next: r => {
        this.metaSeleccionada = r.codigo;
        this.nuevaMetaNombre = '';
        this.asociarMeta();
      },
      error: e => {
        this.metaErr.set(true);
        this.metaMsg.set(e?.error?.detail || 'Error creando meta.');
        this.guardandoMeta.set(false);
      },
    });
  }

  // ── Crear ActividadPlan ──────────────────────────────────────
  apFormAbierto = signal<boolean>(false);
  guardandoAp = signal<boolean>(false);
  apMsg = signal<string>('');
  apErr = signal<boolean>(false);
  apDescripcion = '';

  crearActividadPlan(): void {
    const d = this.data(); if (!d) return;
    if (!this.apDescripcion.trim()) return;
    this.guardandoAp.set(true);
    this.apMsg.set(''); this.apErr.set(false);
    this.http.post(this.cfg.url('/presupuesto/api/actividades-plan/'), {
      proyecto_id: d.id,
      descripcion: this.apDescripcion.trim(),
    }).subscribe({
      next: () => {
        this.apMsg.set('✓ Actividad creada.');
        this.guardandoAp.set(false);
        this.apDescripcion = '';
        this.apFormAbierto.set(false);
        this.cargar(d.id);
      },
      error: e => {
        this.apErr.set(true);
        this.apMsg.set(e?.error?.detail || 'Error.');
        this.guardandoAp.set(false);
      },
    });
  }

  // ── Vinculación Contrato↔ActividadPlan ───────────────────────
  vincForms: Record<number, any> = {};
  guardandoVinc = signal<number | null>(null);
  vincMsg = signal<Record<number, string>>({});
  vincErr = signal<Record<number, boolean>>({});

  setVinc(apId: number, key: string, value: any): void {
    this.vincForms[apId] = { ...(this.vincForms[apId] || {}), [key]: value };
  }

  vincular(apId: number): void {
    const f = this.vincForms[apId];
    if (!f?.contrato_id) return;
    this.guardandoVinc.set(apId);
    this.vincMsg.update(m => ({ ...m, [apId]: '' }));
    this.vincErr.update(m => ({ ...m, [apId]: false }));
    this.http.post(this.cfg.url('/presupuesto/api/vinculaciones/'), {
      contrato_id: f.contrato_id,
      actividad_plan_id: apId,
      monto: f.monto || 0,
    }).subscribe({
      next: () => {
        this.vincMsg.update(m => ({ ...m, [apId]: '✓ Vinculado.' }));
        this.guardandoVinc.set(null);
        delete this.vincForms[apId];
        const id = this.data()?.id; if (id) this.cargar(id);
      },
      error: e => {
        this.vincErr.update(m => ({ ...m, [apId]: true }));
        this.vincMsg.update(m => ({
          ...m, [apId]: e?.error?.detail || 'Error.',
        }));
        this.guardandoVinc.set(null);
      },
    });
  }

  // ── Crear avance manual a KPI ────────────────────────────────
  avForms: Record<number, any> = {};
  guardandoAv = signal<number | null>(null);
  avMsg = signal<Record<number, string>>({});
  avErr = signal<Record<number, boolean>>({});

  setAv(kpiId: number, key: string, value: any): void {
    this.avForms[kpiId] = { ...(this.avForms[kpiId] || {}), [key]: value };
  }

  crearAvance(kpiId: number): void {
    const f = this.avForms[kpiId];
    if (!f?.magnitud_aportada) return;
    this.guardandoAv.set(kpiId);
    this.avMsg.update(m => ({ ...m, [kpiId]: '' }));
    this.avErr.update(m => ({ ...m, [kpiId]: false }));
    this.http.post(this.cfg.url('/presupuesto/api/avances/crear/'), {
      indicador_id: kpiId,
      magnitud_aportada: f.magnitud_aportada,
      fecha_aporte: f.fecha_aporte || null,
      periodo: f.periodo || '',
      observaciones: f.observaciones || '',
    }).subscribe({
      next: () => {
        this.avMsg.update(m => ({ ...m, [kpiId]: '✓ Avance registrado.' }));
        this.guardandoAv.set(null);
        delete this.avForms[kpiId];
        const id = this.data()?.id;
        if (id) this.cargar(id);
      },
      error: e => {
        this.avErr.update(m => ({ ...m, [kpiId]: true }));
        this.avMsg.update(m => ({
          ...m, [kpiId]: e?.error?.detail || 'Error registrando avance.',
        }));
        this.guardandoAv.set(null);
      },
    });
  }

  crearContrato(cdpId: number): void {
    const f = this.ctForms[cdpId];
    if (!f?.numero || !f?.valor) return;
    this.guardandoCt.set(cdpId);
    this.ctMsg.update(m => ({ ...m, [cdpId]: '' }));
    this.ctErr.update(m => ({ ...m, [cdpId]: false }));
    this.http.post(this.cfg.url('/presupuesto/api/contratos/crear/'), {
      numero: f.numero,
      valor: f.valor,
      cdp_id: cdpId,
      fecha_inicio: f.fecha_inicio || null,
      fecha_fin: f.fecha_fin || null,
      objeto: f.objeto || '',
    }).subscribe({
      next: () => {
        this.ctMsg.update(m => ({ ...m, [cdpId]: '✓ Contrato creado.' }));
        this.guardandoCt.set(null);
        delete this.ctForms[cdpId];
        const id = this.data()?.id;
        if (id) this.cargar(id);
      },
      error: e => {
        this.ctErr.update(m => ({ ...m, [cdpId]: true }));
        this.ctMsg.update(m => ({
          ...m, [cdpId]: e?.error?.detail || 'Error creando contrato.',
        }));
        this.guardandoCt.set(null);
      },
    });
  }
}
