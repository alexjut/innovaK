import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, Component, ElementRef,
  OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { firstValueFrom, forkJoin, of, timer } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatNumero, tipoEventoNombre } from '../../shared/format/format.util';
import { StatGridComponent, StatItem } from '../../shared/ui/stat-grid.component';
import { AttentionPanelComponent, AtencionItem } from '../../shared/ui/attention-panel.component';
import { ObjetivosResumenComponent } from './objetivos/objetivos-resumen.component';
import { PerspectivasExploradorComponent } from './objetivos/perspectivas-explorador.component';
import { ObjetivoEstrategico, ProyectoLista } from './objetivos/objetivos.types';
import { ExpedienteProyectoComponent } from './expediente/expediente-proyecto.component';
import {
  MuroSubgruposComponent, SEMAFORO_TEXTO,
  cifraLedger, coberturaLedgerTexto, enMillones, fechaLegible,
} from './muro/muro-subgrupos.component';
import { EstadoSemaforo, MuroSubgrupos } from './muro/muro-subgrupos.types';

Chart.register(...registerables);

interface ResumenEjecutivo {
  proyectos: number; metas_pdd: number; indicadores: number;
  eventos_mes: number; avances: number; en_riesgo: number;
}
interface EventosMesTipo {
  por_mes: { mes: string; total: number }[];
  por_tipo: { tipo: string; total: number }[];
}
type TopSectores = Array<{
  sector: string; porcentaje: number; n_kpis: number; avance: number; meta: number;
}>;
interface MetasProgreso {
  stats: { total: number; cumplidas: number; en_progreso: number;
           en_riesgo: number; sin_avance: number };
  metas: Array<{
    codigo: string; nombre: string; sector?: string;
    porcentaje: number; meta_total?: number; avance_total?: number;
    estado: 'cumplida' | 'en_progreso' | 'en_riesgo' | 'sin_avance';
    fecha_fin?: string; num_indicadores?: number;
  }>;
}
// ── Cockpit ejecutivo (additivo) ──────────────────────────────
interface EjecucionFinanciera {
  contratado_total: number; n_contratos: number; n_con_valor: number;
  pct_ejecucion: number; cdp_asignado: number; cdp_n: number; cdp_con_valor: number;
  por_categoria: Array<{ categoria: string; n: number; valor: number; ejecucion: number | null }>;
  top_proyectos: Array<{ codigo: string; nombre: string; n: number; valor: number }>;
  vigencias: number[]; vigencia_activa: number | null;
}
interface BeneficiariosPerfil {
  beneficiarios: number; organizaciones: number;
  genero: Array<{ nombre: string; total: number }>; pct_mujeres: number;
  participantes: number; eventos_con_participacion: number;
  participantes_por_estado: Array<{ estado: string; total: number }>;
  caracterizaciones: number;
}

// `ObjetivoEstrategico`/`ProyectoLista` se importan de
// `./objetivos/objetivos.types` — es el mismo árbol que consumen
// `<app-objetivos-resumen>` y `<app-perspectivas-explorador>`, una sola
// definición para los tres en vez de repetirla acá.

/** Los cuatro acordeones del pie. Nacen cerrados, todos. */
type Clave = 'muro';

/** Las 5 secciones de nivel superior del centro de control. */
type Vista = 'resumen' | 'proyectos' | 'metas' | 'areas' | 'analitica';

@Component({
  standalone: true,
  selector: 'app-presupuesto-dashboard',
  imports: [
    CommonModule, RouterLink, MuroSubgruposComponent,
    StatGridComponent, AttentionPanelComponent,
    ObjetivosResumenComponent, PerspectivasExploradorComponent,
    ExpedienteProyectoComponent,
  ],
  template: `
    <div class="page">
      @let p = plata();
      @let g = gente();
      @let r = resumen();

      <header class="hero-compacto">
        <div class="hero-compacto__texto">
          <span class="rotulo">Alcaldía Local de Kennedy</span>
          <h1>Presupuesto e Inversión Local</h1>
          <p class="hero-compacto__sub">Control ejecutivo del Plan de Desarrollo Local</p>
        </div>
        <div class="hero-compacto__meta">
          @if (p && p.vigencias.length) {
            <div class="vigencia" role="group" aria-labelledby="vigencia-rot">
              <span class="vigencia__rotulo rotulo" id="vigencia-rot">Vigencia</span>
              <div class="vigencia__opciones">
                <button type="button" class="vchip" [class.vchip--on]="!vigencia()"
                        [attr.aria-pressed]="!vigencia()"
                        (click)="setVigencia(null)">Todas</button>
                <!-- Solo 2025/2026: p.vigencias trae años sueltos de
                     contratos legacy (2015, 2024…) que no son vigencias
                     del PDL actual. La lógica de setVigencia() no cambia. -->
                @for (v of vigenciasVisibles(p.vigencias); track v) {
                  <button type="button" class="vchip" [class.vchip--on]="vigencia() === v"
                          [attr.aria-pressed]="vigencia() === v"
                          (click)="setVigencia(v)">{{ v }}</button>
                }
              </div>
            </div>
          }
          @if (corteTexto(); as c) {
            <span class="hero-compacto__corte">
              <i class="fa fa-clock" aria-hidden="true"></i>
              Corte SECOP: <b>{{ c }}</b>
            </span>
          }
        </div>
      </header>

      @if (errorMsg()) {
        <div class="error-card">
          <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
          <strong>{{ errorMsg() }}</strong>
          <button class="ui-btn ui-btn--sm" (click)="recargar()">
            <i class="fa fa-rotate" aria-hidden="true"></i> Reintentar
          </button>
        </div>
      }

      <!-- ═══════════════════════════════════════════════════════════════════
           CENTRO DE CONTROL — progressive disclosure en 2 niveles:

             Nivel 1 (estas 5 pestañas)   ¿qué está pasando · dónde · qué reviso?
             Nivel 2 (dentro de cada una)  el detalle, bajo demanda

           Resumen    → 4 KPI ejecutivos + estado de la inversión + qué requiere atención
           Proyectos  → Explorador 360° completo (sin cambios internos)
           Metas      → seguimiento del plan + panorama de metas
           Áreas      → el muro de subgrupos (sin cambios internos)
           Analítica  → beneficiarios, género, eventos, sectores (sin cambios internos)

           Ningún dato nuevo: esto solo reorganiza DÓNDE vive cada bloque que ya
           existía. Las 4 pestañas de abajo (Personas/Seguimiento/Eventos/Muro)
           siguen siendo exactamente los mismos acordeones, solo reubicados.
           ═══════════════════════════════════════════════════════════════════ -->

      <nav class="vista-tabs" role="tablist" aria-label="Secciones del centro de control"
           (keydown)="navegarVista($event)">
        <button type="button" role="tab" id="vtab-resumen" class="vista-tab"
                [class.vista-tab--on]="vista() === 'resumen'"
                [attr.aria-selected]="vista() === 'resumen'" aria-controls="vpanel-resumen"
                [attr.tabindex]="vista() === 'resumen' ? 0 : -1" (click)="setVista('resumen')">
          Resumen
        </button>
        <button type="button" role="tab" id="vtab-proyectos" class="vista-tab"
                [class.vista-tab--on]="vista() === 'proyectos'"
                [attr.aria-selected]="vista() === 'proyectos'" aria-controls="vpanel-proyectos"
                [attr.tabindex]="vista() === 'proyectos' ? 0 : -1" (click)="setVista('proyectos')">
          Proyectos
          @if (nProyectosTotal()) { <span class="vista-tab__n">{{ nProyectosTotal() }}</span> }
        </button>
        <button type="button" role="tab" id="vtab-metas" class="vista-tab"
                [class.vista-tab--on]="vista() === 'metas'"
                [attr.aria-selected]="vista() === 'metas'"
                aria-controls="vpanel-metas-panorama vpanel-metas-plan"
                [attr.tabindex]="vista() === 'metas' ? 0 : -1" (click)="setVista('metas')">
          Metas
        </button>
        <button type="button" role="tab" id="vtab-areas" class="vista-tab"
                [class.vista-tab--on]="vista() === 'areas'"
                [attr.aria-selected]="vista() === 'areas'" aria-controls="vpanel-areas"
                [attr.tabindex]="vista() === 'areas' ? 0 : -1" (click)="setVista('areas')">
          Áreas
        </button>
        <button type="button" role="tab" id="vtab-analitica" class="vista-tab"
                [class.vista-tab--on]="vista() === 'analitica'"
                [attr.aria-selected]="vista() === 'analitica'"
                aria-controls="vpanel-analitica-gente vpanel-analitica-eventos"
                [attr.tabindex]="vista() === 'analitica' ? 0 : -1" (click)="setVista('analitica')">
          Analítica
        </button>
      </nav>

      <!-- ════════ RESUMEN — 4 KPI + estado de inversión + requiere atención ═══ -->
      @if (vista() === 'resumen') {
      <div id="vpanel-resumen" role="tabpanel" aria-labelledby="vtab-resumen" tabindex="0">
        <section class="resumen-kpis" aria-label="Indicadores ejecutivos de inversión">
          <app-stat-grid [stats]="kpisEjecutivos()" />
        </section>

        <div class="resumen-cols">
          <section class="inversion" aria-labelledby="inversion-tit" id="estado-inversion">
            <h2 class="inversion__tit rotulo" id="inversion-tit">Estado de la inversión</h2>

            @if (muro(); as m) {
              <div class="inversion__barras">
                @if (ledgerApropiacion(); as ap) {
                  <div class="ibar">
                    <span class="ibar__rotulo">Apropiación<small class="ibar__vig">{{ rangoApropiacion() }}</small></span>
                    <span class="ibar__pista"><span class="ibar__fill ibar__fill--apropiacion"
                          [style.width.%]="anchoRelativo(ap.valor)"></span></span>
                    <span class="ibar__valor">{{ enMillones(ap.valor) }}</span>
                  </div>
                }
                <div class="ibar">
                  <span class="ibar__rotulo">Proyectado<small class="ibar__vig">cuatrienio</small></span>
                  <span class="ibar__pista"><span class="ibar__fill ibar__fill--programado"
                        [style.width.%]="anchoRelativo(ledgerProgramado().valor)"></span></span>
                  <span class="ibar__valor">{{ enMillones(ledgerProgramado().valor) }}</span>
                </div>
                <div class="ibar">
                  <span class="ibar__rotulo">Comprometido</span>
                  <span class="ibar__pista"><span class="ibar__fill ibar__fill--comprometido"
                        [style.width.%]="anchoRelativo(ledgerComprometido().valor)"></span></span>
                  <span class="ibar__valor">{{ enMillones(ledgerComprometido().valor) }}</span>
                </div>
                <div class="ibar">
                  <span class="ibar__rotulo">Girado</span>
                  <span class="ibar__pista"><span class="ibar__fill ibar__fill--girado"
                        [style.width.%]="anchoRelativo(ledgerGirado().valor)"></span></span>
                  <span class="ibar__valor">{{ enMillones(ledgerGirado().valor) }}</span>
                </div>
              </div>
              <p class="inversion__saldo">
                <span class="rotulo">Saldo por girar</span>
                {{ enMillones(ledgerSaldo().valor) }}
                <small>comprometido − girado</small>
              </p>

              <div class="inversion__cortes">
                <span class="corte">
                  <span class="rotulo">Corte SECOP</span>
                  @if (m.cabecera.corte) { <b>{{ fecha(m.cabecera.corte) }}</b> }
                  @else { <span class="sin-dato">sin dato</span> }
                </span>
                <span class="corte">
                  <span class="rotulo">Corte PDL oficial</span>
                  @if (m.cabecera.corte_pdl_oficial) { <b>{{ fecha(m.cabecera.corte_pdl_oficial) }}</b> }
                  @else { <span class="sin-dato">sin dato</span> }
                </span>
                <span class="corte corte--tiempo">
                  <span class="rotulo">Tiempo del PDL</span>
                  @if (pctTiempo() != null) {
                    <span class="tiempo">
                      <span class="tiempo__barra" aria-hidden="true">
                        <span class="tiempo__fill" [style.width.%]="pctTiempo()"></span>
                      </span>
                      <b>{{ pctTiempo() }} %</b>
                    </span>
                  } @else { <span class="sin-dato">sin ventana declarada</span> }
                </span>
              </div>

              <!-- Este aviso NO es decoración: sin él, las barras de arriba mienten. -->
              <p class="resumen__aviso">
                <i class="fa fa-circle-info" aria-hidden="true"></i>
                <span>
                  Son <strong>dos cortes distintos</strong>: lo comprometido y lo girado
                  vienen de SECOP; lo programado, del PDL oficial de la SDP.
                  <strong>No se restan entre sí</strong> — el saldo es comprometido menos
                  girado, nunca programado menos comprometido: serían dos universos y dos
                  fechas de corte, y esa resta daría un número plausible y falso.
                </span>
              </p>
              <p class="resumen__aviso resumen__aviso--alcance">
                <i class="fa fa-list-check" aria-hidden="true"></i>
                <span>
                  Las cuatro cifras son del <strong>total de la localidad</strong> y no
                  cambian al filtrar: los filtros de Proyectos acotan esa lista, no este
                  estado de inversión.
                </span>
              </p>
            } @else if (muroError()) {
              <p class="resumen__aviso resumen__aviso--error">
                <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
                <span>{{ muroError() }}</span>
              </p>
            } @else {
              <p class="resumen__aviso"><span>Midiendo cortes y ejecución…</span></p>
            }
          </section>

          <app-attention-panel [items]="atencionItems()" (accion)="onAtencionClick($event)" />
        </div>

        <!-- Adelanto liviano de Metas y Analítica: los números que ya se
             calcularon para sus propias pestañas, sin repetir su detalle
             (metas una por una, gráficos). Un vistazo y un enlace, no una
             copia de la pestaña. -->
        <div class="resumen-extra">
          <section class="mini" aria-labelledby="mini-metas-tit">
            <div class="mini__cabeza">
              <h2 class="mini__tit" id="mini-metas-tit">Metas del plan</h2>
              <button type="button" class="mini__ver" (click)="setVista('metas')">
                Ver metas <i class="fa fa-arrow-right-long" aria-hidden="true"></i>
              </button>
            </div>
            @if (metas(); as m) {
              <div class="stats-strip">
                <span class="stat stat--ok">{{ m.stats.cumplidas }} cumplidas</span>
                <span class="stat stat--prog">{{ m.stats.en_progreso }} en progreso</span>
                <span class="stat stat--warn">{{ m.stats.en_riesgo }} en riesgo</span>
                <span class="stat stat--none">{{ m.stats.sin_avance }} sin avance</span>
              </div>
            } @else {
              <p class="sin-dato">midiendo…</p>
            }
          </section>

          <section class="mini" aria-labelledby="mini-analitica-tit">
            <div class="mini__cabeza">
              <h2 class="mini__tit" id="mini-analitica-tit">Analítica</h2>
              <button type="button" class="mini__ver" (click)="setVista('analitica')">
                Ver analítica <i class="fa fa-arrow-right-long" aria-hidden="true"></i>
              </button>
            </div>
            @if (g) {
              <div class="mini__cifras">
                <span class="mini__cifra"><b>{{ formatNumero(g.beneficiarios) }}</b> beneficiarios</span>
                <span class="mini__cifra"><b>{{ formatNumero(g.participantes) }}</b> participantes</span>
                <span class="mini__cifra"><b>{{ formatNumero(g.organizaciones) }}</b> organizaciones</span>
                @if (r) {
                  <span class="mini__cifra"><b>{{ r.eventos_mes }}</b> eventos este mes</span>
                }
              </div>
            } @else {
              <p class="sin-dato">midiendo…</p>
            }
          </section>
        </div>

        <!-- ════════ PERSPECTIVAS DEL PDL — Objetivo Estratégico → Programa
             → Proyecto → Meta. Se agrega DEBAJO de lo anterior, no lo
             reemplaza. El resumen (KPIs + donut de alertas) es GLOBAL: no
             cambia al elegir una perspectiva ni al filtrar más abajo. ═══ -->
        <section class="perspectivas-seccion" aria-labelledby="persp-seccion-tit">
          <h2 class="rotulo" id="persp-seccion-tit">Perspectivas del Plan de Desarrollo Local</h2>
          <p class="resumen__aviso resumen__aviso--alcance">
            <i class="fa fa-circle-info" aria-hidden="true"></i>
            <span>
              Este bloque cubre <strong>todas las vigencias</strong> — el filtro de
              vigencia de arriba todavía no recalcula perspectivas, programas,
              proyectos ni metas (pendiente de backend).
            </span>
          </p>
          <app-objetivos-resumen [objetivos]="objetivos()" />
          <app-perspectivas-explorador [objetivos]="objetivos()" [abrirProyectoId]="abrirProyectoId()" />
        </section>
      </div>
      }

      <!-- ════════ METAS — seguimiento del plan + panorama ══════════════ -->
      @if (vista() === 'metas') {
      <div id="vpanel-metas-panorama" role="tabpanel" aria-labelledby="vtab-metas" tabindex="0">
        @if (metas(); as m) {
          <div class="stats-strip">
            <span class="stat stat--ok">{{ m.stats.cumplidas }} cumplidas</span>
            <span class="stat stat--prog">{{ m.stats.en_progreso }} en progreso</span>
            <span class="stat stat--warn">{{ m.stats.en_riesgo }} en riesgo</span>
            <span class="stat stat--none">{{ m.stats.sin_avance }} sin avance</span>
          </div>
          <p class="bloque__pie">
            El porcentaje es contra la meta <strong>de la vigencia</strong>, no contra
            la del cuatrienio que suele venir en el nombre.
            @if (mapaMetaProyecto().size) {
              Al pulsar una meta se abre su proyecto en Proyectos.
            }
          </p>
          <ul class="metas" role="list">
            @for (mt of m.metas; track mt.codigo) {
              <li class="metas__fila" [class]="'metas__fila--' + mt.estado">
                <button type="button" class="meta"
                        [attr.aria-disabled]="proyectoDeMeta(mt.codigo) ? null : 'true'"
                        [attr.title]="proyectoDeMeta(mt.codigo)
                                      ? 'Abrir el proyecto de esta meta en Proyectos'
                                      : 'Esta meta no tiene proyecto asociado en la base'"
                        [attr.aria-label]="proyectoDeMeta(mt.codigo)
                                      ? 'Abrir en Proyectos el proyecto de la meta ' + mt.codigo
                                      : 'La meta ' + mt.codigo
                                        + ' no tiene proyecto asociado en la base'"
                        (click)="abrirProyectoDeMeta(mt.codigo)">
                  <span class="meta__id">{{ mt.codigo }}</span>
                  <span class="meta__nombre">{{ mt.nombre }}</span>
                  <span class="meta__estado" [class]="'meta__estado--' + mt.estado">
                    {{ etiquetaEstado(mt.estado) }}
                  </span>
                  <span class="meta__barra" aria-hidden="true">
                    <span class="meta__fill" [class]="claseBarra(mt.porcentaje)"
                          [style.width.%]="Math.min(mt.porcentaje, 100)"></span>
                  </span>
                  <span class="meta__pct">{{ formatNumero(mt.porcentaje) }} %</span>
                  <span class="meta__marco">
                    {{ formatNumero(mt.avance_total) }} de {{ formatNumero(mt.meta_total) }}
                    <em>de la vigencia</em>
                    @if (mt.sector) { · {{ mt.sector }} }
                    @if (mt.num_indicadores) { · {{ mt.num_indicadores }} KPI }
                  </span>
                </button>
              </li>
            }
          </ul>
        } @else {
          <p class="tabs__vacio">Cargando las metas del plan…</p>
        }
      </div>
      }

      <!-- ════════ PROYECTOS · Explorador 360°: lista plana con filtros a la
           izquierda y expediente a la derecha, más las 5 tarjetas de
           perspectiva como filtro adicional. ═══ -->
      @if (vista() === 'proyectos') {
      <div id="vpanel-proyectos" role="tabpanel" aria-labelledby="vtab-proyectos" tabindex="0">
        <app-perspectivas-explorador [objetivos]="objetivos()" [soloPerspectivas]="true"
                                      (perspectivaElegida)="onPerspectivaElegida($event)" />
      <div class="explorador" id="explorador-360">

        <!-- ── MAESTRO ─────────────────────────────────────────────── -->
        <aside class="maestro" aria-labelledby="maestro-tit">
          <div class="maestro__cabeza">
            <div class="maestro__titulo">
              <h2 id="maestro-tit"><span class="rotulo">Explorador 360°</span>Proyectos</h2>
              <span class="maestro__conteo"
                    [attr.aria-label]="proyectosVisibles().length + ' de '
                                       + todosLosProyectos().length + ' proyectos'">
                {{ proyectosVisibles().length }}<i>/{{ todosLosProyectos().length }}</i>
              </span>
            </div>

            <!-- FILTROS EN CASCADA — al cambiar de área el subgrupo se limpia
                 solo y el selector de subgrupo sólo ofrece los del área
                 elegida. Filtran PROYECTOS, la unidad que manda acá. -->
            <div class="filtros">
              <label class="filtros__campo filtros__campo--busca">
                <span class="ui-sr-only">Buscar proyecto</span>
                <i class="fa fa-magnifying-glass" aria-hidden="true"></i>
                <input type="search" name="q_proyecto" autocomplete="off"
                       placeholder="Buscar proyecto…"
                       [value]="busqueda()" (input)="cambiarBusqueda($event)">
              </label>

              <div class="filtros__dupla">
                <label class="filtros__campo">
                  <span class="rotulo">Área ejecutora</span>
                  <select [value]="areaSel()" (change)="cambiarArea($event)">
                    <option value="" [selected]="!areaSel()">Todas las áreas ejecutoras</option>
                    @for (a of areas(); track a) {
                      <option [value]="a" [selected]="a === areaSel()">{{ a }}</option>
                    }
                  </select>
                </label>

                <label class="filtros__campo">
                  <span class="rotulo">Subgrupo</span>
                  <select [value]="subgrupoSel() ?? ''" (change)="cambiarSubgrupo($event)">
                    <option value="" [selected]="subgrupoSel() == null">Todos los subgrupos</option>
                    @for (s of subgruposDelArea(); track s.id) {
                      <option [value]="s.id" [selected]="s.id === subgrupoSel()">{{ s.nombre }}</option>
                    }
                  </select>
                </label>
              </div>

              @if (hayFiltro()) {
                <button type="button" class="filtros__limpiar" (click)="limpiarFiltros()">
                  <i class="fa fa-xmark" aria-hidden="true"></i> Limpiar filtros
                </button>
              }
            </div>

            @if (perspectivaSel(); as persp) {
              <p class="maestro__ambito">
                <i class="fa fa-bullseye" aria-hidden="true"></i>
                Solo <b>{{ persp }}</b>
                <button type="button" class="maestro__ambito-quitar" (click)="onPerspectivaElegida('')">
                  quitar
                </button>
              </p>
            }
          </div>

          <!-- Lista de PROYECTOS. Scroll propio: los filtros de arriba no se
               van de la pantalla al bajar. -->
          @if (proyectosVisibles().length) {
            <ul class="maestro__lista" (keydown)="navegarLista($event)">
              @for (p of proyectosVisibles(); track p.id) {
                <li>
                  <button type="button" class="proy"
                          [attr.aria-current]="p.id === proyectoSel() ? 'true' : null"
                          (click)="seleccionar(p.id)">
                    <span class="proy__fila1">
                      <span class="proy__codigo">{{ p.codigo || '—' }}</span>
                      <span class="sem" [class]="'sem--' + (p.semaforo ?? 'sin')">
                        <span class="sem__punto" aria-hidden="true"></span>{{ textoSemaforo(p.semaforo) }}
                      </span>
                      @if (p.id === proyectoSel()) {
                        <i class="fa fa-chevron-right proy__marca" aria-hidden="true"></i>
                      }
                    </span>

                    <span class="proy__nombre">{{ p.nombre || 'Sin nombre' }}</span>

                    <span class="proy__meta">
                      @if (p.area) { <span class="tag">{{ p.area }}</span> }
                      @else { <span class="tag tag--vacio">Sin área ejecutora</span> }
                      @if (p.subgrupo) { <span class="tag tag--suave">{{ p.subgrupo }}</span> }
                      @if (p.dependencia) { <span class="proy__dep">{{ p.dependencia }}</span> }
                    </span>

                    <span class="proy__pie">
                      <span class="proy__avance">
                        @if (p.avance_pct != null) {
                          <span class="mini-barra" aria-hidden="true">
                            <span class="mini-barra__fill" [class]="claseBarra(p.avance_pct)"
                                  [style.width.%]="Math.min(100, p.avance_pct)"></span>
                          </span>
                          <b>{{ p.avance_pct }} %</b>
                        } @else {
                          <span class="sin-dato">sin avance cargado</span>
                        }
                      </span>
                      <span class="proy__conteos">
                        <span [attr.title]="'Metas del proyecto'">
                          <b>{{ p.n_metas ?? '—' }}</b> metas
                        </span>
                        <span [attr.title]="'Contratos atribuidos al proyecto'">
                          <b>{{ p.n_contratos ?? '—' }}</b> contratos
                        </span>
                      </span>
                    </span>
                  </button>
                </li>
              }
            </ul>
          } @else {
            <p class="maestro__vacio">
              @if (todosLosProyectos().length) {
                Ningún proyecto coincide con el filtro.
                Hay {{ todosLosProyectos().length }} en total.
              } @else {
                Cargando proyectos…
              }
            </p>
          }
        </aside>

        <!-- ── DETALLE ─────────────────────────────────────────────────
             El expediente es de OTRO componente: acá sólo se le pasa el id. -->
        <section class="detalle" aria-label="Expediente del proyecto">
          @if (proyectoSel() != null) {
            <app-expediente-proyecto [proyectoId]="proyectoSel()" />
          } @else {
            <p class="detalle__vacio" role="status">
              <i class="fa fa-folder-open" aria-hidden="true"></i>
              Elegí un proyecto de la izquierda para abrir su expediente.
            </p>
          }
        </section>
      </div>
      </div>
      }

      <!-- ════════ ANALÍTICA · beneficiarios/género + eventos, ═════════
           acordeones sin cambios internos, solo reubicados. -->
      @if (vista() === 'analitica') {
      <div id="vpanel-analitica-gente" role="tabpanel" aria-labelledby="vtab-analitica" tabindex="0">

      <!-- ── Personas beneficiadas ───────────────────────────────────── -->
      <section class="acc acc--abierto acc--fijo">
        <h2 class="acc__h">
          <div class="acc__cabeza acc__cabeza--fija" id="acc-gente-bt">
            <span class="acc__icono acc__icono--gente" aria-hidden="true"><i class="fa fa-users"></i></span>
            <span class="acc__titulo">Personas beneficiadas</span>
            <span class="acc__resumen">
              @if (g) {
                <b>{{ formatNumero(g.beneficiarios) }}</b> beneficiarios
                · <b>{{ formatNumero(g.participantes) }}</b> participantes
                · <b>{{ formatNumero(g.organizaciones) }}</b> organizaciones
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </div>
        </h2>
        <div class="acc__cuerpo" id="acc-gente" role="region" aria-labelledby="acc-gente-bt">
          <div class="acc__inner">
            <div class="band band--llana" [class.skeleton]="!g">
            <div class="band__grid">
              <article class="big-stat big-stat--people">
                <div class="big-stat__value">{{ g ? formatNumero(g.beneficiarios) : '…' }}</div>
                <div class="big-stat__label">Beneficiarios</div>
              </article>
              <article class="big-stat">
                <div class="big-stat__value">{{ g ? formatNumero(g.pct_mujeres) + ' %' : '…' }}</div>
                <div class="big-stat__label">Mujeres</div>
              </article>
              <article class="big-stat">
                <div class="big-stat__value">{{ g ? formatNumero(g.participantes) : '…' }}</div>
                <div class="big-stat__label">Participantes · {{ g?.eventos_con_participacion }} eventos</div>
              </article>
              <article class="band__chart">
                <canvas #chartGenero></canvas>
              </article>
            </div>
            @if (g && g.caracterizaciones === 0) {
              <p class="band__note band__note--info">
                <i class="fa fa-circle-info" aria-hidden="true"></i>
                Edad, etnia y enfoque diferencial fino se activan cuando se diligencie la caracterización.
              </p>
            }
            </div>
            <!-- Contratación por categoría — comparte esta misma cabecera:
                 las dos se redibujan con la misma llamada (dibujarCockpitCharts). -->
            <h3 class="sub-bloque__titulo rotulo">Contratación por categoría</h3>
            <div class="chart-card">
              <canvas #chartCategoria></canvas>
            </div>
          </div>
        </div>
      </section>
      </div>
      }

      <!-- ── Seguimiento del Plan ────────────────────────────────────── -->
      @if (vista() === 'metas') {
      <div id="vpanel-metas-plan" role="tabpanel" aria-labelledby="vtab-metas" tabindex="0">
      <section class="acc acc--abierto acc--fijo">
        <h2 class="acc__h">
          <div class="acc__cabeza acc__cabeza--fija" id="acc-plan-bt">
            <span class="acc__icono acc__icono--plan" aria-hidden="true"><i class="fa fa-list-check"></i></span>
            <span class="acc__titulo">Seguimiento del Plan</span>
            <span class="acc__resumen">
              @if (r) {
                <b>{{ r.metas_pdd }}</b> metas
                · <b>{{ r.indicadores }}</b> KPIs
                · <b>{{ r.avances }}</b> avances
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </div>
        </h2>
        <div class="acc__cuerpo" id="acc-plan" role="region" aria-labelledby="acc-plan-bt">
          <div class="acc__inner">
            <div class="kpi-grid" [class.skeleton]="!r">
              <a class="kpi-card kpi-card--accent kpi-card--link" routerLink="/presupuesto/proyectos"
                 aria-label="Ver listado de proyectos del plan">
                <span class="kpi-card__icon" aria-hidden="true"><i class="fa fa-folder-open"></i></span>
                <span class="kpi-card__body">
                  <span class="kpi-card__value">{{ r?.proyectos ?? '…' }}</span>
                  <span class="kpi-card__label">Proyectos del Plan</span>
                </span>
              </a>
              <a class="kpi-card kpi-card--accent kpi-card--link" routerLink="/presupuesto/metas"
                 aria-label="Ver listado de metas">
                <span class="kpi-card__icon" aria-hidden="true"><i class="fa fa-flag-checkered"></i></span>
                <span class="kpi-card__body">
                  <span class="kpi-card__value">{{ r?.metas_pdd ?? '…' }}</span>
                  <span class="kpi-card__label">Metas PDD</span>
                </span>
              </a>
              <a class="kpi-card kpi-card--info kpi-card--link" routerLink="/presupuesto/indicadores"
                 aria-label="Ver listado de indicadores (KPIs)">
                <span class="kpi-card__icon" aria-hidden="true"><i class="fa fa-gauge-high"></i></span>
                <span class="kpi-card__body">
                  <span class="kpi-card__value">{{ r?.indicadores ?? '…' }}</span>
                  <span class="kpi-card__label">Indicadores (KPIs)</span>
                </span>
              </a>
              <article class="kpi-card kpi-card--static"
                       title="Solo contador (eventos del mes en curso)">
                <span class="kpi-card__icon" aria-hidden="true"><i class="fa fa-calendar-alt"></i></span>
                <span class="kpi-card__body">
                  <span class="kpi-card__value">{{ r?.eventos_mes ?? '…' }}</span>
                  <span class="kpi-card__label">Eventos del mes</span>
                </span>
              </article>
              <a class="kpi-card kpi-card--success kpi-card--link" routerLink="/presupuesto/avances"
                 aria-label="Ver listado de avances a KPIs">
                <span class="kpi-card__icon" aria-hidden="true"><i class="fa fa-arrow-trend-up"></i></span>
                <span class="kpi-card__body">
                  <span class="kpi-card__value">{{ r?.avances ?? '…' }}</span>
                  <span class="kpi-card__label">Avances a KPIs</span>
                </span>
              </a>
              <!-- El ámbar SOLO si hay alguno. La hoja ya decía que «un cero
                   pintado de rojo se lee como un problema que no existe», pero
                   la clase estaba fija: el cero salía pintado igual. Sin el
                   modificador el chip cae al neutro base de .kpi-card__icon,
                   que es justo lo que se quería. (Sin acentos graves acá: la
                   plantilla vive dentro de un template literal y un acento
                   grave la cierra en seco.) -->
              <article class="kpi-card kpi-card--static"
                       [class.kpi-card--riesgo]="(r?.en_riesgo ?? 0) > 0"
                       title="Solo contador (KPIs en riesgo de incumplimiento)">
                <span class="kpi-card__icon" aria-hidden="true"><i class="fa fa-triangle-exclamation"></i></span>
                <span class="kpi-card__body">
                  <span class="kpi-card__value">{{ r?.en_riesgo ?? '…' }}</span>
                  <span class="kpi-card__label">KPIs en riesgo</span>
                </span>
              </article>
            </div>
            <!-- Objetivos NO vuelve como bloque ni como tab: la pantalla ya
                 existe y funciona. Un clic, cero espacio en el tablero. -->
            <p class="acc__enlaces">
              <a class="enlace-fino" routerLink="/presupuesto/objetivos">
                <i class="fa fa-bullseye" aria-hidden="true"></i>
                Objetivos por proyecto
                <i class="fa fa-arrow-right-long" aria-hidden="true"></i>
              </a>
            </p>
          </div>
        </div>
      </section>
      </div>
      }

      <!-- ── Eventos y analítica ─────────────────────────────────────── -->
      @if (vista() === 'analitica') {
      <div id="vpanel-analitica-eventos" role="tabpanel" aria-labelledby="vtab-analitica" tabindex="0">
      <section class="acc acc--abierto acc--fijo">
        <h2 class="acc__h">
          <div class="acc__cabeza acc__cabeza--fija" id="acc-eventos-bt">
            <span class="acc__icono acc__icono--eventos" aria-hidden="true"><i class="fa fa-chart-line"></i></span>
            <span class="acc__titulo">Eventos y analítica</span>
            <span class="acc__resumen">
              @if (r) {
                <b>{{ r.eventos_mes }}</b> {{ r.eventos_mes === 1 ? 'evento' : 'eventos' }} este mes
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </div>
        </h2>
        <div class="acc__cuerpo" id="acc-eventos" role="region" aria-labelledby="acc-eventos-bt">
          <div class="acc__inner">
            <div class="charts-row">
              <article class="chart-card">
                <header><h3><i class="fa fa-chart-line" aria-hidden="true"></i> Eventos por mes</h3></header>
                <canvas #chartMes></canvas>
              </article>
              <article class="chart-card">
                <header><h3><i class="fa fa-chart-pie" aria-hidden="true"></i> Eventos por tipo</h3></header>
                <canvas #chartTipo></canvas>
              </article>
              <!-- Si no hay sectores la tarjeta SE ENCOGE: reservar 220 px de alto
                   para un vacío es exactamente lo que hace que el tablero se lea
                   como un formulario a medio llenar. -->
              <article class="chart-card" [class.chart-card--vacio]="sectores() && !sectores()!.length">
                <header><h3><i class="fa fa-ranking-star" aria-hidden="true"></i> Top sectores</h3></header>
                @if (sectores() && !sectores()!.length) {
                  <p class="chart-card__vacio">Sin información de sectores disponible.</p>
                } @else {
                  <canvas #chartSect></canvas>
                }
              </article>
            </div>
          </div>
        </div>
      </section>
      </div>
      }

      <!-- ── Dinero y pendientes por área (el muro, en compacto) ─────── -->
      @if (vista() === 'areas') {
      <div id="vpanel-areas" role="tabpanel" aria-labelledby="vtab-areas" tabindex="0">
      <section class="acc" [class.acc--abierto]="abierto('muro')">
        <h2 class="acc__h">
          <button type="button" class="acc__cabeza" id="acc-muro-bt"
                  [attr.aria-expanded]="abierto('muro')" aria-controls="acc-muro"
                  (click)="alternar('muro')">
            <i class="fa fa-chevron-right acc__flecha" aria-hidden="true"></i>
            <span class="acc__icono acc__icono--muro" aria-hidden="true"><i class="fa fa-layer-group"></i></span>
            <span class="acc__titulo">Dinero y pendientes por área</span>
            <span class="acc__resumen">
              @if (muro(); as m) {
                <b>{{ m.tarjetas.length }}</b> subgrupos, con sus pendientes y la cobertura del PDL
              } @else if (muroError()) {
                <span class="sin-dato">no disponible</span>
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </button>
        </h2>
        <div class="acc__cuerpo" id="acc-muro" role="region" aria-labelledby="acc-muro-bt">
          <div class="acc__inner">
            <app-muro-subgrupos [datos]="muro()" [error]="muroError()" [compacto]="true" />
          </div>
        </div>
      </section>
      </div>
      }
    </div>
  `,
  styleUrl: './presupuesto-dashboard.component.scss',
})
export class PresupuestoDashboardComponent implements OnInit, AfterViewInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  private auth = inject(AuthService);
  private router = inject(Router);

  @ViewChild('chartMes') private chartMesRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTipo') private chartTipoRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSect') private chartSectRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartGenero') private chartGeneroRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartCategoria') private chartCategoriaRef?: ElementRef<HTMLCanvasElement>;

  Math = Math;
  formatNumero = formatNumero;
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  resumen = signal<ResumenEjecutivo | null>(null);
  eventos = signal<EventosMesTipo | null>(null);
  sectores = signal<TopSectores | null>(null);
  metas = signal<MetasProgreso | null>(null);
  // Cockpit ejecutivo
  plata = signal<EjecucionFinanciera | null>(null);
  gente = signal<BeneficiariosPerfil | null>(null);
  vigencia = signal<number | null>(null);

  // ══ PRESENTACIÓN: vista de nivel superior y acordeones ═════════════
  //
  // Sólo gobiernan qué se ve y qué está plegado. Ni una de estas piezas
  // toca datos, endpoints, filtros ni selección: si mañana se cambia el
  // orden, no hay ninguna cifra que recalcular.

  private readonly VISTAS: Vista[] = ['resumen', 'proyectos', 'metas', 'areas', 'analitica'];

  /** Sección de nivel superior activa. Arranca en el resumen ejecutivo. */
  vista = signal<Vista>('resumen');

  setVista(v: Vista): void {
    this.vista.set(v);
    // Analítica ya no vive detrás de acordeones (ver comentario en `abiertos`):
    // el redibujado que antes disparaba abrir el acordeón ahora lo dispara
    // entrar a la pestaña — el canvas recién mide algo distinto de 0 cuando
    // Angular monta esta sección, así que hay que esperar ese tick.
    if (v === 'analitica') {
      setTimeout(() => { this.dibujarCockpitCharts(); this.dibujarCharts(); }, 60);
    }
  }

  /** Flechas / Inicio / Fin sobre el `role="tablist"` (mismo patrón WAI-ARIA
   *  que ya usaban las sub-pestañas PDL/Metas, ahora a nivel de toda la página). */
  navegarVista(ev: KeyboardEvent): void {
    const k = ev.key;
    if (k !== 'ArrowRight' && k !== 'ArrowLeft' && k !== 'Home' && k !== 'End') return;
    const i = this.VISTAS.indexOf(this.vista());
    let j = i;
    if (k === 'ArrowRight') j = (i + 1) % this.VISTAS.length;
    if (k === 'ArrowLeft') j = (i - 1 + this.VISTAS.length) % this.VISTAS.length;
    if (k === 'Home') j = 0;
    if (k === 'End') j = this.VISTAS.length - 1;
    ev.preventDefault();
    this.vista.set(this.VISTAS[j]);
    const destino = ev.currentTarget as HTMLElement;
    setTimeout(() => destino.querySelector<HTMLElement>('[aria-selected="true"]')?.focus(), 0);
  }

  /** Fecha de corte para el encabezado — el mismo dato que ya usa el ledger. */
  corteTexto = computed<string | null>(() => {
    const c = this.muro()?.cabecera?.corte;
    return c ? this.fecha(c) : null;
  });

  /**
   * Los 4 KPI ejecutivos. Programado/Comprometido/Girado salen del MISMO
   * ledger —misma fuente, mutuamente consistentes—, nunca mezclados con
   * `plata()`, que es una lente distinta con su propio universo. Avance
   * físico sí sale de `plata()` porque es la única fuente que lo calcula.
   */
  kpisEjecutivos = computed<StatItem[]>(() => {
    const prog = this.ledgerProgramado();
    const comp = this.ledgerComprometido();
    const gir = this.ledgerGirado();
    const p = this.plata();
    const ap = this.ledgerApropiacion();
    return [
      // Encabeza la APROPIACIÓN, no el proyectado: es el primer eslabón real
      // de la cadena (Apropiación → Comprometido → Girado) y es contra ella
      // que un «% de ejecución» significa algo. Si todavía no hay ninguna
      // matriz cargada, el tile cae al proyectado en vez de quedar vacío.
      ap
        ? {
            value: this.enMillones(ap.valor),
            label: 'Apropiación',
            sublabel: this.rangoApropiacion(),
          }
        : {
            value: prog.valor != null ? this.enMillones(prog.valor) : 'Sin dato',
            label: 'Proyectado', sublabel: this.coberturaDe('programado') ?? 'PDL oficial',
          },
      {
        value: comp.valor != null ? this.enMillones(comp.valor) : 'Sin dato',
        label: 'Comprometido', sublabel: this.coberturaDe('comprometido') ?? undefined,
      },
      {
        value: gir.valor != null ? this.enMillones(gir.valor) : 'Sin dato',
        label: 'Girado', sublabel: this.coberturaDe('girado') ?? undefined,
      },
      {
        value: p ? `${this.formatNumero(p.pct_ejecucion)} %` : 'Sin dato',
        label: 'Avance físico', sublabel: 'ponderado',
        variant: p ? this.varianteAvance(p.pct_ejecucion) : undefined,
      },
    ];
  });

  private varianteAvance(pct: number): 'ok' | 'warn' | undefined {
    if (pct >= 80) return 'ok';
    if (pct < 50) return 'warn';
    return undefined;
  }

  /** Ancho relativo (0-100) de una barra frente al mayor de los 3 valores del ledger. */
  anchoRelativo(valor: number | null): number {
    if (valor == null) return 0;
    const max = Math.max(
      this.ledgerApropiacion()?.valor ?? 0,
      this.ledgerProgramado().valor ?? 0,
      this.ledgerComprometido().valor ?? 0,
      this.ledgerGirado().valor ?? 0,
      1,
    );
    return Math.max(0, Math.min(100, (valor / max) * 100));
  }

  /**
   * Bandeja "requiere atención". Cada item sale de un signal que YA existe:
   * nada se calcula de nuevo acá, solo se agrupa lo que hoy vivía disperso
   * en el hero, la banda de dinero y la tarjeta de KPIs en riesgo.
   */
  atencionItems = computed<AtencionItem[]>(() => {
    const items: AtencionItem[] = [];

    const criticos = this.todosLosProyectos().filter((p) => p.semaforo === 'critico').length;
    if (criticos > 0) {
      items.push({
        clave: 'criticos', cantidad: criticos, severidad: 'critico', accionable: true,
        etiqueta: criticos === 1 ? 'proyecto crítico' : 'proyectos críticos',
      });
    }

    const sinArea = this.todosLosProyectos().filter((p) => !p.area).length;
    if (sinArea > 0) {
      items.push({
        clave: 'sin-area', cantidad: sinArea, severidad: 'alto', accionable: true,
        etiqueta: 'proyectos sin área ejecutora',
      });
    }

    const p = this.plata();
    if (p && p.cdp_con_valor < p.cdp_n) {
      items.push({
        clave: 'cdp-sin-valor', cantidad: p.cdp_n - p.cdp_con_valor, severidad: 'medio', accionable: true,
        etiqueta: 'CDP sin valor cargado',
      });
    }

    const r = this.resumen();
    if (r && r.en_riesgo > 0) {
      items.push({
        clave: 'kpis-riesgo', cantidad: r.en_riesgo, severidad: 'alto', accionable: true,
        etiqueta: 'KPIs en riesgo',
      });
    }

    for (const c of this.chipsCompletitud()) {
      if (c.con < c.de) {
        items.push({
          clave: `chip-${c.clave}`, cantidad: c.de - c.con, severidad: 'neutral', accionable: false,
          etiqueta: `${c.etiqueta.toLowerCase()} sin completar`,
        });
      }
    }
    return items;
  });

  /** Click en un item de la bandeja: navega a donde ya existe una vista real. */
  onAtencionClick(clave: string): void {
    if (clave === 'criticos' || clave === 'sin-area') { this.setVista('proyectos'); return; }
    if (clave === 'kpis-riesgo') { this.router.navigate(['/presupuesto/avances']); return; }
    if (clave === 'cdp-sin-valor') {
      this.setVista('resumen');
      setTimeout(() => document.getElementById('estado-inversion')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
    }
  }

  /**
   * Acordeón. Sólo queda «muro» (Áreas): «Seguimiento del Plan» y los dos de
   * Analítica dejaron de serlo — vivían solos dentro de su propia pestaña, así
   * que el clic para abrirlos era una segunda capa de plegado sobre la
   * primera (la pestaña), y esa doble ocultación era ilegible: dos clics para
   * ver un dato que ya se vino a buscar.
   */
  private abiertos = signal<ReadonlySet<Clave>>(new Set<Clave>());

  abierto(k: Clave): boolean { return this.abiertos().has(k); }

  alternar(k: Clave): void {
    const s = new Set(this.abiertos());
    const abriendo = !s.has(k);
    if (abriendo) s.add(k); else s.delete(k);
    this.abiertos.set(s);
  }

  // ── Muro de subgrupos (Fase 1) ──
  muro = signal<MuroSubgrupos | null>(null);
  muroError = signal<string | null>(null);

  /**
   * Los tres chips de completitud del hero. Salen MEDIDOS del backend; no hay
   * ninguno escrito a mano. `titulo` explica la causa —no es lo mismo «no hay
   * dónde guardarlo» que «la tabla está vacía»— y `aria` lo deja disponible
   * para lector de pantalla, porque un tooltip no es accesible.
   */
  chipsCompletitud = computed(() => {
    const chips = this.muro()?.cabecera?.chips;
    if (!chips) return [];
    const lista = Array.isArray(chips)
      ? chips.map((c, i) => ({ ...c, clave: c.clave ?? String(i) }))
      : Object.entries(chips).map(([clave, c]) => ({ ...c, clave }));

    const ETIQUETAS: Record<string, string> = {
      etapa: 'Etapa',
      forma_pago: 'Forma de pago',
      vinculo_proyecto: 'Contrato ↔ proyecto',
    };
    const CAUSAS: Record<string, string> = {
      columna_inexistente: 'todavía no hay dónde guardarlo',
      tabla_vacia: 'la tabla existe pero está vacía',
      dato_faltante: 'hay dónde guardarlo, faltan valores',
    };

    return lista.map(c => {
      const etiqueta = c.etiqueta ?? ETIQUETAS[c.clave] ?? c.clave.replace(/_/g, ' ');
      const causa = CAUSAS[c.causa ?? ''] ?? c.causa ?? '';
      const partes = [`${etiqueta}: ${c.con} de ${c.de}`];
      if (causa) partes.push(causa);
      if (c.detalle) partes.push(c.detalle);
      if (c.accion) partes.push(`Acción: ${c.accion}`);
      const texto = partes.join(' — ');
      return { clave: c.clave, etiqueta, con: c.con, de: c.de, titulo: texto, aria: texto };
    });
  });

  // ══ EXPLORADOR MAESTRO / DETALLE ═══════════════════════════════════
  //
  // El resumen superior (cortes + ledger) reusa los MISMOS helpers del muro
  // en vez de escribir unos nuevos: un tercer formateador de plata en la
  // misma página es exactamente lo que no se quiere.
  fecha = fechaLegible;
  enMillones = enMillones;
  cifra = cifraLedger;
  /**
   * La procedencia de cada cifra del ledger, en una línea.
   *
   * No basta con `coberturaLedgerTexto` porque el payload guarda la cobertura
   * en DOS sitios distintos, y esa era la razón de que no se imprimiera nunca:
   *
   *   ledger.programado   → objeto, con su cobertura DENTRO y de otra forma
   *                         (proyectos_oficiales / ambito, no con/de)
   *   ledger.comprometido → número plano; su cobertura vive un nivel arriba,
   *   ledger.girado         en `ledger.cobertura.comprometido` / `.girado`
   *   ledger.saldo        → derivado, no tiene cobertura propia
   *
   * Decirlo importa: «$35.165 M» sin el «22 de 25 contratos» al lado se lee
   * como el total, y es el total DE LO QUE TIENE VALOR CARGADO.
   */
  coberturaTexto = coberturaLedgerTexto;

  coberturaDe(clave: 'programado' | 'comprometido' | 'girado' | 'saldo'): string | null {
    const led: any = this.muro()?.ledger;
    if (!led) return null;
    if (clave === 'programado') {
      const amb = led.programado?.cobertura?.ambito;
      return amb ? String(amb) : null;
    }
    if (clave === 'saldo') return null;          // derivado: no tiene cobertura propia
    const c = led.cobertura?.[clave];
    return (c && c.con != null && c.de != null) ? `${c.con} de ${c.de} contratos` : null;
  }

  pctTiempo = computed(() =>
    this.muro()?.cabecera?.ventana_pdl?.pct_tiempo_transcurrido ?? null);

  /**
   * Apropiación POAI: el PRIMER eslabón real de la ejecución. La cadena
   * correcta es Apropiación → Comprometido → Girado; «Proyectado PDL» es la
   * meta aspiracional del cuatrienio y por eso bajó a segunda barra en vez de
   * encabezar. Puede venir null si todavía no se ha cargado ninguna matriz,
   * y en ese caso la barra simplemente no se pinta.
   */
  ledgerApropiacion = computed(() => this.muro()?.ledger?.apropiacion ?? null);

  /**
   * El rango de vigencias sale del DATO, no escrito a mano. El POAI se apropia
   * año a año: hoy son 2025-2026 y 2027-2028 aún no existen. Rotular esto como
   * «2025-2028» haría ver la cifra como la mitad de lo que debería y se leería
   * como un retraso que no es tal.
   */
  rangoApropiacion = computed(() => {
    const ap = this.ledgerApropiacion();
    if (!ap) return '';
    return ap.vigencia_desde === ap.vigencia_hasta
      ? `${ap.vigencia_desde}`
      : `${ap.vigencia_desde}-${ap.vigencia_hasta}`;
  });

  ledgerProgramado = computed(() => this.cifra(this.muro()?.ledger?.programado));
  ledgerComprometido = computed(() => this.cifra(this.muro()?.ledger?.comprometido));
  ledgerGirado = computed(() => this.cifra(this.muro()?.ledger?.girado));
  ledgerSaldo = computed(() => this.cifra(this.muro()?.ledger?.saldo));

  // ── Objetivo Estratégico → Programa → Proyecto → Meta. El árbol
  // completo se pide una sola vez acá y se pasa por @Input a los dos
  // componentes que lo consumen —así el resumen y el explorador nunca
  // pueden mostrar números distintos del mismo dato. ──
  objetivos = signal<ObjetivoEstrategico[]>([]);

  /** El backend manda `subgrupo`/`dependencia` como `{id, nombre}` —el mismo
   *  shape que ya usaba `expediente_lista()` para el Explorador 360°
   *  viejo—, no como texto plano. Ahí existía un aplanado (`nombreRef`/
   *  `idRef`) que nunca se trajo cuando este árbol se armó: sin él, «área
   *  ejecutora» y «subgrupo» quedaban vacíos en cualquier pantalla que lea
   *  `objetivos()`, jerarquía o explorador plano por igual. */
  private nombreRef(v: any): string | null {
    if (v == null) return null;
    return typeof v === 'string' ? v : (v.nombre ?? null);
  }
  private idRef(v: any): number | null {
    return (v && typeof v === 'object' && v.id != null) ? Number(v.id) : null;
  }

  private async cargarObjetivos(): Promise<void> {
    const data = await this.safeGet('/presupuesto/api/objetivos-estrategicos/');
    const crudos: ObjetivoEstrategico[] = Array.isArray(data?.objetivos) ? data.objetivos : [];
    for (const obj of crudos) {
      for (const prog of obj.programas) {
        for (const p of prog.proyectos as any[]) {
          p.subgrupo_id = this.idRef(p.subgrupo);
          p.subgrupo = this.nombreRef(p.subgrupo);
          p.dependencia = this.nombreRef(p.dependencia);
        }
      }
    }
    this.objetivos.set(crudos);
    this.reconciliarSeleccion();
  }

  /** Id del proyecto a abrir de un salto en `<app-perspectivas-explorador>`
   *  —lo dispara `abrirProyectoDeMeta()` desde la pestaña Metas. */
  abrirProyectoId = signal<number | null>(null);

  /** Proyectos únicos de todo el árbol — un proyecto sale una sola vez
   *  aunque sus metas toquen más de un programa. Reemplaza a la lista
   *  plana que traía el Explorador 360° retirado: es la misma fuente
   *  (`/proyectos/expediente/`), solo que ahora llega reagrupada por
   *  `/objetivos-estrategicos/`. */
  todosLosProyectos = computed<ProyectoLista[]>(() => {
    const vistos = new Map<number, ProyectoLista>();
    for (const obj of this.objetivos()) {
      for (const prog of obj.programas) for (const p of prog.proyectos) vistos.set(p.id, p);
    }
    return [...vistos.values()];
  });

  /** Total de proyectos, para el badge de la pestaña «Proyectos». */
  nProyectosTotal = computed(() => this.todosLosProyectos().length);

  // ══ EXPLORADOR 360° — lista plana con filtros a la izquierda ═══════
  //
  // Convive con `<app-perspectivas-explorador>` (que acá solo aporta las 5
  // tarjetas, `soloPerspectivas=true`): usa el mismo árbol `objetivos()`
  // que ya se pidió una sola vez — no dispara una segunda petición de red.
  proyectoSel = signal<number | null>(null);
  busqueda = signal<string>('');
  areaSel = signal<string>('');
  subgrupoSel = signal<number | null>(null);
  /** Nombre completo del objetivo estratégico elegido en las 5 tarjetas de
   *  perspectiva («1 - Bogotá avanza…»), o '' si no hay ninguna elegida. */
  perspectivaSel = signal<string>('');

  onPerspectivaElegida(nombre: string): void {
    this.perspectivaSel.set(nombre);
    this.reconciliarSeleccion();
  }

  /** Ids de proyecto que caen bajo la perspectiva elegida, o `null` si no
   *  hay ninguna elegida (sin filtrar por este eje). */
  private proyectosDePerspectiva = computed<Set<number> | null>(() => {
    const nombre = this.perspectivaSel();
    if (!nombre) return null;
    const obj = this.objetivos().find(o => o.nombre === nombre);
    const ids = new Set<number>();
    if (obj) for (const prog of obj.programas) for (const p of prog.proyectos) ids.add(p.id);
    return ids;
  });

  private planoTexto(t: string | null | undefined): string {
    return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  areas = computed<string[]>(() => {
    const set = new Set<string>();
    for (const p of this.todosLosProyectos()) if (p.dependencia) set.add(p.dependencia);
    return [...set].sort((a, b) => a.localeCompare(b, 'es'));
  });

  subgruposDelArea = computed<Array<{ id: number; nombre: string }>>(() => {
    const area = this.areaSel();
    const vistos = new Map<number, string>();
    for (const p of this.todosLosProyectos()) {
      if (p.subgrupo_id == null || !p.subgrupo) continue;
      if (area && p.dependencia !== area) continue;
      vistos.set(p.subgrupo_id, p.subgrupo);
    }
    return [...vistos.entries()].map(([id, nombre]) => ({ id, nombre }))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  hayFiltro = computed(() =>
    !!this.areaSel() || this.subgrupoSel() != null || !!this.busqueda().trim() || !!this.perspectivaSel());

  private pasaFiltroProyecto(p: ProyectoLista): boolean {
    const ids = this.proyectosDePerspectiva();
    if (ids && !ids.has(p.id)) return false;
    if (this.areaSel() && p.dependencia !== this.areaSel()) return false;
    if (this.subgrupoSel() != null && p.subgrupo_id !== this.subgrupoSel()) return false;
    const q = this.planoTexto(this.busqueda().trim());
    if (q
        && !this.planoTexto(p.nombre).includes(q)
        && !this.planoTexto(p.codigo).includes(q)
        && !this.planoTexto(p.subgrupo).includes(q)
        && !this.planoTexto(p.area).includes(q)
        && !this.planoTexto(p.dependencia).includes(q)) return false;
    return true;
  }

  proyectosVisibles = computed(() => this.todosLosProyectos().filter(p => this.pasaFiltroProyecto(p)));

  private reconciliarSeleccion(): void {
    const visibles = this.proyectosVisibles();
    const sel = this.proyectoSel();
    if (sel != null && visibles.some(p => p.id === sel)) return;
    this.proyectoSel.set(visibles.length ? visibles[0].id : null);
  }

  cambiarArea(ev: Event): void {
    this.areaSel.set((ev.target as HTMLSelectElement).value || '');
    this.subgrupoSel.set(null);
    this.reconciliarSeleccion();
  }
  cambiarSubgrupo(ev: Event): void {
    const v = (ev.target as HTMLSelectElement).value;
    this.subgrupoSel.set(v ? Number(v) : null);
    this.reconciliarSeleccion();
  }
  cambiarBusqueda(ev: Event): void {
    this.busqueda.set((ev.target as HTMLInputElement).value || '');
    this.reconciliarSeleccion();
  }
  limpiarFiltros(): void {
    this.areaSel.set('');
    this.subgrupoSel.set(null);
    this.busqueda.set('');
    this.perspectivaSel.set('');
    this.reconciliarSeleccion();
  }

  seleccionar(id: number): void { this.proyectoSel.set(id); }

  /** Flechas / Inicio / Fin mueven el foco por la lista sin usar el mouse. */
  navegarLista(ev: KeyboardEvent): void {
    const k = ev.key;
    if (k !== 'ArrowDown' && k !== 'ArrowUp' && k !== 'Home' && k !== 'End') return;
    const cont = ev.currentTarget as HTMLElement;
    const botones = Array.from(cont.querySelectorAll<HTMLButtonElement>('button.proy'));
    if (!botones.length) return;
    const i = botones.indexOf(document.activeElement as HTMLButtonElement);
    let j = i;
    if (k === 'ArrowDown') j = i < 0 ? 0 : Math.min(i + 1, botones.length - 1);
    if (k === 'ArrowUp') j = i <= 0 ? 0 : i - 1;
    if (k === 'Home') j = 0;
    if (k === 'End') j = botones.length - 1;
    ev.preventDefault();
    botones[j]?.focus();
  }

  /** El color NUNCA va solo: el semáforo lleva punto + palabra (WCAG 1.4.1). */
  textoSemaforo(s: EstadoSemaforo | null): string {
    if (!s) return 'Sin calificar';
    return SEMAFORO_TEXTO[s] ?? s;
  }

  // ══ METAS DEL PLAN → EXPLORADOR ════════════════════════════════════
  //
  // El panorama de metas es un ÍNDICE: pulsando una meta se abre su proyecto
  // en el explorador de abajo, sin cambiar de ruta y sin desplegar la meta ahí
  // mismo (el detalle de la meta —sus indicadores— vive dentro del expediente
  // y en ningún otro sitio).
  //
  // El destino NO se inventa: sale de `/presupuesto/api/metas-proyecto/`, que
  // ya existía y publica la pareja (meta_codigo → proyecto_id) tal como está en
  // la base. Medido hoy: las 24 metas del panorama encuentran proyecto y los 12
  // destinos distintos están en la lista del explorador. Si una meta no
  // apareciera en ese mapa, su fila queda inerte —no se le fabrica un destino
  // plausible— y el botón sale deshabilitado con el motivo en el title.
  private mapaMetaProyectoRaw = signal<Map<string, number>>(new Map());
  mapaMetaProyecto = computed(() => this.mapaMetaProyectoRaw());

  /**
   * El proyecto de una meta, o `undefined` si la base no lo relaciona.
   *
   * La clave se compara como TEXTO en las dos puntas: `metas-progreso` manda el
   * código como número (100032) y la interfaz local lo declaraba `string`. En
   * vez de apostar a cuál de las dos tiene razón, se normaliza y funciona con
   * ambas.
   */
  proyectoDeMeta(codigo: string | number): number | undefined {
    return this.mapaMetaProyecto().get(String(codigo));
  }

  private async cargarMapaMetaProyecto(): Promise<void> {
    const d = await this.safeGet('/presupuesto/api/metas-proyecto/?page_size=500');
    const filas = Array.isArray(d) ? d : (d?.results ?? []);
    const m = new Map<string, number>();
    for (const f of filas) {
      const cod = f?.meta_codigo == null ? '' : String(f.meta_codigo);
      const pid = Number(f?.proyecto_id);
      // Sólo la primera: una meta con dos proyectos no puede abrir dos paneles.
      // Medido hoy: 0 metas con más de un proyecto, así que no se pierde nada.
      if (cod && Number.isFinite(pid) && !m.has(cod)) m.set(cod, pid);
    }
    this.mapaMetaProyectoRaw.set(m);
  }

  /**
   * Abre de un salto el proyecto de una meta en la jerarquía nueva:
   * cambia a la pestaña Proyectos y le manda el id al explorador, que se
   * encarga de encontrar su perspectiva/programa y desplegarlos.
   */
  abrirProyectoDeMeta(codigoMeta: string | number): void {
    const pid = this.proyectoDeMeta(codigoMeta);
    if (pid == null) return;
    this.setVista('proyectos');
    this.limpiarFiltros();
    this.seleccionar(pid);
    this.abrirProyectoId.set(pid);
    // Se reinicia en el siguiente tick: un `@Input` que no CAMBIA de valor
    // no dispara `ngOnChanges` en el hijo, así que un segundo clic sobre la
    // MISMA meta no volvería a saltar sin este pulso.
    setTimeout(() => this.abrirProyectoId.set(null), 0);
    const destino = document.getElementById('vpanel-proyectos');
    if (!destino) return;
    const quieto = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    destino.scrollIntoView({ behavior: quieto ? 'auto' : 'smooth', block: 'start' });
  }


  private charts: Chart[] = [];
  private cockpitCharts: Chart[] = [];

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Dashboard de KPIs' },
    ]);
    this.cargar();
  }

  private intentos = 0;

  ngAfterViewInit(): void { /* charts se dibujan al recibir data */ }

  recargar(): void {
    this.errorMsg.set('');
    this.intentos = 0;
    this.cargar();
  }

  private async safeGet(url: string): Promise<any> {
    // HttpClient (no fetch) para que el jwtInterceptor añada el Bearer:
    // en full-Angular el endpoint es JWT-first y un fetch con solo cookies
    // de sesión daría 401.
    try {
      return await firstValueFrom(this.http.get(this.cfg.url(url)));
    } catch (e: any) {
      if (e?.status === 401 || e?.status === 403) {
        (this as any)._needLogin = true;
      }
      return null;
    }
  }

  private cargar(): void {
    const base = '/dashboard/api/presupuesto';
    (this as any)._needLogin = false;
    this.loading.set(false); // muestra el shell inmediatamente, NO el "Cargando…"

    // ── Cada endpoint dispara su propia actualización de signal ──
    // Resultado: las secciones aparecen progresivamente, no a la vez.

    // 1. KPIs cards (lo primero que se ve, lo más importante)
    this.safeGet(`${base}/resumen-ejecutivo/`).then(r => {
      if (r) this.resumen.set(r);
      else this.maybeRetry();
    });

    // 2. Eventos por mes + tipo (gráficos)
    this.safeGet(`${base}/eventos-mes-tipo/`).then(e => {
      if (e) {
        this.eventos.set(e);
        setTimeout(() => this.dibujarCharts(), 80);
      }
    });

    // 3. Top sectores.
    //
    // El endpoint responde `{ sectores: [...] }`, NO un array pelado, y acá se
    // guardaba el objeto entero. Consecuencia medida (2026-08-23): la tarjeta
    // pintaba SIEMPRE «sin datos de sectores» —porque `{}.length` es undefined
    // y `!undefined` es true— con 6 sectores reales del otro lado. Un vacío
    // falso es peor que un vacío: manda a llenar algo que ya está lleno.
    // Se desenvuelve acá, en el borde, para que el resto del componente vea
    // siempre un array (o null mientras carga).
    this.safeGet(`${base}/top-sectores/`).then(s => {
      const filas: TopSectores | null =
        Array.isArray(s) ? s : (Array.isArray(s?.sectores) ? s.sectores : null);
      if (filas) {
        this.sectores.set(filas);
        setTimeout(() => this.dibujarCharts(), 80);
      }
    });

    // 4. Metas del plan (panorama) + el mapa que le da destino a cada una.
    this.safeGet(`${base}/metas-progreso/`).then(m => {
      if (m) this.metas.set(m);
    });
    this.cargarMapaMetaProyecto();

    // ── Cockpit ejecutivo (additivo) ──
    this.cargarCockpit();

    // ── Muro de subgrupos (Fase 1) — petición independiente: si falla,
    //    el resto del dashboard sigue en pie. ──
    this.cargarMuro();

    // ── Objetivo Estratégico → Programa → Proyecto → Meta — el árbol que
    //    alimenta el explorador jerárquico y su resumen. ──
    this.cargarObjetivos();
  }

  /**
   * Trae el payload del muro.
   *
   * Una sola ruta, la real. Antes probaba tres candidatas en orden porque el
   * muro y su vista DRF se escribieron en paralelo — y las tres daban 404, así
   * que el muro salía siempre con el aviso de «no disponible» aunque el
   * endpoint funcionara. Si esta falla NO se pinta nada inventado: se muestra
   * el aviso, que es la conducta correcta.
   */
  private async cargarMuro(): Promise<void> {
    const d = await this.safeGet('/presupuesto/api/muro-subgrupos/');
    if (d && Array.isArray(d.tarjetas)) {
      this.muro.set(d as MuroSubgrupos);
      this.muroError.set(null);
      return;
    }
    this.muroError.set(
      'El muro de áreas no está disponible: el endpoint no respondió. '
      + 'No se muestran cifras estimadas.',
    );
  }

  /** Carga las dos lentes del cockpit (plata / gente). */
  private cargarCockpit(): void {
    const base = '/dashboard/api/presupuesto';
    const vq = this.vigencia() ? `?vigencia=${this.vigencia()}` : '';

    this.safeGet(`${base}/ejecucion-financiera/${vq}`).then(d => {
      if (d) { this.plata.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
    this.safeGet(`${base}/beneficiarios-perfil/`).then(d => {
      if (d) { this.gente.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
  }

  /** Solo 2025/2026 en el chip, aunque `plata()` traiga más años (contratos
   *  legacy con vigencias sueltas que no son del PDL vigente). */
  private static readonly VIGENCIAS_PDL = [2025, 2026];
  vigenciasVisibles(traidas: number[]): number[] {
    return PresupuestoDashboardComponent.VIGENCIAS_PDL.filter(v => traidas.includes(v));
  }

  /** Cambia la vigencia activa y recarga solo lo que depende de ella. */
  setVigencia(v: number | null): void {
    this.vigencia.set(v);
    const base = '/dashboard/api/presupuesto';
    const vq = v ? `?vigencia=${v}` : '';
    this.safeGet(`${base}/ejecucion-financiera/${vq}`).then(d => {
      if (d) { this.plata.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
  }

  /**
   * Formatea pesos a millones legibles: 11283436256 → "$11.283 M".
   *
   * Delega en `enMillones` —el mismo del muro y del resumen superior— para que
   * la página tenga UN formateador de plata y no tres. Conserva su '…' propio
   * porque acá el null significa «todavía cargando», no «no hay dato».
   */
  plataMM(n?: number | null): string {
    return n == null ? '…' : enMillones(n);
  }

  private maybeRetry(): void {
    if ((this as any)._needLogin && this.intentos < 1) {
      this.intentos++;
      this.auth.fetchMe().subscribe({
        next: () => setTimeout(() => this.cargar(), 150),
        error: () => this.errorMsg.set('Sesión expirada. Logout + login.'),
      });
    } else if ((this as any)._needLogin) {
      this.errorMsg.set('Sesión Django no activa. Cerrá sesión y entrá otra vez.');
    }
  }

  etiquetaEstado(e: string): string {
    return ({
      cumplida: 'Cumplida',
      en_progreso: 'En progreso',
      en_riesgo: 'En riesgo',
      sin_avance: 'Sin avance',
    } as any)[e] || e;
  }

  claseBarra(pct: number): string {
    if (pct >= 80) return 'green';
    if (pct >= 50) return 'yellow';
    if (pct > 0) return 'red';
    return 'gray';
  }

  private destruirCharts(): void {
    for (const c of this.charts) c.destroy();
    this.charts = [];
  }

  private dibujarCockpitCharts(): void {
    for (const c of this.cockpitCharts) c.destroy();
    this.cockpitCharts = [];

    const g = this.gente();
    const p = this.plata();
    const cg = this.chartGeneroRef?.nativeElement;
    const cc = this.chartCategoriaRef?.nativeElement;

    // Género (doughnut) — dato real: 62% mujeres
    if (g?.genero?.length && cg) {
      const colores: Record<string, string> = {
        'Femenino': '#EC4899', 'Masculino': '#0EA5E9', 'Prefiere no decirlo': '#94A3B8',
      };
      this.cockpitCharts.push(new Chart(cg, {
        type: 'doughnut',
        data: {
          labels: g.genero.map(x => x.nombre),
          datasets: [{
            data: g.genero.map(x => x.total),
            backgroundColor: g.genero.map(x => colores[x.nombre] || '#8B5CF6'),
            borderWidth: 2, borderColor: '#fff',
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10 } } },
          cutout: '62%',
        },
      }));
    }

    // Contratación por categoría (barras horizontales, en millones)
    if (p?.por_categoria?.length && cc) {
      const cats = p.por_categoria.filter(x => x.valor > 0);
      this.cockpitCharts.push(new Chart(cc, {
        type: 'bar',
        data: {
          labels: cats.map(x => x.categoria),
          datasets: [{
            label: 'Valor (millones)',
            data: cats.map(x => Math.round(x.valor / 1e6)),
            backgroundColor: ['#0D9488', '#0EA5E9', '#F59E0B', '#8B5CF6', '#EC4899', '#6B7280'],
            borderRadius: 6,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx: any) =>
                  '$' + Number(ctx.raw).toLocaleString('es-CO') + ' millones',
              },
            },
          },
          scales: {
            x: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
            y: { grid: { display: false } },
          },
        },
      }));
    }
  }

  private dibujarCharts(): void {
    this.destruirCharts();
    const cMes = this.chartMesRef?.nativeElement;
    const cTipo = this.chartTipoRef?.nativeElement;
    const cSect = this.chartSectRef?.nativeElement;
    if (!cMes && !cTipo && !cSect) return;

    const e = this.eventos();
    const s = this.sectores();

    const accent = '#0D9488';
    const primary = '#D6001C';
    const secondary = '#FFC72C';

    // Eventos por mes (línea)
    if (e?.por_mes?.length && cMes) {
      this.charts.push(new Chart(cMes, {
        type: 'line',
        data: {
          labels: e.por_mes.map(p => p.mes),
          datasets: [{
            label: 'Eventos',
            data: e.por_mes.map(p => p.total),
            borderColor: primary,
            backgroundColor: 'rgba(214,0,28,0.15)',
            fill: true, tension: 0.35, borderWidth: 3,
            pointBackgroundColor: primary, pointRadius: 4, pointHoverRadius: 7,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
          scales: {
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
            x: { grid: { display: false } },
          },
        },
      }));
    }

    // Eventos por tipo (doughnut)
    if (e?.por_tipo?.length && cTipo) {
      const palette = ['#D6001C', '#0D9488', '#0EA5E9', '#F59E0B',
                       '#8B5CF6', '#EC4899', '#22C55E', '#6B7280'];
      this.charts.push(new Chart(cTipo, {
        type: 'doughnut',
        data: {
          labels: e.por_tipo.map(t => tipoEventoNombre(t.tipo)),
          datasets: [{
            data: e.por_tipo.map(t => t.total),
            backgroundColor: e.por_tipo.map((_, i) => palette[i % palette.length]),
            borderWidth: 2, borderColor: '#fff',
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } },
          },
          cutout: '60%',
        },
      }));
    }

    // Top sectores (horizontal bar) — backend devuelve array directo
    if (Array.isArray(s) && s.length && cSect) {
      this.charts.push(new Chart(cSect, {
        type: 'bar',
        data: {
          labels: s.map(x => x.sector),
          datasets: [{
            label: '% Avance',
            data: s.map(x => x.porcentaje),
            backgroundColor: s.map(x =>
              x.porcentaje >= 80 ? '#22C55E'
                : x.porcentaje >= 50 ? '#F59E0B'
                : '#DC2626'),
            borderRadius: 6,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, max: 100,
                 grid: { color: 'rgba(0,0,0,0.05)' } },
            y: { grid: { display: false } },
          },
        },
      }));
    }
  }
}
