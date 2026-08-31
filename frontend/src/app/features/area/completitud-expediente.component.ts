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
        <!-- Estado del expediente: la barra es la primera lectura, antes que
             cualquier cifra suelta — es la sección más importante de la
             pantalla y ahora se ve como tal. -->
        <div class="resumen">
          <div class="resumen__cabeza">
            <h3 class="resumen__tit">Estado del expediente</h3>
            @if (d.tiles.pct !== null) {
              <span class="resumen__pct" [class]="'resumen__pct--' + nivel(d.tiles.pct)">
                {{ d.tiles.pct }}% completado
              </span>
            }
          </div>
          @if (d.tiles.pct !== null) {
            <div class="barra" role="progressbar" [attr.aria-valuenow]="d.tiles.pct"
                 aria-valuemin="0" aria-valuemax="100" aria-label="Porcentaje del expediente completo">
              <span class="barra__fill" [class]="'barra__fill--' + nivel(d.tiles.pct)"
                    [style.width.%]="d.tiles.pct"></span>
            </div>
          }
          <div class="resumen__cifras">
            <span class="cifra"><b>{{ d.tiles.n_proyectos }}</b> proyecto{{ d.tiles.n_proyectos === 1 ? '' : 's' }}</span>
            <span class="cifra"><b>{{ d.tiles.n_contratos }}</b> contrato{{ d.tiles.n_contratos === 1 ? '' : 's' }}</span>
            <span class="cifra cifra--falta" [class.cifra--ok]="!d.tiles.n_faltantes">
              @if (d.tiles.n_faltantes) { <i class="fa fa-triangle-exclamation" aria-hidden="true"></i> }
              @else { <i class="fa fa-circle-check" aria-hidden="true"></i> }
              <b>{{ d.tiles.n_faltantes }}</b> pendiente{{ d.tiles.n_faltantes === 1 ? '' : 's' }}
            </span>
          </div>
        </div>

        @if (d.tiles.n_faltantes && puedeCapturar()) {
          <p class="llamado">
            <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
            <span>
              <strong>{{ d.tiles.n_faltantes }}</strong>
              dato{{ d.tiles.n_faltantes === 1 ? '' : 's' }} necesita{{ d.tiles.n_faltantes === 1 ? '' : 'n' }} atención.
              Abrí un contrato y usá <em>Completar</em> en los campos pendientes.
            </span>
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
                            <!-- Soltar: la única forma de corregir un contrato
                                 mal ubicado sin poder quitárselo a otra área.
                                 Queda libre y lo reclama quien corresponda. -->
                            @if (x.clave === 'proyecto' && x.estado === 'ok' && puedeCapturar()) {
                              @if (soltando() === c.contrato_id) {
                                <span class="confirmar">
                                  ¿Soltarlo de esta área?
                                  <button type="button" class="si" (click)="soltar(c)">Sí, soltar</button>
                                  <button type="button" class="no" (click)="soltando.set(null)">No</button>
                                </span>
                              } @else {
                                <button type="button" class="soltar"
                                        (click)="soltando.set(c.contrato_id)"
                                        title="Si este contrato no es de esta área, soltalo para que otra lo reclame">
                                  No es de esta área
                                </button>
                              }
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
                                    @for (e of d.etapas_catalogo; track e.codigo) {
                                      <option [ngValue]="e.codigo">{{ e.nombre }}</option>
                                    }
                                  </select>
                                </label>
                              } @else if (x.clave === 'proyecto') {
                                @if (proyectos().length) {
                                  <label class="form__l form__l--ancho">
                                    <span>Proyecto del área</span>
                                    <select [(ngModel)]="valorProyecto" name="proy">
                                      <option [ngValue]="null">Elegí uno…</option>
                                      @for (p2 of proyectos(); track p2.id) {
                                        <option [ngValue]="p2.id">{{ p2.codigo }} — {{ p2.nombre }}</option>
                                      }
                                    </select>
                                  </label>
                                } @else {
                                  <p class="form__aviso form__aviso--info">
                                    Esta área no tiene proyectos en el plan.
                                  </p>
                                }
                              } @else if (x.clave === 'actividad') {
                                @if (actividadesDe(c).length) {
                                  <label class="form__l form__l--ancho">
                                    <span>Actividad del plan</span>
                                    <select [(ngModel)]="valorActividad" name="act">
                                      <option [ngValue]="null">Elegí una…</option>
                                      @for (a of actividadesDe(c); track a.id) {
                                        <option [ngValue]="a.id">{{ a.descripcion }}</option>
                                      }
                                    </select>
                                  </label>
                                  <label class="form__l">
                                    <span>Monto (opcional)</span>
                                    <input type="number" min="0" [(ngModel)]="montoActividad" name="monto">
                                  </label>
                                } @else {
                                  <p class="form__aviso form__aviso--info">
                                    @if (!tieneProyecto(c)) {
                                      Primero hay que asignarle el proyecto: las actividades
                                      cuelgan de él.
                                    } @else {
                                      Los proyectos de esta área no tienen actividades en el plan.
                                    }
                                  </p>
                                }
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
    @use '../../../styles/tokens' as *;

    /* Acento de acción — mismo teal que \`.ui-btn--accent\` en
       \`_components.scss\` y el acento de dinero del dashboard de
       presupuesto. No es un token global todavía (deuda reconocida);
       se declara UNA vez acá para no repetir el hex en cada regla. */
    $acento: #0F766E;
    $acento-hondo: #115E59;
    $acento-suave: #F1F8F7;

    :host { display: block; }

    .resumen {
      padding: $space-4;
      margin-bottom: $space-3;
      background: $color-bg-subtle;
      border: 1px solid $color-border;
      border-radius: $radius-xl;
    }
    .resumen__cabeza {
      display: flex; align-items: baseline; justify-content: space-between;
      gap: $space-3; flex-wrap: wrap; margin-bottom: $space-2;
    }
    .resumen__tit { margin: 0; font-size: $font-size-sm; font-weight: $font-weight-bold; color: $color-neutral-900; }
    .resumen__pct {
      font-size: $font-size-md; font-weight: $font-weight-bold;
      font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
    }
    .resumen__pct--alto { color: $color-success-hondo; }
    .resumen__pct--medio { color: $color-warning-hondo; }
    .resumen__pct--bajo { color: $color-danger-hondo; }

    .barra {
      height: 10px; border-radius: $radius-pill; background: $color-neutral-200;
      overflow: hidden; margin-bottom: $space-3;
    }
    .barra__fill { display: block; height: 100%; border-radius: $radius-pill; transition: width $transition-base; }
    .barra__fill--alto  { background: $color-success; }
    .barra__fill--medio { background: $color-warning; }
    .barra__fill--bajo  { background: $color-danger; }

    .resumen__cifras { display: flex; gap: $space-5; flex-wrap: wrap; }
    .cifra { display: inline-flex; align-items: baseline; gap: 5px; font-size: $font-size-sm; color: $color-neutral-600; }
    .cifra b { font-size: $font-size-md; color: $color-neutral-900; font-variant-numeric: tabular-nums; }
    .cifra--falta { align-items: center; }
    .cifra--falta i { font-size: 11px; color: $color-warning-hondo; }
    .cifra--falta b { color: $color-warning-hondo; }
    .cifra--ok i { color: $color-success-hondo; }
    .cifra--ok b { color: $color-success-hondo; }

    /* Segmented control: un solo track, no dos chips flotando. */
    .filtros {
      display: inline-flex; gap: 2px; margin-bottom: $space-3;
      padding: 3px; background: $color-bg-muted; border-radius: $radius-pill;
    }
    .chip {
      min-height: 30px; padding: 3px 16px; border-radius: $radius-pill;
      font-size: $font-size-xs; font-weight: $font-weight-semibold;
      border: 0; background: transparent; color: $color-neutral-600; cursor: pointer;
      transition: background $transition-fast, color $transition-fast, box-shadow $transition-fast;
    }
    .chip:hover:not(.chip--on) { color: $color-neutral-900; }
    .chip--on { background: $color-bg; color: $acento-hondo; box-shadow: $shadow-xs; }
    .chip:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }

    .llamado {
      display: flex; align-items: flex-start; gap: $space-2;
      margin: 0 0 $space-3; padding: $space-2 $space-3;
      font-size: $font-size-sm; line-height: $line-height-snug; color: $color-warning-hondo;
      background: $color-warning-bg;
      border-left: 3px solid $color-warning; border-radius: 0 $radius-sm $radius-sm 0;
    }
    .llamado i { margin-top: 2px; flex: none; }
    .llamado strong { font-variant-numeric: tabular-nums; }
    .llamado em { font-style: normal; font-weight: $font-weight-semibold; }

    .proy {
      margin-bottom: $space-4;
      padding: $space-4;
      background: $color-bg;
      border: 1px solid $color-border;
      border-radius: $radius-xl;
    }
    .proy__h {
      display: flex; align-items: center; justify-content: space-between;
      gap: $space-3; padding-bottom: $space-2; border-bottom: 1px solid $color-border;
      margin-bottom: $space-2;
    }
    .proy__cod {
      display: block; font-size: 10px; font-weight: $font-weight-semibold; letter-spacing: 0.12em;
      text-transform: uppercase; color: $color-neutral-600;
      font-family: $font-family-mono;
    }
    .proy__nom { margin: 2px 0 0; font-size: $font-size-md; font-weight: $font-weight-bold; color: $color-neutral-900; }
    .proy__pct {
      font-size: $font-size-md; font-weight: $font-weight-bold; font-variant-numeric: tabular-nums; flex: none;
    }
    .proy__pct--alto { color: $color-success-hondo; }
    .proy__pct--medio { color: $color-warning-hondo; }
    .proy__pct--bajo { color: $color-danger-hondo; }

    .con { border: 1px solid $color-border; border-radius: $radius-lg; margin-bottom: $space-2; background: $color-bg; }
    .con--abierto { border-color: $color-border-strong; }
    /* Llegó por enlace desde la lista de SECOP: se marca para que se encuentre. */
    .con--destacado { border-color: $acento; box-shadow: 0 0 0 3px rgba(13,148,136,.12); }
    .con__h {
      display: flex; align-items: center; gap: $space-2; width: 100%;
      padding: $space-3; background: none; border: 0; cursor: pointer; text-align: left;
      border-radius: $radius-lg;
    }
    .con__h:hover { background: $color-bg-subtle; }
    .con__h:focus-visible { outline: $focus-ring; outline-offset: -3px; }
    .con__chev {
      flex: none; width: 7px; height: 7px;
      border-right: 1.5px solid $color-neutral-500; border-bottom: 1.5px solid $color-neutral-500;
      transform: rotate(-45deg); transition: transform $transition-fast;
    }
    .con--abierto .con__chev { transform: rotate(45deg); }
    .con__num {
      font-family: $font-family-mono;
      font-size: $font-size-xs; font-weight: $font-weight-semibold; color: $color-neutral-900; flex: none;
    }
    .con__obj {
      flex: 1; min-width: 0; font-size: $font-size-sm; color: $color-neutral-600;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .con__falta {
      flex: none; font-size: 11px; padding: 2px 8px; border-radius: $radius-pill;
      background: $color-warning-bg; color: $color-warning-hondo; font-weight: $font-weight-semibold;
    }
    .con__falta--ok { background: $color-success-bg; color: $color-success-hondo; }
    .con__pct {
      flex: none; font-size: $font-size-sm; font-weight: $font-weight-bold; color: $color-neutral-600;
      font-variant-numeric: tabular-nums; min-width: 2.5rem; text-align: right;
    }

    .con__abrir {
      flex: none; font-size: 11px; font-weight: $font-weight-semibold; color: $acento-hondo;
      white-space: nowrap;
    }
    .con__h:hover .con__abrir { text-decoration: underline; }

    .con__cuerpo { padding: 0 $space-3 $space-3; border-top: 1px solid $color-border; }

    .bloques { display: flex; gap: 6px; flex-wrap: wrap; margin: $space-3 0; }
    .bloque {
      display: flex; align-items: baseline; gap: 6px;
      padding: 3px 10px; border-radius: $radius-pill;
      background: $color-bg-muted; border: 1px solid $color-border;
    }
    .bloque--ok { background: $color-success-bg; border-color: rgba(22,163,74,.2); }
    .bloque__lbl { font-size: 11px; color: $color-neutral-600; }
    .bloque__n {
      font-size: 11px; font-weight: $font-weight-bold; color: $color-neutral-900; font-variant-numeric: tabular-nums;
    }

    .campos { margin: 0; display: grid; gap: 1px; background: $color-border; border-radius: $radius-md; overflow: hidden; }
    .campo {
      display: grid; grid-template-columns: minmax(9rem, 14rem) 1fr; gap: $space-3;
      padding: $space-2 $space-3; background: $color-bg; align-items: baseline;
    }
    .campo--sin_dato, .campo--pendiente { background: $color-warning-bg; }
    .campo--no_aplica { background: $color-bg-subtle; }
    .campo__lbl { margin: 0; font-size: $font-size-sm; color: $color-neutral-600; }
    .campo__fuente {
      display: inline-block; margin-left: 6px; padding: 1px 6px;
      font-size: 9px; font-weight: $font-weight-semibold; letter-spacing: 0.06em; text-transform: uppercase;
      background: $color-bg-muted; color: $color-neutral-600; border-radius: $radius-sm;
    }
    .campo__val {
      margin: 0; font-size: $font-size-sm; color: $color-neutral-900; overflow-wrap: anywhere;
      display: flex; align-items: baseline; gap: $space-2; flex-wrap: wrap;
    }
    .sin { color: $color-neutral-500; font-style: italic; }
    .completar {
      padding: 2px 10px; font-size: 11px; font-weight: $font-weight-semibold;
      border: 1px solid $acento; background: $color-bg; color: $acento-hondo;
      border-radius: $radius-sm; cursor: pointer;
    }
    .completar:hover { background: $acento-suave; }
    .completar:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }

    .form {
      grid-column: 1 / -1; margin: $space-2 0 0;
      display: flex; gap: $space-2; flex-wrap: wrap; align-items: flex-end;
      padding: $space-3; background: $acento-suave; border-radius: $radius-md;
    }
    .form__l { display: flex; flex-direction: column; gap: 3px; }
    .form__l span {
      font-size: 10px; font-weight: $font-weight-semibold; letter-spacing: 0.06em;
      text-transform: uppercase; color: $color-neutral-600;
    }
    .form__l--ancho { flex: 1; min-width: 12rem; }
    .form__l select, .form__l input {
      min-height: 32px; padding: 4px 8px; font: inherit; font-size: $font-size-sm;
      border: 1px solid $color-border-strong; border-radius: $radius-md; background: $color-bg; color: $color-neutral-900;
    }
    .form__l select:focus-visible, .form__l input:focus-visible {
      outline: $focus-ring; outline-offset: $focus-ring-offset;
    }
    .form__acc { display: flex; gap: 6px; }
    .guardar, .cancelar {
      min-height: 32px; padding: 4px 14px; font-size: $font-size-sm; font-weight: $font-weight-semibold;
      border-radius: $radius-md; cursor: pointer;
    }
    .guardar { background: $acento; color: $color-text-inverse; border: 1px solid $acento; }
    .guardar:hover:not(:disabled) { background: $acento-hondo; }
    .guardar:disabled { opacity: .6; cursor: default; }
    .cancelar { background: $color-bg; color: $color-neutral-600; border: 1px solid $color-border-strong; }
    .guardar:focus-visible, .cancelar:focus-visible {
      outline: $focus-ring; outline-offset: $focus-ring-offset;
    }
    .form__aviso {
      flex-basis: 100%; margin: $space-1 0 0; font-size: $font-size-xs; color: $color-danger-hondo;
    }

    .plan { flex-basis: 100%; }
    .plan__t { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .plan__t th {
      text-align: left; padding: 2px 6px 6px;
      font-size: 10px; font-weight: $font-weight-semibold; letter-spacing: 0.06em;
      text-transform: uppercase; color: $color-neutral-600;
    }
    .plan__t td { padding: 2px 4px; }
    .plan__n { color: $color-neutral-600; font-variant-numeric: tabular-nums; width: 1.5rem; }
    .plan__t input {
      width: 100%; min-height: 30px; padding: 3px 8px; font: inherit;
      font-size: $font-size-sm; border: 1px solid $color-border-strong; border-radius: $radius-md;
      background: $color-bg; color: $color-neutral-900;
    }
    .plan__t input:focus-visible { outline: $focus-ring; outline-offset: 1px; }
    .plan__x {
      width: 26px; height: 26px; padding: 0; line-height: 1;
      font-size: 1rem; color: $color-danger-hondo; background: none;
      border: 1px solid $color-border-strong; border-radius: $radius-md; cursor: pointer;
    }
    .plan__x:hover { background: $color-danger-bg; border-color: $color-danger-hondo; }
    .plan__x:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    .plan__pie {
      display: flex; align-items: baseline; justify-content: space-between;
      gap: $space-3; flex-wrap: wrap; margin-top: $space-2;
    }
    .plan__mas {
      padding: 3px 11px; font-size: $font-size-xs; font-weight: $font-weight-semibold;
      color: $acento-hondo; background: $color-bg; border: 1px dashed $acento;
      border-radius: $radius-md; cursor: pointer;
    }
    .plan__mas:hover { background: $acento-suave; }
    .plan__mas:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    .plan__tot { font-size: $font-size-sm; color: $color-neutral-600; }
    .plan__tot b { color: $color-neutral-900; font-variant-numeric: tabular-nums; }
    .plan__ayuda { margin: $space-2 0 0; font-size: $font-size-xs; color: $color-neutral-600; }

    .soltar {
      padding: 2px 10px; font-size: 11px; font-weight: $font-weight-semibold;
      border: 1px solid $color-border-strong; background: $color-bg; color: $color-warning-hondo;
      border-radius: $radius-sm; cursor: pointer;
    }
    .soltar:hover { background: $color-warning-bg; border-color: $color-warning-hondo; }
    .soltar:focus-visible, .si:focus-visible, .no:focus-visible {
      outline: $focus-ring; outline-offset: $focus-ring-offset;
    }
    .confirmar {
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 11px; color: $color-warning-hondo;
    }
    .si, .no {
      padding: 2px 9px; font-size: 11px; font-weight: $font-weight-semibold;
      border-radius: $radius-sm; cursor: pointer;
    }
    .si { background: $color-warning-hondo; color: $color-text-inverse; border: 1px solid $color-warning-hondo; }
    .no { background: $color-bg; color: $color-neutral-600; border: 1px solid $color-border-strong; }

    .nota { margin: $space-2 0 0; font-size: $font-size-xs; color: $color-neutral-600; font-style: italic; }
    .vacio {
      margin: $space-3 0; padding: $space-5 $space-4; text-align: center;
      font-size: $font-size-sm; color: $color-neutral-600;
      background: $color-bg-subtle; border: 1px dashed $color-border-strong; border-radius: $radius-xl;
    }
    .vacio--chico { padding: $space-2; margin: $space-1 0; }

    @media (prefers-reduced-motion: reduce) {
      .con__chev, .barra__fill { transition: none; }
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
      next: (o) => {
        this.cdps.set(o.cdps ?? []);
        this.formasPago.set(o.formas_pago ?? []);
        this.proyectos.set(o.proyectos ?? []);
        this.actividades.set(o.actividades ?? []);
      },
      error: () => {
        this.cdps.set([]); this.formasPago.set([]);
        this.proyectos.set([]); this.actividades.set([]);
      },
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
  private readonly CAPTURABLES = new Set(
    ['etapa', 'ejecucion_tec', 'cdp', 'forma_pago', 'plan_pago', 'proyecto', 'actividad']);
  // Las etapas NO se cablean acá: vienen en `datos().etapas_catalogo`, que las
  // lee de la tabla. Esta lista escrita a mano bloqueó durante semanas el
  // retiro de dos etapas del catálogo, porque quitarlas de la base habría
  // dejado la pantalla ofreciendo una etapa que ya no existe y el guardado
  // habría reventado contra la llave foránea. Si mañana Planeación agrega o
  // quita una, esta pantalla se entera sola.
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
  proyectos = signal<{ id: number; codigo: string; nombre: string }[]>([]);
  actividades = signal<{ id: number; descripcion: string; proyecto_id: number }[]>([]);
  valorProyecto: number | null = null;
  valorActividad: number | null = null;
  montoActividad: number | null = null;
  /** El contrato para el que se está confirmando «soltar». */
  soltando = signal<number | null>(null);
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
    this.valorProyecto = null;
    this.valorActividad = null;
    this.montoActividad = null;
    this.soltando.set(null);
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

  /** El proyecto al que ya está enganchado el contrato, si lo hay. */
  private proyectoDe(c: ContratoCompletitud): number | null {
    const campo = c.campos.find((x) => x.clave === 'proyecto');
    const v = campo?.valor;
    return Array.isArray(v) && v.length ? Number(v[0]) : null;
  }

  tieneProyecto(c: ContratoCompletitud): boolean {
    return this.proyectoDe(c) !== null;
  }

  /** Sólo las actividades del proyecto de ESTE contrato. Ofrecer las de otro
   *  proyecto sería invitar al error que el endpoint después rechaza. */
  actividadesDe(c: ContratoCompletitud) {
    const pid = this.proyectoDe(c);
    return pid === null ? [] : this.actividades().filter((a) => a.proyecto_id === pid);
  }

  soltar(c: ContratoCompletitud): void {
    this.guardando.set(true);
    this.api.soltarContrato(this.area(), c.contrato_id).subscribe({
      next: () => {
        this.guardando.set(false);
        this.soltando.set(null);
        // Tras soltarlo, este contrato deja de ser del área: la pantalla se
        // recarga entera y simplemente ya no aparece.
        this.recargar();
      },
      error: (e) => {
        this.guardando.set(false);
        this.soltando.set(null);
        this.error.set(e?.error?.detail || 'No se pudo soltar el contrato.');
      },
    });
  }

  private guardarProyecto(c: ContratoCompletitud): void {
    if (this.valorProyecto === null) {
      this.avisoForm.set('Elegí un proyecto.');
      return;
    }
    this.guardando.set(true);
    this.avisoForm.set(null);
    this.api.asignarProyecto(this.area(), c.contrato_id, this.valorProyecto,
                             this.observacion.trim() || undefined).subscribe({
      next: () => { this.guardando.set(false); this.cerrarCaptura(); this.recargar(); },
      error: (e) => {
        this.guardando.set(false);
        this.avisoForm.set(e?.error?.detail || 'No se pudo asignar el proyecto.');
      },
    });
  }

  private guardarActividad(c: ContratoCompletitud): void {
    if (this.valorActividad === null) {
      this.avisoForm.set('Elegí una actividad del plan.');
      return;
    }
    this.guardando.set(true);
    this.avisoForm.set(null);
    this.api.vincularContrato(this.area(), c.contrato_id, this.valorActividad,
                              this.montoActividad ?? undefined).subscribe({
      next: () => { this.guardando.set(false); this.cerrarCaptura(); this.recargar(); },
      error: (e) => {
        this.guardando.set(false);
        this.avisoForm.set(e?.error?.detail || 'No se pudo enganchar la actividad.');
      },
    });
  }

  guardar(c: ContratoCompletitud, x: CampoExpediente): void {
    if (x.clave === 'plan_pago') { this.guardarPlan(c); return; }
    if (x.clave === 'proyecto') { this.guardarProyecto(c); return; }
    if (x.clave === 'actividad') { this.guardarActividad(c); return; }

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
