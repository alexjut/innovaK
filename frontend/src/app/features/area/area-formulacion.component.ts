import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { FormulacionApi } from './formulacion.api';
import {
  BusquedaSecop, ContratoLigado, Formulacion, ListaFormulaciones, Requisito,
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

        @if (d.formulaciones.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  <th scope="col">Código</th>
                  <th scope="col">Objeto</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Completitud</th>
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
                    <td class="der">
                      {{ f.valor_estimado === null ? '—' : moneda(f.valor_estimado) }}
                    </td>
                  </tr>
                  @if (abierta()?.id === f.id) {
                    <tr class="detalle">
                      <td colspan="5">
                        @if (detalle(); as det) {
                          <div class="det">
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
    this.api.detalle(f.id).subscribe({ next: (d) => this.detalle.set(d) });
    this.api.contratos(f.id).subscribe({ next: (r) => this.contratos.set(r.contratos) });
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
