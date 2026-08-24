import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, Component, ElementRef,
  OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { firstValueFrom, forkJoin, of, timer } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatNumero, tipoEventoNombre } from '../../shared/format/format.util';
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

/**
 * Una fila del panel izquierdo. Es la unidad que manda en esta página.
 *
 * Todo lo que puede faltar es `| null` y se pinta declarado: `semaforo: null`
 * sale «sin calificar», NUNCA como un estado supuesto, y `avance_pct: null`
 * sale «sin avance cargado», NUNCA como 0 % (un 0 % dice «no avanzó» cuando
 * lo cierto es «nadie lo midió»).
 */
interface ProyectoLista {
  id: number;
  codigo: string | null;
  nombre: string | null;
  subgrupo: string | null;
  subgrupo_id: number | null;
  /** Área PLANIG. Medido: 9 de los 12 proyectos la tienen, 3 no. */
  area: string | null;
  dependencia: string | null;
  avance_pct: number | null;
  n_metas: number | null;
  n_contratos: number | null;
  semaforo: EstadoSemaforo | null;
  semaforo_motivo: string | null;
}

/** De dónde salió la lista: importa para saber qué campos NO vienen. */
type OrigenLista = 'expediente' | 'compuesto' | null;

/** Los cuatro acordeones del pie. Nacen cerrados, todos. */
type Clave = 'gente' | 'plan' | 'eventos' | 'muro';

@Component({
  standalone: true,
  selector: 'app-presupuesto-dashboard',
  imports: [CommonModule, RouterLink, MuroSubgruposComponent, ExpedienteProyectoComponent],
  template: `
    <div class="page">
      <header class="hero">
        <div>
          <h1>
            <i class="fa fa-chart-pie" aria-hidden="true"></i> Dashboard Presupuesto
          </h1>
          <p class="hero__subtitle">
            Visión 360° del Plan de Desarrollo: planeación, ejecución y seguimiento.
          </p>
        </div>
        <!-- Los dos badges de antes ('PDD activo', '12 entidades operativas')
             estaban escritos a mano y no salían de ningún dato. Los reemplazan
             los chips de completitud MEDIDOS que manda el muro. -->
        <div class="hero__badges hero__badges--chips">
          @if (muro()) {
            @for (c of chipsCompletitud(); track c.clave) {
              <span class="badge badge--chip"
                    [attr.title]="c.titulo"
                    [attr.aria-label]="c.aria">
                <span class="badge__rotulo">{{ c.etiqueta }}</span>
                <b>{{ c.con }}/{{ c.de }}</b>
              </span>
            }
          } @else if (muroError()) {
            <span class="badge badge--chip">Completitud no disponible</span>
          } @else {
            <span class="badge badge--chip">Midiendo completitud…</span>
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
           ORDEN DE LECTURA (Alex, 2026-08-23, segunda pasada):

             1 · Vigencia          franja de filtro, sin card
             2 · Dinero            SIEMPRE visible
             3 · Tabs              Plan de Desarrollo Local | Metas del Plan
             4 · EXPLORADOR 360    el protagonista, ABIERTO y sin acordeón que
                                   lo envuelva (ya trae los suyos por dentro)
             5 · Acordeones        gente · seguimiento · eventos · muro,
                                   los cuatro CERRADOS al entrar

           Un acordeón cerrado tiene que INFORMAR: cada cabecera lleva su
           mini-resumen con cifras del payload. Si una cifra no llegó, ese
           trozo NO se pinta — nunca un número inventado para rellenar.
           ═══════════════════════════════════════════════════════════════════ -->
      @let p = plata();
      @let g = gente();
      @let r = resumen();

      <!-- ════════ 1 · VIGENCIA ════════════════════════════════════════ -->
      @if (p && p.vigencias.length) {
        <div class="vigencia" role="group" aria-labelledby="vigencia-rot">
          <span class="vigencia__rotulo rotulo" id="vigencia-rot">Vigencia</span>
          <div class="vigencia__opciones">
            <button type="button" class="vchip" [class.vchip--on]="!vigencia()"
                    [attr.aria-pressed]="!vigencia()"
                    (click)="setVigencia(null)">Todas</button>
            @for (v of p.vigencias; track v) {
              <button type="button" class="vchip" [class.vchip--on]="vigencia() === v"
                      [attr.aria-pressed]="vigencia() === v"
                      (click)="setVigencia(v)">{{ v }}</button>
            }
          </div>
          <span class="vigencia__nota">Acota inversión y contratación.</span>
        </div>
      }

      <!-- ════════ 2 · DINERO — franja ejecutiva, siempre visible ═══════ -->
      <section class="band band--plata" [class.skeleton]="!p" aria-labelledby="band-plata-tit">
        <header class="band__header">
          <span class="band__icono" aria-hidden="true"><i class="fa fa-coins"></i></span>
          <h2 id="band-plata-tit">
            <span class="rotulo">Dinero</span>
            Inversión y contratación
          </h2>
          @if (p) {
            <span class="band__pill">{{ p.n_contratos }} contratos · {{ p.n_con_valor }} con valor</span>
          }
        </header>
        <div class="band__grid">
          <article class="big-stat big-stat--money">
            <div class="big-stat__value">{{ plataMM(p?.contratado_total) }}</div>
            <div class="big-stat__label">Contratado</div>
          </article>
          <article class="big-stat">
            <div class="big-stat__value">{{ p ? formatNumero(p.pct_ejecucion) + ' %' : '…' }}</div>
            <div class="big-stat__label">Ejecución física (ponderada)</div>
            <div class="barra">
              <div class="barra__fill" [class]="claseBarra(p?.pct_ejecucion || 0)"
                   [style.width.%]="Math.min(p?.pct_ejecucion || 0, 100)"></div>
            </div>
          </article>
          <article class="big-stat big-stat--soft"
                   [title]="'CDP con valor cargado: ' + (p?.cdp_con_valor || 0) + '/' + (p?.cdp_n || 0)">
            <div class="big-stat__value">{{ plataMM(p?.cdp_asignado) }}</div>
            <div class="big-stat__label">CDP registrado <i class="fa fa-circle-info" aria-hidden="true"></i></div>
          </article>
          <article class="band__chart">
            <canvas #chartCategoria></canvas>
          </article>
        </div>
        @if (p && p.cdp_con_valor < p.cdp_n) {
          <p class="band__note">
            <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
            {{ p.cdp_n - p.cdp_con_valor }} CDP sin valor cargado — el presupuesto asignado real será mayor.
          </p>
        }
      </section>

      <!-- ════════ 3 · TABS · Plan de Desarrollo Local / Metas ══════════
           Dos lecturas del MISMO plan, alternativas entre sí: antes eran dos
           bloques verticales que empujaban el explorador media pantalla
           abajo. El contenido de cada una es el que ya existía. -->
      <div class="tabs">
        <div class="tabs__lista" role="tablist"
             aria-label="Plan de desarrollo local" (keydown)="navegarTabs($event)">
          <button type="button" role="tab" class="tabs__tab" id="tab-pdl"
                  [class.tabs__tab--on]="tab() === 'pdl'"
                  [attr.aria-selected]="tab() === 'pdl'"
                  [attr.tabindex]="tab() === 'pdl' ? 0 : -1"
                  aria-controls="panel-pdl" (click)="setTab('pdl')">
            Plan de Desarrollo Local
          </button>
          <button type="button" role="tab" class="tabs__tab" id="tab-metas"
                  [class.tabs__tab--on]="tab() === 'metas'"
                  [attr.aria-selected]="tab() === 'metas'"
                  [attr.tabindex]="tab() === 'metas' ? 0 : -1"
                  aria-controls="panel-metas" (click)="setTab('metas')">
            Metas del Plan
            @if (metas(); as m) { <span class="tabs__conteo">{{ m.metas.length }}</span> }
          </button>
        </div>

        <div class="tabs__panel" role="tabpanel" id="panel-pdl" aria-labelledby="tab-pdl"
             [hidden]="tab() !== 'pdl'" tabindex="0">
          @if (tab() === 'pdl') {
          <section class="resumen" aria-labelledby="resumen-tit">
            <span class="resumen__marca" aria-hidden="true"></span>
            <div class="resumen__cuerpo">
              <h2 class="resumen__tit" id="resumen-tit">
                <span class="rotulo">Expediente de inversión local</span>
                Corte y ejecución presupuestal
              </h2>

              @if (muro(); as m) {
                <div class="resumen__cortes">
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

                <dl class="ledger">
                  <div class="ledger__item">
                    <dt class="rotulo">Programado</dt>
                    <dd>
                      {{ enMillones(ledgerProgramado().valor) }}
                      @if (coberturaDe('programado'); as c) { <small>{{ c }}</small> }
                    </dd>
                  </div>
                  <div class="ledger__item">
                    <dt class="rotulo">Comprometido</dt>
                    <dd>
                      {{ enMillones(ledgerComprometido().valor) }}
                      @if (coberturaDe('comprometido'); as c) { <small>{{ c }}</small> }
                    </dd>
                  </div>
                  <div class="ledger__item">
                    <dt class="rotulo">Girado</dt>
                    <dd>
                      {{ enMillones(ledgerGirado().valor) }}
                      @if (coberturaDe('girado'); as c) { <small>{{ c }}</small> }
                    </dd>
                  </div>
                  <div class="ledger__item ledger__item--saldo">
                    <dt class="rotulo">Saldo por girar</dt>
                    <dd>
                      {{ enMillones(ledgerSaldo().valor) }}
                      <small>comprometido − girado</small>
                    </dd>
                  </div>
                </dl>

                <!-- Estos dos avisos NO son decoración: sin ellos el ledger miente.
                     Van pegados a las cifras, no en un pliegue: una advertencia que
                     hay que desplegar para verla no advierte a nadie. -->
                <p class="resumen__aviso">
                  <i class="fa fa-circle-info" aria-hidden="true"></i>
                  <span>
                    Son <strong>dos cortes distintos</strong>: lo comprometido y lo girado
                    vienen de SECOP; lo programado, del PDL oficial de la SDP.
                    <strong>No se restan entre sí</strong> — el saldo es comprometido menos
                    girado, nunca programado menos comprometido: serían dos universos
                    (proyectos del PDL frente a proyectos cargados) y dos fechas de corte,
                    y esa resta daría un número plausible y falso.
                  </span>
                </p>
                <p class="resumen__aviso resumen__aviso--alcance">
                  <i class="fa fa-list-check" aria-hidden="true"></i>
                  <span>
                    Las cuatro cifras son del <strong>total de la localidad</strong> y no
                    cambian al filtrar: los filtros de abajo acotan la lista de proyectos,
                    no el ledger.
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
            </div>
          </section>
          }
        </div>

        <div class="tabs__panel" role="tabpanel" id="panel-metas" aria-labelledby="tab-metas"
             [hidden]="tab() !== 'metas'">
          @if (tab() === 'metas') {
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
                Al pulsar una meta se abre su proyecto en el explorador de abajo.
              }
            </p>
              <!-- Scroll PROPIO: las 24 metas no se despliegan sobre todo el
                   tablero, que era lo que sepultaba al explorador. -->
            <ul class="metas" role="list">
              @for (mt of m.metas; track mt.codigo) {
                <li class="metas__fila" [class]="'metas__fila--' + mt.estado">
                  <button type="button" class="meta"
                          [attr.aria-disabled]="proyectoDeMeta(mt.codigo) ? null : 'true'"
                          [attr.title]="proyectoDeMeta(mt.codigo)
                                        ? 'Abrir el proyecto de esta meta en el explorador'
                                        : 'Esta meta no tiene proyecto asociado en la base'"
                          [attr.aria-label]="proyectoDeMeta(mt.codigo)
                                        ? 'Abrir en el explorador el proyecto de la meta ' + mt.codigo
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
          }
        </div>
      </div>

      <!-- ════════ 4 · EXPLORADOR 360 · el protagonista ═════════════════
           NO va dentro de un acordeón: ya tiene los suyos por dentro y
           anidarlo dejaría el expediente a tres niveles de profundidad. -->
      <div class="explorador" id="explorador-360">

        <!-- ── MAESTRO ─────────────────────────────────────────────── -->
        <aside class="maestro" aria-labelledby="maestro-tit">
          <div class="maestro__cabeza">
            <div class="maestro__titulo">
              <h2 id="maestro-tit"><span class="rotulo">Explorador 360°</span>Proyectos</h2>
              <span class="maestro__conteo"
                    [attr.aria-label]="proyectosVisibles().length + ' de '
                                       + proyectos().length + ' proyectos'">
                {{ proyectosVisibles().length }}<i>/{{ proyectos().length }}</i>
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

            @if (!areaSel() && sinArea()) {
              <p class="maestro__nota">
                {{ sinArea() }} de {{ proyectos().length }} proyectos todavía no tienen
                área ejecutora asignada: sólo aparecen con el filtro en «Todas las
                áreas ejecutoras».
              </p>
            }
            @if (origenLista() === 'compuesto' && proyectos().length) {
              <p class="maestro__nota">
                Información parcial: el semáforo sale «sin calificar» y el número de
                contratos «—». El conteo disponible en este modo se queda corto, y
                publicarlo sería peor que dejarlo vacío. Código, nombre, área, subgrupo,
                dependencia y metas
                y avance sí son los medidos.
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
              @if (proyectos().length) {
                Ningún proyecto coincide con el filtro.
                Hay {{ proyectos().length }} en total.
              } @else if (proyectosError()) {
                {{ proyectosError() }}
              } @else {
                Cargando proyectos…
              }
            </p>
          }
        </aside>

        <!-- ── DETALLE ─────────────────────────────────────────────────
             El expediente es de OTRO componente: acá sólo se le pasa el id.
             Él resuelve su propia carga. -->
        <!-- SIN aria-live acá. El expediente son 772 líneas de plantilla con 86
             bloques condicionales, y todos se insertan DENTRO de esta sección:
             con la región viva puesta en el contenedor, el lector de pantalla
             recitaba el panel entero no sólo al elegir proyecto, sino cada vez
             que se abría una meta o un contrato. Encima el expediente ya trae
             sus propias regiones vivas pequeñas y correctas (role=status y
             role=alert), que quedaban anidadas dentro de ésta.
             El aria-label, además, lo promueve a landmark con nombre. -->
        <section class="detalle" aria-label="Expediente del proyecto">
          @if (proyectoSel() != null) {
            <app-expediente-proyecto [proyectoId]="proyectoSel()" />
          } @else {
            <!-- role=status acá y no en el contenedor: este aviso reaparece
                 durante el uso (el proyecto vuelve a null al cambiar filtros),
                 así que sí tiene que anunciarse — pero él solo. -->
            <p class="detalle__vacio" role="status">
              <i class="fa fa-folder-open" aria-hidden="true"></i>
              Elegí un proyecto de la izquierda para abrir su expediente.
            </p>
          }
        </section>
      </div>

      <!-- ════════ 5 · ACORDEONES — los cuatro CERRADOS al entrar ═══════ -->

      <!-- ── Personas beneficiadas ───────────────────────────────────── -->
      <section class="acc" [class.acc--abierto]="abierto('gente')">
        <h2 class="acc__h">
          <button type="button" class="acc__cabeza" id="acc-gente-bt"
                  [attr.aria-expanded]="abierto('gente')" aria-controls="acc-gente"
                  (click)="alternar('gente')">
            <i class="fa fa-chevron-right acc__flecha" aria-hidden="true"></i>
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
          </button>
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
          </div>
        </div>
      </section>

      <!-- ── Seguimiento del Plan ────────────────────────────────────── -->
      <section class="acc" [class.acc--abierto]="abierto('plan')">
        <h2 class="acc__h">
          <button type="button" class="acc__cabeza" id="acc-plan-bt"
                  [attr.aria-expanded]="abierto('plan')" aria-controls="acc-plan"
                  (click)="alternar('plan')">
            <i class="fa fa-chevron-right acc__flecha" aria-hidden="true"></i>
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
          </button>
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

      <!-- ── Eventos y analítica ─────────────────────────────────────── -->
      <section class="acc" [class.acc--abierto]="abierto('eventos')">
        <h2 class="acc__h">
          <button type="button" class="acc__cabeza" id="acc-eventos-bt"
                  [attr.aria-expanded]="abierto('eventos')" aria-controls="acc-eventos"
                  (click)="alternar('eventos')">
            <i class="fa fa-chevron-right acc__flecha" aria-hidden="true"></i>
            <span class="acc__icono acc__icono--eventos" aria-hidden="true"><i class="fa fa-chart-line"></i></span>
            <span class="acc__titulo">Eventos y analítica</span>
            <span class="acc__resumen">
              @if (r) {
                <b>{{ r.eventos_mes }}</b> {{ r.eventos_mes === 1 ? 'evento' : 'eventos' }} este mes
              } @else {
                <span class="sin-dato">midiendo…</span>
              }
            </span>
          </button>
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

      <!-- ── Dinero y pendientes por área (el muro, en compacto) ─────── -->
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
            <app-muro-subgrupos [datos]="muro()" [error]="muroError()" [compacto]="true"
                                [filtroArea]="areaSel()"
                                [filtroSubgrupoId]="subgrupoSel()"
                                [filtroBusqueda]="busqueda()" />
          </div>
        </div>
      </section>
    </div>
  `,
  styleUrl: './presupuesto-dashboard.component.scss',
})
export class PresupuestoDashboardComponent implements OnInit, AfterViewInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  private auth = inject(AuthService);

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

  // ══ PRESENTACIÓN: tabs y acordeones ════════════════════════════════
  //
  // Sólo gobiernan qué se ve y qué está plegado. Ni una de estas piezas
  // toca datos, endpoints, filtros ni selección: si mañana se cambia el
  // orden, no hay ninguna cifra que recalcular.

  /** Pestaña activa del bloque del plan. Arranca en el PDL. */
  tab = signal<'pdl' | 'metas'>('pdl');
  private readonly TABS: Array<'pdl' | 'metas'> = ['pdl', 'metas'];

  setTab(t: 'pdl' | 'metas'): void { this.tab.set(t); }

  /** Flechas / Inicio / Fin sobre el `role="tablist"` (patrón WAI-ARIA). */
  navegarTabs(ev: KeyboardEvent): void {
    const k = ev.key;
    if (k !== 'ArrowRight' && k !== 'ArrowLeft' && k !== 'Home' && k !== 'End') return;
    const i = this.TABS.indexOf(this.tab());
    let j = i;
    if (k === 'ArrowRight') j = (i + 1) % this.TABS.length;
    if (k === 'ArrowLeft') j = (i - 1 + this.TABS.length) % this.TABS.length;
    if (k === 'Home') j = 0;
    if (k === 'End') j = this.TABS.length - 1;
    ev.preventDefault();
    this.tab.set(this.TABS[j]);
    // El foco sigue a la pestaña: si no, el teclado cambia el panel y el
    // anillo de foco se queda en la pestaña anterior.
    const destino = ev.currentTarget as HTMLElement;
    setTimeout(() => destino.querySelector<HTMLElement>('[aria-selected="true"]')?.focus(), 0);
  }

  /**
   * Acordeones. Los CUATRO nacen cerrados: la pantalla tiene que abrir en el
   * dinero y el explorador, no en un acordeón desplegado que los empuje
   * fuera del primer viewport.
   */
  private abiertos = signal<ReadonlySet<Clave>>(new Set<Clave>());

  abierto(k: Clave): boolean { return this.abiertos().has(k); }

  alternar(k: Clave): void {
    const s = new Set(this.abiertos());
    const abriendo = !s.has(k);
    if (abriendo) s.add(k); else s.delete(k);
    this.abiertos.set(s);
    // Chart.js mide el canvas al dibujar y dentro de un acordeón cerrado
    // ese canvas mide 0: si no se redibuja al abrir, el gráfico sale en
    // blanco. Se espera a que termine la transición del pliegue.
    if (!abriendo) return;
    if (k === 'eventos') setTimeout(() => this.dibujarCharts(), 260);
    if (k === 'gente') setTimeout(() => this.dibujarCockpitCharts(), 260);
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

  ledgerProgramado = computed(() => this.cifra(this.muro()?.ledger?.programado));
  ledgerComprometido = computed(() => this.cifra(this.muro()?.ledger?.comprometido));
  ledgerGirado = computed(() => this.cifra(this.muro()?.ledger?.girado));
  ledgerSaldo = computed(() => this.cifra(this.muro()?.ledger?.saldo));

  // ── Lista de proyectos (panel izquierdo) ────────────────────────────
  private proyectosRaw = signal<ProyectoLista[]>([]);
  proyectosError = signal<string | null>(null);
  origenLista = signal<OrigenLista>(null);
  proyectoSel = signal<number | null>(null);

  /**
   * Subgrupo (por nombre normalizado) → id + área PLANIG + dependencia.
   *
   * Sale del payload del muro, que ya trae las 45 tarjetas con su área. NO es
   * un mapa escrito a mano: si el backend cambia la asignación de áreas, esto
   * cambia con él. Medido hoy: los 12 proyectos resuelven tarjeta por nombre y
   * 9 de ellos reciben área (3 la tienen en null en el propio muro).
   */
  private mapaSubgrupo = computed(() => {
    const m = new Map<string, { id: number; area: string | null; dependencia: string | null }>();
    for (const t of this.muro()?.tarjetas ?? []) {
      m.set(this.plano(t.nombre || ''), {
        id: t.id, area: t.area ?? null, dependencia: t.dependencia ?? null,
      });
    }
    return m;
  });

  /** La lista cruda, enriquecida con el área que aporta el muro. */
  proyectos = computed<ProyectoLista[]>(() => {
    const mapa = this.mapaSubgrupo();
    return this.proyectosRaw().map(p => {
      const t = p.subgrupo ? mapa.get(this.plano(p.subgrupo)) : undefined;
      return {
        ...p,
        subgrupo_id: p.subgrupo_id ?? t?.id ?? null,
        area: p.area ?? t?.area ?? null,
        dependencia: p.dependencia ?? t?.dependencia ?? null,
      };
    });
  });

  /** Cuántos proyectos no tienen área PLANIG. Se declara, no se esconde. */
  sinArea = computed(() => this.proyectos().filter(p => !p.area).length);

  // ── FILTROS EN CASCADA ──────────────────────────────────────────────
  //
  // Mismo mecanismo que traía el muro —signals, computed y handlers— mudado
  // acá porque ahora filtra PROYECTOS. Lo único que cambió es el criterio de
  // pertenencia: antes `t.id === subgrupoSel`, ahora `p.subgrupo_id`.
  areaSel = signal<string>('');
  subgrupoSel = signal<number | null>(null);
  busqueda = signal<string>('');

  /** Quita tildes para que «Educación» se encuentre escribiendo «educacion». */
  private plano(t: string): string {
    return (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  /**
   * ÁREA EJECUTORA. Se alimenta de la **dependencia**, y es PROVISIONAL.
   *
   * Antes este selector ofrecía el «área» del mapa PLANIG (Cultura, Deporte,
   * Educación…). Eso estaba mal por dos motivos: esos nombres SON subgrupos, no
   * áreas ejecutoras —así que el primer nivel repetía el segundo— y salían de un
   * mapa escrito a mano en el backend, no de una relación de la base.
   *
   * El «Área Ejecutora» de SEGPLAN (Secretaría de Ambiente, Instituto Distrital
   * de Recreación y Deporte…) NO existe para Kennedy: la columna `Entidad` sí
   * está en el CSV oficial —y no la ingerimos, de 62 columnas mapeamos 30— pero
   * trae UN SOLO valor en las 280 filas, «FONDO DE DESARROLLO LOCAL DE KENNEDY».
   * Lógico: en un plan de desarrollo LOCAL el ejecutor siempre es el FDL; las
   * secretarías son ejecutores del nivel Distrital y viven en otro dataset.
   *
   * Así que se usa la DEPENDENCIA, que es el área ejecutora dentro de la
   * Alcaldía y sale de una FK poblada (subgrupo → dependencia). Medido:
   * INVERSIÓN LOCAL 10 proyectos, ADMINISTRATIVO Y FINANCIERO 1, DESPACHO 1.
   *
   * Decisión de Alex (2026-08-23): queda así **hasta que exista la tabla propia
   * de área ejecutora**. Cuando exista, se cambia SOLO la fuente de este
   * computed y de `pasaFiltro`; el rótulo, la cascada y el filtrado no cambian.
   *
   * Se alimenta de los proyectos y no del catálogo entero: el filtro sirve para
   * ENCONTRAR proyectos, y una opción que siempre devuelve cero no ayuda.
   */
  areas = computed<string[]>(() => {
    const set = new Set<string>();
    for (const p of this.proyectos()) if (p.dependencia) set.add(p.dependencia);
    return [...set].sort((a, b) => a.localeCompare(b, 'es'));
  });

  /** Sólo los subgrupos del área ejecutora elegida (o todos si no hay). */
  subgruposDelArea = computed<Array<{ id: number; nombre: string }>>(() => {
    const area = this.areaSel();
    const vistos = new Map<number, string>();
    for (const p of this.proyectos()) {
      if (p.subgrupo_id == null || !p.subgrupo) continue;
      if (area && p.dependencia !== area) continue;
      vistos.set(p.subgrupo_id, p.subgrupo);
    }
    return [...vistos.entries()]
      .map(([id, nombre]) => ({ id, nombre }))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  hayFiltro = computed(() =>
    !!this.areaSel() || this.subgrupoSel() != null || !!this.busqueda().trim());

  private pasaFiltro(p: ProyectoLista): boolean {
    // Primer nivel = área ejecutora (dependencia). Un proyecto SIN dependencia
    // aparece con «Todas» y desaparece al elegir una concreta: no se le
    // inventa una relación para que salga.
    if (this.areaSel() && p.dependencia !== this.areaSel()) return false;
    if (this.subgrupoSel() != null && p.subgrupo_id !== this.subgrupoSel()) return false;
    const q = this.plano(this.busqueda().trim());
    if (q
        && !this.plano(p.nombre || '').includes(q)
        && !this.plano(p.codigo || '').includes(q)
        && !this.plano(p.subgrupo || '').includes(q)
        && !this.plano(p.area || '').includes(q)
        && !this.plano(p.dependencia || '').includes(q)) return false;
    return true;
  }

  proyectosVisibles = computed(() => this.proyectos().filter(p => this.pasaFiltro(p)));

  /** Al cambiar de área el subgrupo se limpia solo: si no, quedaría uno
   *  seleccionado que ya no pertenece al área y la lista saldría vacía. */
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
    this.reconciliarSeleccion();
  }

  // ── Selección: NO se navega, se cambia el id del panel derecho ───────
  seleccionar(id: number): void { this.proyectoSel.set(id); }

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
   * Abre en el explorador el proyecto de una meta.
   *
   * Si el proyecto quedó fuera por un filtro activo, los filtros se limpian:
   * seleccionar un proyecto que no está en la lista dejaría el panel derecho
   * mostrando un expediente que el maestro no puede señalar.
   */
  abrirProyectoDeMeta(codigoMeta: string | number): void {
    const pid = this.proyectoDeMeta(codigoMeta);
    if (pid == null) return;
    if (!this.proyectosVisibles().some(p => p.id === pid)) {
      this.areaSel.set('');
      this.subgrupoSel.set(null);
      this.busqueda.set('');
    }
    this.proyectoSel.set(pid);
    const destino = document.getElementById('explorador-360');
    if (!destino) return;
    const quieto = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    destino.scrollIntoView({ behavior: quieto ? 'auto' : 'smooth', block: 'start' });
  }

  /**
   * Mantiene coherente lo elegido con lo que se ve. Si el proyecto abierto
   * dejó de pasar el filtro se abre el primero visible; si no queda ninguno,
   * el panel derecho se vacía con su leyenda (no se queda con un expediente
   * huérfano que ya no está en la lista).
   */
  private reconciliarSeleccion(): void {
    const visibles = this.proyectosVisibles();
    const sel = this.proyectoSel();
    if (sel != null && visibles.some(p => p.id === sel)) return;
    this.proyectoSel.set(visibles.length ? visibles[0].id : null);
  }

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

  /**
   * Carga la lista del panel izquierdo.
   *
   * Vía buena: `/presupuesto/api/proyectos/expediente/`, que trae el semáforo
   * y los conteos ya calculados. Si todavía no responde NO se inventa nada: se
   * compone la lista con los dos endpoints que sí existen —el catálogo de
   * proyectos (id, código, nombre, subgrupo, dependencia) y la cadena
   * (n_metas, n_contratos, avance_pct)— y el semáforo queda en null, que se
   * pinta «sin calificar». Un semáforo calculado acá sería una segunda fuente
   * de verdad enfrentada a `_semaforo()` del backend.
   */
  private async cargarProyectos(): Promise<void> {
    const exp = await this.safeGet('/presupuesto/api/proyectos/expediente/');
    const filas = Array.isArray(exp) ? exp
      : (Array.isArray(exp?.results) ? exp.results
        : (Array.isArray(exp?.proyectos) ? exp.proyectos : null));
    if (filas?.length) {
      this.proyectosRaw.set(filas.map((f: any) => this.filaExpediente(f)));
      this.origenLista.set('expediente');
      this.proyectosError.set(null);
      this.reconciliarSeleccion();
      return;
    }

    const [cat, cad] = await Promise.all([
      this.safeGet('/presupuesto/api/proyectos/?page_size=200'),
      this.safeGet('/dashboard/api/presupuesto/proyectos-cadena/'),
    ]);
    const base = Array.isArray(cat) ? cat : (cat?.results ?? []);
    if (!base.length) {
      this.proyectosError.set(
        'No se pudo cargar la lista de proyectos: ningún endpoint respondió. '
        + 'No se muestran filas de ejemplo.');
      this.proyectosRaw.set([]);
      this.proyectoSel.set(null);
      return;
    }
    const porId = new Map<number, any>();
    for (const c of (cad?.proyectos ?? [])) porId.set(Number(c.id), c);

    this.proyectosRaw.set(base.map((b: any) => {
      const c = porId.get(Number(b.id));
      return {
        id: Number(b.id),
        codigo: b.codigo ?? null,
        nombre: b.nombre ?? null,
        subgrupo: this.nombreRef(b.subgrupo),
        subgrupo_id: this.idRef(b.subgrupo),
        area: b.area ?? null,
        dependencia: this.nombreRef(b.dependencia),
        avance_pct: c?.avance_pct ?? null,
        n_metas: c?.n_metas ?? null,
        // n_contratos NO se toma de la cadena: está MEDIDO que no cuenta lo
        // mismo. Contra la BD, la unión de las dos vías de atribución
        // (contrato_proyecto ∪ contrato_actividad_plan → actividad_plan) da 24
        // contratos, y la cadena reporta 5: al proyecto 2780 le asigna 0
        // cuando tiene 15. Un conteo equivocado engaña más que un vacío, así
        // que acá va null y en la tarjeta sale «—» hasta que responda el
        // endpoint del expediente, que sí hace esa unión en SQL.
        n_contratos: null,
        semaforo: null,
        semaforo_motivo: null,
      } as ProyectoLista;
    }));
    this.origenLista.set('compuesto');
    this.proyectosError.set(null);
    this.reconciliarSeleccion();
  }

  /** Una fila tal como la manda el endpoint del expediente. */
  private filaExpediente(f: any): ProyectoLista {
    return {
      id: Number(f.id),
      codigo: f.codigo ?? null,
      nombre: f.nombre ?? null,
      subgrupo: this.nombreRef(f.subgrupo),
      subgrupo_id: this.idRef(f.subgrupo) ?? (f.subgrupo_id ?? null),
      area: f.area ?? null,
      dependencia: this.nombreRef(f.dependencia),
      avance_pct: f.avance_pct ?? null,
      n_metas: f.n_metas ?? null,
      n_contratos: f.n_contratos ?? null,
      semaforo: (f.semaforo ?? null) as EstadoSemaforo | null,
      semaforo_motivo: f.semaforo_motivo ?? null,
    };
  }

  /** El backend manda las referencias como string o como {id, nombre}. */
  private nombreRef(v: any): string | null {
    if (v == null) return null;
    return typeof v === 'string' ? v : (v.nombre ?? null);
  }
  private idRef(v: any): number | null {
    return (v && typeof v === 'object' && v.id != null) ? Number(v.id) : null;
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

    // ── Lista de proyectos del explorador maestro/detalle ──
    this.cargarProyectos();
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
      // El muro aporta el área de cada proyecto: al llegar puede cambiar lo
      // que pasa el filtro, así que la selección se revisa otra vez.
      this.reconciliarSeleccion();
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
