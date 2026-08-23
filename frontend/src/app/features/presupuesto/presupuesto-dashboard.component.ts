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
interface KpisAvance {
  total_kpis: number; en_riesgo: number; pct_promedio_cumplimiento: number;
  kpis: Array<{
    id: number; nombre: string; unidad?: string; meta?: number;
    avance?: number; porcentaje: number; en_riesgo?: boolean;
    fecha_fin?: string; num_avances?: number;
  }>;
}
interface ObjetivosProy {
  rows: Array<{ proyecto: string; objetivos: number; programas?: number }>;
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
interface ProyectoCadena {
  id: number; codigo: string; nombre: string;
  contratado: number; ejecucion: number | null; n_contratos: number; cdp: number;
  n_metas: number; n_kpis: number; avance_pct: number;
  n_actividades: number; n_eventos: number; n_beneficiarios: number;
}
interface CadenaResp {
  proyectos: ProyectoCadena[];
  totales: { n_proyectos: number; contratado: number; beneficiarios: number; eventos: number };
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

@Component({
  standalone: true,
  selector: 'app-presupuesto-dashboard',
  imports: [CommonModule, RouterLink, MuroSubgruposComponent, ExpedienteProyectoComponent],
  template: `
    <div class="page">
      <header class="hero">
        <div>
          <h1>
            <i class="fa fa-chart-pie"></i> Dashboard Presupuesto
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
          <i class="fa fa-exclamation-triangle"></i>
          <strong>{{ errorMsg() }}</strong>
          <button class="ui-btn ui-btn--sm" (click)="recargar()">
            <i class="fa fa-rotate"></i> Reintentar
          </button>
        </div>
      }
      <!-- ════════ RESUMEN SUPERIOR COMPACTO ═══════════════════════════
           Los cortes y las cuatro cifras del ledger NO se pierden: se
           mudaron acá desde el muro (que ahora entra en modo «compacto»)
           y ocupan una franja de dos filas en vez de dos bloques. Las
           cifras son las mismas del mismo endpoint: no se recalcula nada. -->
      <section class="resumen" aria-labelledby="resumen-tit">
        <span class="resumen__marca" aria-hidden="true"></span>
        <div class="resumen__cuerpo">
          <h2 class="resumen__tit" id="resumen-tit">
            <span class="rotulo">Expediente de inversión local</span>
            Corte y ejecución
          </h2>

          @if (muro(); as m) {
            <div class="resumen__cortes">
              <span class="corte">
                <span class="rotulo">Corte SECOP</span>
                @if (m.cabecera.corte) { {{ fecha(m.cabecera.corte) }} }
                @else { <span class="sin-dato">sin dato</span> }
              </span>
              <span class="corte">
                <span class="rotulo">Corte PDL oficial</span>
                @if (m.cabecera.corte_pdl_oficial) { {{ fecha(m.cabecera.corte_pdl_oficial) }} }
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
              <div class="ledger__item">
                <dt class="rotulo">Saldo por girar</dt>
                <dd>
                  {{ enMillones(ledgerSaldo().valor) }}
                  <small>comprometido − girado</small>
                </dd>
              </div>
            </dl>

            <!-- Estos dos avisos NO son decoración: sin ellos el ledger miente.
                 Venían con las cifras en el muro y se perdieron al compactarlo.
                 Van pegados a las cifras, no en un pliegue: una advertencia que
                 hay que desplegar para verla no advierte a nadie. -->
            <p class="resumen__aviso">
              <i class="fa fa-circle-info" aria-hidden="true"></i>
              Son <strong>dos cortes distintos</strong>: lo comprometido y lo girado
              vienen de SECOP; lo programado, del PDL oficial de la SDP.
              <strong>No se restan entre sí</strong> — el saldo es comprometido menos
              girado, nunca programado menos comprometido: serían dos universos
              (proyectos del PDL frente a proyectos cargados) y dos fechas de corte,
              y esa resta daría un número plausible y falso.
            </p>
            <p class="resumen__aviso resumen__aviso--alcance">
              <i class="fa fa-list-check" aria-hidden="true"></i>
              Las cuatro cifras son del <strong>total de la localidad</strong> y no
              cambian al filtrar: los filtros de abajo acotan la lista de proyectos,
              no el ledger.
            </p>
          } @else if (muroError()) {
            <p class="resumen__aviso resumen__aviso--error">
              <i class="fa fa-triangle-exclamation" aria-hidden="true"></i> {{ muroError() }}
            </p>
          } @else {
            <p class="resumen__aviso">Midiendo cortes y ejecución…</p>
          }
        </div>
      </section>

      <!-- ════════ EXPLORADOR MAESTRO / DETALLE ════════════════════════
           La unidad principal es el PROYECTO. A la izquierda se busca y se
           filtra; a la derecha se abre el expediente SIN cambiar de ruta.
           El muro de áreas sigue vivo, plegado al final de esta sección. -->
      <div class="explorador">

        <!-- ── MAESTRO ─────────────────────────────────────────────── -->
        <aside class="maestro" aria-labelledby="maestro-tit">
          <div class="maestro__cabeza">
            <div class="maestro__titulo">
              <h2 id="maestro-tit"><span class="rotulo">Explorador</span>Proyectos</h2>
              <span class="maestro__conteo"
                    [attr.aria-label]="proyectosVisibles().length + ' de '
                                       + proyectos().length + ' proyectos'">
                {{ proyectosVisibles().length }}<i>/{{ proyectos().length }}</i>
              </span>
            </div>

            <!-- FILTROS EN CASCADA — el mismo mecanismo del muro, mudado acá:
                 al cambiar de área el subgrupo se limpia solo y el selector de
                 subgrupo sólo ofrece los del área elegida. Ahora filtran
                 PROYECTOS, que es la unidad que manda en esta página. -->
            <div class="filtros">
              <label class="filtros__campo filtros__campo--busca">
                <span class="ui-sr-only">Buscar proyecto</span>
                <i class="fa fa-magnifying-glass" aria-hidden="true"></i>
                <input type="search" name="q_proyecto" autocomplete="off"
                       placeholder="Buscar proyecto…"
                       [value]="busqueda()" (input)="cambiarBusqueda($event)">
              </label>

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

              @if (hayFiltro()) {
                <button type="button" class="filtros__limpiar" (click)="limpiarFiltros()">
                  <i class="fa fa-xmark" aria-hidden="true"></i> Limpiar filtros
                </button>
              }
            </div>

            @if (!areaSel() && sinArea()) {
              <p class="maestro__nota">
                {{ sinArea() }} de {{ proyectos().length }} proyectos no tienen área asignada
                en el mapa PLANIG: sólo aparecen con el filtro de área en «Todas».
              </p>
            }
            @if (origenLista() === 'compuesto' && proyectos().length) {
              <p class="maestro__nota">
                Lista compuesta con los endpoints ya disponibles.
                <code>/presupuesto/api/proyectos/expediente/</code> todavía no
                responde, así que el semáforo sale «sin calificar» y el número de
                contratos sale «—»: el conteo que hay a mano se queda corto
                (5 de los 24 contratos atribuidos) y publicarlo sería peor que
                dejarlo vacío. Código, nombre, área, subgrupo, dependencia, metas
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
                      @else { <span class="tag tag--vacio">Sin área PLANIG</span> }
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
        <section class="detalle" aria-live="polite">
          @if (proyectoSel() != null) {
            <app-expediente-proyecto [proyectoId]="proyectoSel()" />
          } @else {
            <p class="detalle__vacio">
              <i class="fa fa-folder-open" aria-hidden="true"></i>
              Elegí un proyecto de la izquierda para abrir su expediente.
            </p>
          }
        </section>
      </div>

      <!-- ════════ MURO DE ÁREAS (plegado) ═════════════════════════════
           El muro de 45 tarjetas dejó de ser el explorador principal, pero
           su información —dinero y pendientes por área— NO se borra: queda
           acá, plegada, y obedece los mismos filtros de arriba. Va en modo
           «compacto» porque sus cortes y su ledger ya los pinta el resumen. -->
      <details class="pliegue">
        <summary class="pliegue__cabeza">
          <span class="rotulo">Dinero y pendientes por área</span>
          <span class="pliegue__nota">
            @if (muro(); as m) { {{ m.tarjetas.length }} subgrupos, con sus pendientes y la cobertura del PDL }
            @else { midiendo… }
          </span>
        </summary>
        <app-muro-subgrupos [datos]="muro()" [error]="muroError()" [compacto]="true"
                            [filtroArea]="areaSel()"
                            [filtroSubgrupoId]="subgrupoSel()"
                            [filtroBusqueda]="busqueda()" />
      </details>

      <!-- Layout siempre visible — secciones aparecen progresivamente -->
      @if (true) {
        @let r = resumen();

        <!-- ════════ COCKPIT EJECUTIVO (nuevo, no reemplaza nada) ════════ -->
        @let p = plata();
        @let g = gente();
        @let cad = cadena();

        <!-- Filtro de vigencia (afecta Plata + Cadena) -->
        @if (p && p.vigencias.length) {
          <div class="cockpit-filtros">
            <span class="cockpit-filtros__label"><i class="fa fa-filter"></i> Vigencia</span>
            <button class="vchip" [class.vchip--on]="!vigencia()" (click)="setVigencia(null)">Todas</button>
            @for (v of p.vigencias; track v) {
              <button class="vchip" [class.vchip--on]="vigencia() === v" (click)="setVigencia(v)">{{ v }}</button>
            }
          </div>
        }

        <!-- Banda 💰 PLATA -->
        <section class="band band--plata" [class.skeleton]="!p">
          <header class="band__header">
            <h2><i class="fa fa-coins"></i> Inversión y contratación</h2>
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
              <div class="big-stat__value">{{ p ? formatNumero(p.pct_ejecucion) + '%' : '…' }}</div>
              <div class="big-stat__label">Ejecución física (ponderada)</div>
              <div class="barra">
                <div class="barra__fill" [class]="claseBarra(p?.pct_ejecucion || 0)"
                     [style.width.%]="Math.min(p?.pct_ejecucion || 0, 100)"></div>
              </div>
            </article>
            <article class="big-stat big-stat--soft"
                     [title]="'CDP con valor cargado: ' + (p?.cdp_con_valor || 0) + '/' + (p?.cdp_n || 0)">
              <div class="big-stat__value">{{ plataMM(p?.cdp_asignado) }}</div>
              <div class="big-stat__label">CDP registrado <i class="fa fa-circle-info"></i></div>
            </article>
            <article class="band__chart">
              <canvas #chartCategoria></canvas>
            </article>
          </div>
          @if (p && p.cdp_con_valor < p.cdp_n) {
            <p class="band__note">
              <i class="fa fa-triangle-exclamation"></i>
              {{ p.cdp_n - p.cdp_con_valor }} CDP sin valor cargado — el presupuesto asignado real será mayor.
            </p>
          }
        </section>

        <!-- Banda 👥 GENTE -->
        <section class="band band--gente" [class.skeleton]="!g">
          <header class="band__header">
            <h2><i class="fa fa-users"></i> Personas beneficiadas</h2>
            @if (g) { <span class="band__pill">{{ g.organizaciones }} organizaciones</span> }
          </header>
          <div class="band__grid">
            <article class="big-stat big-stat--people">
              <div class="big-stat__value">{{ g ? formatNumero(g.beneficiarios) : '…' }}</div>
              <div class="big-stat__label">Beneficiarios</div>
            </article>
            <article class="big-stat">
              <div class="big-stat__value">{{ g ? formatNumero(g.pct_mujeres) + '%' : '…' }}</div>
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
            <p class="band__note">
              <i class="fa fa-circle-info"></i>
              Edad, etnia y enfoque diferencial fino se activan cuando se diligencie la caracterización.
            </p>
          }
        </section>

        <!-- 🔗 CADENA POR PROYECTO -->
        @if (cad) {
          <section class="seccion seccion--cadena">
            <header class="seccion__header">
              <h2><i class="fa fa-link" style="color:#0D9488"></i> Cadena de cada proyecto</h2>
              <div class="stats-strip">
                <span class="stat">{{ cad.totales.n_proyectos }} proyectos</span>
                <span class="stat stat--ok">{{ plataMM(cad.totales.contratado) }}</span>
              </div>
            </header>
            <p class="seccion__hint">
              Trazabilidad de punta a punta: dinero → metas → KPIs → actividades → eventos → beneficiarios.
              Click en una fila abre el 360° del proyecto.
            </p>
            <div class="ui-table-responsive">
              <table class="ui-table cadena-table">
                <thead>
                  <tr>
                    <th>Proyecto</th><th>Contratado</th><th>Ejec.</th>
                    <th>Metas</th><th>KPIs</th><th>Avance</th>
                    <th>Activ.</th><th>Eventos</th><th>Benef.</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  @for (f of cad.proyectos; track f.id) {
                    <tr class="cadena-row" [routerLink]="['/presupuesto/proyectos', f.id]"
                        tabindex="0" [attr.aria-label]="'Ver cadena 360° del proyecto ' + f.nombre">
                      <td class="cadena-row__name">
                        <strong>{{ f.codigo }}</strong><span>{{ f.nombre }}</span>
                      </td>
                      <td class="num">{{ f.contratado ? plataMM(f.contratado) : '—' }}</td>
                      <td class="num">{{ f.ejecucion != null ? formatNumero(f.ejecucion) + '%' : '—' }}</td>
                      <td><span class="chip">{{ f.n_metas }}</span></td>
                      <td><span class="chip">{{ f.n_kpis }}</span></td>
                      <td class="avance-cell">
                        <div class="mini-barra">
                          <div class="mini-barra__fill" [class]="claseBarra(f.avance_pct)"
                               [style.width.%]="Math.min(f.avance_pct, 100)"></div>
                        </div>
                        <span class="mini-pct">{{ formatNumero(f.avance_pct) }}%</span>
                      </td>
                      <td><span class="chip">{{ f.n_actividades }}</span></td>
                      <td><span class="chip" [class.chip--zero]="!f.n_eventos">{{ f.n_eventos }}</span></td>
                      <td><span class="chip" [class.chip--zero]="!f.n_beneficiarios">{{ f.n_beneficiarios }}</span></td>
                      <td class="chevron"><i class="fa fa-chevron-right"></i></td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        }
        <!-- ════════ FIN COCKPIT — debajo sigue el dashboard clásico ════════ -->

        <div class="kpi-grid" [class.skeleton]="!r">
          <a class="kpi-card kpi-card--primary kpi-card--link" routerLink="/presupuesto/proyectos"
             aria-label="Ver listado de proyectos del plan">
            <div class="kpi-card__icon"><i class="fa fa-folder-open"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.proyectos ?? '…' }}</div>
              <div class="kpi-card__label">Proyectos del Plan</div>
            </div>
          </a>
          <a class="kpi-card kpi-card--accent kpi-card--link" routerLink="/presupuesto/metas"
             aria-label="Ver listado de metas">
            <div class="kpi-card__icon"><i class="fa fa-bullseye"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.metas_pdd ?? '…' }}</div>
              <div class="kpi-card__label">Metas PDD</div>
            </div>
          </a>
          <a class="kpi-card kpi-card--info kpi-card--link" routerLink="/presupuesto/indicadores"
             aria-label="Ver listado de indicadores (KPIs)">
            <div class="kpi-card__icon"><i class="fa fa-chart-line"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.indicadores ?? '…' }}</div>
              <div class="kpi-card__label">Indicadores (KPIs)</div>
            </div>
          </a>
          <article class="kpi-card kpi-card--secondary kpi-card--static"
                   title="Solo contador (eventos del mes en curso)">
            <div class="kpi-card__icon"><i class="fa fa-calendar-alt"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.eventos_mes ?? '…' }}</div>
              <div class="kpi-card__label">Eventos del mes</div>
            </div>
          </article>
          <a class="kpi-card kpi-card--success kpi-card--link" routerLink="/presupuesto/avances"
             aria-label="Ver listado de avances a KPIs">
            <div class="kpi-card__icon"><i class="fa fa-check-circle"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.avances ?? '…' }}</div>
              <div class="kpi-card__label">Avances a KPIs</div>
            </div>
          </a>
          <article class="kpi-card kpi-card--danger kpi-card--static"
                   title="Solo contador (KPIs en riesgo de incumplimiento)">
            <div class="kpi-card__icon"><i class="fa fa-exclamation-triangle"></i></div>
            <div class="kpi-card__body">
              <div class="kpi-card__value">{{ r?.en_riesgo ?? '…' }}</div>
              <div class="kpi-card__label">KPIs en riesgo</div>
            </div>
          </article>
        </div>

        <!-- 3 GRÁFICOS -->
        <div class="charts-row">
          <article class="chart-card">
            <header><h2><i class="fa fa-chart-line"></i> Eventos por mes</h2></header>
            <canvas #chartMes></canvas>
          </article>
          <article class="chart-card">
            <header><h2><i class="fa fa-chart-pie"></i> Eventos por tipo</h2></header>
            <canvas #chartTipo></canvas>
          </article>
          <article class="chart-card">
            <header>
              <h2><i class="fa fa-trophy" style="color:#f59e0b"></i> Top sectores</h2>
            </header>
            @if (sectores() && !sectores()!.length) {
              <div class="ui-empty-state">Sin datos de sectores aún.</div>
            } @else {
              <canvas #chartSect></canvas>
            }
          </article>
        </div>

        <!-- METAS + KPIs lado a lado -->
        <div class="dos-cols">
          @if (metas()) {
            @let m = metas()!;
            <section class="seccion">
              <header class="seccion__header">
                <h2><i class="fa fa-flag" style="color:#8b5cf6"></i> Metas del Plan</h2>
                <div class="stats-strip">
                  <span class="stat stat--ok">{{ m.stats.cumplidas }} ✓</span>
                  <span class="stat stat--prog">{{ m.stats.en_progreso }} ↗</span>
                  <span class="stat stat--warn">{{ m.stats.en_riesgo }} ⚠</span>
                  <span class="stat stat--none">{{ m.stats.sin_avance }} —</span>
                </div>
              </header>
              <div class="seccion__scroll">
                <div class="metas-grid">
                  @for (mt of m.metas; track mt.codigo) {
                    <article class="meta-card" [class]="'meta-card--' + mt.estado">
                      <div class="meta-card__head">
                        <strong>{{ mt.codigo }}</strong>
                        <span class="meta-card__badge"
                              [class]="'badge-' + mt.estado">
                          {{ etiquetaEstado(mt.estado) }}
                        </span>
                      </div>
                      <p class="meta-card__nombre">{{ mt.nombre }}</p>
                      <div class="meta-card__foot">
                        @if (mt.sector) { <span>{{ mt.sector }}</span> }
                        @if (mt.num_indicadores) {
                          <span><i class="fa fa-chart-line"></i> {{ mt.num_indicadores }} KPI</span>
                        }
                        @if (mt.fecha_fin) {
                          <span><i class="fa fa-calendar-alt"></i> {{ mt.fecha_fin }}</span>
                        }
                      </div>
                      <!-- El porcentaje es contra la meta DE LA VIGENCIA, no
                           contra la del cuatrienio que suele venir en el
                           nombre. Sin decirlo, una tarjeta que se titula
                           «Impactar 1400» y pinta media barra se lee como 700
                           personas cuando son 174. -->
                      <div class="barra">
                        <div class="barra__fill"
                             [class]="claseBarra(mt.porcentaje)"
                             [style.width.%]="Math.min(mt.porcentaje, 100)">
                        </div>
                        <span class="barra__label">{{ formatNumero(mt.porcentaje) }}%</span>
                      </div>
                      <p class="meta-card__marco">
                        {{ formatNumero(mt.avance_total) }} de
                        {{ formatNumero(mt.meta_total) }} <strong>de la vigencia</strong>
                      </p>
                    </article>
                  }
                </div>
              </div>
            </section>
          }

          @if (kpisData()) {
            @let kd = kpisData()!;
            <section class="seccion">
              <header class="seccion__header">
                <h2><i class="fa fa-bullseye"></i> Avance de KPIs</h2>
                <div class="stats-strip">
                  <span class="stat">{{ kd.total_kpis }}</span>
                  <span class="stat stat--warn">{{ kd.en_riesgo }} riesgo</span>
                  <span class="stat stat--ok">{{ formatNumero(kd.pct_promedio_cumplimiento) }}% prom.</span>
                </div>
              </header>
              <div class="seccion__scroll">
                <div class="kpis-table">
                  @for (k of kpisOrdenados(); track k.id) {
                    <article class="kpi-item">
                      <div class="kpi-item__head">
                        <strong>{{ k.nombre }}</strong>
                        <span class="kpi-item__pct"
                              [class]="claseTexto(k.porcentaje)">
                          {{ formatNumero(k.porcentaje) }}%
                        </span>
                      </div>
                      <div class="barra">
                        <div class="barra__fill"
                             [class]="claseBarra(k.porcentaje)"
                             [style.width.%]="Math.min(k.porcentaje, 100)"></div>
                      </div>
                    </article>
                  }
                </div>
              </div>
            </section>
          }
        </div>

        <!-- OBJETIVOS POR PROYECTO -->
        @if (objetivos(); as o) {
          @if (o.rows.length) {
            <section class="seccion">
              <header class="seccion__header">
                <h2><i class="fa fa-bullseye" style="color:#0EA5E9"></i>
                    Objetivos por Proyecto</h2>
              </header>
              <div class="ui-table-responsive">
                <table class="ui-table">
                  <thead>
                    <tr><th>Proyecto</th><th>Objetivos</th><th>Programas</th></tr>
                  </thead>
                  <tbody>
                    @for (r of o.rows; track r.proyecto) {
                      <tr>
                        <td>{{ r.proyecto }}</td>
                        <td><span class="badge-pill">{{ r.objetivos }}</span></td>
                        <td>
                          @if (r.programas) {
                            <span class="badge-pill">{{ r.programas }}</span>
                          } @else { — }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </section>
          }
        }
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
  kpisData = signal<KpisAvance | null>(null);
  objetivos = signal<ObjetivosProy | null>(null);
  // Cockpit ejecutivo
  plata = signal<EjecucionFinanciera | null>(null);
  gente = signal<BeneficiariosPerfil | null>(null);
  cadena = signal<CadenaResp | null>(null);
  vigencia = signal<number | null>(null);

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

    // 3. Top sectores
    this.safeGet(`${base}/top-sectores/`).then(s => {
      if (s) {
        this.sectores.set(s);
        setTimeout(() => this.dibujarCharts(), 80);
      }
    });

    // 4. Metas
    this.safeGet(`${base}/metas-progreso/`).then(m => {
      if (m) this.metas.set(m);
    });

    // 5. KPIs lista
    this.safeGet(`${base}/kpis-avance/`).then(k => {
      if (k) this.kpisData.set(k);
    });

    // 6. Objetivos / cascada
    this.safeGet(`${base}/cascada-resumen`).then(o => {
      if (o) this.objetivos.set(this.adaptarObjetivos(o));
    });

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

  /** Carga las 3 lentes del cockpit (plata / gente / cadena). */
  private cargarCockpit(): void {
    const base = '/dashboard/api/presupuesto';
    const vq = this.vigencia() ? `?vigencia=${this.vigencia()}` : '';

    this.safeGet(`${base}/ejecucion-financiera/${vq}`).then(d => {
      if (d) { this.plata.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
    this.safeGet(`${base}/beneficiarios-perfil/`).then(d => {
      if (d) { this.gente.set(d); setTimeout(() => this.dibujarCockpitCharts(), 80); }
    });
    this.safeGet(`${base}/proyectos-cadena/${vq}`).then(d => {
      if (d) this.cadena.set(d);
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
    this.safeGet(`${base}/proyectos-cadena/${vq}`).then(d => {
      if (d) this.cadena.set(d);
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

  private adaptarObjetivos(raw: any): ObjetivosProy {
    if (raw?.rows) return raw;
    const rows = (raw?.proyectos || raw || []).map((p: any) => ({
      proyecto: p.codigo ? `${p.codigo} ${p.nombre || ''}`.trim()
                          : (p.nombre || `#${p.id || '?'}`),
      objetivos: p.n_objetivos ?? p.objetivos ?? 0,
      programas: p.n_programas ?? p.programas ?? 0,
    }));
    return { rows };
  }

  kpisOrdenados(): KpisAvance['kpis'] {
    const k = this.kpisData();
    if (!k) return [];
    return [...k.kpis].sort((a, b) => a.porcentaje - b.porcentaje).slice(0, 25);
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
  claseTexto(pct: number): string {
    if (pct >= 80) return 'pct-ok';
    if (pct >= 50) return 'pct-warn';
    return 'pct-bad';
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
