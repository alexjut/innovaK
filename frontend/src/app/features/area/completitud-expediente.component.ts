import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Component, computed, inject, input, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AreaApi } from './area.api';
import { CampoExpediente, CompletitudArea, ContratoCompletitud } from './area.types';

/**
 * Completitud del expediente — el centro operativo de Mi Área.
 *
 * Responde la pregunta que el área necesita: **qué me falta, y en cuál
 * contrato**. Se edita contrato por contrato, nunca en un formulario del
 * subgrupo entero.
 *
 * Tres reglas que vienen del backend y NO se recalculan acá:
 *
 * 1. El porcentaje. Es `completos / aplicables`, plano. El front no pondera.
 * 2. El permiso. `puede_capturar` lo decide el servidor (rol Coordinador del
 *    área). Ocultar el botón no autoriza — la validación real está en el
 *    endpoint, esto sólo evita ofrecer lo que se va a rechazar.
 * 3. El estado de cada campo. `$0` llega como `ok` porque es un dato medido;
 *    convertir ausencia en cero es inventar.
 */
@Component({
  standalone: true,
  selector: 'app-completitud-expediente',
  imports: [CommonModule, FormsModule],
  template: `
    @if (cargando()) {
      <p class="ui-info-bar ui-info-bar--info" role="status">Revisando el expediente…</p>
    }
    @if (error(); as e) {
      <p class="ui-info-bar ui-info-bar--danger" role="alert">{{ e }}</p>
    }

    @if (datos(); as d) {
      @if (d.sin_plan) {
        <p class="vacio">{{ d.motivo }}</p>
      } @else {
        <!-- Resumen del área. El pendiente va con dueño y con nombre, nunca
             como un cero anónimo. -->
        <div class="resumen">
          <div class="resumen__cifras">
            <span class="cifra"><b>{{ d.tiles.n_proyectos }}</b> proyectos</span>
            <span class="cifra"><b>{{ d.tiles.n_contratos }}</b> contratos</span>
            <span class="cifra cifra--falta" [class.cifra--ok]="!d.tiles.n_faltantes">
              <b>{{ d.tiles.n_faltantes }}</b> datos pendientes
            </span>
          </div>
          @if (d.tiles.pct !== null) {
            <div class="global">
              <span class="global__pct">{{ d.tiles.pct }}%</span>
              <span class="global__lbl">del expediente completo</span>
            </div>
          }
        </div>

        @if (d.tiles.n_faltantes && puedeCapturar()) {
          <p class="llamado">
            <strong>{{ d.tiles.n_faltantes }}</strong>
            dato{{ d.tiles.n_faltantes === 1 ? '' : 's' }} por completar.
            Abrí un contrato y usá <em>Completar</em> en los campos pendientes.
          </p>
        }

        <div class="filtros" role="group" aria-label="Filtrar contratos">
          <button type="button" class="chip" [class.chip--on]="!soloPendientes()"
                  (click)="soloPendientes.set(false)">Todos</button>
          <button type="button" class="chip" [class.chip--on]="soloPendientes()"
                  (click)="soloPendientes.set(true)">Solo pendientes</button>
        </div>

        @for (p of proyectosVisibles(); track p.id) {
          <article class="proy">
            <header class="proy__h">
              <div>
                <span class="proy__cod">{{ p.codigo }}</span>
                <h3 class="proy__nom">{{ p.nombre }}</h3>
              </div>
              @if (p.pct !== null) {
                <span class="proy__pct" [class]="'proy__pct--' + nivel(p.pct)">{{ p.pct }}%</span>
              }
            </header>

            @if (!p.contratos.length) {
              <p class="vacio vacio--chico">
                Este proyecto todavía no tiene contratos.
              </p>
            }

            @for (c of contratosVisibles(p.contratos); track c.contrato_id) {
              <div class="con" [id]="'con-' + c.contrato_id"
                   [class.con--abierto]="abierto() === c.contrato_id"
                   [class.con--destacado]="destacado() === c.contrato_id">
                <button type="button" class="con__h"
                        [attr.aria-expanded]="abierto() === c.contrato_id"
                        (click)="alternar(c.contrato_id)">
                  <span class="con__chev" aria-hidden="true"></span>
                  <span class="con__num">{{ c.numero }}</span>
                  <span class="con__obj">{{ c.objeto || '—' }}</span>
                  @if (c.n_faltantes) {
                    <span class="con__falta">{{ c.n_faltantes }} pendiente{{ c.n_faltantes === 1 ? '' : 's' }}</span>
                  } @else {
                    <span class="con__falta con__falta--ok">completo</span>
                  }
                  @if (c.pct !== null) {
                    <span class="con__pct">{{ c.pct }}%</span>
                  }
                  <span class="con__abrir">
                    {{ abierto() === c.contrato_id ? 'Cerrar' : 'Ver y completar' }}
                  </span>
                </button>

                @if (abierto() === c.contrato_id) {
                  <div class="con__cuerpo">
                    <!-- Por bloques: se ve QUÉ falta, no sólo cuánto. -->
                    <div class="bloques">
                      @for (b of c.bloques; track b.clave) {
                        <div class="bloque" [class.bloque--ok]="b.completos === b.total">
                          <span class="bloque__lbl">{{ b.etiqueta }}</span>
                          <span class="bloque__n">{{ b.completos }}/{{ b.total }}</span>
                        </div>
                      }
                    </div>

                    <dl class="campos">
                      @for (x of c.campos; track x.clave) {
                        <div class="campo" [class]="'campo--' + x.estado">
                          <dt class="campo__lbl">
                            {{ x.etiqueta }}
                            @if (x.fuente) {
                              <span class="campo__fuente" [title]="'Dato de ' + x.fuente">{{ x.fuente }}</span>
                            }
                          </dt>
                          <dd class="campo__val">
                            @if (x.estado === 'ok') {
                              {{ mostrar(x) }}
                            } @else if (x.estado === 'no_aplica') {
                              <span class="sin">No aplica</span>
                            } @else {
                              <span class="sin">Pendiente por diligenciar</span>
                            }
                            @if (capturable(x) && x.estado !== 'ok' && puedeCapturar()) {
                              <button type="button" class="completar"
                                      (click)="abrirCaptura(c, x)">Completar</button>
                            }
                          </dd>

                          @if (capturando()?.contrato === c.contrato_id
                               && capturando()?.campo === x.clave) {
                            <dd class="form">
                              @if (x.clave === 'etapa') {
                                <label class="form__l">
                                  <span>Etapa</span>
                                  <select [(ngModel)]="valorEtapa" name="etapa">
                                    <option [ngValue]="null">Elegí una…</option>
                                    @for (e of ETAPAS; track e.codigo) {
                                      <option [ngValue]="e.codigo">{{ e.nombre }}</option>
                                    }
                                  </select>
                                </label>
                              } @else if (x.clave === 'plan_pago') {
                                <!-- El plan es una TABLA, no un campo: períodos
                                     con lo programado. La etiqueta es libre a
                                     propósito — caben meses, hitos o anticipos. -->
                                <div class="plan">
                                  <table class="plan__t">
                                    <thead>
                                      <tr>
                                        <th scope="col">#</th>
                                        <th scope="col">Período</th>
                                        <th scope="col">Programado</th>
                                        <th scope="col"><span class="ui-sr-only">Quitar</span></th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      @for (f of planFilas(); track $index) {
                                        <tr>
                                          <td class="plan__n">{{ $index + 1 }}</td>
                                          <td>
                                            <input type="text" [(ngModel)]="f.periodo"
                                                   [name]="'per' + $index"
                                                   placeholder="Enero 2026 · Hito 1 · Anticipo 30 %">
                                          </td>
                                          <td>
                                            <input type="number" min="0" [(ngModel)]="f.programado"
                                                   [name]="'prog' + $index" placeholder="Sin dato">
                                          </td>
                                          <td>
                                            <button type="button" class="plan__x"
                                                    (click)="quitarFila($index)"
                                                    [attr.aria-label]="'Quitar el período ' + ($index + 1)">×</button>
                                          </td>
                                        </tr>
                                      }
                                    </tbody>
                                  </table>
                                  <div class="plan__pie">
                                    <button type="button" class="plan__mas" (click)="agregarFila()">
                                      + Agregar período
                                    </button>
                                    @if (totalPlan() !== null) {
                                      <span class="plan__tot">
                                        Total programado:
                                        <b>{{ totalPlan() | currency:'COP':'symbol-narrow':'1.0-0' }}</b>
                                      </span>
                                    }
                                  </div>
                                  <p class="plan__ayuda">
                                    Dejá el monto vacío si todavía no se sabe.
                                    Un <b>0</b> significa que ese período no paga.
                                  </p>
                                </div>
                              } @else if (x.clave === 'forma_pago') {
                                <label class="form__l form__l--ancho">
                                  <span>Forma de pago</span>
                                  <select [(ngModel)]="valorForma" name="forma">
                                    <option [ngValue]="null">Elegí una…</option>
                                    @for (f of formasPago(); track f.codigo) {
                                      <option [ngValue]="f.codigo">{{ f.nombre }}</option>
                                    }
                                  </select>
                                </label>
                              } @else if (x.clave === 'cdp') {
                                @if (cdps().length) {
                                  <label class="form__l form__l--ancho">
                                    <span>CDP del proyecto</span>
                                    <select [(ngModel)]="valorCdp" name="cdp">
                                      <option [ngValue]="null">Elegí uno…</option>
                                      @for (c2 of cdps(); track c2.id) {
                                        <option [ngValue]="c2.id">{{ c2.etiqueta }}</option>
                                      }
                                    </select>
                                  </label>
                                } @else {
                                  <p class="form__aviso form__aviso--info">
                                    Esta área todavía no tiene CDP registrados.
                                    Hay que crear el CDP antes de poder asociarlo.
                                  </p>
                                }
                              } @else {
                                <label class="form__l">
                                  <span>Avance %</span>
                                  <input type="number" min="0" max="100"
                                         [(ngModel)]="valorAvance" name="avance">
                                </label>
                                <label class="form__l">
                                  <span>Fecha de corte</span>
                                  <input type="date" [(ngModel)]="fechaCorte"
                                         [max]="hoy" name="corte">
                                </label>
                              }
                              @if (x.clave !== 'cdp' || cdps().length) {
                              <label class="form__l form__l--ancho">
                                <span>Observación</span>
                                <input type="text" [(ngModel)]="observacion"
                                       name="obs" placeholder="Opcional">
                              </label>
                              }
                              <div class="form__acc">
                                @if (x.clave !== 'cdp' || cdps().length) {
                                <button type="button" class="guardar"
                                        [disabled]="guardando()"
                                        (click)="guardar(c, x)">
                                  {{ guardando() ? 'Guardando…' : 'Guardar' }}
                                </button>
                                }
                                <button type="button" class="cancelar"
                                        (click)="cerrarCaptura()">Cancelar</button>
                              </div>
                              @if (avisoForm(); as a) {
                                <p class="form__aviso" role="alert">{{ a }}</p>
                              }
                            </dd>
                          }
                        </div>
                      }
                    </dl>

                    @if (!puedeCapturar() && c.n_faltantes) {
                      <p class="nota">
                        Para completar estos datos hace falta el rol de Coordinador de esta área.
                      </p>
                    }
                  </div>
                }
              </div>
            }
          </article>
        }

        @if (!proyectosVisibles().length) {
          <p class="vacio">
            @if (soloPendientes()) {
              No hay contratos con datos pendientes. El expediente está al día.
            } @else {
              Esta área todavía no tiene contratos.
            }
          </p>
        }
      }
    }
  `,
  styles: [`
    :host { display: block; }

    .resumen {
      display: flex; align-items: center; justify-content: space-between;
      gap: 1rem; flex-wrap: wrap;
      padding: 0.75rem 1rem; margin-bottom: 0.75rem;
      background: #FAF9F8; border: 1px solid #EDEBE8; border-radius: 0.75rem;
    }
    .resumen__cifras { display: flex; gap: 1.25rem; flex-wrap: wrap; }
    .cifra { font-size: 0.875rem; color: #4B5563; }
    .cifra b { font-size: 1.125rem; color: #111827; font-variant-numeric: tabular-nums; }
    .cifra--falta b { color: #92400E; }
    .cifra--ok b { color: #166534; }
    .global { text-align: right; }
    .global__pct {
      display: block; font-size: 1.5rem; font-weight: 700;
      color: #111827; font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
    }
    .global__lbl { font-size: 0.75rem; color: #4B5563; }

    .filtros { display: flex; gap: 0.25rem; margin-bottom: 0.75rem; }
    .chip {
      min-height: 28px; padding: 3px 14px; border-radius: 9999px;
      font-size: 0.75rem; font-weight: 600;
      border: 1px solid #DFDCD7; background: #fff; color: #4B5563; cursor: pointer;
    }
    .chip:hover { border-color: #0F766E; color: #0F766E; }
    .chip--on { background: #0F766E; color: #fff; border-color: #0F766E; }
    .chip:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }

    .llamado {
      margin: 0 0 0.75rem; padding: 0.5rem 0.75rem;
      font-size: 0.8125rem; line-height: 1.375; color: #92400E;
      background: rgba(245, 158, 11, 0.09);
      border-left: 3px solid #F59E0B; border-radius: 0 0.25rem 0.25rem 0;
    }
    .llamado strong { font-variant-numeric: tabular-nums; }
    .llamado em { font-style: normal; font-weight: 600; }

    .proy { margin-bottom: 1rem; }
    .proy__h {
      display: flex; align-items: center; justify-content: space-between;
      gap: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #EDEBE8;
      margin-bottom: 0.5rem;
    }
    .proy__cod {
      display: block; font-size: 10px; font-weight: 600; letter-spacing: 0.12em;
      text-transform: uppercase; color: #4B5563;
      font-family: 'SF Mono', Monaco, 'Roboto Mono', Consolas, monospace;
    }
    .proy__nom { margin: 2px 0 0; font-size: 0.9375rem; font-weight: 700; color: #111827; }
    .proy__pct {
      font-size: 1rem; font-weight: 700; font-variant-numeric: tabular-nums; flex: none;
    }
    .proy__pct--alto { color: #166534; }
    .proy__pct--medio { color: #92400E; }
    .proy__pct--bajo { color: #991B1B; }

    .con { border: 1px solid #EDEBE8; border-radius: 0.5rem; margin-bottom: 0.375rem; background: #fff; }
    .con--abierto { border-color: #DFDCD7; }
    /* Llegó por enlace desde la lista de SECOP: se marca para que se encuentre. */
    .con--destacado { border-color: #0F766E; box-shadow: 0 0 0 3px rgba(13,148,136,.12); }
    .con__h {
      display: flex; align-items: center; gap: 0.5rem; width: 100%;
      padding: 0.625rem 0.75rem; background: none; border: 0; cursor: pointer; text-align: left;
    }
    .con__h:hover { background: #FAF9F8; }
    .con__h:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: -3px; }
    .con__chev {
      flex: none; width: 7px; height: 7px;
      border-right: 1.5px solid #6B7280; border-bottom: 1.5px solid #6B7280;
      transform: rotate(-45deg); transition: transform 150ms ease-out;
    }
    .con--abierto .con__chev { transform: rotate(45deg); }
    .con__num {
      font-family: 'SF Mono', Monaco, 'Roboto Mono', Consolas, monospace;
      font-size: 0.75rem; font-weight: 600; color: #111827; flex: none;
    }
    .con__obj {
      flex: 1; min-width: 0; font-size: 0.8125rem; color: #4B5563;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .con__falta {
      flex: none; font-size: 11px; padding: 2px 8px; border-radius: 9999px;
      background: rgba(245,158,11,.14); color: #92400E; font-weight: 600;
    }
    .con__falta--ok { background: rgba(22,163,74,.10); color: #166534; }
    .con__pct {
      flex: none; font-size: 0.8125rem; font-weight: 700; color: #4B5563;
      font-variant-numeric: tabular-nums; min-width: 2.5rem; text-align: right;
    }

    .con__abrir {
      flex: none; font-size: 11px; font-weight: 600; color: #0F766E;
      white-space: nowrap;
    }
    .con__h:hover .con__abrir { text-decoration: underline; }

    .con__cuerpo { padding: 0 0.75rem 0.75rem; border-top: 1px solid #EDEBE8; }

    .bloques { display: flex; gap: 0.375rem; flex-wrap: wrap; margin: 0.625rem 0; }
    .bloque {
      display: flex; align-items: baseline; gap: 6px;
      padding: 3px 10px; border-radius: 9999px;
      background: #F4F3F1; border: 1px solid #EDEBE8;
    }
    .bloque--ok { background: rgba(22,163,74,.08); border-color: rgba(22,163,74,.2); }
    .bloque__lbl { font-size: 11px; color: #4B5563; }
    .bloque__n {
      font-size: 11px; font-weight: 700; color: #111827; font-variant-numeric: tabular-nums;
    }

    .campos { margin: 0; display: grid; gap: 1px; background: #EDEBE8; border-radius: 0.375rem; overflow: hidden; }
    .campo {
      display: grid; grid-template-columns: minmax(9rem, 14rem) 1fr; gap: 0.75rem;
      padding: 0.5rem 0.75rem; background: #fff; align-items: baseline;
    }
    .campo--sin_dato, .campo--pendiente { background: #FEFCF7; }
    .campo--no_aplica { background: #FAFAFA; }
    .campo__lbl { margin: 0; font-size: 0.8125rem; color: #4B5563; }
    .campo__fuente {
      display: inline-block; margin-left: 6px; padding: 1px 6px;
      font-size: 9px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
      background: #F4F3F1; color: #4B5563; border-radius: 0.25rem;
    }
    .campo__val {
      margin: 0; font-size: 0.8125rem; color: #111827; overflow-wrap: anywhere;
      display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;
    }
    .sin { color: #6B7280; font-style: italic; }
    .completar {
      padding: 2px 10px; font-size: 11px; font-weight: 600;
      border: 1px solid #0F766E; background: #fff; color: #0F766E;
      border-radius: 0.25rem; cursor: pointer;
    }
    .completar:hover { background: #F1F8F7; }
    .completar:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }

    .form {
      grid-column: 1 / -1; margin: 0.5rem 0 0;
      display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: flex-end;
      padding: 0.625rem; background: #F1F8F7; border-radius: 0.375rem;
    }
    .form__l { display: flex; flex-direction: column; gap: 3px; }
    .form__l span {
      font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
      text-transform: uppercase; color: #4B5563;
    }
    .form__l--ancho { flex: 1; min-width: 12rem; }
    .form__l select, .form__l input {
      min-height: 32px; padding: 4px 8px; font: inherit; font-size: 0.8125rem;
      border: 1px solid #DFDCD7; border-radius: 0.375rem; background: #fff; color: #111827;
    }
    .form__l select:focus-visible, .form__l input:focus-visible {
      outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px;
    }
    .form__acc { display: flex; gap: 0.375rem; }
    .guardar, .cancelar {
      min-height: 32px; padding: 4px 14px; font-size: 0.8125rem; font-weight: 600;
      border-radius: 0.375rem; cursor: pointer;
    }
    .guardar { background: #0F766E; color: #fff; border: 1px solid #0F766E; }
    .guardar:hover:not(:disabled) { background: #115E59; }
    .guardar:disabled { opacity: .6; cursor: default; }
    .cancelar { background: #fff; color: #4B5563; border: 1px solid #DFDCD7; }
    .guardar:focus-visible, .cancelar:focus-visible {
      outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px;
    }
    .form__aviso {
      flex-basis: 100%; margin: 0.25rem 0 0; font-size: 0.75rem; color: #991B1B;
    }

    .plan { flex-basis: 100%; }
    .plan__t { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .plan__t th {
      text-align: left; padding: 2px 6px 6px;
      font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
      text-transform: uppercase; color: #4B5563;
    }
    .plan__t td { padding: 2px 4px; }
    .plan__n { color: #4B5563; font-variant-numeric: tabular-nums; width: 1.5rem; }
    .plan__t input {
      width: 100%; min-height: 30px; padding: 3px 8px; font: inherit;
      font-size: 0.8125rem; border: 1px solid #DFDCD7; border-radius: 0.375rem;
      background: #fff; color: #111827;
    }
    .plan__t input:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 1px; }
    .plan__x {
      width: 26px; height: 26px; padding: 0; line-height: 1;
      font-size: 1rem; color: #991B1B; background: none;
      border: 1px solid #DFDCD7; border-radius: 0.375rem; cursor: pointer;
    }
    .plan__x:hover { background: #FEE2E2; border-color: #991B1B; }
    .plan__x:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }
    .plan__pie {
      display: flex; align-items: baseline; justify-content: space-between;
      gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem;
    }
    .plan__mas {
      padding: 3px 11px; font-size: 0.75rem; font-weight: 600;
      color: #0F766E; background: #fff; border: 1px dashed #0F766E;
      border-radius: 0.375rem; cursor: pointer;
    }
    .plan__mas:hover { background: #F1F8F7; }
    .plan__mas:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }
    .plan__tot { font-size: 0.8125rem; color: #4B5563; }
    .plan__tot b { color: #111827; font-variant-numeric: tabular-nums; }
    .plan__ayuda { margin: 0.5rem 0 0; font-size: 0.75rem; color: #4B5563; }

    .nota { margin: 0.625rem 0 0; font-size: 0.75rem; color: #4B5563; font-style: italic; }
    .vacio {
      margin: 0.75rem 0; padding: 1.25rem 1rem; text-align: center;
      font-size: 0.8125rem; color: #4B5563;
      background: #FAF9F8; border: 1px dashed #DFDCD7; border-radius: 0.75rem;
    }
    .vacio--chico { padding: 0.625rem; margin: 0.375rem 0; }

    @media (prefers-reduced-motion: reduce) {
      .con__chev { transition: none; }
    }
  `],
})
export class CompletitudExpedienteComponent {
  /** Slug o id del área. El backend acepta los dos. */
  area = input.required<string>();

  private api = inject(AreaApi);
  private route = inject(ActivatedRoute);

  datos = signal<CompletitudArea | null>(null);
  cargando = signal(true);
  error = signal<string | null>(null);
  abierto = signal<number | null>(null);
  /** El que se pidió por URL: se resalta un momento para no perderlo de vista. */
  destacado = signal<number | null>(null);
  soloPendientes = signal(false);

  puedeCapturar = computed(() => this.datos()?.puede_capturar ?? false);

  proyectosVisibles = computed(() => {
    const d = this.datos();
    if (!d || d.sin_plan) return [];
    if (!this.soloPendientes()) return d.proyectos;
    return d.proyectos
      .map((p) => ({ ...p, contratos: p.contratos.filter((c) => c.n_faltantes > 0) }))
      .filter((p) => p.contratos.length > 0);
  });

  ngOnInit(): void {
    // Los catálogos van aparte del panel: se necesitan ANTES de abrir un
    // formulario, y si fallan no deben tumbar la pantalla entera.
    this.api.opcionesCaptura(this.area()).subscribe({
      next: (o) => { this.cdps.set(o.cdps ?? []); this.formasPago.set(o.formas_pago ?? []); },
      error: () => { this.cdps.set([]); this.formasPago.set([]); },
    });

    this.api.completitud(this.area()).subscribe({
      next: (d) => {
        this.datos.set(d);
        this.cargando.set(false);
        // Si el área tiene POCOS contratos, se abre el primero que tenga
        // pendientes. Plegado, «Completar» queda a dos clics de distancia y no
        // se encuentra — pasó en la primera prueba. Con muchos (Cultura tiene
        // 15) abrirlos sería un muro, así que el umbral es 3.
        const todos = d.proyectos?.flatMap((p) => p.contratos) ?? [];

        // Si se llegó desde la lista de SECOP con `?contrato=<id>`, se abre ESE
        // y se le hace scroll. Sin esto, el enlace deja al usuario en una
        // pantalla con quince contratos plegados y sin pista de cuál era.
        const pedido = Number(this.route.snapshot.queryParamMap.get('contrato'));
        if (pedido && todos.some((c) => c.contrato_id === pedido)) {
          this.abierto.set(pedido);
          this.destacado.set(pedido);
          queueMicrotask(() => {
            document.getElementById(`con-${pedido}`)
              ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          });
          return;
        }

        if (todos.length && todos.length <= 3) {
          const conFalta = todos.find((c) => c.n_faltantes > 0);
          if (conFalta) this.abierto.set(conFalta.contrato_id);
        }
      },
      error: () => {
        this.error.set('No se pudo revisar el expediente de esta área.');
        this.cargando.set(false);
      },
    });
  }

  contratosVisibles(cs: ContratoCompletitud[]): ContratoCompletitud[] {
    return this.soloPendientes() ? cs.filter((c) => c.n_faltantes > 0) : cs;
  }

  alternar(id: number): void {
    this.abierto.update((a) => (a === id ? null : id));
  }

  nivel(pct: number): string {
    return pct >= 80 ? 'alto' : pct >= 50 ? 'medio' : 'bajo';
  }

  /** Presenta el valor según su forma. Las metas van en plural: son N. */
  mostrar(x: CampoExpediente): string {
    const v = x.valor;
    if (v === null || v === undefined) return '—';
    if (Array.isArray(v)) {
      if (x.clave === 'metas') {
        const n = v.length;
        return n === 1
          ? `Meta ${(v[0] as { nombre?: string })?.nombre ?? ''} · determinada automáticamente`
          : `${n} metas`;
      }
      return `${v.length}`;
    }
    if (typeof v === 'number') {
      // Dinero y conteos: el separador de miles hace legible una cifra larga.
      return x.clave === 'valor' || x.clave === 'ejecucion_fin'
        ? '$' + v.toLocaleString('es-CO', { maximumFractionDigits: 0 })
        : String(v);
    }
    return String(v);
  }

  // ── captura ────────────────────────────────────────────────────────────
  /** Los únicos dos capturables: los que ninguna fuente oficial publica. */
  private readonly CAPTURABLES = new Set(['etapa', 'ejecucion_tec', 'cdp', 'forma_pago', 'plan_pago']);
  readonly ETAPAS = [
    { codigo: 1, nombre: 'Formulación' },
    { codigo: 2, nombre: 'Ejecución' },
    { codigo: 3, nombre: 'Liquidación' },
    { codigo: 4, nombre: 'Sancionatorio' },
  ];
  readonly hoy = new Date().toISOString().slice(0, 10);

  capturando = signal<{ contrato: number; campo: string } | null>(null);
  guardando = signal(false);
  avisoForm = signal<string | null>(null);
  valorEtapa: number | null = null;
  valorAvance: number | null = null;
  valorCdp: number | null = null;
  valorForma: number | null = null;
  /** El plan se edita como tabla: filas en memoria hasta que se guarda. */
  planFilas = signal<{ periodo: string; programado: number | null }[]>([]);
  formasPago = signal<{ codigo: number; nombre: string }[]>([]);
  /** Catálogos del servidor: las 4 etapas y los CDP de ESTA área. */
  cdps = signal<{ id: number; etiqueta: string; proyecto_id: number | null }[]>([]);
  fechaCorte = this.hoy;
  observacion = '';

  capturable(x: CampoExpediente): boolean {
    return x.editable && this.CAPTURABLES.has(x.clave);
  }

  abrirCaptura(c: ContratoCompletitud, x: CampoExpediente): void {
    this.avisoForm.set(null);
    this.valorEtapa = null;
    this.valorAvance = null;
    this.valorCdp = null;
    this.valorForma = null;
    if (x.clave === 'plan_pago') {
      // Arranca con tres filas vacías: una tabla en blanco no invita a nada, y
      // tres es lo mínimo donde se ve que se pueden agregar y quitar.
      this.planFilas.set([
        { periodo: '', programado: null },
        { periodo: '', programado: null },
        { periodo: '', programado: null },
      ]);
    }
    this.fechaCorte = this.hoy;
    this.observacion = '';
    this.capturando.set({ contrato: c.contrato_id, campo: x.clave });
  }

  cerrarCaptura(): void {
    this.capturando.set(null);
    this.avisoForm.set(null);
  }

  agregarFila(): void {
    this.planFilas.update((f) => [...f, { periodo: '', programado: null }]);
  }

  quitarFila(i: number): void {
    this.planFilas.update((f) => f.filter((_, k) => k !== i));
  }

  /** Suma lo programado ignorando los vacíos: sumar «no se sabe» como cero
   *  daría un total que parece medido y no lo es. */
  totalPlan(): number | null {
    const con = this.planFilas().filter((f) => f.programado !== null
                                            && f.programado !== undefined);
    return con.length ? con.reduce((a, f) => a + Number(f.programado), 0) : null;
  }

  private guardarPlan(c: ContratoCompletitud): void {
    const filas = this.planFilas()
      .filter((f) => (f.periodo || '').trim())
      .map((f, i) => ({
        orden: i + 1,
        periodo: f.periodo.trim(),
        // '' y undefined viajan como null: es «no se sabe», no cero.
        programado: (f.programado === null || f.programado === undefined
                     || (f.programado as unknown) === '') ? null : Number(f.programado),
      }));

    if (!filas.length) {
      this.avisoForm.set('Agregá al menos un período con nombre.');
      return;
    }

    this.guardando.set(true);
    this.avisoForm.set(null);
    this.api.guardarPlanPago(this.area(), c.contrato_id, filas).subscribe({
      next: () => {
        this.guardando.set(false);
        this.cerrarCaptura();
        this.recargar();
      },
      error: (e) => {
        this.guardando.set(false);
        this.avisoForm.set(e?.error?.detail || 'No se pudo guardar el plan.');
      },
    });
  }

  guardar(c: ContratoCompletitud, x: CampoExpediente): void {
    if (x.clave === 'plan_pago') { this.guardarPlan(c); return; }

    const campo = x.clave as 'etapa' | 'ejecucion_tec' | 'cdp' | 'forma_pago';
    const valor = campo === 'etapa' ? this.valorEtapa
                : campo === 'cdp' ? this.valorCdp
                : campo === 'forma_pago' ? this.valorForma
                : this.valorAvance;

    if (valor === null || valor === undefined) {
      this.avisoForm.set(
        campo === 'etapa' ? 'Elegí una etapa.'
        : campo === 'cdp' ? 'Elegí un CDP.'
        : campo === 'forma_pago' ? 'Elegí una forma de pago.'
        : 'Escribí el avance.');
      return;
    }
    if (campo === 'ejecucion_tec' && (valor < 0 || valor > 100)) {
      this.avisoForm.set('El avance va de 0 a 100.');
      return;
    }

    this.guardando.set(true);
    this.avisoForm.set(null);
    this.api.capturarDato(this.area(), c.contrato_id, {
      campo,
      valor,
      ...(campo === 'ejecucion_tec' ? { fecha_corte: this.fechaCorte } : {}),
      ...(this.observacion.trim() ? { observacion: this.observacion.trim() } : {}),
    }).subscribe({
      next: () => {
        // Se recarga entero en vez de parchear el modelo local: el porcentaje
        // y los bloques los calcula el backend, y reproducir esa cuenta acá
        // sería una segunda fuente de verdad que se va a separar.
        this.guardando.set(false);
        this.cerrarCaptura();
        this.recargar();
      },
      error: (e) => {
        this.guardando.set(false);
        // El backend explica por qué rechazó —rol, área, valor fuera de
        // rango— y ese mensaje es mejor que uno genérico de acá.
        this.avisoForm.set(e?.error?.detail || 'No se pudo guardar.');
      },
    });
  }

  private recargar(): void {
    this.api.completitud(this.area()).subscribe({
      next: (d) => this.datos.set(d),
      error: () => this.error.set('Se guardó, pero no se pudo refrescar la pantalla.'),
    });
  }
}
