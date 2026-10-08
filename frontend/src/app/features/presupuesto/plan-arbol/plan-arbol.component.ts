import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../../core/config/config.service';
import { errorDeCarga, ErrorDeCarga } from '../estado-carga';
import { enMillones } from '../muro/muro-subgrupos.component';
import {
  BALDE, MetaNodo, ObjetivoNodo, PlanArbol, ProgramaNodo, ProyectoNodo, QUE_ES,
} from './plan-arbol.types';

/** Un nodo aplanado, listo para pintar en una sola lista. */
interface Fila {
  /** Identidad estable. La clave de `track` y la del estado de expansión. */
  id: string;
  nivel: 'objetivo' | 'programa' | 'proyecto' | 'meta';
  /** 0..3 — la sangría, y `aria-level` es esto + 1. */
  profundidad: number;
  /** Lo que se muestra en el chip: el código con el que se reconoce el nodo. */
  codigo: string;
  nombre: string;
  /** `null` en las metas: no tienen hijos (pero SÍ se despliegan, ver `desplegable`). */
  hijos: number | null;
  /** 1..n entre sus hermanos, y cuántos son. El patrón de árbol los exige
   *  junto con `aria-level` cuando la lista está aplanada. */
  pos: number;
  total: number;
  /** El id del padre. Sirve para expandir la rama al buscar. */
  padre: string | null;
  meta?: MetaNodo;
  resumen?: ObjetivoNodo['resumen'];
  proyecto?: ProyectoNodo;
}

/**
 * El Plan de Desarrollo Local como árbol: Objetivo → Programa → Proyecto → Meta.
 *
 * Reemplaza a la sección «El Plan» del hub, que eran cuatro tarjetas hacia
 * cuatro listas planas. Las listas siguen existiendo y se siguen llegando por
 * URL; lo que esas tarjetas no daban —y esta pantalla sí— es la jerarquía: qué
 * cuelga de qué, y cuánto lleva cada rama.
 *
 * ## De dónde salen las cifras
 *
 * De `GET /dashboard/api/v2/presupuesto/plan-oficial/`, que trae el árbol
 * entero con los agregados ya calculados por el backend: 135 nodos, 98 KB,
 * cuatro consultas. **Este componente no suma ni promedia nada.** Si lo
 * hiciera, el mismo objetivo podría decir una cifra acá y otra en el tablero —
 * que es exactamente lo que pasó cuando siete lectores calculaban el avance
 * cada uno por su lado.
 *
 * ## Por qué una lista aplanada y no `@for` anidados
 *
 * El patrón ARIA de árbol quiere `role="tree"` con `treeitem` que declaran su
 * `aria-level`, y eso se escribe mucho mejor sobre una lista plana con
 * profundidad que sobre cuatro bucles encajados. Además el buscador necesita
 * recorrer todo y expandir la rama del hallazgo, y sobre una lista plana con
 * punteros al padre eso es una línea.
 *
 * Son 135 nodos: caben enteros en memoria y no hace falta virtualizar. La
 * expansión por clic es por LEGIBILIDAD, no por rendimiento.
 */
/**
 * ¿Se pinta el ÁRBOL, o solo la franja de totales?
 *
 * En `false` —como está hoy— esta pantalla muestra únicamente la franja
 * (5 objetivos · 22 programas · 30 proyectos · 78 metas, con la plata y el
 * avance) y la nota de fuente. El buscador, el botón de colapsar y la lista de
 * ramas no se renderizan.
 *
 * El motivo es de producto y no técnico: **la jerarquía ya se recorre en el
 * Tablero**, y tenerla dos veces en la misma entrada obliga a elegir entre dos
 * caminos para lo mismo. La franja sí aporta algo que no estaba: el tamaño del
 * Plan y sus cifras de cabecera, en una línea.
 *
 * El componente NO se borró, y por eso esto es una bandera y no una supresión:
 * el árbol funciona, tiene sus tests y está revisado. Si mañana se decide que
 * la jerarquía navegable vale la pena acá, es poner `true`.
 *
 * Con la bandera apagada la petición a `plan-oficial` se hace IGUAL: la franja
 * sale de esa misma respuesta. Ni se duplica la llamada ni se queman cifras.
 */
const MOSTRAR_ARBOL = false;

@Component({
  standalone: true,
  selector: 'app-plan-arbol',
  imports: [CommonModule, FormsModule, RouterLink, LucideAngularModule],
  template: `
    <section class="arbol" [attr.aria-busy]="cargando()">
      <header class="arbol__head" [class.arbol__head--compacta]="!mostrarArbol">
        <div>
          @if (mostrarArbol) {
            <h2 class="arbol__titulo">
              <lucide-icon name="folder-kanban" [size]="18" aria-hidden="true"></lucide-icon>
              El Plan, rama por rama
            </h2>
            <p class="arbol__sub">
              Objetivo → Programa → Proyecto → Meta. Las cifras son las de la
              Matriz de Seguimiento PDL, las mismas del tablero.
            </p>
            <!-- Qué es cada nivel: una vez para el lector de pantalla, no 135
                 veces en el «title» de cada chip. -->
            <p class="ui-sr-only">
              Objetivo: {{ ayuda('objetivo') }}
              Programa: {{ ayuda('programa') }}
              Proyecto: {{ ayuda('proyecto') }}
              Meta: {{ ayuda('meta') }}
            </p>
          }
        </div>

        @if (mostrarArbol && !cargando() && !error()) {
          <div class="arbol__acciones">
            <label class="buscador">
              <i class="fa fa-search" aria-hidden="true"></i>
              <input type="search" [(ngModel)]="consulta"
                     (ngModelChange)="buscar($event)"
                     placeholder="Buscar objetivo, programa, proyecto o meta…"
                     aria-label="Buscar en el Plan" />
            </label>
            <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm"
                    (click)="colapsarTodo()">
              <!-- »fa-chevron-up» y no »fa-compress»: el subset de Font
                   Awesome que se despacha no trae »compress», así que el botón
                   salía sin icono. El generador del subset está roto aparte
                   (»npm run iconos:subset» rechaza hasta »fa-1x»). -->
              <i class="fa fa-chevron-up" aria-hidden="true"></i> Colapsar
            </button>
          </div>
        }
      </header>

      @if (cargando()) {
        <p class="muted"><i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Cargando el Plan…</p>
      } @else if (error()) {
        <div class="ui-empty-state">
          <i class="fa" [class]="error()!.icono" aria-hidden="true"></i>
          <p><strong>{{ error()!.titulo }}</strong></p>
          <p class="muted">{{ error()!.detalle }}</p>
        </div>
      } @else if (datos()) {
        <!-- «as» no se permite en un @else if, solo en el @if primario
             (NG5002). «@let» hace lo mismo y deja el bloque legible. -->
        @let d = datos()!;

        <!-- El total del Plan, con la MISMA regla que cada nodo: la plata se
             suma, el avance se promedia. Lo calcula el backend. -->
        <div class="totales">
          <div class="totales__cifra">
            <span class="totales__n">{{ d.conteo.objetivos }}</span>
            <span class="totales__l">objetivos</span>
          </div>
          <div class="totales__cifra">
            <span class="totales__n">{{ d.conteo.programas }}</span>
            <span class="totales__l">programas</span>
          </div>
          <div class="totales__cifra">
            <span class="totales__n">{{ d.conteo.proyectos }}</span>
            <span class="totales__l">proyectos</span>
          </div>
          <div class="totales__cifra">
            <span class="totales__n">{{ d.conteo.metas }}</span>
            <span class="totales__l">metas</span>
          </div>
          <div class="totales__cifra totales__cifra--ancha">
            <span class="totales__n">{{ mm(d.resumen.plata.apropiacion) }}</span>
            <span class="totales__l">apropiado (POAI) {{ rango(d.resumen.plata) }}</span>
          </div>
          <div class="totales__cifra totales__cifra--ancha">
            <span class="totales__n">{{ pct(d.resumen.avance.pct) }}</span>
            <span class="totales__l">
              avance {{ d.resumen.avance.vigencia ? '(' + d.resumen.avance.vigencia + ')' : '' }}
              · {{ d.resumen.avance.regla }}
            </span>
          </div>
        </div>

        @if (mostrarArbol) {
          <!--
            Colgaba de «!filas().length», que NUNCA es cierto: los objetivos se
            pintan siempre, así que una búsqueda sin resultados no decía nada y
            parecía que el árbol se había colapsado solo. Ahora depende de las
            coincidencias, y el acierto también se anuncia.
          -->
          @if (consulta.trim()) {
            <p class="sin-hallazgo" role="status" aria-live="polite">
              @if (nHallazgos()) {
                {{ nHallazgos() }}
                {{ nHallazgos() === 1 ? 'coincidencia' : 'coincidencias' }} con «{{ consulta }}».
              } @else {
                Nada coincide con «{{ consulta }}» en los {{ d.conteo.metas }} renglones del Plan.
              }
            </p>
          }

          <ul class="rama" role="tree"
              [attr.aria-label]="'Plan de Desarrollo Local, ' + d.conteo.metas + ' metas'">
            @for (f of filas(); track f.id) {
              <li class="nodo"
                  [class]="'nodo--' + f.nivel"
                  [style.--sangria.px]="f.profundidad * 18"
                  role="treeitem"
                  [attr.data-nodo]="f.id"
                  [attr.aria-level]="f.profundidad + 1"
                  [attr.aria-posinset]="f.pos"
                  [attr.aria-setsize]="f.total"
                  [attr.aria-expanded]="desplegable(f) ? abierto(f.id) : null"
                  [attr.aria-current]="resaltado(f.id) ? 'true' : null"
                  [class.nodo--resaltado]="resaltado(f.id)"
                  [tabindex]="f.id === focoVisible() ? 0 : -1"
                  (keydown)="teclado($event, f)"
                  (click)="alternar(f)">

                <div class="nodo__fila">
                  <span class="nodo__flecha" aria-hidden="true">
                    @if (desplegable(f)) {
                      <i class="fa" [class]="abierto(f.id) ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                    }
                  </span>

                  <span class="nodo__chip"
                        [attr.title]="ayuda(f.nivel)">{{ f.codigo }}</span>

                  <span class="nodo__nombre">{{ f.nombre }}</span>

                  @if (f.hijos) {
                    <span class="nodo__hijos">{{ f.hijos }}</span>
                  }

                  <!-- Nodo agregado: avance promediado y plata sumada. -->
                  @if (f.resumen; as r) {
                    <span class="nodo__avance"
                          [attr.title]="tituloAvance(r)">
                      <span class="barra" [attr.aria-hidden]="true">
                        <span class="barra__f"
                              [style.width.%]="ancho(r.avance.pct)"
                              [class]="'barra__f--' + nivelAvance(r.avance.pct)"></span>
                      </span>
                      <span class="nodo__pct">{{ pct(r.avance.pct) }}</span>
                      <!-- El »title» no llega al lector de pantalla ni al
                           teclado: la regla y el desglose van también acá. -->
                      <span class="ui-sr-only">{{ tituloAvance(r) }}</span>
                    </span>
                    <span class="nodo__plata" [attr.title]="tituloPlata(r)">
                      {{ mm(r.plata.apropiacion) }}
                      <span class="ui-sr-only">{{ tituloPlata(r) }}</span>
                    </span>
                  }

                  <!-- Hoja: la meta, con su alerta. -->
                  @if (f.meta; as m) {
                    @if (m.alerta) {
                      <span class="pastilla" [class]="'pastilla--' + balde(m.alerta)">
                        {{ m.alerta }}
                      </span>
                    }
                    <span class="nodo__pct nodo__pct--meta">{{ pct(m.cumplimiento_pct) }}</span>
                  }
                </div>

                <!-- El detalle de la meta: magnitud, avance y plata. -->
                @if (f.meta && abierto(f.id)) {
                  @let m = f.meta!;
                  <!--
                    El keydown TAMBIÉN se detiene, no solo el click. El panel vive
                    dentro del treeitem, así que un Enter sobre un enlace burbujeaba
                    hasta teclado(), que llamaba alternar() —cerrando el panel— y
                    preventDefault() —cancelando justo la acción que el navegador
                    convierte en el click del ancla—. Con ratón navegaba; con
                    teclado no. Medido en un navegador real.
                  -->
                  <div class="detalle"
                       (click)="$event.stopPropagation()"
                       (keydown)="$event.stopPropagation()">
                    <dl class="detalle__campos">
                      <div>
                        <dt>Meta SEGPLAN</dt>
                        <dd class="mono">{{ m.codigo_meta || '—' }}</dd>
                      </div>
                      <div>
                        <dt>Magnitud</dt>
                        <dd>
                          {{ m.kpi_magnitud !== null ? (m.kpi_magnitud | number:'1.0-0') : '—' }}
                          <small>{{ m.kpi_unidad || '' }}</small>
                        </dd>
                      </div>
                      <div>
                        <dt>Contratada / ejecutada</dt>
                        <dd>
                          {{ m.magnitud_contratada !== null ? (m.magnitud_contratada | number:'1.0-0') : '—' }}
                          ·
                          {{ m.magnitud_ejecutada !== null ? (m.magnitud_ejecutada | number:'1.0-0') : '—' }}
                        </dd>
                      </div>
                      <div>
                        <dt>Apropiado (POAI)</dt>
                        <dd>{{ mm(m.apropiacion_poai) }}
                          @if (m.apropiacion_vigencia_desde) {
                            <small>{{ m.apropiacion_vigencia_desde }}–{{ m.apropiacion_vigencia_hasta }}</small>
                          }
                        </dd>
                      </div>
                      <div><dt>Comprometido</dt><dd>{{ mm(m.comprometido) }}</dd></div>
                      <div><dt>Girado</dt><dd>{{ mm(m.girado) }}</dd></div>
                    </dl>

                    <!--
                      El contraste con el Distrito. «null» NO se pinta en cero:
                      que una meta no esté en Datos Abiertos es un hallazgo, no
                      un cero.
                    -->
                    @if (m.espejo; as e) {
                      <p class="detalle__espejo">
                        Datos Abiertos SDP: programado
                        {{ e.programado !== null ? (e.programado | number:'1.0-0') : '—' }},
                        entregado
                        {{ e.entregado !== null ? (e.entregado | number:'1.0-0') : '—' }}
                        @if (e.tipo_anualizacion) { <span>· {{ e.tipo_anualizacion }}</span> }
                      </p>
                    } @else {
                      <p class="detalle__espejo detalle__espejo--falta">
                        Esta meta está en la Matriz de la Alcaldía pero no tiene par
                        en Datos Abiertos del Distrito.
                      </p>
                    }

                    <p class="detalle__enlaces">
                      <a routerLink="/plan/metas" (click)="$event.stopPropagation()">
                        Ver esta meta en la lista ↗
                      </a>
                      <a routerLink="/plan/dashboard" (click)="$event.stopPropagation()">
                        Abrir el tablero ↗
                      </a>
                    </p>
                  </div>
                }
              </li>
            }
          </ul>
        }

        <!-- Las metas sin programa se publican aparte y no en un cajón «otros»:
             una meta sin clasificar es la que hay que clasificar. Solo con el
             árbol a la vista: sin ramas, «no aparecen en ninguna rama» no le
             dice nada a nadie. Igual entran en el total de la franja. -->
        @if (mostrarArbol && d.sin_clasificar.length) {
          <p class="sin-clasificar">
            <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
            {{ d.sin_clasificar.length }}
            {{ d.sin_clasificar.length === 1 ? 'meta no está clasificada' : 'metas no están clasificadas' }}
            bajo ningún objetivo del Plan, así que no aparecen en ninguna rama.
          </p>
        }

        <p class="fuente">{{ d.fuente }} · contraste: {{ d.contraste }}</p>
      }
    </section>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    :host { display: block; }
    .arbol { margin-top: $space-5; }
    .arbol__head {
      display: flex; flex-wrap: wrap; gap: $space-3;
      align-items: flex-end; justify-content: space-between;
      margin-bottom: $space-3;
    }
    .arbol__titulo {
      margin: 0; font-size: $font-size-lg; color: $color-text;
      i { color: $color-primary; margin-right: $space-1; }
    }
    .arbol__sub { margin: $space-1 0 0; color: $color-text-muted; font-size: $font-size-sm; max-width: 68ch; }
    .arbol__acciones { display: flex; gap: $space-2; align-items: center; flex-wrap: wrap; }
    .muted { color: $color-text-muted; }

    .buscador {
      display: inline-flex; align-items: center; gap: $space-1;
      border: 1px solid $color-border; border-radius: $radius-sm;
      padding: 4px 8px; background: $color-bg;
      i { color: $color-text-muted; }
      input { border: 0; outline: 0; background: transparent; min-width: 230px; font: inherit; }
    }

    .totales {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
      gap: $space-2; margin-bottom: $space-3;
      padding: $space-3; background: $color-bg-subtle; border-radius: $radius-sm;
    }
    .totales__cifra { display: flex; flex-direction: column; text-align: center; }
    .totales__cifra--ancha { grid-column: span 2; }
    .totales__n { font-size: 1.25rem; font-weight: 700; color: $color-primary; font-variant-numeric: tabular-nums; }
    .totales__l { font-size: $font-size-xs; color: $color-text-muted; }

    .rama { list-style: none; margin: 0; padding: 0; }

    .nodo {
      border-bottom: 1px solid rgba(0,0,0,.06);
      cursor: pointer;
      &:focus-visible { outline: 2px solid $color-primary; outline-offset: -2px; }
      &--meta { cursor: pointer; }
      &--resaltado > .nodo__fila { background: $color-warning-bg; }
    }
    .nodo__fila {
      display: flex; align-items: center; gap: $space-2;
      padding: 7px $space-2 7px calc(#{$space-2} + var(--sangria, 0px));
      min-height: 38px;
      &:hover { background: $color-bg-subtle; }
    }
    .nodo__flecha { width: 14px; flex: 0 0 14px; color: $color-text-muted; font-size: .75rem; }

    .nodo__chip {
      flex: 0 0 auto; padding: 1px 8px; border-radius: 999px;
      font-size: .72rem; font-weight: 700; font-variant-numeric: tabular-nums;
      background: rgba(0,0,0,.06); color: $color-text;
    }
    .nodo--objetivo .nodo__chip { background: $color-primary; color: #fff; }
    .nodo--programa .nodo__chip { background: $color-info-bg; color: $color-info-hondo; }
    // #0D9488 daba 3,17:1 sobre este fondo — por debajo de AA. El teal hondo
    // sube a 6,4:1 y se mantiene en hover.
    .nodo--proyecto .nodo__chip { background: rgba(13,148,136,.14); color: #115E59; }

    .nodo__nombre {
      flex: 1 1 auto; min-width: 0; font-size: $font-size-sm;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .nodo--objetivo .nodo__nombre { font-weight: 700; }
    .nodo--programa .nodo__nombre { font-weight: 600; }
    .nodo--meta .nodo__nombre { color: $color-text-muted; white-space: normal; }

    .nodo__hijos {
      // $color-text-muted daba 4,32:1: pasa AA para texto normal pero NO
      // para este tamaño. El neutro 600 sube a 6,75:1.
      flex: 0 0 auto; font-size: $font-size-xs; color: $color-neutral-600;
      background: rgba(0,0,0,.05); border-radius: 999px; padding: 0 7px;
    }

    .nodo__avance { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
    .barra { width: 68px; height: 7px; border-radius: 999px; background: rgba(0,0,0,.09); overflow: hidden; }
    .barra__f { display: block; height: 100%; border-radius: 999px; min-width: 2px; transition: width .3s ease; }
    .barra__f--alto { background: $color-success; }
    .barra__f--medio { background: $color-warning; }
    .barra__f--bajo { background: $color-danger; }
    .barra__f--nulo { background: transparent; }

    .nodo__pct {
      flex: 0 0 auto; min-width: 48px; text-align: right;
      font-variant-numeric: tabular-nums; font-size: $font-size-sm;
    }
    .nodo__pct--meta { color: $color-text-muted; }
    .nodo__plata {
      flex: 0 0 auto; min-width: 96px; text-align: right;
      font-variant-numeric: tabular-nums; font-size: $font-size-sm; color: $color-text-muted;
    }

    .pastilla {
      flex: 0 0 auto; padding: 1px 8px; border-radius: 999px;
      font-size: .68rem; font-weight: 600; white-space: nowrap;
      &--rojo { background: $color-danger-bg; color: $color-danger-hondo; }
      &--amarillo { background: $color-warning-bg; color: $color-warning-hondo; }
      &--verde { background: $color-success-bg; color: $color-success-hondo; }
      &--gris { background: rgba(0,0,0,.06); color: $color-text-muted; }
    }

    .detalle {
      padding: $space-2 $space-3 $space-3 calc(#{$space-3} + var(--sangria, 0px));
      background: $color-bg-subtle; cursor: default;
    }
    .detalle__campos {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: $space-2; margin: 0 0 $space-2;
      dt { font-size: $font-size-xs; color: $color-text-muted; }
      dd { margin: 0; font-size: $font-size-sm; font-variant-numeric: tabular-nums; }
      small { color: $color-text-muted; margin-left: 3px; }
    }
    .mono { font-variant-numeric: tabular-nums; }
    .detalle__espejo {
      margin: 0 0 $space-2; font-size: $font-size-xs; color: $color-text-muted;
      &--falta { color: $color-warning-hondo; }
    }
    .detalle__enlaces {
      margin: 0; display: flex; gap: $space-3; flex-wrap: wrap;
      a { font-size: $font-size-sm; color: $color-primary; }
    }

    .sin-hallazgo, .sin-clasificar, .fuente {
      font-size: $font-size-sm; color: $color-text-muted;
    }
    .sin-clasificar {
      margin-top: $space-3; padding: $space-2 $space-3;
      background: $color-warning-bg; color: $color-warning-hondo;
      border-radius: $radius-sm;
    }
    .fuente { margin-top: $space-3; font-size: $font-size-xs; }

    // ── Teléfono ──────────────────────────────────────────────────────
    // Se esconde la plata antes que el avance: en una pantalla angosta la
    // pregunta que sobrevive es «cómo va», no «cuánto cuesta».
    @media (max-width: 760px) {
      .nodo__plata { display: none; }
      .arbol__acciones { width: 100%; }
      .buscador { flex: 1 1 auto; input { min-width: 0; width: 100%; } }
    }
    @media (max-width: 520px) {
      .barra { width: 38px; }
      .nodo__hijos { display: none; }
      .totales__cifra--ancha { grid-column: span 3; }
    }
  `],
})
export class PlanArbolComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  datos = signal<PlanArbol | null>(null);
  cargando = signal(true);
  error = signal<ErrorDeCarga | null>(null);

  /** Ids expandidos. Arranca solo con los objetivos, como pidió el encargo. */
  private expandidos = signal<Set<string>>(new Set());
  /** Ids que el buscador encontró. Se resaltan; su rama se abre. */
  private hallazgos = signal<Set<string>>(new Set());
  nHallazgos = computed(() => this.hallazgos().size);
  /** Lo que el funcionario abrió A MANO, aparte de lo que abre el buscador. */
  private manual = signal<Set<string>>(new Set());
  /** El nodo que tiene el foco del teclado. Solo ése es tabulable. */
  foco = signal<string>('');

  /**
   * El foco, replegado a un nodo que EXISTA en la lista visible.
   *
   * `foco` guarda un id que puede dejar de pintarse: al colapsar, o al buscar
   * —que reemplaza qué está abierto—. Si el `tabindex` dependiera del signal
   * crudo, ningún nodo quedaría en `0` y el árbol ENTERO saldría del recorrido
   * con Tab: no se pierde un nodo, se pierden los 135 y no hay forma de volver
   * a entrar sin ratón.
   *
   * Como los ids son rutas (`o:1/p:5/pr:2688/m:100020`), el repliegue natural
   * es el ancestro visible más cercano; si tampoco está, el primer nodo.
   * Derivarlo acá cubre a `colapsarTodo()`, a `buscar()` y a cualquier futuro
   * escritor de `expandidos`, en vez de parchear cada uno.
   */
  focoVisible = computed<string>(() => {
    const filas = this.filas();
    if (!filas.length) return '';
    const vivos = new Set(filas.map(f => f.id));
    const actual = this.foco();
    if (vivos.has(actual)) return actual;
    const partes = actual.split('/');
    while (partes.length > 1) {
      partes.pop();
      const ancestro = partes.join('/');
      if (vivos.has(ancestro)) return ancestro;
    }
    return filas[0].id;
  });
  consulta = '';

  /** El árbol aplanado a una sola lista, respetando qué está abierto. */
  filas = computed<Fila[]>(() => {
    const d = this.datos();
    if (!d) return [];
    const abierto = this.expandidos();
    const out: Fila[] = [];

    d.objetivos.forEach((o, io) => {
      const idO = `o:${o.codigo}`;
      out.push({
        id: idO, nivel: 'objetivo', profundidad: 0, padre: null,
        codigo: String(o.codigo), nombre: o.nombre,
        hijos: o.n_programas, resumen: o.resumen,
        pos: io + 1, total: d.objetivos.length,
      });
      if (!abierto.has(idO)) return;

      o.programas.forEach((p, ip) => {
        const idP = `${idO}/p:${p.codigo}`;
        out.push({
          id: idP, nivel: 'programa', profundidad: 1, padre: idO,
          codigo: String(p.codigo), nombre: p.nombre,
          hijos: p.n_proyectos, resumen: p.resumen,
          pos: ip + 1, total: o.programas.length,
        });
        if (!abierto.has(idP)) return;

        p.proyectos.forEach((pr, ipr) => {
          const idPr = `${idP}/pr:${pr.codigo}`;
          out.push({
            id: idPr, nivel: 'proyecto', profundidad: 2, padre: idP,
            codigo: pr.codigo, nombre: pr.nombre,
            hijos: pr.n_metas, resumen: pr.resumen, proyecto: pr,
            pos: ipr + 1, total: p.proyectos.length,
          });
          if (!abierto.has(idPr)) return;

          pr.metas.forEach((m, im) => {
            out.push({
              id: `${idPr}/m:${m.codigo}`, nivel: 'meta', profundidad: 3,
              padre: idPr, codigo: m.codigo_meta || '—', nombre: m.nombre,
              hijos: null, meta: m,
              pos: im + 1, total: pr.metas.length,
            });
          });
        });
      });
    });
    return out;
  });

  // ── Estado ─────────────────────────────────────────────────────────

  /** Ver el porqué en el comentario de `MOSTRAR_ARBOL`. */
  mostrarArbol = MOSTRAR_ARBOL;

  abierto(id: string): boolean { return this.expandidos().has(id); }

  /**
   * ¿Este nodo se abre? Un nodo con hijos, sí — y una META también, porque
   * despliega su panel de detalle.
   *
   * Estaba preguntando por `f.hijos`, así que la meta se dibujaba sin flecha y
   * se anunciaba como hoja, pero el clic la abría igual y `→` no hacía nada.
   * Un solo predicado para el ARIA, el chevron y el teclado.
   */
  desplegable(f: Fila): boolean { return !!f.hijos || !!f.meta; }
  resaltado(id: string): boolean { return this.hallazgos().has(id); }
  ayuda(nivel: string): string { return QUE_ES[nivel] ?? ''; }

  alternar(f: Fila): void {
    this.foco.set(f.id);
    const s = new Set(this.expandidos());
    const m = new Set(this.manual());
    if (s.has(f.id)) { s.delete(f.id); m.delete(f.id); } else { s.add(f.id); m.add(f.id); }
    this.expandidos.set(s);
    // Se guarda aparte lo abierto a mano: así el buscador puede sumar su rama
    // sin borrar el trabajo del funcionario, y borrar el texto lo devuelve.
    this.manual.set(m);
  }

  colapsarTodo(): void {
    this.consulta = '';
    this.hallazgos.set(new Set());
    this.expandidos.set(new Set());
    this.manual.set(new Set());
  }

  // ── Buscador: expande la rama del hallazgo y la resalta ────────────

  buscar(texto: string): void {
    const q = (texto || '').trim().toLowerCase();
    if (!q) {
      // Borrar el texto devuelve lo que estaba abierto antes de buscar, no
      // deja el árbol como lo dejó la última búsqueda.
      this.hallazgos.set(new Set());
      this.expandidos.set(new Set(this.manual()));
      return;
    }
    const d = this.datos();
    if (!d) return;

    const encontrados = new Set<string>();
    const abrir = new Set<string>();
    const mira = (s: string | null | undefined) =>
      !!s && s.toLowerCase().includes(q);
    const qProy = q.replace(/^0+/, '') || q;

    for (const o of d.objetivos) {
      const idO = `o:${o.codigo}`;
      if (mira(o.nombre) || mira(String(o.codigo))) encontrados.add(idO);

      for (const p of o.programas) {
        const idP = `${idO}/p:${p.codigo}`;
        if (mira(p.nombre) || mira(String(p.codigo))) {
          encontrados.add(idP);
          abrir.add(idO);
        }
        for (const pr of p.proyectos) {
          const idPr = `${idP}/pr:${pr.codigo}`;
          // El código sin ceros a la izquierda, como lo normaliza el backend:
          // «0002377» y «2377» son el mismo proyecto.
          if (mira(pr.nombre) || mira(pr.codigo)
              || (!!pr.codigo && pr.codigo.replace(/^0+/, '').toLowerCase().includes(qProy))) {
            encontrados.add(idPr);
            abrir.add(idO); abrir.add(idP);
          }
          for (const m of pr.metas) {
            // También la alerta, que es lo único que la pantalla pinta y el
            // buscador no miraba.
            if (mira(m.nombre) || mira(m.codigo_meta) || mira(m.sector)
                || mira(m.alerta)) {
              encontrados.add(`${idPr}/m:${m.codigo}`);
              // La rama entera, para que el hallazgo se VEA y no quede
              // escondido bajo un nodo cerrado.
              abrir.add(idO); abrir.add(idP); abrir.add(idPr);
            }
          }
        }
      }
    }
    this.hallazgos.set(encontrados);
    // FUSIONA, no reemplaza: una búsqueda sin resultados dejaba colapsado, en
    // silencio, todo lo que el funcionario tenía abierto.
    this.expandidos.set(new Set([...this.manual(), ...abrir]));
  }

  // ── Teclado: el patrón ARIA de árbol ───────────────────────────────

  teclado(ev: KeyboardEvent, f: Fila): void {
    const filas = this.filas();
    const i = filas.findIndex(x => x.id === f.id);
    const mover = (j: number) => {
      const destino = filas[j];
      if (!destino) return;
      this.foco.set(destino.id);
      (document.querySelector(`[data-nodo="${destino.id}"]`) as HTMLElement | null)?.focus();
      ev.preventDefault();
    };

    switch (ev.key) {
      case 'ArrowDown': mover(i + 1); break;
      case 'ArrowUp': mover(i - 1); break;
      case 'ArrowRight':
        if (this.desplegable(f) && !this.abierto(f.id)) { this.alternar(f); ev.preventDefault(); }
        else mover(i + 1);
        break;
      case 'ArrowLeft':
        if (this.desplegable(f) && this.abierto(f.id)) { this.alternar(f); ev.preventDefault(); }
        else if (f.padre) {
          const j = filas.findIndex(x => x.id === f.padre);
          if (j >= 0) mover(j);
        }
        break;
      case 'Enter':
      case ' ':
        this.alternar(f);
        ev.preventDefault();
        break;
      case 'Home': mover(0); break;
      case 'End': mover(filas.length - 1); break;
    }
  }

  // ── Formato ────────────────────────────────────────────────────────

  mm(v: number | null | undefined): string { return enMillones(v); }

  /** `null` es «sin dato», y se dice así: un «0 %» afirma que no avanzó. */
  pct(v: number | null | undefined): string {
    return v === null || v === undefined ? '—' : `${v} %`;
  }

  ancho(v: number | null | undefined): number {
    return v === null || v === undefined ? 0 : Math.max(0, Math.min(100, v));
  }

  nivelAvance(v: number | null | undefined): 'alto' | 'medio' | 'bajo' | 'nulo' {
    if (v === null || v === undefined) return 'nulo';
    return v >= 80 ? 'alto' : v >= 50 ? 'medio' : 'bajo';
  }

  balde(alerta: string | null): 'rojo' | 'amarillo' | 'verde' | 'gris' {
    return (alerta && BALDE[alerta]) || 'gris';
  }

  /** La regla, dicha donde se ve el número. */
  tituloAvance(r: ObjetivoNodo['resumen']): string {
    const anio = r.avance.vigencia ? ` (${r.avance.vigencia})` : '';
    const base = `${r.avance.regla}${anio} · ${r.avance.metas_medidas} de ${r.n_metas} medidas`;
    return r.avance.metas_sin_medir
      ? `${base}. Las ${r.avance.metas_sin_medir} sin medir NO cuentan como cero.`
      : base;
  }

  /** «2025-2026», o «2026» si es un solo año, o cadena vacía si no hay dato. */
  rango(p: { vigencia_desde: number | null; vigencia_hasta: number | null }): string {
    const { vigencia_desde: a, vigencia_hasta: b } = p;
    if (a === null || b === null) return '';
    return a === b ? `· ${a}` : `· ${a}-${b}`;
  }

  tituloPlata(r: ObjetivoNodo['resumen']): string {
    const p = r.plata;
    const r2 = this.rango(p).replace('· ', '');
    return `Apropiado ${this.mm(p.apropiacion)} · comprometido ${this.mm(p.comprometido)}`
         + ` · girado ${this.mm(p.girado)}` + (r2 ? ` · vigencias ${r2}` : '');
  }

  async ngOnInit(): Promise<void> {
    try {
      const r = await firstValueFrom(this.http.get<PlanArbol>(
        this.cfg.url('/dashboard/api/v2/presupuesto/plan-oficial/')));
      this.datos.set(r);
      // Arranca con los objetivos a la vista y todo lo demás cerrado.
      if (r?.objetivos?.length) this.foco.set(`o:${r.objetivos[0].codigo}`);
    } catch (e: any) {
      this.error.set(errorDeCarga(e, 'el Plan'));
    } finally {
      this.cargando.set(false);
    }
  }
}
