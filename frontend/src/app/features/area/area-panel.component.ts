import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { ToastService } from '../../shared/ui/toast.service';
import { AreaApi } from './area.api';
import { CompletitudExpedienteComponent } from './completitud-expediente.component';
import { AreaPanel, ContratoArea, FilaPlan } from './area.types';

/**
 * UN panel para las 15 áreas. No hay quince componentes.
 *
 * Lo que cambia entre un área y otra son datos, no código: las tarjetas de
 * módulo salen del registro del backend (`modulos_area.py`) y el resto del
 * árbol es el mismo tronco para todas — proyecto, plan, contrato, evento.
 *
 * Dos decisiones que valen la pena explicar:
 *
 * 1. El panel se ancla en el PLAN, no en el evento. Por eso Educación e
 *    Infraestructura se ven aunque no hayan capturado un solo evento.
 *
 * 2. Lo que está roto se muestra primero, no se esconde. La sección "Lo que
 *    está suelto" existe porque fue posible que 20 de 24 contratos pasaran
 *    meses sin llegar a ninguna actividad sin que nadie lo notara: no había
 *    ninguna pantalla donde eso se viera.
 */
@Component({
  standalone: true,
  selector: 'app-area-panel',
  imports: [CommonModule, FormsModule, RouterLink, CompletitudExpedienteComponent],
  template: `
    @if (loading()) {
      <div class="ui-info-bar ui-info-bar--info" role="status">Cargando…</div>
    }
    @if (error()) {
      <div class="ui-info-bar ui-info-bar--danger" role="alert">{{ error() }}</div>
    }

    @if (p(); as panel) {
      <div class="page">
        <header class="page__header">
          <div>
            <a routerLink="/mi-area" class="ui-back-link">
              <i class="fa fa-arrow-left"></i> Mis áreas
            </a>
            <h1>{{ panel.area.nombre }}</h1>
            <p class="page__sub">{{ panel.area.dependencia }}</p>
          </div>
        </header>

        <!-- La cadena de un vistazo: cada tile dice cuántos DE cuántos, para
             que el hueco se vea sin tener que abrir nada. -->
        <section class="cadena" aria-label="La cadena, de lo macro al beneficiario">
          <div class="eslabon">
            <span class="eslabon__val">{{ panel.tiles.n_proyectos }}</span>
            <span class="eslabon__lbl">Proyectos</span>
          </div>
          <div class="eslabon" [class.eslabon--roto]="rotoActividades(panel)">
            <span class="eslabon__val">
              {{ panel.tiles.n_actividades_con_kpi }}<small>/{{ panel.tiles.n_actividades }}</small>
            </span>
            <span class="eslabon__lbl">Actividades con meta</span>
          </div>
          <div class="eslabon" [class.eslabon--roto]="rotoContratos(panel)">
            <span class="eslabon__val">
              {{ panel.tiles.n_contratos_enganchados }}<small>/{{ panel.tiles.n_contratos }}</small>
            </span>
            <span class="eslabon__lbl">Contratos en el plan</span>
          </div>
          <div class="eslabon" [class.eslabon--roto]="rotoEventos(panel)">
            <span class="eslabon__val">
              {{ panel.tiles.n_eventos_con_actividad }}<small>/{{ panel.tiles.n_eventos }}</small>
            </span>
            <span class="eslabon__lbl">Ejecuciones que suman</span>
          </div>
          <div class="eslabon eslabon--dinero">
            <span class="eslabon__val">
              {{ panel.tiles.valor_contratado | currency:'COP':'symbol-narrow':'1.0-0' }}
            </span>
            <span class="eslabon__lbl">Contratado</span>
          </div>
        </section>

        <!-- Módulos del área -->
        <section>
          <h2>Lo que maneja esta área</h2>
          @if (panel.modulos.length) {
            <div class="modulos">
              @for (m of panel.modulos; track m.codigo) {
                <a class="modulo" [routerLink]="m.ruta">
                  <i class="fa {{ m.icono }}" aria-hidden="true"></i>
                  <span class="modulo__nom">
                    {{ m.nombre }}
                    @if (m.transversal) {
                      <span class="ui-badge ui-badge--muted" title="Herramienta que comparte con otras áreas">compartido</span>
                    }
                  </span>
                  <span class="modulo__desc">{{ m.descripcion }}</span>
                  @if (m.conteo !== null) {
                    <span class="modulo__n">{{ m.conteo }} {{ m.etiqueta_conteo }}</span>
                  }
                </a>
              }
            </div>
          } @else {
            <p class="muted">
              Esta área todavía no tiene herramienta propia ni ha abierto cursos,
              entregas o convocatorias. Trabaja con el plan y los contratos de
              abajo; cuando registre su primera actividad de un tipo, la tarjeta
              aparece sola.
            </p>
          }
        </section>

        <!-- COMPLETITUD DEL EXPEDIENTE: va ANTES de «lo que está suelto» a
             propósito. «Suelto» dice qué relaciones faltan; esto dice qué
             DATOS faltan, contrato por contrato — que es lo que el área viene
             a llenar. Es el trabajo, no el diagnóstico. -->
        <section class="expediente">
          <h2>Completitud del expediente</h2>
          <p class="expediente__sub">
            Lo que las fuentes oficiales ya trajeron viene lleno y no se edita.
            Lo que falta se completa acá, contrato por contrato.
          </p>
          <app-completitud-expediente [area]="areaSlug" />
        </section>

        <!-- Lo que está suelto: primero, no escondido -->
        <section class="sueltos">
          <h2>Lo que está suelto</h2>
          @if (todoConectado(panel)) {
            <div class="ui-info-bar ui-info-bar--success">
              Nada suelto: todo el plan de esta área tiene meta y plata, y todo
              lo ejecutado le suma a algo.
            </div>
          } @else {
            <div class="sueltos__grid">
              @for (s of listaSueltos(panel); track s.clave) {
                @if (s.n) {
                  <article class="suelto">
                    <h3>
                      <span class="suelto__n">{{ s.n }}</span>
                      <span class="suelto__de">de {{ s.de }}</span>
                      {{ s.titulo }}
                    </h3>
                    <p class="muted">{{ s.significa }}</p>
                    <ul>
                      @for (i of s.items.slice(0, 6); track $index) {
                        <li>{{ etiqueta(i) }}</li>
                      }
                      @if (s.items.length > 6) {
                        <li class="muted">… y {{ s.items.length - 6 }} más</li>
                      }
                    </ul>
                  </article>
                }
              }
            </div>
          }
        </section>

        <!-- Enganchar contrato → actividad -->
        @if (panel.sueltos.contratos_sin_actividad.n && panel.plan.length) {
          <section class="enganchar">
            <h2>Enganchar un contrato a una actividad</h2>
            <p class="muted">
              Mientras el contrato no cuelgue de una actividad, esa plata no se
              puede rastrear hasta el beneficiario.
            </p>
            <div class="enganchar__form">
              <label class="ui-field">
                <span>Contrato sin enganchar</span>
                <select class="ui-input" [(ngModel)]="contratoSel">
                  <option [ngValue]="null">— escoge —</option>
                  @for (c of panel.sueltos.contratos_sin_actividad.items; track c.id) {
                    <option [ngValue]="c.id">
                      {{ c.numero }} — {{ (c.objeto || 'sin objeto') | slice:0:60 }}
                    </option>
                  }
                </select>
              </label>
              <label class="ui-field">
                <span>Actividad del plan</span>
                <select class="ui-input" [(ngModel)]="actividadSel">
                  <option [ngValue]="null">— escoge —</option>
                  @for (a of panel.plan; track a.actividad_plan_id) {
                    <option [ngValue]="a.actividad_plan_id">
                      {{ a.proyecto_codigo }} · {{ a.descripcion | slice:0:70 }}
                    </option>
                  }
                </select>
              </label>
              <label class="ui-field">
                <span>Monto (opcional)</span>
                <input class="ui-input" type="number" [(ngModel)]="montoSel">
              </label>
              <button class="ui-btn ui-btn--primary"
                      [disabled]="!contratoSel || !actividadSel || guardando()"
                      (click)="enganchar()">
                <i class="fa fa-link"></i> Enganchar
              </button>
            </div>
          </section>
        }

        <!-- El plan -->
        <section>
          <h2>Plan del área</h2>
          @if (!panel.plan.length) {
            <p class="muted">
              Esta área no tiene actividades en el plan.
              @if (panel.tiles.n_contratos) {
                Y sin embargo tiene {{ panel.tiles.n_contratos }} contrato(s):
                esa plata no está atada a ninguna actividad planeada.
              }
            </p>
          }
          @for (a of panel.plan; track a.actividad_plan_id) {
            <article class="act" [class.act--incompleta]="a.sin_kpi || a.sin_contrato">
              <header>
                <!-- Sin enlace a propósito. /presupuesto/actividades-plan/:id
                     casa con el catch-all :entidad/:id de presupuesto, cuyo
                     mapa de endpoints no conoce actividades-plan: la pantalla
                     respondía "Detalle no disponible". Un enlace que lleva a un
                     callejón es peor que no tenerlo. Vuelve cuando exista la
                     vista de detalle de actividad en Angular. -->
                <strong>{{ a.descripcion }}</strong>
                <small>{{ a.proyecto_codigo }} · {{ a.proyecto_nombre }}</small>
              </header>
              <div class="act__chips">
                @if (a.sin_kpi) { <span class="chip chip--warn">sin meta</span> }
                @else { <span class="chip chip--ok">{{ a.kpis.length }} meta(s)</span> }
                @if (a.sin_contrato) { <span class="chip chip--warn">sin plata</span> }
                @else {
                  <span class="chip chip--ok">
                    {{ a.monto_contratado | currency:'COP':'symbol-narrow':'1.0-0' }}
                  </span>
                }
                <span class="chip">{{ a.n_eventos }} ejecución(es)</span>
              </div>
            </article>
          }
        </section>
      </div>
    }
  `,
  styles: [`
    .cadena { display: flex; flex-wrap: wrap; gap: .75rem; margin: 1rem 0 2rem; }
    .eslabon {
      flex: 1 1 150px; padding: .85rem 1rem; border-radius: 8px;
      background: rgba(0,0,0,.04); display: flex; flex-direction: column; gap: .2rem;
    }
    .eslabon__val { font-size: 1.6rem; font-weight: 700; line-height: 1; }
    .eslabon__val small { font-size: .9rem; font-weight: 400; opacity: .6; }
    .eslabon__lbl { font-size: .78rem; color: var(--color-text-muted, #6b7280); }
    .eslabon--roto { background: rgba(220,38,38,.10); }
    .eslabon--roto .eslabon__val { color: #b91c1c; }
    .eslabon--dinero .eslabon__val { font-size: 1.15rem; }

    .modulos { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap: 1rem; }
    .modulo {
      display: grid; gap: .3rem; padding: 1rem; border-radius: 8px;
      background: rgba(0,0,0,.03); text-decoration: none; color: inherit;
    }
    .modulo:hover { background: rgba(0,0,0,.06); }
    .modulo__nom { font-weight: 600; }
    .modulo__desc { font-size: .82rem; color: var(--color-text-muted,#6b7280); }
    .modulo__n { font-size: .8rem; font-weight: 600; }

    .sueltos__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr)); gap: 1rem; }
    .suelto { padding: 1rem; border-radius: 8px; background: rgba(245,158,11,.10); }
    .suelto h3 { font-size: .95rem; margin: 0 0 .3rem; }
    .suelto__n { font-size: 1.5rem; font-weight: 700; }
    .suelto__de { font-size: .8rem; opacity: .7; margin-right: .3rem; }
    .suelto ul { margin: .5rem 0 0 1rem; font-size: .82rem; }

    .enganchar__form {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr));
      gap: 1rem; align-items: end;
    }
    .act { padding: .75rem 1rem; border-radius: 8px; background: rgba(0,0,0,.03); margin-bottom: .5rem; }
    .act--incompleta { border-left: 3px solid #f59e0b; }
    .act header { display: flex; flex-direction: column; }
    .act header small { color: var(--color-text-muted,#6b7280); font-size: .78rem; }
    .act__chips { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .4rem; }
    .chip { font-size: .74rem; padding: .12rem .5rem; border-radius: 999px; background: rgba(0,0,0,.07); }
    .chip--warn { background: rgba(245,158,11,.25); }
    .chip--ok { background: rgba(22,163,74,.18); }
    .muted { color: var(--color-text-muted,#6b7280); }
    section { margin-bottom: 2rem; }
  
    /* Completitud del expediente: el trabajo del área, no el diagnóstico. */
    .expediente { margin-bottom: 1.5rem; }
    .expediente__sub {
      margin: -0.25rem 0 0.75rem;
      font-size: 0.8125rem; line-height: 1.375; color: #4B5563;
      max-width: 60ch;
    }
`],
})
export class AreaPanelComponent implements OnInit {
  private api = inject(AreaApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private toast = inject(ToastService);

  p = signal<AreaPanel | null>(null);
  loading = signal<boolean>(true);
  error = signal<string>('');
  guardando = signal<boolean>(false);

  contratoSel: number | null = null;
  actividadSel: number | null = null;
  montoSel: number | null = null;

  /** Slug del área tal como viene en la URL (`educacion`). */
  /** Público: lo consume la sección de completitud en la plantilla. */
  areaSlug = '';

  ngOnInit(): void {
    this.areaSlug = this.route.snapshot.paramMap.get('slug') || '';
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.api.panel(this.areaSlug).subscribe({
      next: (p) => {
        this.p.set(p);
        // La miga de pan dice lo mismo que la URL, segmento por segmento:
        // /app/mi-area/educacion  →  Inicio › Mi área › Educación
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Mi área', url: '/mi-area' },
          { label: p.area.nombre || 'Área' },
        ]);
        this.loading.set(false);
      },
      error: (e) => {
        this.error.set(e?.status === 403
          ? 'No tienes acceso a esta área.'
          : 'No se pudo cargar el panel del área.');
        this.loading.set(false);
      },
    });
  }

  // Un eslabón se pinta roto cuando hay algo que enganchar, no cuando está
  // vacío: un área sin contratos todavía no tiene nada roto.
  rotoActividades(p: AreaPanel): boolean {
    return p.tiles.n_actividades > p.tiles.n_actividades_con_kpi;
  }
  rotoContratos(p: AreaPanel): boolean {
    return p.tiles.n_contratos > p.tiles.n_contratos_enganchados;
  }
  rotoEventos(p: AreaPanel): boolean {
    return p.tiles.n_eventos > p.tiles.n_eventos_con_actividad;
  }

  todoConectado(p: AreaPanel): boolean {
    const s = p.sueltos;
    return !(s.actividades_sin_contrato.n || s.actividades_sin_kpi.n
             || s.eventos_sin_actividad.n || s.contratos_sin_actividad.n);
  }

  listaSueltos(p: AreaPanel) {
    const s = p.sueltos;
    return [
      { clave: 'act_sin_plata', titulo: 'actividades sin plata',
        ...this.desSuelto(s.actividades_sin_contrato) },
      { clave: 'act_sin_meta', titulo: 'actividades sin meta',
        ...this.desSuelto(s.actividades_sin_kpi) },
      { clave: 'ev_sueltos', titulo: 'ejecuciones que no suman',
        ...this.desSuelto(s.eventos_sin_actividad) },
      { clave: 'con_sueltos', titulo: 'contratos fuera del plan',
        ...this.desSuelto(s.contratos_sin_actividad) },
    ];
  }

  private desSuelto(s: { n: number; de: number; que_significa: string; items: unknown[] }) {
    return { n: s.n, de: s.de, significa: s.que_significa, items: s.items };
  }

  /** Etiqueta legible de un ítem suelto, sea actividad, evento o contrato. */
  etiqueta(i: unknown): string {
    const o = i as Record<string, unknown>;
    return String(o['descripcion'] ?? o['nombre'] ?? o['numero'] ?? o['id'] ?? '—');
  }

  enganchar(): void {
    if (!this.contratoSel || !this.actividadSel) return;
    this.guardando.set(true);
    this.api.vincularContrato(this.areaSlug, this.contratoSel, this.actividadSel,
                              this.montoSel ?? undefined).subscribe({
      next: () => {
        this.guardando.set(false);
        this.contratoSel = this.actividadSel = this.montoSel = null;
        this.toast.success('Contrato enganchado a la actividad.');
        this.cargar();
      },
      error: (e) => {
        this.guardando.set(false);
        this.toast.error(e?.error?.detail || 'No se pudo enganchar.');
      },
    });
  }
}
