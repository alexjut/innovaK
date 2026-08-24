import { CommonModule } from '@angular/common';
import { Component, computed, inject, input, signal } from '@angular/core';
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
  imports: [CommonModule],
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
              <div class="con" [class.con--abierto]="abierto() === c.contrato_id">
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
                            @if (x.editable && x.estado !== 'ok' && puedeCapturar()) {
                              <button type="button" class="completar" (click)="pedirCaptura(c, x)">
                                Completar
                              </button>
                            }
                          </dd>
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

  datos = signal<CompletitudArea | null>(null);
  cargando = signal(true);
  error = signal<string | null>(null);
  abierto = signal<number | null>(null);
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
    this.api.completitud(this.area()).subscribe({
      next: (d) => { this.datos.set(d); this.cargando.set(false); },
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

  /** La captura llega en el siguiente paso: hoy el endpoint de escritura aún
   *  no existe, y ofrecer un botón que no guarda sería peor que no tenerlo. */
  pedirCaptura(c: ContratoCompletitud, x: CampoExpediente): void {
    this.error.set(
      `Capturar «${x.etiqueta}» del contrato ${c.numero} todavía no está habilitado.`);
  }
}
