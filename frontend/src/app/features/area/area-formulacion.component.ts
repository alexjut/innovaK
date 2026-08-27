import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { FormulacionApi } from './formulacion.api';
import {
  BusquedaSecop, ContratoLigado, DocumentoFormulacion, Formulacion,
  ListaFormulaciones, Requisito,
} from './formulacion.types';

/**
 * FORMULACIÓN de un área: lo que se prepara ANTES de que exista el contrato.
 *
 * Vive en `/mi-area/<slug>/formulacion` y no dentro del panel, porque
 * `area-panel.component.ts` lo tiene abierto otra persona. La puerta de entrada
 * la pone el backend (`modulos_area._formulacion_de`), así que la tarjeta
 * aparece en el panel sin tocar ese archivo.
 *
 * TRES REGLAS DE ESTA PANTALLA, heredadas de la casa:
 *
 *  1. **El color nunca va solo.** Cada semáforo lleva su etiqueta escrita y su
 *     motivo (WCAG 1.4.1), igual que el muro.
 *  2. **Ningún cero anónimo.** Si el área no tiene formulaciones, se dice POR
 *     QUÉ: no tiene proyectos, no tiene líneas del plan, ya está todo
 *     contratado, o no ha empezado. Son cuatro cosas distintas.
 *  3. **La pantalla no decide permisos.** `puede_formular` y los `destinos` de
 *     cada estado vienen del servidor. Acá sólo se pintan.
 */
@Component({
  standalone: true,
  selector: 'app-area-formulacion',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <a [routerLink]="['/mi-area', slug]" class="ui-back-link">
            <i class="fa fa-arrow-left" aria-hidden="true"></i> {{ datos()?.area?.nombre || 'Mi área' }}
          </a>
          <h1><i class="fa fa-clipboard-list" aria-hidden="true"></i> Formulación</h1>
          <p class="page__sub">
            Lo que el área prepara antes de que exista el contrato. Cada actividad
            del plan se formula una vez por vigencia.
          </p>
        </div>
      </header>

      @if (error()) {
        <div class="ui-info-bar ui-info-bar--danger" role="alert">{{ error() }}</div>
      }
      @if (cargando()) {
        <div class="ui-info-bar ui-info-bar--info" role="status">Cargando…</div>
      }

      @if (datos(); as d) {
        <!-- Contadores: salen del MISMO semáforo que pinta cada fila -->
        <section class="kpis" aria-label="Resumen de formulaciones">
          @for (c of contadores(); track c.etiqueta) {
            <div class="kpi">
              <span class="kpi__val">{{ c.n }}</span>
              <span class="kpi__lbl">{{ c.icono }} {{ c.etiqueta }}</span>
            </div>
          }
          <div class="kpi kpi--ancho">
            <span class="kpi__val">
              {{ d.resumen.valor_formulado === null ? 'Sin dato' : moneda(d.resumen.valor_formulado) }}
            </span>
            <span class="kpi__lbl">
              Valor formulado
              @if (d.resumen.valor_formulado !== null) {
                <small>({{ d.resumen.valor_cobertura.con }} de {{ d.resumen.valor_cobertura.de }})</small>
              }
            </span>
          </div>
        </section>

        @if (d.resumen.valor_motivo) {
          <p class="motivo">{{ d.resumen.valor_motivo }}</p>
        }

        <!-- El vacío, con su causa. Nunca un 0 pelado. -->
        @if (d.contexto; as ctx) {
          <div class="ui-info-bar"
               [class.ui-info-bar--warn]="ctx.causa === 'sin_lineas_de_plan' || ctx.causa === 'sin_proyectos'"
               [class.ui-info-bar--info]="ctx.causa !== 'sin_lineas_de_plan' && ctx.causa !== 'sin_proyectos'"
               role="status">
            <strong>Todavía no hay formulaciones.</strong> {{ ctx.detalle }}
            @if (ctx.lineas_de_plan) {
              <small>({{ ctx.lineas_de_plan }} actividad(es) del plan,
                     {{ ctx.lineas_con_contrato }} ya con contrato)</small>
            }
          </div>
        }

        @if (d.puede_formular) {
          <div class="alta">
            @if (!altaAbierta()) {
              <button type="button" class="ui-btn" (click)="abrirAlta(d)">
                <i class="fa fa-plus" aria-hidden="true"></i> Nueva formulación
              </button>
            } @else {
              <form class="alta__form" (ngSubmit)="crear(d)">
                <h3>Nueva formulación</h3>
                <label class="ui-field">
                  <span>Actividad del plan</span>
                  <select class="ui-input" [(ngModel)]="nueva.actividad_plan_id"
                          name="actividad" required>
                    <option [ngValue]="null">— Elegí una —</option>
                    @for (a of d.actividades; track a.id) {
                      <option [ngValue]="a.id"
                              [disabled]="a.formulada_en.includes(nueva.vigencia)">
                        {{ a.descripcion }}
                        @if (a.formulada_en.includes(nueva.vigencia)) {
                          — ya formulada en {{ nueva.vigencia }}
                        }
                      </option>
                    }
                  </select>
                </label>
                <label class="ui-field ui-field--corto">
                  <span>Vigencia</span>
                  <select class="ui-input" [(ngModel)]="nueva.vigencia" name="vigencia">
                    @for (v of d.vigencias; track v) { <option [ngValue]="v">{{ v }}</option> }
                  </select>
                </label>
                <label class="ui-field">
                  <span>Objeto — lo que se va a contratar</span>
                  <input class="ui-input" [(ngModel)]="nueva.objeto" name="objeto"
                         required placeholder="Ej. Dotación de implementos deportivos">
                </label>
                <label class="ui-field ui-field--corto">
                  <span>Valor estimado <small>(opcional)</small></span>
                  <input class="ui-input" type="number" [(ngModel)]="nueva.valor_estimado"
                         name="valor" placeholder="Sin dato">
                </label>
                <label class="ui-field">
                  <span>Encargado <small>(se puede asignar después)</small></span>
                  @if (d.funcionarios.length) {
                    <select class="ui-input" [(ngModel)]="nueva.responsable_funcionario_id"
                            name="encargado">
                      <option [ngValue]="null">— Sin encargado por ahora —</option>
                      @for (f of d.funcionarios; track f.id) {
                        <option [ngValue]="f.id">{{ f.nombre }}</option>
                      }
                    </select>
                  } @else {
                    <span class="field-aviso">{{ d.funcionarios_motivo }}</span>
                  }
                </label>
                <div class="alta__acciones">
                  <button type="submit" class="ui-btn"
                          [disabled]="!nueva.actividad_plan_id || !nueva.objeto.trim()">Crear</button>
                  <button type="button" class="ui-btn ui-btn--sutil"
                          (click)="altaAbierta.set(false)">Cancelar</button>
                </div>
                @if (avisoAlta()) {
                  <div class="ui-info-bar ui-info-bar--warn" role="alert">{{ avisoAlta() }}</div>
                }
              </form>
            }
          </div>
        }

        @if (d.formulaciones.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  <th scope="col">Código</th>
                  <th scope="col">Objeto</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Completitud</th>
                  <th scope="col">Encargado</th>
                  <th scope="col" class="der">Valor estimado</th>
                </tr>
              </thead>
              <tbody>
                @for (f of d.formulaciones; track f.id) {
                  <tr [class.fila--activa]="abierta()?.id === f.id">
                    <td>
                      <button type="button" class="enlace" (click)="abrir(f)"
                              [attr.aria-expanded]="abierta()?.id === f.id"
                              [attr.aria-label]="'Abrir ' + f.codigo">{{ f.codigo }}</button>
                    </td>
                    <td>
                      {{ f.objeto }}
                      <small class="act">{{ f.actividad }} · vigencia {{ f.vigencia }}</small>
                    </td>
                    <td>
                      <span class="sem" [attr.data-clave]="f.semaforo.clave"
                            [title]="f.semaforo.motivo">
                        {{ f.semaforo.icono }} {{ f.semaforo.etiqueta }}
                      </span>
                      <small class="act">{{ f.estado.nombre }}</small>
                    </td>
                    <td>
                      @if (f.completitud === null) {
                        <span class="sindato">Sin dato</span>
                      } @else {
                        <div class="barra" [attr.aria-label]="f.completitud + ' por ciento'">
                          <span [style.width.%]="f.completitud"
                                [class.barra--bloqueada]="f.bloqueada"></span>
                        </div>
                        <small class="act">
                          {{ f.completitud }}% · {{ f.completitud_detalle.ok }} de
                          {{ f.completitud_detalle.aplicables }}
                        </small>
                      }
                    </td>
                    <td>
                      @if (f.responsable.id) { {{ f.responsable.nombre }} }
                      @else { <span class="sindato">Sin encargado</span> }
                    </td>
                    <td class="der">
                      {{ f.valor_estimado === null ? '—' : moneda(f.valor_estimado) }}
                    </td>
                  </tr>
                  @if (abierta()?.id === f.id) {
                    <tr class="detalle">
                      <td colspan="6">
                        @if (detalle(); as det) {
                          <div class="det">
                            <!-- Sin catálogo del servidor NO hay stepper: los
                                 pasos son las filas del catálogo de estados, y
                                 dibujarlas de memoria sería inventarlas. -->
                            @if (pasos(det).length) {
                              <ol class="stepper"
                                  [class.stepper--cancelada]="det.cancelada"
                                  [attr.aria-label]="'Estado de la formulación: ' + det.estado.nombre">
                                @for (p of pasos(det); track p.codigo) {
                                  <li [class]="'paso paso--' + p.estado"
                                      [class.paso--ultimo]="p.ultimo"
                                      [attr.aria-current]="p.estado === 'actual' ? 'step' : null"
                                      [title]="p.descripcion || p.etiqueta">
                                    @if (!p.ultimo) {
                                      <span class="paso__via" aria-hidden="true">
                                        @if (p.recorrido) { <span class="paso__via-fill"></span> }
                                      </span>
                                    }
                                    <span class="paso__nodo" aria-hidden="true">{{ p.n }}</span>
                                    <!-- La etiqueta va SIEMPRE escrita: el color
                                         y la posición acompañan, no sustituyen. -->
                                    <span class="paso__etiqueta">{{ p.etiqueta }}</span>
                                  </li>
                                }
                              </ol>
                              @if (det.cancelada) {
                                <p class="motivo motivo--salida">
                                  ⛔ <strong>Cancelada.</strong> No continuará el proceso.
                                  El recorrido queda como estaba, no se borra.
                                </p>
                              }
                            }

                            <!-- El motivo del semáforo, escrito -->
                            <p class="motivo"><strong>{{ det.semaforo.etiqueta }}.</strong>
                               {{ det.semaforo.motivo }}</p>

                            <h3>Requisitos</h3>
                            @for (bloque of bloques(); track bloque) {
                              <h4>{{ bloque }}</h4>
                              <ul class="reqs">
                                @for (r of requisitosDe(bloque); track r.codigo) {
                                  <li [class.req--bloquea]="r.bloquea && r.estado !== 'ok'">
                                    <span class="req__ico">{{ icono(r) }}</span>
                                    <span class="req__nom">
                                      {{ r.nombre }}
                                      @if (r.bloquea) { <b class="critico">crítico</b> }
                                      @if (!r.obligatorio) { <small>opcional</small> }
                                    </span>
                                    @if (r.exige_evidencia) {
                                      @if (r.tiene_evidencia) {
                                        <span class="ev ev--si" title="Tiene soporte cargado">📎</span>
                                      } @else {
                                        <span class="ev" title="Este requisito pide soporte">📎 falta</span>
                                      }
                                    }
                                    @if (det.puede_formular && r.exige_evidencia) {
                                      <label class="subir" [attr.aria-label]="'Subir soporte de ' + r.nombre">
                                        <input type="file" hidden
                                               (change)="subir(det, $event, r.codigo)">
                                        <span class="ui-btn ui-btn--sutil">Subir</span>
                                      </label>
                                    }
                                    @if (det.puede_formular) {
                                      <select class="ui-input req__sel"
                                              [attr.aria-label]="'Estado de ' + r.nombre"
                                              [ngModel]="r.estado"
                                              (ngModelChange)="marcar(det, r, $event)">
                                        <option value="sin_dato">Sin revisar</option>
                                        <option value="pendiente">Pendiente</option>
                                        <option value="ok">Cumplido</option>
                                        <option value="no_aplica">No aplica</option>
                                      </select>
                                    } @else {
                                      <span class="req__est">{{ etiquetaEstado(r.estado) }}</span>
                                    }
                                  </li>
                                }
                              </ul>
                            }

                            @if (det.puede_formular && det.destinos?.length) {
                              <h3>Mover a</h3>
                              <div class="acciones">
                                @for (dst of det.destinos; track dst.codigo) {
                                  <button type="button" class="ui-btn"
                                          (click)="mover(det, dst.codigo)">{{ dst.nombre }}</button>
                                }
                              </div>
                              @if (avisoEstado()) {
                                <div class="ui-info-bar ui-info-bar--warn" role="alert">
                                  {{ avisoEstado() }}
                                </div>
                              }
                            }

                            <h3>Soportes</h3>
                            @if (documentos().length) {
                              <ul class="reqs">
                                @for (doc of documentos(); track doc.id) {
                                  <li>
                                    <span class="req__ico">📎</span>
                                    <span class="req__nom">
                                      <a [href]="urlDoc(det, doc.id)" target="_blank"
                                         rel="noopener">{{ doc.nombre }}</a>
                                      <small>
                                        {{ doc.tipo || 'soporte suelto' }}
                                        @if (doc.tamano_bytes) { · {{ pesoKb(doc.tamano_bytes) }} }
                                        @if (!doc.en_onedrive) { · espejo pendiente }
                                      </small>
                                    </span>
                                    @if (det.puede_formular) {
                                      <button type="button" class="ui-btn ui-btn--sutil"
                                              (click)="borrarDoc(det, doc.id)">Quitar</button>
                                    }
                                  </li>
                                }
                              </ul>
                            } @else {
                              <p class="motivo">
                                Todavía no hay soportes cargados. Los requisitos marcados
                                con 📎 los piden.
                              </p>
                            }
                            @if (det.puede_formular) {
                              <label class="subir">
                                <input type="file" hidden (change)="subir(det, $event)">
                                <span class="ui-btn ui-btn--sutil">Subir un soporte suelto</span>
                              </label>
                            }
                            @if (avisoDoc()) {
                              <div class="ui-info-bar ui-info-bar--warn" role="alert">{{ avisoDoc() }}</div>
                            }

                            <h3>Encargado</h3>
                            @if (det.puede_formular && datos()?.funcionarios?.length) {
                              <select class="ui-input req__sel"
                                      aria-label="Encargado de la formulación"
                                      [ngModel]="det.responsable.id"
                                      (ngModelChange)="asignar(det, $event)">
                                <option [ngValue]="null">— Sin encargado —</option>
                                @for (fn of datos()!.funcionarios; track fn.id) {
                                  <option [ngValue]="fn.id">{{ fn.nombre }}</option>
                                }
                              </select>
                            } @else {
                              <p class="motivo">
                                {{ det.responsable.nombre || datos()?.funcionarios_motivo
                                   || det.responsable.motivo }}
                              </p>
                            }

                            <h3>Contrato</h3>
                            @if (contratos().length) {
                              <ul class="reqs">
                                @for (ct of contratos(); track ct.contrato_id) {
                                  <li>
                                    <span class="req__ico">✓</span>
                                    <span class="req__nom">
                                      {{ ct.numero }}
                                      <small>{{ ct.etapa || 'etapa sin registrar' }}
                                             · {{ ct.valor === null ? 'sin valor' : moneda(ct.valor) }}</small>
                                    </span>
                                    @if (det.puede_formular) {
                                      <button type="button" class="ui-btn ui-btn--sutil"
                                              (click)="desenlazar(det, ct)">Desenlazar</button>
                                    }
                                  </li>
                                }
                              </ul>
                            } @else {
                              <p class="motivo">
                                Todavía no hay contrato. Cuando SECOP lo publique, se
                                busca acá por su número y se enlaza — no se crea otro.
                              </p>
                            }

                            @if (det.puede_formular) {
                              <div class="buscador">
                                <label class="ui-field">
                                  <span>Buscar el contrato en SECOP por su número</span>
                                  <input class="ui-input" type="search" [(ngModel)]="termino"
                                         (keyup.enter)="buscar(det)" placeholder="Ej. 983">
                                </label>
                                <button type="button" class="ui-btn" (click)="buscar(det)">Buscar</button>
                              </div>
                              @if (busqueda(); as b) {
                                @if (b.motivo_vacio) {
                                  <div class="ui-info-bar ui-info-bar--info" role="status">
                                    {{ b.motivo_vacio }}
                                  </div>
                                } @else {
                                  <div class="ui-table-responsive">
                                    <table class="ui-table">
                                      <thead>
                                        <tr>
                                          <th scope="col">Referencia</th>
                                          <th scope="col">Objeto</th>
                                          <th scope="col" class="der">Valor</th>
                                          <th scope="col"></th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        @for (s of b.resultados; track s.id_contrato) {
                                          <tr>
                                            <td>
                                              {{ s.referencia }}
                                              <small class="act">{{ s.anio }}
                                                @if (s.ya_en_innovak) { · ya en innovaK }
                                              </small>
                                            </td>
                                            <td><small>{{ s.objeto }}</small></td>
                                            <td class="der">{{ s.valor === null ? '—' : moneda(s.valor) }}</td>
                                            <td>
                                              @if (!s.parseable) {
                                                <small class="sindato">Referencia sin formato: no se
                                                  puede deducir el número</small>
                                              } @else {
                                                <button type="button" class="ui-btn"
                                                        (click)="enlazar(det, s.id_contrato)">Es este</button>
                                              }
                                            </td>
                                          </tr>
                                        }
                                      </tbody>
                                    </table>
                                  </div>
                                }
                              }
                            }
                          </div>
                        } @else {
                          <p class="motivo">Cargando el detalle…</p>
                        }
                      </td>
                    </tr>
                  }
                }
              </tbody>
            </table>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .kpis { display: flex; flex-wrap: wrap; gap: .75rem; margin-bottom: 1rem; }
    .kpi--ancho { min-width: 220px; }
    .kpi__lbl small { display: block; color: var(--color-text-muted, #6b7280); }
    .motivo { color: var(--color-text-muted, #6b7280); font-size: .86rem; margin: .35rem 0 .9rem; }
    .act { display: block; color: var(--color-text-muted, #6b7280); font-size: .74rem; }
    .der { text-align: right; }
    .sindato { color: var(--color-text-muted, #6b7280); font-style: italic; }
    .enlace { background: none; border: 0; padding: 0; font: inherit; font-weight: 600;
              color: inherit; cursor: pointer; text-decoration: underline; }
    /* El color acompaña a la etiqueta, nunca la sustituye (WCAG 1.4.1). */
    .sem { font-size: .8rem; padding: .12rem .45rem; border-radius: 999px;
           background: #F1F5F9; color: #334155; white-space: nowrap; }
    .sem[data-clave="lista"]       { background: #DCFCE7; color: #166534; }
    .sem[data-clave="en_proceso"]  { background: #FEF3C7; color: #92400E; }
    .sem[data-clave="observada"]   { background: #FFEDD5; color: #9A3412; }
    .sem[data-clave="bloqueada"]   { background: #FEE2E2; color: #991B1B; }
    .barra { height: 7px; background: #E5E7EB; border-radius: 999px; overflow: hidden; min-width: 90px; }
    .barra span { display: block; height: 100%; background: #166534; }
    .barra span.barra--bloqueada { background: #B45309; }
    .fila--activa > td { background: #F8FAFC; }
    .detalle > td { background: #F8FAFC; }
    .det h3 { font-size: .95rem; margin: 1rem 0 .35rem; }
    .det h4 { font-size: .78rem; text-transform: uppercase; letter-spacing: .04em;
              color: var(--color-text-muted, #6b7280); margin: .7rem 0 .2rem; }
    .reqs { list-style: none; padding: 0; margin: 0; }
    .reqs li { display: flex; align-items: center; gap: .5rem; padding: .22rem 0; }
    .req__ico { width: 1.2rem; text-align: center; }
    .req__nom { flex: 1; }
    .req__nom small { color: var(--color-text-muted, #6b7280); }
    .req__sel { max-width: 150px; padding: .15rem .35rem; font-size: .82rem; }
    .critico { color: #991B1B; font-size: .7rem; text-transform: uppercase;
               margin-left: .3rem; letter-spacing: .03em; }
    .req--bloquea .req__nom { font-weight: 600; }
    .acciones { display: flex; flex-wrap: wrap; gap: .4rem; }
    /* Stepper. Calcado del del expediente: nodos numerados, tramo que sólo
       se rellena cuando ya se recorrió, y la etiqueta SIEMPRE escrita. */
    .stepper { display: flex; list-style: none; margin: .2rem 0 1rem; padding: 0;
               flex-wrap: wrap; gap: .2rem 0; }
    .paso { position: relative; flex: 1 1 0; min-width: 92px; text-align: center;
            padding-top: 1.5rem; }
    .paso__nodo { position: absolute; top: 0; left: 50%; transform: translateX(-50%);
                  width: 20px; height: 20px; border-radius: 50%; font-size: .68rem;
                  line-height: 20px; background: #E5E7EB; color: #6B7280;
                  border: 2px solid #E5E7EB; }
    .paso__etiqueta { font-size: .66rem; letter-spacing: .02em; color: #6B7280;
                      display: block; padding: 0 .2rem; }
    .paso__via { position: absolute; top: 9px; left: 50%; width: 100%; height: 2px;
                 background: #E5E7EB; }
    .paso__via-fill { display: block; height: 100%; width: 100%; background: #166534; }
    .paso--completada .paso__nodo { background: #166534; border-color: #166534; color: #fff; }
    .paso--completada .paso__etiqueta { color: #166534; }
    .paso--actual .paso__nodo { background: #fff; border-color: #166534; color: #166534;
                                font-weight: 700; }
    .paso--actual .paso__etiqueta { color: #111827; font-weight: 600; }
    .paso--ultimo .paso__via { display: none; }
    /* Cancelada: el recorrido se apaga entero, no se pinta un paso más. */
    .stepper--cancelada .paso__nodo,
    .stepper--cancelada .paso__via-fill { background: #9CA3AF; border-color: #9CA3AF; }
    .stepper--cancelada .paso__etiqueta { color: #9CA3AF; }
    .motivo--salida { color: #991B1B; }
    .ev { font-size: .72rem; color: #92400E; white-space: nowrap; }
    .ev--si { color: #166534; }
    .subir { cursor: pointer; }
    .alta { margin: .8rem 0; }
    .alta__form { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
                  padding: .9rem 1rem; max-width: 640px; }
    .alta__form h3 { margin: 0 0 .6rem; font-size: .95rem; }
    .alta__form .ui-field { margin-bottom: .55rem; }
    .ui-field--corto { max-width: 220px; }
    .alta__acciones { display: flex; gap: .5rem; margin-top: .7rem; }
    .buscador { display: flex; align-items: flex-end; gap: .5rem; margin-top: .6rem; }
    .buscador .ui-field { flex: 1; max-width: 420px; }
  `],
})
export class AreaFormulacionComponent implements OnInit {
  private api = inject(FormulacionApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  slug = '';
  termino = '';
  moneda = formatMoneda;

  datos = signal<ListaFormulaciones | null>(null);
  abierta = signal<Formulacion | null>(null);
  detalle = signal<Formulacion | null>(null);
  contratos = signal<ContratoLigado[]>([]);
  busqueda = signal<BusquedaSecop | null>(null);
  avisoEstado = signal<string>('');
  cargando = signal(true);
  error = signal('');
  documentos = signal<DocumentoFormulacion[]>([]);
  avisoDoc = signal('');
  altaAbierta = signal(false);
  avisoAlta = signal('');
  nueva: {
    actividad_plan_id: number | null; vigencia: number; objeto: string;
    valor_estimado: number | null; responsable_funcionario_id: number | null;
  } = { actividad_plan_id: null, vigencia: new Date().getFullYear(), objeto: '',
        valor_estimado: null, responsable_funcionario_id: null };

  /** Los contadores SE DERIVAN del semáforo: no pueden separarse del icono. */
  contadores = computed(() => {
    const r = this.datos()?.resumen;
    if (!r) return [];
    return [
      { icono: '⚪', etiqueta: 'Sin iniciar', n: r.sin_iniciar },
      { icono: '🟡', etiqueta: 'En proceso', n: r.en_proceso },
      { icono: '🟠', etiqueta: 'Con observaciones', n: r.observadas },
      { icono: '🔴', etiqueta: 'Bloqueadas', n: r.bloqueadas },
      { icono: '🟢', etiqueta: 'Listas', n: r.listas },
    ].filter(c => c.n > 0 || r.n === 0);
  });

  bloques = computed(() => {
    const reqs = this.detalle()?.requisitos ?? [];
    return [...new Set(reqs.map(r => r.bloque))];
  });

  ngOnInit(): void {
    this.slug = this.route.snapshot.paramMap.get('slug') || '';
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mi área', url: '/mi-area' },
      { label: this.slug, url: `/mi-area/${this.slug}` },
      { label: 'Formulación' },
    ]);
    this.cargar();
  }

  abrirAlta(d: ListaFormulaciones): void {
    // La vigencia arranca en la más reciente que el catálogo ofrezca y no en
    // el año del navegador: si el catálogo llega hasta 2027 y el reloj del
    // equipo está mal, el `<select>` mostraría un año que la FK rechaza.
    const vig = d.vigencias.includes(this.nueva.vigencia)
      ? this.nueva.vigencia : (d.vigencias[0] ?? this.nueva.vigencia);
    this.nueva = { actividad_plan_id: null, vigencia: vig, objeto: '',
                   valor_estimado: null, responsable_funcionario_id: null };
    this.avisoAlta.set('');
    this.altaAbierta.set(true);
  }

  crear(d: ListaFormulaciones): void {
    if (!this.nueva.actividad_plan_id || !this.nueva.objeto.trim()) return;
    this.avisoAlta.set('');
    this.api.crear(this.slug, {
      actividad_plan_id: this.nueva.actividad_plan_id,
      vigencia: this.nueva.vigencia,
      objeto: this.nueva.objeto.trim(),
      valor_estimado: this.nueva.valor_estimado,
    }).subscribe({
      next: (f) => {
        const encargado = this.nueva.responsable_funcionario_id;
        this.altaAbierta.set(false);
        if (encargado) {
          this.api.asignarEncargado(f.id, encargado).subscribe({ next: () => this.cargar() });
        } else {
          this.cargar();
        }
      },
      // El servidor explica el 409 del duplicado con palabras; se muestra tal cual.
      error: (e) => this.avisoAlta.set(e?.error?.detail || 'No se pudo crear la formulación.'),
    });
  }

  asignar(f: Formulacion, funcionarioId: number | null): void {
    this.api.asignarEncargado(f.id, funcionarioId).subscribe({
      next: () => { this.api.detalle(f.id).subscribe({ next: (d) => this.detalle.set(d) }); this.cargar(); },
      error: (e) => this.error.set(e?.error?.detail || 'No se pudo asignar el encargado.'),
    });
  }

  /** Los pasos del recorrido, del catálogo del servidor.
   *
   * **«Cancelada» NO es un paso.** Es `es_final` y una salida desde casi
   * cualquier estado; ponerla al final de la fila sugeriría que toda
   * formulación termina cancelada. Cuando ocurre, el recorrido se apaga entero
   * y se dice aparte, con palabras.
   */
  pasos(f: Formulacion): Array<{
    codigo: number; n: number; etiqueta: string; descripcion: string | null;
    estado: 'completada' | 'actual' | 'futura' | 'neutra';
    recorrido: boolean; ultimo: boolean;
  }> {
    const cat = (this.datos()?.estados_catalogo ?? [])
      .filter(e => !e.es_final)
      .sort((a, b) => a.orden - b.orden);
    const actual = f.cancelada ? null : f.estado.orden;
    return cat.map((e, i) => ({
      codigo: e.codigo,
      n: i + 1,
      etiqueta: e.nombre,
      descripcion: e.descripcion ?? null,
      estado: actual == null ? 'neutra'
            : e.orden < actual ? 'completada'
            : e.orden === actual ? 'actual' : 'futura',
      // Un tramo sólo cuenta como recorrido si su nodo de DESTINO ya se
      // alcanzó; el tramo se dibuja a la derecha de cada nodo.
      recorrido: actual != null && e.orden < actual,
      ultimo: i === cat.length - 1,
    }));
  }

  requisitosDe(bloque: string): Requisito[] {
    return (this.detalle()?.requisitos ?? []).filter(r => r.bloque === bloque);
  }

  icono(r: Requisito): string {
    if (r.estado === 'ok') return '✓';
    if (r.estado === 'no_aplica') return '—';
    return r.bloquea ? '✗' : '·';
  }

  etiquetaEstado(e: string): string {
    return { ok: 'Cumplido', pendiente: 'Pendiente', no_aplica: 'No aplica',
             sin_dato: 'Sin revisar' }[e] ?? e;
  }

  private cargar(): void {
    this.cargando.set(true);
    this.api.lista(this.slug).subscribe({
      next: (d) => { this.datos.set(d); this.cargando.set(false); },
      error: () => {
        this.cargando.set(false);
        this.error.set('No se pudieron cargar las formulaciones de esta área.');
      },
    });
  }

  abrir(f: Formulacion): void {
    if (this.abierta()?.id === f.id) { this.abierta.set(null); return; }
    this.abierta.set(f);
    this.detalle.set(null);
    this.busqueda.set(null);
    this.avisoEstado.set('');
    this.termino = '';
    this.avisoDoc.set('');
    this.documentos.set([]);
    this.api.detalle(f.id).subscribe({ next: (d) => this.detalle.set(d) });
    this.api.contratos(f.id).subscribe({ next: (r) => this.contratos.set(r.contratos) });
    this.api.documentos(f.id).subscribe({ next: (r) => this.documentos.set(r.documentos) });
  }

  urlDoc(f: Formulacion, docId: number): string {
    return this.api.urlDocumento(f.id, docId);
  }

  pesoKb(bytes: number): string {
    return bytes < 1024 * 1024
      ? `${Math.round(bytes / 1024)} KB`
      : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  subir(f: Formulacion, ev: Event, requisito?: string): void {
    const input = ev.target as HTMLInputElement;
    const archivo = input.files?.[0];
    if (!archivo) return;
    this.avisoDoc.set('');
    this.api.subirDocumento(f.id, archivo, requisito).subscribe({
      next: (r) => {
        this.documentos.set(r.documentos);
        this.api.detalle(f.id).subscribe({ next: (d) => this.detalle.set(d) });
        this.cargar();
        input.value = '';   // deja volver a subir el mismo archivo
      },
      // El servidor explica si fue el tamaño, el tipo o el almacenamiento; ese
      // texto se muestra tal cual porque cada caso se arregla distinto.
      error: (e) => { this.avisoDoc.set(e?.error?.detail || 'No se pudo subir el soporte.');
                      input.value = ''; },
    });
  }

  borrarDoc(f: Formulacion, docId: number): void {
    this.api.borrarDocumento(f.id, docId).subscribe({
      next: (r) => {
        this.documentos.set(r.documentos);
        this.api.detalle(f.id).subscribe({ next: (d) => this.detalle.set(d) });
        this.cargar();
      },
      error: (e) => this.avisoDoc.set(e?.error?.detail || 'No se pudo quitar el soporte.'),
    });
  }

  marcar(f: Formulacion, r: Requisito, estado: string): void {
    this.api.marcarRequisito(f.id, r.codigo, estado).subscribe({
      next: () => { this.api.detalle(f.id).subscribe({ next: (d) => this.detalle.set(d) }); this.cargar(); },
      error: () => this.error.set('No se pudo guardar ese requisito.'),
    });
  }

  mover(f: Formulacion, codigo: number): void {
    this.avisoEstado.set('');
    this.api.cambiarEstado(f.id, codigo).subscribe({
      next: (r) => { this.detalle.set(r.formulacion); this.cargar(); },
      // El servidor explica POR QUÉ no se puede, y ese texto se muestra tal cual.
      error: (e) => this.avisoEstado.set(e?.error?.detail || 'No se pudo cambiar el estado.'),
    });
  }

  buscar(f: Formulacion): void {
    if (!this.termino.trim()) return;
    this.api.contratos(f.id, this.termino).subscribe({
      next: (r) => { this.contratos.set(r.contratos); this.busqueda.set(r.busqueda ?? null); },
    });
  }

  enlazar(f: Formulacion, idSecop: string): void {
    this.api.enlazar(f.id, idSecop).subscribe({
      next: (r) => { this.contratos.set(r.contratos); this.busqueda.set(null); this.termino = ''; },
      error: (e) => this.error.set(e?.error?.detail || 'No se pudo enlazar el contrato.'),
    });
  }

  desenlazar(f: Formulacion, ct: ContratoLigado): void {
    this.api.desenlazar(f.id, ct.contrato_id).subscribe({
      next: (r) => this.contratos.set(r.contratos),
      error: (e) => this.error.set(e?.error?.detail || 'No se pudo desenlazar.'),
    });
  }
}
