import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  AfterViewInit, ChangeDetectionStrategy, Component, ElementRef,
  OnDestroy, OnInit, ViewChild, computed, effect, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import * as L from 'leaflet';
import { Subject, debounceTime, forkJoin } from 'rxjs';

Chart.register(...registerables);
import { LayoutService } from '../../core/layout/layout.service';
import {
  CaiProps, ColegioProps, ConteoSubgrupo, EscuelaActividad, EscuelaProps,
  EventoFiltros, FeatureCollection, GeoFeature, GeoService, SubgrupoLite,
  TipoEventoLite,
} from '../../core/geo/geo.service';
import { formatFecha, tipoEventoNombre } from '../../shared/format/format.util';

/** Cómo le fue a una capa en su última carga. */
type EstadoCapa = 'cargando' | 'ok' | 'error' | 'sesion' | 'vacia';

/** Una disciplina lista para pintar en el popup, ya con los "faltan" resueltos. */
interface DisciplinaSede {
  escuela: string;
  actividad: string;
  horarios: string;
  edades: string;
  contactoLabel: string;
  contacto: string;
}

/**
 * Una SEDE: el punto físico. 27 direcciones tienen más de una escuela y hoy se
 * pintan una encima de otra — acá se agrupan y el popup lista todo lo que se
 * dicta en ese punto.
 */
interface SedeEscuela {
  lat: number;
  lng: number;
  tipo: 'Cultura' | 'Deporte';
  nombre: string;
  otrosNombres: string[];
  direccion: string;
  upz: string;
  upzFuente: string | null;
  barrio: string;
  barrioFuente: string | null;
  disciplinas: DisciplinaSede[];
  avisos: string[];
  /** El punto es el de respaldo (Alcaldía), no el de la sede. */
  aproximada: boolean;
  /** Por qué no tiene punto propio: lo que hay que hacer para arreglarlo. */
  motivo: 'sin_direccion' | 'direccion_no_ubicada' | null;
  /** Punto real, pero fuera del contorno de la localidad. */
  fueraDeKennedy: boolean;
}

/**
 * Mapa Kennedy en Angular nativo con Leaflet.
 *
 * Reemplaza el iframe al Django legacy. Consume:
 *   GET /geo/api/mapa/catalogos/   — UPZ, Barrios, Tipos, Dep, Subgrupo, N18
 *   GET /geo/api/eventos/?...      — FeatureCollection eventos
 *   GET /geo/api/kennedy/contorno/ — polígono localidad
 *   GET /geo/api/kennedy/upz/      — polígonos UPZ
 *   GET /geo/api/kennedy/barrios/  — polígonos barrios
 *   GET /geo/api/kennedy/parques/  — polígonos parques
 */
@Component({
  standalone: true,
  selector: 'app-mapa-kennedy',
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- Esta ruta va SIN LayoutComponent (app.routes.ts), que es donde viven el
         skip-link y el <main> de toda la app. Sin repetirlos acá, /app/mapa
         queda sin landmarks y sin forma de saltarse el panel de filtros: para
         alguien que navega con teclado eso son decenas de tabuladas antes de
         llegar al mapa. -->
    <a class="ui-skip-link" href="#contenido-mapa">Saltar al mapa</a>
    <div class="mapa">
      <header class="mapa__header">
        <div>
          <h1>Mapa de Kennedy</h1>
          <p class="mapa__subtitle">
            Eventos, parques, escuelas y barrios georreferenciados.
            <span class="mapa__count">{{ eventos().features.length }} eventos visibles</span>
          </p>
        </div>
        <div class="mapa__kpis">
          <div class="mapa-kpi">
            <span class="mapa-kpi__value">{{ eventos().features.length }}</span>
            <span class="mapa-kpi__label">Eventos</span>
          </div>
          <div class="mapa-kpi">
            <span class="mapa-kpi__value">{{ kpiHoy() }}</span>
            <span class="mapa-kpi__label">Hoy</span>
          </div>
          <div class="mapa-kpi">
            <span class="mapa-kpi__value">{{ kpiProximos() }}</span>
            <span class="mapa-kpi__label">Próximos</span>
          </div>
        </div>
      </header>

      <div class="mapa__body">
        <aside class="mapa-side" aria-label="Filtros y capas del mapa">
          <section class="mapa-side__section">
            <h2>Filtros</h2>

            <div class="mapa-field">
              <span class="mapa-field__label">Tipo de evento</span>
              <div class="mapa-chips" role="group" aria-label="Tipo de evento">
                @for (t of catalogos()?.tipos_evento ?? []; track t.codigo) {
                  <button type="button" class="mapa-chip"
                          [class.mapa-chip--on]="selectedTipos.includes(t.codigo)"
                          [attr.aria-pressed]="selectedTipos.includes(t.codigo)"
                          (click)="toggleTipo(t.codigo)">
                    <span class="mapa-chip__dot" [style.background]="t.color_hex"></span>
                    {{ t.nombre }}
                  </button>
                } @empty {
                  <span class="mapa-field__hint">Sin tipos.</span>
                }
              </div>
            </div>

            <label class="mapa-field">
              <span>Dependencia</span>
              <select [(ngModel)]="selectedDependencia" (change)="onDependenciaChange()">
                <option [ngValue]="null">— Todas —</option>
                @for (d of catalogos()?.dependencias ?? []; track d.id) {
                  <option [ngValue]="d.id">{{ d.nombre }}</option>
                }
              </select>
            </label>

            <div class="mapa-field">
              <span class="mapa-field__label">Subgrupo</span>
              <div class="mapa-chips" role="group" aria-label="Subgrupo">
                @for (s of subgruposFiltrados(); track s.id) {
                  <button type="button" class="mapa-chip"
                          [class.mapa-chip--on]="selectedSubgrupos.includes(s.id)"
                          [attr.aria-pressed]="selectedSubgrupos.includes(s.id)"
                          (click)="toggleSubgrupo(s.id)">
                    {{ s.nombre }}
                  </button>
                } @empty {
                  <span class="mapa-field__hint">Sin subgrupos.</span>
                }
              </div>
            </div>

            <label class="mapa-field">
              <span>Buscar</span>
              <input type="search" [(ngModel)]="query" (input)="onBuscar()"
                     placeholder="Nombre, dirección, dependencia…">
            </label>

            <div class="mapa-side__actions">
              <button class="ui-btn ui-btn--sm ui-btn--ghost" type="button"
                      (click)="limpiarFiltros()">Limpiar</button>
            </div>
          </section>

          <section class="mapa-side__section">
            <h2>Capas</h2>
            <!-- Acá vivía un checkbox por cada tipo de evento (Banco, Curso,
                 Estímulo…). Era el MISMO catálogo que los chips de "Tipo de
                 evento" en Filtros, pero por otra vía: los chips filtran en el
                 servidor y estos escondían en el navegador. Con los dos podías
                 filtrar "Curso" arriba, destildar "Curso" acá y no ver nada sin
                 que nada lo explicara. Retirado por decisión de Alex 2026-07-16:
                 el tipo de evento se filtra en Filtros, y punto. -->
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.parques" (change)="toggleCapa('parques')">
              <span class="mapa-poly mapa-poly--parque"></span> Parques
              @if (mensajeCapa('parques')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('parques')"
                      role="status">{{ mensajeCapa('parques') }}</span>
              }
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.barrios" (change)="toggleCapa('barrios')">
              <span class="mapa-poly mapa-poly--barrio"></span> Barrios
              @if (mensajeCapa('barrios')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('barrios')"
                      role="status">{{ mensajeCapa('barrios') }}</span>
              }
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.upz" (change)="toggleCapa('upz')">
              <span class="mapa-poly mapa-poly--upz"></span> UPZ
              @if (mensajeCapa('upz')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('upz')"
                      role="status">{{ mensajeCapa('upz') }}</span>
              }
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.estratificacion" (change)="toggleCapa('estratificacion')">
              <span class="mapa-poly mapa-poly--estrato"></span> Estratificación (IDECA)
              @if (estratificacionCargando) {
                <span class="mapa-cargando" role="status">cargando…</span>
              }
              @if (mensajeCapa('estratificacion')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('estratificacion')"
                      role="status">{{ mensajeCapa('estratificacion') }}</span>
              }
            </label>
            @if (capas.estratificacion && !estratificacionCargando) {
              <!-- La leyenda ES el filtro: cada chip prende y apaga su estrato.
                   El backend ya aceptaba ?estrato= repetido y nadie lo usaba;
                   pedir 2 estratos baja la capa de ~5.000 manzanas a ~500. -->
              <div class="mapa-estrato-leyenda" role="group"
                   aria-label="Filtrar manzanas por estrato socioeconómico">
                @for (it of estratoLeyenda; track it.e) {
                  <button type="button" class="mapa-estrato-chip"
                          [class.mapa-estrato-chip--off]="!estratoVisible(it.e)"
                          [attr.aria-pressed]="estratoVisible(it.e)"
                          (click)="toggleEstrato(it.e)">
                    <span class="mapa-estrato-dot" [style.background]="colorEstrato(it.e)"></span>
                    {{ it.label }}
                  </button>
                }
              </div>
              <p class="mapa-estrato-ayuda">
                {{ resumenEstratos() }}
                @if (!todosLosEstratos()) {
                  <button type="button" class="mapa-estrato-reset" (click)="mostrarTodosLosEstratos()">
                    Ver todos
                  </button>
                }
              </p>
            }
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.banco" (change)="toggleCapa('banco')">
              <span class="mapa-dot mapa-dot--banco"></span> Iniciativas del Banco (Deporte)
              @if (mensajeCapa('banco')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('banco')"
                      role="status">{{ mensajeCapa('banco') }}</span>
              }
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.localidad" (change)="toggleCapa('localidad')">
              <span class="mapa-line mapa-line--localidad"></span> Localidad
              @if (mensajeCapa('localidad')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('localidad')"
                      role="status">{{ mensajeCapa('localidad') }}</span>
              }
            </label>
            <!-- Acá vivía "Oferta formativa (cursos por sede)". Retirada el
                 2026-08-05: la capa agrupa cursos por la columna escuela_id del
                 evento, que está en NULL en el 100% de los eventos, así que el
                 endpoint siempre devolvía cero burbujas. Era un checkbox que no
                 podía pintar nada — el usuario lo marcaba, no pasaba nada y no
                 había forma de saber si estaba roto o vacío. Vuelve cuando los
                 cursos se enganchen a su sede, no antes. -->
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.festivales" (change)="toggleCapa('festivales')">
              <span class="mapa-festival-dot">★</span> Festivales
              @if (mensajeCapa('festivales')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('festivales')"
                      role="status">{{ mensajeCapa('festivales') }}</span>
              }
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.colegios" (change)="toggleCapa('colegios')">
              <span class="mapa-colegio-dot">🎓</span> Colegios distritales
              @if (mensajeCapa('colegios')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('colegios')"
                      role="status">{{ mensajeCapa('colegios') }}</span>
              }
            </label>
            @if (capas.colegios && resumenColegios()) {
              <div class="mapa-capa-resumen" role="status">
                {{ resumenColegios() }}
              </div>
            }
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.cai" (change)="toggleCapa('cai')">
              <span class="mapa-cai-dot">🛡</span> CAI (Policía)
              @if (mensajeCapa('cai')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('cai')"
                      role="status">{{ mensajeCapa('cai') }}</span>
              }
            </label>
            @if (capas.cai) {
              <!-- La distinción fijo/móvil es el punto de la capa: un puesto
                   permanente al que la gente puede llegar no es lo mismo que
                   una unidad que hoy está aquí y mañana no. -->
              <div class="mapa-cai-leyenda" aria-label="Leyenda de tipos de CAI">
                <span class="mapa-cai-chip">
                  <span class="mapa-cai-dot mapa-cai-dot--fijo">🛡</span> Fijo
                </span>
                <span class="mapa-cai-chip">
                  <span class="mapa-cai-dot mapa-cai-dot--movil">🚓</span> Móvil
                </span>
              </div>
              @if (resumenCai()) {
                <div class="mapa-capa-resumen" role="status">{{ resumenCai() }}</div>
              }
            }
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.tramosViales" (change)="toggleCapa('tramosViales')">
              <span class="mapa-line mapa-line--obra"></span> Malla vial / obras
              @if (mensajeCapa('tramosViales')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('tramosViales')"
                      role="status">{{ mensajeCapa('tramosViales') }}</span>
              }
            </label>
            <label class="mapa-layer">
              <input type="checkbox" [(ngModel)]="capas.parquesObras" (change)="toggleCapa('parquesObras')">
              <span class="mapa-obra-dot">🌳</span> Parques (obras)
              @if (mensajeCapa('parquesObras')) {
                <span class="mapa-layer__estado"
                      [class.mapa-layer__estado--problema]="esCapaProblema('parquesObras')"
                      role="status">{{ mensajeCapa('parquesObras') }}</span>
              }
            </label>

            @if (capas.tramosViales || capas.parquesObras) {
              <div class="mapa-avance-leyenda" aria-label="Leyenda por porcentaje de avance">
                <span class="mapa-avance-chip">
                  <span class="mapa-avance-dot mapa-avance-dot--rojo"></span> 0% (sin iniciar)
                </span>
                <span class="mapa-avance-chip">
                  <span class="mapa-avance-dot mapa-avance-dot--ambar"></span> Parcial
                </span>
                <span class="mapa-avance-chip">
                  <span class="mapa-avance-dot mapa-avance-dot--verde"></span> 100% (terminado)
                </span>
              </div>
            }
            <hr>
            <small class="mapa-side__hint">
              El equipamiento (escenarios de
              Cultura y Deporte) se muestra según el subgrupo seleccionado
              arriba del mapa.
            </small>
          </section>
        </aside>

        <main id="contenido-mapa" class="mapa-canvas" tabindex="-1">
          <!-- Esto NO es un tablist.
               Lo declaraba, pero a medias: los hijos no tenían role="tab" ni
               aria-selected y no existía ningún tabpanel, así que anunciaba un
               patrón que no cumplía — peor que no declarar nada. Y de fondo no
               son pestañas: son filtros excluyentes que recargan el mapa. Como
               grupo de botones con aria-pressed queda igual a los chips de
               arriba, que ya funcionan así en esta misma página. -->
          @if (subgruposInversion().length) {
            <div class="mapa-tabs" role="group" aria-label="Filtrar por subgrupo de Inversión Local">
              <button class="mapa-tab" type="button"
                      [class.mapa-tab--active]="!subgrupoTab()"
                      [attr.aria-pressed]="!subgrupoTab()"
                      (click)="setSubgrupoTab(null)">Todos</button>
              @for (s of subgruposInversion(); track s.id) {
                <button class="mapa-tab" type="button"
                        [class.mapa-tab--active]="subgrupoTab() === s.id"
                        [attr.aria-pressed]="subgrupoTab() === s.id"
                        (click)="setSubgrupoTab(s.id)"
                        [title]="s.nombre">
                  {{ s.nombre }}
                  @if (conteosSubgrupo()[s.id]; as c) {
                    <span class="mapa-tab__count">
                      {{ c.total }}
                      <span class="ui-sr-only">actividades</span>
                    </span>
                  }
                </button>
              }
            </div>
          }
          <div #mapEl class="mapa-leaflet"
               role="application"
               aria-label="Mapa de Kennedy. Use las flechas para desplazarse y las teclas más y menos para acercar o alejar. El listado de actividades bajo el mapa tiene la misma información en forma de tabla."></div>
          @if (loading()) {
            <div class="mapa-loading" role="status" aria-live="polite">Cargando datos…</div>
          }
          @if (errorMsg()) {
            <div class="mapa-error" role="alert">
              <span class="mapa-error__texto">{{ errorMsg() }}</span>
              <button type="button" class="mapa-error__cerrar"
                      aria-label="Cerrar el mensaje de error"
                      (click)="errorMsg.set('')">×</button>
            </div>
          }
          <!-- Cero resultados dejaba el mapa en blanco sin una palabra. Un mapa
               vacío se lee como "está roto", no como "no hay nada que cumpla lo
               que pediste". -->
          @if (!loading() && !errorMsg() && !eventosFiltrados().length) {
            <div class="mapa-vacio" role="status">
              <p><strong>Ninguna actividad coincide con los filtros.</strong></p>
              <p>Prueba quitando algún filtro o ampliando la búsqueda.</p>
              <button type="button" class="ui-btn ui-btn--sm"
                      (click)="limpiarFiltros()">Quitar todos los filtros</button>
            </div>
          }
        </main>
      </div>

      <section class="mapa-stats">
        <button type="button" class="mapa-stats__head"
                [attr.aria-expanded]="statsAbierto()"
                aria-controls="panel-analisis"
                (click)="statsAbierto.set(!statsAbierto())">
          <h2>Análisis de actividades
            <small>· {{ eventosFiltrados().length }} en vista</small></h2>
          <span class="mapa-stats__chevron" aria-hidden="true">
            {{ statsAbierto() ? '▲' : '▼' }}
          </span>
        </button>
        @if (statsAbierto()) {
          <div id="panel-analisis">
          <div class="mapa-stats__kpis">
            <article class="stat-card stat-card--total">
              <span class="stat-card__value">{{ eventosFiltrados().length }}</span>
              <span class="stat-card__label">En vista</span>
            </article>
            <article class="stat-card stat-card--ok">
              <span class="stat-card__value">{{ statKpis().ejecutados }}</span>
              <span class="stat-card__label">Ejecutados</span>
            </article>
            <article class="stat-card stat-card--soon">
              <span class="stat-card__value">{{ statKpis().proximos }}</span>
              <span class="stat-card__label">Próximos</span>
            </article>
            <article class="stat-card stat-card--carac">
              <span class="stat-card__value">{{ statKpis().conKpi }}</span>
              <span class="stat-card__label">Con KPI</span>
            </article>
          </div>
          <!-- Un <canvas> es opaco para un lector de pantalla: sin role ni
               aria-label solo se anuncia el <h3> de al lado. El texto alternativo
               remite a la tabla de abajo, que ES la misma información en una
               forma que sí se puede leer. -->
          <div class="mapa-stats__charts">
            <div class="chart-box">
              <h3 id="chart-tipo-titulo">Por tipo de actividad</h3>
              <canvas #chartTipo role="img" aria-labelledby="chart-tipo-titulo"
                      aria-describedby="charts-alternativa"></canvas>
            </div>
            <div class="chart-box">
              <h3 id="chart-sub-titulo">Por subgrupo (top 8)</h3>
              <canvas #chartSub role="img" aria-labelledby="chart-sub-titulo"
                      aria-describedby="charts-alternativa"></canvas>
            </div>
            <div class="chart-box chart-box--wide">
              <h3 id="chart-mes-titulo">Evolución mensual</h3>
              <canvas #chartMes role="img" aria-labelledby="chart-mes-titulo"
                      aria-describedby="charts-alternativa"></canvas>
            </div>
          </div>
          <p id="charts-alternativa" class="ui-sr-only">
            Estos gráficos resumen las mismas actividades que lista la tabla
            "Actividades en el mapa", más abajo en esta página.
          </p>
          </div>
        }
      </section>

      <section class="mapa-table" aria-labelledby="tabla-actividades-titulo">
        <h2 id="tabla-actividades-titulo">Actividades en el mapa
          <span class="mapa-table__count">({{ eventosFiltrados().length }})</span>
        </h2>
        <p class="mapa-table__ayuda">
          Selecciona una fila para centrar el mapa en esa actividad.
        </p>
        <div class="mapa-table__wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Fecha</th>
                <th scope="col">Tipo</th>
                <th scope="col">Dependencia</th>
                <th scope="col">Dirección</th>
              </tr>
            </thead>
            <tbody>
              <!-- La fila centra el mapa, así que es un control y tiene que
                   alcanzarse con Tab y dispararse con Enter/Espacio. Es el
                   mismo patrón que ya usan infra-panel y festivales-list. -->
              @for (f of eventosFiltrados(); track f.properties.id) {
                <tr class="mapa-table__row"
                    role="button" tabindex="0"
                    [attr.aria-label]="'Centrar el mapa en ' + (f.properties.nombre || 'esta actividad')"
                    (click)="centrar(f)"
                    (keyup.enter)="centrar(f)"
                    (keyup.space)="centrar(f)">
                  <td>{{ f.properties.nombre || '—' }}</td>
                  <td>{{ fechaLegible(f.properties.fecha_inicio) }}</td>
                  <td>
                    <span class="mapa-pill"
                          [style.background]="colorTipo(f.properties.tipo_evento_codigo)"
                          [style.color]="textoSobre(colorTipo(f.properties.tipo_evento_codigo))">
                      {{ tipoNombre(f.properties.tipo_evento_codigo) }}
                    </span>
                  </td>
                  <td>{{ f.properties.dependencia || '—' }}</td>
                  <td>{{ f.properties.direccion || '—' }}</td>
                </tr>
              } @empty {
                <tr><td colspan="5" class="mapa-table__empty">
                  No hay eventos que coincidan con los filtros.
                </td></tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      <!-- Mismo criterio que con las escuelas: lo que no se puede ubicar se
           CUENTA, no se disimula. Estas sí se pintan (en la sede de la
           Alcaldía, que es el respaldo del backend), y justamente por eso hay
           que decir en voz alta que ese punto no es donde ocurrieron. -->
      @if (eventosSinUbicacionReal().length) {
        <section class="mapa-faltantes mapa-faltantes--aprox">
          <button type="button" class="mapa-faltantes__head"
                  [attr.aria-expanded]="sinUbicacionAbierto()"
                  aria-controls="panel-sin-ubicacion"
                  (click)="sinUbicacionAbierto.set(!sinUbicacionAbierto())">
            <h2>
              Actividades sin ubicación registrada
              <small>· {{ eventosSinUbicacionReal().length }} de {{ eventosFiltrados().length }} en vista</small>
            </h2>
            <span class="mapa-faltantes__chevron" aria-hidden="true">
              {{ sinUbicacionAbierto() ? '▲' : '▼' }}
            </span>
          </button>
          @if (sinUbicacionAbierto()) {
            <div id="panel-sin-ubicacion">
              <p class="mapa-faltantes__hint">
                No tienen dirección propia en el sistema, así que se muestran en
                la sede de la Alcaldía y con el borde punteado. <strong>El punto
                del mapa no es el lugar donde ocurrieron.</strong> Para que
                aparezcan donde corresponde hay que registrarles la dirección en
                la actividad.
              </p>
              <div class="mapa-faltantes__wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Nombre</th>
                      <th scope="col">Subgrupo</th>
                      <th scope="col">Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (f of eventosSinUbicacionReal(); track f.properties.id) {
                      <tr>
                        <td>{{ f.properties.nombre || '—' }}</td>
                        <td>{{ f.properties.subgrupo || '—' }}</td>
                        <td>{{ fechaLegible(f.properties.fecha_inicio) }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          }
        </section>
      }

      <!-- Las escuelas sin coordenada propia se pintan en la sede de la
           Alcaldía, marcadas y desapiladas, PERO también se listan acá: en el
           mapa se ve que existen, y en esta tabla se ve qué le falta a cada
           una. Son dos preguntas distintas — "¿dónde está?" y "¿qué hay que
           conseguir para ubicarla?" — y el listado responde la segunda. -->
      @if (escuelasSinUbicacion().length) {
        <section class="mapa-faltantes">
          <button type="button" class="mapa-faltantes__head"
                  [attr.aria-expanded]="faltantesAbierto()"
                  aria-controls="panel-escuelas-sin-ubicacion"
                  (click)="faltantesAbierto.set(!faltantesAbierto())">
            <h2>
              Escuelas sin ubicación
              <small>· {{ escuelasSinUbicacion().length }} sin coordenada</small>
            </h2>
            <span class="mapa-faltantes__chevron" aria-hidden="true">
              {{ faltantesAbierto() ? '▲' : '▼' }}
            </span>
          </button>
          @if (faltantesAbierto()) {
            <div id="panel-escuelas-sin-ubicacion">
            <p class="mapa-faltantes__hint">
              Están cargadas en el sistema pero sin ubicación propia: el censo no
              trae dirección, o la que trae no se pudo resolver. En el mapa se
              muestran en la sede de la Alcaldía, con borde punteado, para que se
              vea que existen — no quedan ahí. Se listan para que el área las
              complete.
            </p>
            <div class="mapa-faltantes__wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Nombre</th>
                    <th scope="col">Tipo</th>
                    <th scope="col">Actividades</th>
                    <th scope="col">Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  @for (e of escuelasSinUbicacion(); track e.id) {
                    <tr>
                      <td>{{ e.nombre || '—' }}</td>
                      <td>{{ e.tipo || '—' }}</td>
                      <td>{{ resumenActividades(e) }}</td>
                      <td>{{ motivoSinUbicacion(e) }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            </div>
          }
        </section>
      }
    </div>
  `,
  styleUrl: './mapa.component.scss',
})
export class MapaKennedyComponent implements OnInit, AfterViewInit, OnDestroy {
  private geo = inject(GeoService);
  private layout = inject(LayoutService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  // ── C1: estado del mapa en la URL ───────────────────────────────
  /** Vista (centro/zoom) que trae la URL; si existe, gana sobre el fitBounds. */
  private vistaInicial?: { center: [number, number]; zoom: number };
  /** Conjunto de capas ON declarado por la URL (autoritativo si viene). */
  private capasInicial?: Set<string>;
  /** No se escribe la URL hasta terminar de restaurar lo que se leyó de ella. */
  private hidratado = false;
  /** Coalesce de escrituras: un solo navigate por ráfaga de pan/zoom/tecleo. */
  private urlSync$ = new Subject<void>();

  @ViewChild('mapEl', { static: false }) mapEl!: ElementRef<HTMLDivElement>;
  @ViewChild('chartTipo') private chartTipoRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartSub') private chartSubRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartMes') private chartMesRef?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];
  statsAbierto = signal<boolean>(true);
  faltantesAbierto = signal<boolean>(false);
  sinUbicacionAbierto = signal<boolean>(false);
  /** Escuelas del censo que no tienen coordenada: se listan, no se pintan. */
  escuelasSinUbicacion = signal<EscuelaProps[]>([]);

  constructor() {
    // Redibuja los gráficos cuando cambian los eventos filtrados o se abre
    // el panel. Reactivo a TODOS los filtros (signals + query).
    effect(() => {
      const feats = this.eventosFiltrados();
      if (this.statsAbierto()) {
        queueMicrotask(() => this.dibujarCharts(feats));
      }
    });

    // C1: el estado que vive en signals (panel, pestaña de subgrupo, filtro de
    // estratos) también se refleja en la URL. Los campos planos y las capas lo
    // disparan desde sus propios métodos.
    effect(() => {
      this.statsAbierto(); this.subgrupoTab(); this.estratosVisibles();
      if (this.hidratado) this.urlSync$.next();
    });

    // Un solo navigate por ráfaga: el debounce absorbe el arrastre y el tecleo.
    this.urlSync$.pipe(debounceTime(350)).subscribe(() => this.escribirUrl());
  }

  // ── Estado reactivo ─────────────────────────────────────────────
  catalogos = signal<MapaCatalogosLocal | null>(null);
  eventos = signal<FeatureCollection>({ type: 'FeatureCollection', features: [] });
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  subgrupoTab = signal<number | null>(null);
  query = '';
  selectedTipos: string[] = [];
  selectedSubgrupos: number[] = [];
  selectedDependencia: number | null = null;

  /**
   * Qué capas arrancan encendidas.
   *
   * `parques` estaba en `true` y era, con diferencia, lo más caro de abrir el
   * mapa: 554 polígonos que se descargaban antes de que el usuario tocara nada
   * y que casi nadie viene a ver. Pasó a apagada y a cargarse solo cuando se
   * marca (2026-08-05, bloque B3). Queda encendido el contorno de la localidad,
   * que es lo que le dice a alguien que llega que está mirando Kennedy.
   */
  capas = {
    parques: false, barrios: false, upz: false, localidad: true,
    escuelasCultura: false, escuelasDeporte: false,
    festivales: false,
    tramosViales: false, parquesObras: false,
    estratificacion: false,
    banco: false,
    colegios: false, cai: false,
  };

  /** Resúmenes que se muestran bajo el check una vez cargada la capa. */
  resumenColegios = signal<string>('');
  resumenCai = signal<string>('');

  /**
   * Estado de carga por capa.
   *
   * Antes 7 capas tenían `error: () => {}` y 2 ni siquiera handler. El usuario
   * marcaba el check, el check quedaba encendido y el mapa no cambiaba: nunca
   * sabía si estaba cargando, si no había datos o si había reventado.
   *
   * Y hay un caso que en una página PÚBLICA es peor: cuatro capas (Festivales,
   * Malla vial, Parques-obras, Banco) exigen sesión. Un visitante anónimo las
   * marca, recibe 401 y no pasa nada. Distinguir 'sesion' de 'error' es lo que
   * permite decirle la verdad: no falló, no es para él.
   */
  capasEstado = signal<Record<string, EstadoCapa>>({});

  private setEstadoCapa(nombre: string, estado: EstadoCapa): void {
    this.capasEstado.update(m => ({ ...m, [nombre]: estado }));
  }

  /** Mensaje corto al lado del check. Cadena vacía = no mostrar nada. */
  mensajeCapa(nombre: string): string {
    switch (this.capasEstado()[nombre]) {
      case 'cargando': return 'cargando…';
      case 'sesion':   return 'requiere iniciar sesión';
      case 'error':    return 'no se pudo cargar';
      case 'vacia':    return 'sin datos';
      default:         return '';
    }
  }

  esCapaProblema(nombre: string): boolean {
    const e = this.capasEstado()[nombre];
    return e === 'sesion' || e === 'error';
  }

  private errorDeCapa(nombre: string, err: unknown): void {
    const status = (err as HttpErrorResponse)?.status;
    this.setEstadoCapa(nombre, status === 401 || status === 403 ? 'sesion' : 'error');
    console.error(`[mapa] capa "${nombre}" falló`, err);
  }

  // Paleta de estratos (IDECA). 0/sin dato = gris; 1→6 rojo→morado (convención Bogotá).
  readonly estratoColores: Record<number, string> = {
    0: '#9CA3AF', 1: '#E4572E', 2: '#F3A712', 3: '#F4D35E',
    4: '#59A14F', 5: '#4E79A7', 6: '#7B4FA3',
  };
  readonly estratoLeyenda = [
    { e: 1, label: 'Estrato 1' }, { e: 2, label: 'Estrato 2' }, { e: 3, label: 'Estrato 3' },
    { e: 4, label: 'Estrato 4' }, { e: 5, label: 'Estrato 5' }, { e: 6, label: 'Estrato 6' },
    { e: 0, label: 'Sin estrato' },
  ];
  colorEstrato(e: number | null | undefined): string {
    return this.estratoColores[e ?? 0] ?? this.estratoColores[0];
  }

  /**
   * Qué estratos se piden al servidor. Todos = no se manda filtro.
   *
   * El endpoint acepta `?estrato=` repetido desde que existe y la UI nunca lo
   * usó: el ciudadano solo podía bajar las ~5.000 manzanas de Kennedy enteras.
   * Filtrar no es cosmética acá — pedir uno o dos estratos es un décimo de la
   * descarga y un décimo de los polígonos que Leaflet tiene que dibujar.
   */
  estratosVisibles = signal<number[]>([0, 1, 2, 3, 4, 5, 6]);

  estratoVisible(e: number): boolean {
    return this.estratosVisibles().includes(e);
  }

  todosLosEstratos(): boolean {
    return this.estratosVisibles().length === this.estratoLeyenda.length;
  }

  resumenEstratos(): string {
    const n = this.estratosVisibles().length;
    if (n === this.estratoLeyenda.length) return 'Mostrando todos los estratos.';
    if (n === 0) return 'Ningún estrato seleccionado: marca al menos uno.';
    return n === 1 ? 'Mostrando 1 estrato.' : `Mostrando ${n} estratos.`;
  }

  toggleEstrato(e: number): void {
    const actual = this.estratosVisibles();
    this.estratosVisibles.set(
      actual.includes(e) ? actual.filter(x => x !== e) : [...actual, e].sort(),
    );
    this.recargarEstratificacion();
  }

  mostrarTodosLosEstratos(): void {
    this.estratosVisibles.set([0, 1, 2, 3, 4, 5, 6]);
    this.recargarEstratificacion();
  }

  /** Bota la capa dibujada y la vuelve a pedir con el filtro puesto. */
  private recargarEstratificacion(): void {
    this.estratificacionLayer?.remove();
    this.estratificacionLayer = undefined;
    if (this.capas.estratificacion && this.estratosVisibles().length) {
      this.cargarEstratificacionLazy();
    }
  }

  // ── Estado Leaflet ──────────────────────────────────────────────
  private map?: L.Map;
  private eventoLayer?: L.LayerGroup;
  private contornoLayer?: L.GeoJSON;
  private upzLayer?: L.GeoJSON;
  private barriosLayer?: L.GeoJSON;
  private parquesLayer?: L.GeoJSON;
  private escuelasCulturaLayer?: L.LayerGroup;
  private escuelasDeporteLayer?: L.LayerGroup;
  private festivalesLayer?: L.LayerGroup;
  private tramosLayer?: L.GeoJSON;
  private parquesObrasLayer?: L.LayerGroup;
  private bancoLayer?: L.LayerGroup;
  private colegiosLayer?: L.LayerGroup;
  private caiLayer?: L.LayerGroup;
  private estratificacionLayer?: L.GeoJSON;
  /** Etiquetas permanentes (divIcon) de UPZ y barrio, por umbral de zoom. */
  private upzLabelsLayer?: L.LayerGroup;
  private barriosLabelsLayer?: L.LayerGroup;
  /** Barra de estado abajo a la izquierda: "Barrio · UPZ" bajo el cursor. */
  private statusEl?: HTMLElement;
  private hoverBarrio = '';
  private hoverUpz = '';
  /** Índices para colgarle su UPZ a un barrio (el GeoJSON de barrios no la trae). */
  private upzNombrePorCodigo = new Map<string, string>();
  private upzCodigoPorBarrioCodigo = new Map<string, string>();
  private upzCodigoPorBarrioNombre = new Map<string, string>();
  /** La capa pesa ~1 MB y tarda: sin esto el check parece muerto mientras baja. */
  estratificacionCargando = false;
  /** Evita disparar dos veces la carga de parques con doble clic en el check. */
  private parquesCargando = false;

  // ── Derivados ───────────────────────────────────────────────────
  subgruposFiltrados = computed<SubgrupoLite[]>(() => {
    const cat = this.catalogos();
    if (!cat) return [];
    if (this.selectedDependencia == null) return cat.subgrupos;
    return cat.subgrupos.filter(s => s.dependencia_id === this.selectedDependencia);
  });

  subgruposInversion = computed<SubgrupoLite[]>(() =>
    this.catalogos()?.subgrupos_inversion_local ?? []);

  conteosSubgrupo = computed<Record<number, ConteoSubgrupo>>(() =>
    this.catalogos()?.conteos_subgrupo ?? {});

  eventosFiltrados = computed<GeoFeature[]>(() => {
    const q = this.query.trim().toLowerCase();
    return this.eventos().features.filter((f) => {
      const p = f.properties;
      if (!q) return true;
      const hay = [p.nombre, p.direccion, p.dependencia, p.funcionario]
        .filter(Boolean).map(String).join(' ').toLowerCase();
      return hay.includes(q);
    });
  });

  /** Actividades pintadas en la sede de la Alcaldía por falta de dirección. */
  eventosSinUbicacionReal = computed<GeoFeature[]>(() =>
    this.eventosFiltrados().filter(f => !!f.properties['ubicacion_aproximada']));

  kpiHoy = computed<number>(() => {
    const today = new Date().toISOString().slice(0, 10);
    return this.eventos().features.filter(f =>
      (f.properties.fecha_inicio || '').slice(0, 10) === today).length;
  });

  kpiProximos = computed<number>(() => {
    const today = new Date().toISOString().slice(0, 10);
    return this.eventos().features.filter(f =>
      (f.properties.fecha_inicio || '') >= today).length;
  });

  /** KPIs del panel de análisis, sobre los eventos filtrados (en vista). */
  statKpis = computed(() => {
    const today = new Date().toISOString().slice(0, 10);
    const feats = this.eventosFiltrados();
    let proximos = 0, conKpi = 0;
    for (const f of feats) {
      if ((f.properties.fecha_inicio || '') >= today) proximos++;
      if (f.properties['indicador']) conKpi++;
    }
    return { proximos, ejecutados: feats.length - proximos, conKpi };
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mapa de Kennedy' },
    ]);
    // C1: leer la URL ANTES de initMap/cargarCatalogos, para que la primera
    // petición de eventos ya salga filtrada y el mapa se siembre en la vista
    // compartida (sin flash de "todo" ni reencuadre).
    this.leerEstadoDeUrl();
  }

  ngAfterViewInit(): void {
    this.initMap();
    this.cargarCatalogos();
  }

  ngOnDestroy(): void {
    this.map?.remove();
    this.charts.forEach(c => c.destroy());
    this.urlSync$.complete();
  }

  // ── C1: URL ↔ estado del mapa ───────────────────────────────────

  /** Lee el estado de los query params al arrancar (antes de initMap). */
  private leerEstadoDeUrl(): void {
    const p = this.route.snapshot.queryParamMap;

    const tipos = p.get('tipos');
    if (tipos) this.selectedTipos = tipos.split(',').filter(Boolean);

    const subs = p.get('subs');
    if (subs) this.selectedSubgrupos = subs.split(',').map(Number).filter(n => !isNaN(n));

    const dep = p.get('dep');
    if (dep) { const n = Number(dep); if (!isNaN(n)) this.selectedDependencia = n; }

    const q = p.get('q');
    if (q) this.query = q;

    const tab = p.get('tab');
    if (tab) { const n = Number(tab); if (!isNaN(n)) this.subgrupoTab.set(n); }

    const estratos = p.get('estratos');
    if (estratos) {
      const arr = estratos.split(',').map(Number).filter(n => !isNaN(n) && n >= 0 && n <= 6);
      if (arr.length) this.estratosVisibles.set([...new Set(arr)].sort());
    }

    if (p.get('stats') === '0') this.statsAbierto.set(false);

    // Capas: si viene el param, es el conjunto autoritativo (lo ausente = off).
    const capas = p.get('capas');
    if (capas != null) {
      const set = new Set(capas.split(',').filter(Boolean));
      for (const k of Object.keys(this.capas)) (this.capas as any)[k] = set.has(k);
      this.capasInicial = set;
    }

    // Vista: se valida para no sembrar el mapa con basura de una URL manipulada.
    const c = p.get('c'); const z = p.get('z');
    if (c && z) {
      const [lat, lng] = c.split(',').map(Number);
      const zoom = Number(z);
      const plausible = !isNaN(lat) && !isNaN(lng) && !isNaN(zoom)
        && lat > 3.9 && lat < 5.2 && lng > -74.7 && lng < -73.9
        && zoom >= 10 && zoom <= 19;
      if (plausible) this.vistaInicial = { center: [lat, lng], zoom };
    }
  }

  /** Dispara la carga de las capas lazy que la URL traía encendidas. */
  private restaurarCapasDesdeUrl(): void {
    if (!this.capasInicial || !this.map) return;
    // Prender el flag no basta para las lazy: hay que llamar su loader. localidad
    // la añade drawContorno y escuelas las añade cargarEscuelas, con las flags ya
    // fijadas en leerEstadoDeUrl; aquí solo faltan estas.
    const lazy = [
      'parques', 'barrios', 'upz', 'estratificacion', 'festivales',
      'tramosViales', 'parquesObras', 'banco', 'colegios', 'cai',
    ];
    for (const k of lazy) {
      if ((this.capas as any)[k]) this.toggleCapa(k as any);
    }
  }

  /** Serializa el estado a query params (omitiendo defaults) y lo escribe. */
  private escribirUrl(): void {
    if (!this.hidratado || !this.map) return;
    const c = this.map.getCenter();
    const onCapas = Object.keys(this.capas)
      .filter(k => (this.capas as any)[k]).sort();
    // El default es "solo localidad": si es eso, se omite el param.
    const capasDefault = onCapas.length === 1 && onCapas[0] === 'localidad';
    const estratosParam = (this.capas.estratificacion && !this.todosLosEstratos())
      ? this.estratosVisibles().join(',') : null;
    const q: Record<string, string | null> = {
      tipos: this.selectedTipos.length ? this.selectedTipos.join(',') : null,
      dep: this.selectedDependencia != null ? String(this.selectedDependencia) : null,
      subs: this.selectedSubgrupos.length ? this.selectedSubgrupos.join(',') : null,
      q: this.query.trim() ? this.query.trim() : null,
      tab: this.subgrupoTab() != null ? String(this.subgrupoTab()) : null,
      capas: capasDefault ? null : onCapas.join(','),
      estratos: estratosParam,
      stats: this.statsAbierto() ? null : '0',
      c: `${c.lat.toFixed(6)},${c.lng.toFixed(6)}`,
      z: String(this.map.getZoom()),
    };
    // merge + valor null = se quita el param → URL limpia sin defaults.
    // replaceUrl = no crea una entrada de historial por cada micro-cambio.
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: q,
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Dibuja/actualiza los 3 gráficos con los eventos en vista. */
  private dibujarCharts(feats: GeoFeature[]): void {
    const cTipo = this.chartTipoRef?.nativeElement;
    const cSub = this.chartSubRef?.nativeElement;
    const cMes = this.chartMesRef?.nativeElement;
    if (!cTipo || !cSub || !cMes) return;
    this.charts.forEach(c => c.destroy());
    this.charts = [];

    // Por tipo (con color del catálogo).
    const porTipo = new Map<string, number>();
    const porSub = new Map<string, number>();
    const porMes = new Map<string, number>();
    for (const f of feats) {
      const t = f.properties.tipo_evento_codigo || '—';
      porTipo.set(t, (porTipo.get(t) || 0) + 1);
      const s = (f.properties['subgrupo'] as string) || 'Sin subgrupo';
      porSub.set(s, (porSub.get(s) || 0) + 1);
      const m = (f.properties.fecha_inicio || '').slice(0, 7);
      if (m) porMes.set(m, (porMes.get(m) || 0) + 1);
    }

    const tipoLabels = [...porTipo.keys()];
    this.charts.push(new Chart(cTipo, {
      type: 'doughnut',
      data: {
        labels: tipoLabels.map(c => this.tipoNombre(c)),
        datasets: [{
          data: tipoLabels.map(c => porTipo.get(c)!),
          backgroundColor: tipoLabels.map(c => this.colorTipo(c)),
          borderWidth: 2, borderColor: '#fff',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
      },
    }));

    const subTop = [...porSub.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    this.charts.push(new Chart(cSub, {
      type: 'bar',
      data: {
        labels: subTop.map(([k]) => k),
        datasets: [{
          data: subTop.map(([, v]) => v),
          backgroundColor: '#0D9488', borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    }));

    const meses = [...porMes.keys()].sort();
    this.charts.push(new Chart(cMes, {
      type: 'line',
      data: {
        labels: meses,
        datasets: [{
          data: meses.map(m => porMes.get(m)!),
          borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)',
          fill: true, tension: 0.3, pointRadius: 3,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    }));
  }

  // ── Inicialización ──────────────────────────────────────────────
  private initMap(): void {
    this.map = L.map(this.mapEl.nativeElement, {
      // C1: si la URL trae una vista (enlace compartido), se siembra ahí para no
      // mostrar Kennedy centrado y saltar un instante después.
      center: this.vistaInicial ? this.vistaInicial.center : [4.6280, -74.1530],
      zoom: this.vistaInicial ? this.vistaInicial.zoom : 13,
      // Los controles de Leaflet vienen en inglés ("Zoom in", "Close popup") y
      // ese texto va al `title` Y al `aria-label`, así que un lector de pantalla
      // en español los lee en otro idioma. Se traducen acá porque la librería no
      // trae i18n.
      zoomControl: false,
    });
    L.control.zoom({
      zoomInTitle: 'Acercar',
      zoomOutTitle: 'Alejar',
    }).addTo(this.map);

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      },
    ).addTo(this.map);

    this.eventoLayer = L.layerGroup().addTo(this.map);
    this.agregarBarraEstado();
    // Las etiquetas permanentes aparecen/desaparecen por umbral de zoom.
    this.map.on('zoomend', () => this.actualizarEtiquetas());
    // C1: pan y zoom se reflejan en la URL (moveend cubre ambos).
    this.map.on('moveend', () => { if (this.hidratado) this.urlSync$.next(); });
  }

  private cargarCatalogos(): void {
    this.loading.set(true);
    forkJoin({
      cat: this.geo.catalogos(),
      contorno: this.geo.contornoKennedy(),
    }).subscribe({
      next: ({ cat, contorno }) => {
        this.errorMsg.set('');
        this.catalogos.set(cat as MapaCatalogosLocal);
        this.indexarTerritorio(cat as MapaCatalogosLocal);
        this.drawContorno(contorno);
        // C1: restaurar las capas lazy que la URL traía encendidas (las flags de
        // escuelas y localidad ya se fijaron en leerEstadoDeUrl, antes de estas
        // cargas, así que drawContorno/cargarEscuelas las respetan).
        this.restaurarCapasDesdeUrl();
        // Parques ya NO se carga acá: es la capa más pesada y arranca apagada.
        // Baja cuando el usuario marca su check (`cargarParquesLazy`).
        this.cargarEscuelas();
        this.cargarEventos();
        // A partir de aquí, los cambios del usuario sí escriben la URL.
        this.hidratado = true;
      },
      error: (err) => {
        // Página pública: hablarle de "tu sesión" a un ciudadano que nunca
        // inició una es desorientarlo. El problema es del servidor, no suyo.
        this.errorMsg.set(
          'No se pudieron cargar los datos del mapa. Reintenta en un momento; '
          + 'si sigue igual, el servicio puede estar temporalmente fuera.',
        );
        this.loading.set(false);
        console.error(err);
      },
    });
  }

  private drawContorno(fc: FeatureCollection): void {
    if (!this.map) return;
    this.contornoLayer?.remove();
    this.contornoLayer = L.geoJSON(fc as any, {
      style: { color: '#D6001C', weight: 3, fill: false, dashArray: '6 6' },
    });
    if (this.capas.localidad) this.contornoLayer.addTo(this.map);
    if (this.vistaInicial) {
      // Enlace compartido: su encuadre manda; no reencuadrar a toda la localidad.
      this.map.setView(this.vistaInicial.center, this.vistaInicial.zoom);
    } else {
      try {
        const bb = this.contornoLayer.getBounds();
        if (bb.isValid()) this.map.fitBounds(bb, { padding: [20, 20] });
      } catch { /* sin bounds, ignorar */ }
    }
  }

  /**
   * Parques, bajo demanda y una sola vez.
   *
   * Es la capa más pesada del mapa (554 polígonos de IDECA). Mientras se cargaba
   * al arrancar, todo visitante pagaba su descarga aunque nunca marcara el
   * check. Ahora baja al marcarlo, como barrios, UPZ y estratificación.
   */
  private cargarParquesLazy(): void {
    if (this.parquesLayer || this.parquesCargando) return;
    this.parquesCargando = true;
    this.setEstadoCapa('parques', 'cargando');
    this.geo.parquesKennedy().subscribe({
      next: (fc) => {
        this.parquesCargando = false;
        this.setEstadoCapa('parques', 'ok');
        if (!this.map) return;
        this.parquesLayer = L.geoJSON(fc as any, {
          style: { color: '#10B981', weight: 1, fillColor: '#10B981', fillOpacity: 0.25 },
        });
        if (this.capas.parques) {
          this.parquesLayer.addTo(this.map);
          this.ordenarPoligonos();
        }
      },
      error: (e) => {
        this.parquesCargando = false;
        this.errorDeCapa('parques', e);
      },
    });
  }

  /**
   * Marcador de sede. Cuando la sede dicta más de una disciplina lleva el
   * número encima: es la señal de que ahí hay varias escuelas apiladas y de
   * que vale la pena abrir el popup.
   */
  private escuelaIcon(
    tipo: 'Cultura' | 'Deporte',
    disciplinas = 1,
    estado: { aproximada?: boolean; fuera?: boolean } = {},
  ): L.DivIcon {
    const color = tipo === 'Cultura' ? '#EC4899' : '#14B8A6';

    // Sede sin ubicación propia: borde gris punteado y relleno pálido, igual
    // que los eventos aproximados. Se distingue sin abrir el popup y sin
    // depender del color, que ya está ocupado por Cultura/Deporte.
    if (estado.aproximada) {
      return L.divIcon({
        className: 'mapa-escuela-marker mapa-escuela-marker--aprox',
        html: `<div style="background:${color};opacity:.5;width:11px;height:11px;
                border:2px dashed #6B7280;"></div>`,
        iconSize: [15, 15],
        iconAnchor: [8, 8],
        popupAnchor: [0, -8],
      });
    }

    // Fuera de la localidad: el punto es real, así que va sólido, pero con
    // anillo ámbar para que se vea que algo pasa con esa sede.
    if (estado.fuera) {
      return L.divIcon({
        className: 'mapa-escuela-marker mapa-escuela-marker--fuera',
        html: `<div style="background:${color};width:11px;height:11px;
                border:2px solid #F59E0B;box-shadow:0 0 0 2px rgba(245,158,11,.45);"></div>`,
        iconSize: [15, 15],
        iconAnchor: [8, 8],
        popupAnchor: [0, -8],
      });
    }

    if (disciplinas <= 1) {
      return L.divIcon({
        className: 'mapa-escuela-marker',
        html: `<div style="background:${color};width:11px;height:11px;border:2px solid #fff;
                box-shadow:0 0 0 1px ${color};"></div>`,
        iconSize: [13, 13],
        iconAnchor: [7, 7],
      });
    }
    return L.divIcon({
      className: 'mapa-escuela-marker mapa-escuela-marker--multi',
      html: `<div style="background:${color};color:#fff;width:20px;height:20px;
              border:2px solid #fff;border-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.35);
              display:flex;align-items:center;justify-content:center;
              font-size:11px;font-weight:700;line-height:1;">${disciplinas}</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
      popupAnchor: [0, -11],
    });
  }

  private cargarEscuelas(): void {
    this.setEstadoCapa('escuelas', 'cargando');
    this.geo.escuelasKennedy().subscribe({
      next: (r) => {
        this.setEstadoCapa('escuelas', 'ok');
        if (!this.map) return;
        this.escuelasSinUbicacion.set(r.sin_ubicacion ?? []);
        const culLayer = L.layerGroup();
        const depLayer = L.layerGroup();
        for (const sede of this.desapilarSedes(this.agruparSedes(r.features))) {
          const target = sede.tipo === 'Cultura' ? culLayer : depLayer;
          const m = L.marker([sede.lat, sede.lng], {
            icon: this.escuelaIcon(sede.tipo, sede.disciplinas.length, {
              aproximada: sede.aproximada,
              fuera: sede.fueraDeKennedy,
            }),
            title: sede.aproximada ? `${sede.nombre} — ubicación no registrada` : sede.nombre,
          });
          // maxHeight deja el popup con scroll propio: hay sedes con 7
          // disciplinas y sin esto el globo se sale de la pantalla.
          m.bindPopup(this.sedePopup(sede), { maxWidth: 340, maxHeight: 300 });
          m.addTo(target);
        }
        this.escuelasCulturaLayer = culLayer;
        this.escuelasDeporteLayer = depLayer;
        if (this.capas.escuelasCultura) culLayer.addTo(this.map);
        if (this.capas.escuelasDeporte) depLayer.addTo(this.map);
      },
      error: (e) => this.errorDeCapa('escuelas', e),
    });
  }

  /**
   * Abre en abanico las sedes que caen en la MISMA coordenada.
   *
   * Son las que no tienen ubicación propia: todas se dibujan en la sede de la
   * Alcaldía, así que sin esto quedarían 43 marcadores en un píxel — se vería
   * uno solo, el popup sería el del último y las otras 42 estarían en el mapa
   * sin estar visibles, que es peor que no pintarlas.
   *
   * Es el mismo abanico de `renderEventos()`: anillos de 8, con la corrección
   * por coseno para que el círculo no se vea ovalado en la latitud de Bogotá.
   * La coordenada original no se toca en el popup — el marcador se corre para
   * poder verse, y el texto sigue diciendo que la ubicación no es esa.
   */
  private desapilarSedes(sedes: SedeEscuela[]): SedeEscuela[] {
    const grupos = new Map<string, SedeEscuela[]>();
    for (const s of sedes) {
      const clave = `${s.lat.toFixed(6)},${s.lng.toFixed(6)}`;
      const g = grupos.get(clave);
      if (g) g.push(s);
      else grupos.set(clave, [s]);
    }

    const salida: SedeEscuela[] = [];
    for (const grupo of grupos.values()) {
      const n = grupo.length;
      if (n === 1) {
        salida.push(grupo[0]);
        continue;
      }
      grupo.forEach((s, i) => {
        const anillo = Math.floor(i / 8);
        const enAnillo = Math.min(n - anillo * 8, 8);
        const ang = (2 * Math.PI * (i % 8)) / enAnillo;
        const r = this.RADIO_DESAPILADO * (1 + anillo);
        salida.push({
          ...s,
          lat: s.lat + r * Math.cos(ang),
          lng: s.lng + (r * Math.sin(ang)) / Math.cos((s.lat * Math.PI) / 180),
        });
      });
    }
    return salida;
  }

  // ── Fase 4: una sede = un marcador ──────────────────────────────
  /** Escapa lo que viene de BD antes de meterlo en el HTML del popup. */
  private esc(v: unknown): string {
    return String(v ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /** Primer valor no vacío entre varias claves posibles. */
  private primerTexto(o: Record<string, any> | null | undefined, claves: string[]): string {
    for (const k of claves) {
      const v = o?.[k];
      if (v != null && String(v).trim() !== '') return String(v).trim();
    }
    return '';
  }

  /** Dirección comparable: sin acentos, sin puntuación y sin espacios de más. */
  private normalizarTexto(v: string): string {
    return v.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toUpperCase().replace(/[^A-Z0-9]+/g, ' ').trim();
  }

  /**
   * Agrupa las escuelas en sedes. Dos escuelas son la misma sede si comparten
   * dirección normalizada o si caen exactamente en el mismo punto — lo segundo
   * cubre las direcciones escritas distinto que geocodifican igual, que es
   * justo lo que produce el apilamiento.
   *
   * Cultura y Deporte NO se mezclan aunque compartan dirección: son capas
   * distintas, cada una con su color y su interruptor.
   */
  private agruparSedes(features: GeoFeature[]): SedeEscuela[] {
    const sedes = new Map<string, SedeEscuela>();
    const claveDeCoordenada = new Map<string, string>();

    for (const f of features) {
      const g = f.geometry;
      if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
      const lat = Number(g.coordinates[1]);
      const lng = Number(g.coordinates[0]);
      if (isNaN(lat) || isNaN(lng)) continue;

      const p = (f.properties ?? {}) as EscuelaProps;
      const tipo = (p.tipo || '').trim();
      if (tipo !== 'Cultura' && tipo !== 'Deporte') continue;

      const direccion = (p.direccion || '').trim();
      const aproximada = !!p.ubicacion_aproximada;
      const coordKey = `${tipo}|${lat.toFixed(6)},${lng.toFixed(6)}`;

      // Las aproximadas comparten el punto de respaldo SIN compartir sede: que
      // dos escuelas estén dibujadas en la Alcaldía no dice absolutamente nada
      // sobre si quedan en el mismo lugar. Agruparlas por coordenada —que es lo
      // que hace la regla de abajo— las fundiría en un solo marcador titulado
      // como una de ellas, y las otras 42 desaparecerían del mapa justo después
      // de haberlas rescatado. Cada una es su propia sede, por id.
      let clave: string;
      if (aproximada) {
        clave = `${tipo}|aprox|${p.id}`;
      } else {
        clave = direccion
          ? `${tipo}|${this.normalizarTexto(direccion)}`
          : coordKey;
        const yaEnEsePunto = claveDeCoordenada.get(coordKey);
        if (yaEnEsePunto) clave = yaEnEsePunto;
        else claveDeCoordenada.set(coordKey, clave);
      }

      let sede = sedes.get(clave);
      if (!sede) {
        sede = {
          lat, lng, tipo: tipo as 'Cultura' | 'Deporte',
          nombre: p.nombre || 'Escuela',
          otrosNombres: [],
          direccion,
          upz: this.etiquetaUpz(p),
          upzFuente: p.upz_fuente ?? null,
          barrio: p.barrio_nombre || '',
          barrioFuente: p.barrio_fuente ?? null,
          disciplinas: [],
          avisos: [],
          aproximada,
          motivo: p.motivo_ubicacion ?? null,
          fueraDeKennedy: !!p.fuera_de_kennedy,
        };
        sedes.set(clave, sede);
      } else {
        const nom = p.nombre || '';
        if (nom && nom !== sede.nombre && !sede.otrosNombres.includes(nom)) {
          sede.otrosNombres.push(nom);
        }
        if (!sede.direccion && direccion) sede.direccion = direccion;
        if (!sede.upz) { sede.upz = this.etiquetaUpz(p); sede.upzFuente = p.upz_fuente ?? null; }
        if (!sede.barrio && p.barrio_nombre) {
          sede.barrio = p.barrio_nombre; sede.barrioFuente = p.barrio_fuente ?? null;
        }
      }

      if (p.discrepancia) {
        const aviso = `Barrio declarado (${p.barrio_declarado || 'sin dato'}) distinto del resuelto por geometría`;
        if (!sede.avisos.includes(aviso)) sede.avisos.push(aviso);
      }
      if (p.revision_requerida && p.revision_detalle) {
        if (!sede.avisos.includes(p.revision_detalle)) sede.avisos.push(p.revision_detalle);
      }

      for (const d of this.disciplinasDe(p)) sede.disciplinas.push(d);
    }

    return [...sedes.values()];
  }

  /** "Timiza (48)" con lo que haya; nunca inventa el que falta. */
  private etiquetaUpz(p: EscuelaProps): string {
    const nombre = (p.upz_nombre || '').trim();
    const codigo = (p.upz_codigo || '').trim();
    if (nombre && codigo) return `${nombre} (${codigo})`;
    return nombre || (codigo ? `UPZ ${codigo}` : '');
  }

  /**
   * Normaliza `escuela.actividades` (JSONB) a filas de popup. Las claves se
   * leen con alternativas porque la columna la puebla el cargue del censo:
   * si mañana llega `disciplina` en vez de `actividad`, el popup no se cae.
   *
   * Una escuela SIN actividades igual produce una fila, con todo en
   * "no registrado": el vacío tiene que verse, no desaparecer.
   */
  private disciplinasDe(p: EscuelaProps): DisciplinaSede[] {
    const escuela = p.nombre || 'Escuela';
    const lista: EscuelaActividad[] = Array.isArray(p.actividades) ? p.actividades : [];
    const filas = lista.length ? lista : [{} as EscuelaActividad];
    return filas.map((a) => {
      const o = a as Record<string, any>;
      const formador = this.primerTexto(o, ['formador', 'profesor', 'instructor']);
      const responsable = this.primerTexto(o, ['responsable', 'responsable_alk']);
      const telefono = this.primerTexto(o, ['telefono', 'tel', 'celular', 'contacto']);
      const persona = formador || responsable;
      return {
        escuela,
        actividad: this.primerTexto(o, ['actividad', 'disciplina', 'nombre'])
          || 'Sin actividad registrada',
        horarios: this.primerTexto(o, ['horarios', 'horario'])
          || 'Sin horario registrado',
        edades: this.primerTexto(o, ['edades', 'edad', 'rango_edad'])
          || 'No registrado',
        contactoLabel: (!formador && responsable) ? 'Responsable' : 'Formador',
        contacto: [persona, telefono].filter(Boolean).join(' - ') || 'No registrado',
      };
    });
  }

  private sedePopup(sede: SedeEscuela): string {
    const e = (v: unknown) => this.esc(v);
    const fila = (label: string, valor: string) =>
      `<div><strong>${label}:</strong> ${e(valor)}</div>`;
    const fuente = (f: string | null) =>
      f === 'geometria' ? ' <span class="mapa-popup__tag">geometría</span>'
        : (f === 'declarado' ? ' <span class="mapa-popup__tag">declarado</span>' : '');

    const cabecera = sede.otrosNombres.length
      ? `<div class="mapa-popup__sub">También en esta sede: ${e(sede.otrosNombres.join(', '))}</div>`
      : '';
    const conteo = sede.disciplinas.length > 1
      ? `<div class="mapa-popup__sub">${sede.disciplinas.length} actividades en esta sede</div>`
      : '';

    const discs = sede.disciplinas.map((d) => `
      <article class="mapa-popup__disc">
        <h5>${e(d.actividad)}</h5>
        ${sede.otrosNombres.length ? `<div class="mapa-popup__disc-esc">${e(d.escuela)}</div>` : ''}
        <div><strong>Horarios:</strong> ${e(d.horarios)}</div>
        <div><strong>Edades:</strong> ${e(d.edades)}</div>
        <div><strong>${e(d.contactoLabel)}:</strong> ${e(d.contacto)}</div>
      </article>`).join('');

    const avisos = sede.avisos.length
      ? `<div class="mapa-popup__aviso">⚠ ${sede.avisos.map(a => e(a)).join('<br>⚠ ')}</div>`
      : '';

    // El aviso de ubicación va ARRIBA, antes de la dirección: si el punto no es
    // donde queda la sede, eso es lo primero que hay que saber. Al final
    // equivale a esconderlo.
    let ubicacion = '';
    if (sede.aproximada) {
      const porque = sede.motivo === 'direccion_no_ubicada'
        ? `Tiene dirección registrada, pero no se pudo ubicar en el mapa.`
        : `No tiene dirección registrada en el sistema.`;
      ubicacion = `
        <p class="mapa-popup__aviso">
          <strong>Ubicación no registrada.</strong> ${porque}
          Se muestra en la sede de la Alcaldía; la escuela no queda en este punto.
        </p>`;
    } else if (sede.fueraDeKennedy) {
      ubicacion = `
        <p class="mapa-popup__aviso">
          <strong>Fuera de la localidad.</strong> Está dibujada donde la ubica su
          dirección registrada, que según Catastro queda fuera de Kennedy.
        </p>`;
    }

    return `
      <div class="mapa-popup mapa-popup--sede">
        <h4>${e(sede.nombre)}</h4>
        <div class="mapa-popup__sub">Escuela de ${e(sede.tipo)}</div>
        ${ubicacion}
        ${cabecera}${conteo}
        ${fila('Dirección', sede.direccion || 'No registrada')}
        <div><strong>UPZ:</strong> ${e(sede.upz || 'No registrada')}${fuente(sede.upzFuente)}</div>
        <div><strong>Barrio:</strong> ${e(sede.barrio || 'No registrado')}${fuente(sede.barrioFuente)}</div>
        ${avisos}
        <div class="mapa-popup__discs">${discs}</div>
      </div>`;
  }

  /** Resumen de actividades para la tabla de escuelas sin ubicación. */
  resumenActividades(e: EscuelaProps): string {
    const nombres = (e.actividades ?? [])
      .map(a => this.primerTexto(a as Record<string, any>, ['actividad', 'disciplina', 'nombre']))
      .filter(Boolean);
    return nombres.length ? [...new Set(nombres)].join(', ') : 'Sin actividad registrada';
  }

  /** Por qué esta escuela no está en el mapa. Sin adivinar: lo que dice el dato. */
  motivoSinUbicacion(e: EscuelaProps): string {
    if (e.revision_detalle) return e.revision_detalle;
    if (!e.direccion) return 'Sin dirección en el censo';
    if (e.barrio_estado === 'sin_coordenada') return 'Dirección sin coordenada resuelta';
    return 'Sin coordenada';
  }

  // Iniciativas del Banco (Deporte): un punto por organización inscrita, del
  // color de su estrato IDECA. Lazy: se carga la primera vez que se prende.
  private cargarBanco(): void {
    if (this.bancoLayer) return;
    this.setEstadoCapa('banco', 'cargando');
    this.geo.bancoKennedy().subscribe({
      next: (fc) => {
        this.setEstadoCapa('banco', 'ok');
        if (!this.map) return;
        const grupo = L.layerGroup();
        for (const f of fc.features) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lng = Number(g.coordinates[0]);
          const lat = Number(g.coordinates[1]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const p = f.properties ?? {};
          const color = this.colorEstrato(p['estrato']);
          const m = L.circleMarker([lat, lng], {
            radius: 8, color: '#1f2937', weight: 1.5,
            fillColor: color, fillOpacity: 0.9,
          });
          m.bindPopup(`
            <div class="mapa-popup">
              <h4>🏅 ${p['organizacion'] || 'Organización'}</h4>
              ${p['disciplina'] ? `<div><strong>Disciplina:</strong> ${p['disciplina']}</div>` : ''}
              ${p['estrato'] != null ? `<div><strong>Estrato:</strong> ${p['estrato']}</div>` : ''}
              ${p['barrio'] ? `<div><strong>Barrio:</strong> ${p['barrio']}</div>` : ''}
              <div><strong>Estado:</strong> ${p['estado'] || '—'}</div>
            </div>`);
          m.addTo(grupo);
        }
        this.bancoLayer = grupo;
        if (this.capas.banco) grupo.addTo(this.map);
      },
      error: (e) => this.errorDeCapa('banco', e),
    });
  }

  /**
   * Ícono de sede de colegio: birrete en burbuja azul. La sede principal va
   * más grande y con borde más marcado — en un colegio de cuatro sedes,
   * saber cuál es la principal es la diferencia entre entregar bien y no.
   */
  private colegioIcon(principal: boolean): L.DivIcon {
    const d = principal ? 30 : 24;
    return L.divIcon({
      className: 'mapa-colegio-marker',
      html: `<div style="background:#1D4ED8;color:#fff;width:${d}px;height:${d}px;
              border-radius:50%;border:${principal ? 3 : 2}px solid #fff;
              box-shadow:0 1px 4px rgba(0,0,0,.4);display:flex;
              align-items:center;justify-content:center;
              font-size:${principal ? 15 : 12}px;line-height:1;">🎓</div>`,
      iconSize: [d + 2, d + 2],
      iconAnchor: [(d + 2) / 2, (d + 2) / 2],
      popupAnchor: [0, -(d + 2) / 2],
    });
  }

  /** Capa de colegios distritales. Lazy: se carga una vez. */
  private cargarColegios(): void {
    if (this.colegiosLayer) return;
    this.setEstadoCapa('colegios', 'cargando');
    this.geo.colegiosKennedy().subscribe({
      next: (r) => {
        if (r.disponible === false) {
          // La tabla todavía no está aplicada en este entorno. No es un error
          // del usuario ni una capa rota: es que no hay datos que mostrar.
          this.setEstadoCapa('colegios', 'vacia');
          return;
        }
        this.setEstadoCapa('colegios', r.features?.length ? 'ok' : 'vacia');
        if (!this.map) return;
        const layer = L.layerGroup();
        for (const f of r.features || []) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const p = f.properties as ColegioProps;
          L.marker([lat, lng], { icon: this.colegioIcon(p.es_principal) })
            .bindPopup(this.popupColegio(p))
            .addTo(layer);
        }
        this.colegiosLayer = layer;
        if (this.capas.colegios) layer.addTo(this.map);

        const partes = [`${r.colegios ?? 0} colegios · ${r.features?.length ?? 0} sedes`];
        if (r.matricula_total) {
          partes.push(`${r.matricula_total.toLocaleString('es-CO')} alumnos`);
        }
        if (r.count_sin_ubicacion) {
          partes.push(`${r.count_sin_ubicacion} sin ubicación`);
        }
        this.resumenColegios.set(partes.join(' · '));
      },
      error: (e) => this.errorDeCapa('colegios', e),
    });
  }

  private popupColegio(p: ColegioProps): string {
    const filas: string[] = [];
    if (!p.es_principal || p.sede !== p.colegio) {
      filas.push(`<div>Sede <strong>${p.orden_sede || '—'}</strong>: ${p.sede}</div>`);
    }
    if (p.matricula_total != null) {
      // La fecha de corte va pegada al número a propósito: la matrícula viene
      // de otra capa y con otra fecha que el resto de la ficha.
      const corte = p.matricula_corte ? ` <small>(a ${p.matricula_corte})</small>` : '';
      filas.push(`<div><strong>${p.matricula_total.toLocaleString('es-CO')}</strong> alumnos${corte}</div>`);
    } else {
      filas.push('<div><em>Sin matrícula reportada</em></div>');
    }
    if (p.direccion) filas.push(`<div>${p.direccion}</div>`);
    if (p.barrio) filas.push(`<div><small>Barrio ${p.barrio}</small></div>`);
    if (p.telefono) filas.push(`<div><small>Tel. ${p.telefono}</small></div>`);
    filas.push(`<div><small>${p.clase_nombre}</small></div>`);
    if (p.entregas_n != null) {
      filas.push(p.entregas_n
        ? `<div><small>${p.entregas_n} entrega(s) de insumos registradas</small></div>`
        : '<div><small>Sin entregas de insumos registradas</small></div>');
    }
    return `<div class="mapa-popup"><h4>${p.colegio}</h4>${filas.join('')}</div>`;
  }

  /**
   * Ícono de CAI. Fijo y móvil se pintan DISTINTO a propósito: forma, color e
   * ícono cambian los tres, no solo el color, para que la diferencia se lea
   * también en escala de grises y para quien no distingue colores.
   */
  private caiIcon(movil: boolean): L.DivIcon {
    return L.divIcon({
      className: movil ? 'mapa-cai-marker mapa-cai-marker--movil' : 'mapa-cai-marker',
      html: `<div style="background:${movil ? '#D97706' : '#065F46'};color:#fff;
              width:26px;height:26px;
              border-radius:${movil ? '50%' : '4px'};
              border:2px solid #fff;${movil ? 'border-style:dashed;' : ''}
              box-shadow:0 1px 4px rgba(0,0,0,.4);display:flex;
              align-items:center;justify-content:center;
              font-size:13px;line-height:1;">${movil ? '🚓' : '🛡'}</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14],
    });
  }

  /** Capa de CAI (Seguridad). Lazy: se carga una vez. */
  private cargarCai(): void {
    if (this.caiLayer) return;
    this.setEstadoCapa('cai', 'cargando');
    this.geo.cai().subscribe({
      next: (r) => {
        if (r.disponible === false) {
          this.setEstadoCapa('cai', 'vacia');
          return;
        }
        this.setEstadoCapa('cai', r.features?.length ? 'ok' : 'vacia');
        if (!this.map) return;
        const layer = L.layerGroup();
        for (const f of r.features || []) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const p = f.properties as CaiProps;
          L.marker([lat, lng], { icon: this.caiIcon(p.es_movil) })
            .bindPopup(this.popupCai(p))
            .addTo(layer);
        }
        this.caiLayer = layer;
        if (this.capas.cai) layer.addTo(this.map);

        const fijos = r.count_fijos ?? 0;
        const moviles = r.count_moviles ?? 0;
        // Se dice explícitamente que no hay móviles en vez de callarlo: la
        // fuente oficial no los publica, y omitirlo se leería como que no
        // existen.
        this.resumenCai.set(moviles
          ? `${fijos} fijos · ${moviles} móviles`
          : `${fijos} fijos · ningún móvil en la fuente oficial`);
      },
      error: (e) => this.errorDeCapa('cai', e),
    });
  }

  private popupCai(p: CaiProps): string {
    const filas: string[] = [];
    filas.push(`<div><strong>${p.es_movil ? 'CAI móvil' : 'CAI fijo'}</strong>`
      + ` · <small>${p.codigo}</small></div>`);
    if (p.direccion) filas.push(`<div>${p.direccion}</div>`);
    if (p.upz_nombre) filas.push(`<div><small>UPZ ${p.upz_nombre}</small></div>`);
    if (p.telefono) filas.push(`<div><small>Tel. ${p.telefono}</small></div>`);
    if (p.horario) filas.push(`<div><small>${p.horario}</small></div>`);
    if (p.es_movil) {
      filas.push('<div><small><em>Unidad móvil: su ubicación cambia.</em></small></div>');
    }
    return `<div class="mapa-popup"><h4>${p.nombre}</h4>${filas.join('')}</div>`;
  }

  /** Ícono diferenciado de festival: estrella en burbuja morada. */
  private festivalIcon(): L.DivIcon {
    return L.divIcon({
      className: 'mapa-festival-marker',
      html: `<div style="background:#8B5CF6;color:#fff;width:24px;height:24px;
              border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);
              display:flex;align-items:center;justify-content:center;
              font-size:13px;line-height:1;">★</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      popupAnchor: [0, -13],
    });
  }

  /** Capa de festivales con punto (FEST-F-11). Lazy: se carga una vez. */
  private cargarFestivales(): void {
    if (this.festivalesLayer) return;
    this.setEstadoCapa('festivales', 'cargando');
    this.geo.festivalesGeojson().subscribe({
      next: (fc) => {
        this.setEstadoCapa('festivales', 'ok');
        if (!this.map) return;
        const layer = L.layerGroup();
        for (const f of fc.features || []) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const m = L.marker([lat, lng], { icon: this.festivalIcon() });
          m.bindPopup(this.festivalPopup(f.properties || {}));
          m.addTo(layer);
        }
        this.festivalesLayer = layer;
        if (this.capas.festivales) layer.addTo(this.map);
      },
      error: (e) => this.errorDeCapa('festivales', e),
    });
  }

  private festivalPopup(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    const fechas = [p['fecha_inicio'], p['fecha_fin']].filter(Boolean).join(' → ');
    return `
      <div class="mapa-popup">
        <h4>★ ${p['nombre'] || 'Festival'}</h4>
        ${fila('Tipo', p['tipo_festival'])}
        ${fila('Vigencia', p['vigencia'])}
        ${fila('Estado', p['estado'])}
        ${fila('Fechas', fechas)}
        ${fila('Lugar', p['lugar'])}
        ${fila('Actos', p['n_eventos'])}
      </div>`;
  }

  /** Color por % avance, reutilizable para tramos viales y parques con obra. */
  private colorAvance(pct: number): string {
    if (pct >= 100) return '#16a34a';  // terminado
    if (pct <= 0) return '#dc2626';    // sin iniciar
    return '#f59e0b';                  // parcial
  }

  private fmtMiles(valor: any): string {
    const n = Number(valor);
    if (valor == null || isNaN(n)) return '—';
    return n.toLocaleString('es-CO');
  }

  /** Capa de tramos viales (LineStrings) coloreados por % avance. Lazy. */
  private cargarTramos(): void {
    if (this.tramosLayer) return;
    this.setEstadoCapa('tramosViales', 'cargando');
    this.geo.tramosViales().subscribe({
      next: (fc) => {
        this.setEstadoCapa('tramosViales', 'ok');
        if (!this.map) return;
        this.tramosLayer = L.geoJSON(fc as any, {
          style: (feat: any) => ({
            color: this.colorAvance(Number(feat?.properties?.pct_avance) || 0),
            weight: 5,
            opacity: 0.9,
          }),
          onEachFeature: (feat: any, lyr) => {
            lyr.bindPopup(this.tramoPopup(feat?.properties || {}));
          },
        });
        if (this.capas.tramosViales) this.tramosLayer.addTo(this.map);
      },
      error: (e) => this.errorDeCapa('tramosViales', e),
    });
  }

  private tramoPopup(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value || value === 0 ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    const tramo = [p['desde'], p['hasta']].filter(Boolean).join(' → ');
    return `
      <div class="mapa-popup">
        <h4>${p['eje_vial'] || 'Tramo vial'}</h4>
        ${fila('Tramo', tramo)}
        ${fila('Código del tramo (CIV)', p['civ'])}
        ${fila('Contrato', p['contrato'])}
        ${fila('Valor intervención', '$' + this.fmtMiles(p['valor_intervencion']))}
        ${fila('% avance', (Number(p['pct_avance']) || 0) + '%')}
      </div>`;
  }

  /** Ícono diferenciado de parque con obra: árbol coloreado por % avance. */
  private parqueObraIcon(pct: number): L.DivIcon {
    const color = this.colorAvance(pct);
    return L.divIcon({
      className: 'mapa-obra-marker',
      html: `<div style="background:${color};width:24px;height:24px;border-radius:50%;
              border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);
              display:flex;align-items:center;justify-content:center;
              font-size:13px;line-height:1;">🌳</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      popupAnchor: [0, -13],
    });
  }

  /** Capa de parques con obra (Points) coloreados por % avance. Lazy. */
  private cargarParquesObras(): void {
    if (this.parquesObrasLayer) return;
    this.setEstadoCapa('parquesObras', 'cargando');
    this.geo.parquesObras().subscribe({
      next: (fc) => {
        this.setEstadoCapa('parquesObras', 'ok');
        if (!this.map) return;
        const layer = L.layerGroup();
        for (const f of fc.features || []) {
          const g = f.geometry;
          if (g?.type !== 'Point' || !Array.isArray(g.coordinates)) continue;
          const lat = Number(g.coordinates[1]);
          const lng = Number(g.coordinates[0]);
          if (isNaN(lat) || isNaN(lng)) continue;
          const pct = Number(f.properties?.pct_avance) || 0;
          const m = L.marker([lat, lng], { icon: this.parqueObraIcon(pct) });
          m.bindPopup(this.parqueObraPopup(f.properties || {}));
          m.addTo(layer);
        }
        this.parquesObrasLayer = layer;
        if (this.capas.parquesObras) layer.addTo(this.map);
      },
      error: (e) => this.errorDeCapa('parquesObras', e),
    });
  }

  private parqueObraPopup(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value || value === 0 ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    return `
      <div class="mapa-popup">
        <h4>🌳 ${p['nombre'] || 'Parque'}</h4>
        ${fila('Código', p['codigo_parque'])}
        ${fila('Contrato', p['contrato'])}
        ${fila('% avance', (Number(p['pct_avance']) || 0) + '%')}
      </div>`;
  }

  // ── Fase 5: hover de barrio y UPZ ───────────────────────────────
  //
  // Los polígonos se pintaban mudos: se veía la línea pero no qué era. Acá se
  // agregan tooltip pegado al cursor, resaltado, barra de estado y etiquetas
  // permanentes por zoom — el comportamiento que la gente ya conoce de Google
  // Maps y no tiene que aprender.

  /** Estilos base y de resaltado, en un solo lugar para no repetirlos. */
  private readonly estiloUpz: L.PathOptions = {
    color: '#0EA5E9', weight: 1.5, fillColor: '#0EA5E9', fillOpacity: 0.04,
  };
  private readonly estiloUpzHover: L.PathOptions = {
    color: '#0284C7', weight: 3, fillColor: '#0EA5E9', fillOpacity: 0.18,
  };
  private readonly estiloBarrio: L.PathOptions = {
    color: '#8B5CF6', weight: 0.8, fillColor: '#8B5CF6', fillOpacity: 0.05,
  };
  private readonly estiloBarrioHover: L.PathOptions = {
    color: '#6D28D9', weight: 2.5, fillColor: '#8B5CF6', fillOpacity: 0.22,
  };

  /** Código a dígitos: 'UPZ83' → '83', '004615' → '4615'. */
  private normalizarCodigo(v: unknown): string {
    const solo = String(v ?? '').replace(/\D/g, '');
    return solo ? String(Number(solo)) : '';
  }

  /**
   * Índices barrio→UPZ a partir de `/geo/api/mapa/catalogos/`. El GeoJSON de
   * barrios trae solo SCACODIGO y NOMBRE: la UPZ hay que colgársela desde el
   * catálogo. Se indexa por código Y por nombre porque los códigos de IDECA y
   * los de la tabla `barrio` no siempre coinciden (deuda M22); con las dos
   * llaves, cada barrio que sí empareje queda resuelto y los demás muestran
   * "UPZ no registrada" en vez de mentir.
   */
  private indexarTerritorio(cat: MapaCatalogosLocal): void {
    this.upzNombrePorCodigo.clear();
    this.upzCodigoPorBarrioCodigo.clear();
    this.upzCodigoPorBarrioNombre.clear();
    for (const u of cat.upz ?? []) {
      const cod = this.normalizarCodigo(u?.codigo);
      if (cod) this.upzNombrePorCodigo.set(cod, String(u?.nombre ?? ''));
    }
    for (const b of cat.barrios ?? []) {
      const upzCod = this.normalizarCodigo(b?.upz_codigo);
      if (!upzCod) continue;
      const cod = this.normalizarCodigo(b?.codigo);
      if (cod) this.upzCodigoPorBarrioCodigo.set(cod, upzCod);
      const nom = this.normalizarTexto(String(b?.nombre ?? ''));
      if (nom) this.upzCodigoPorBarrioNombre.set(nom, upzCod);
    }
  }

  /** "UPZ 48 Timiza" para un barrio, con lo que se pueda resolver. */
  private upzDeBarrio(props: Record<string, any>, nombreBarrio: string): string {
    let cod = this.normalizarCodigo(this.primerTexto(props, [
      'upz_codigo', 'UPZ_CODIGO', 'CODIGO_UPZ', 'UPlCodigo', 'upz',
    ]));
    if (!cod) {
      const codBarrio = this.normalizarCodigo(this.primerTexto(props, [
        'SCACODIGO', 'scacodigo', 'codigo', 'CODIGO', 'barrio_codigo',
      ]));
      cod = this.upzCodigoPorBarrioCodigo.get(codBarrio)
        || this.upzCodigoPorBarrioNombre.get(this.normalizarTexto(nombreBarrio))
        || '';
    }
    if (!cod) return 'UPZ no registrada';
    const nombre = this.upzNombrePorCodigo.get(cod);
    return nombre ? `UPZ ${cod} ${nombre}` : `UPZ ${cod}`;
  }

  /** Refresca la barra de estado con lo último que tocó el cursor. */
  private refrescarStatus(): void {
    if (!this.statusEl) return;
    // Sin capas de territorio prendidas la barra no tiene nada que decir:
    // se esconde en vez de quedarse ocupando la esquina con un texto muerto.
    this.statusEl.style.display =
      (this.capas.barrios || this.capas.upz) ? '' : 'none';
    // El texto por defecto decía "Pasa el cursor sobre el mapa": una
    // instrucción imposible de seguir en un celular, en la que además el
    // usuario táctil se queda esperando a que algo pase. Ahora nombra las dos
    // formas, y "toca" va primero porque el móvil es como más se abre esto.
    const texto = (this.hoverBarrio || this.hoverUpz)
      ? `${this.hoverBarrio || 'Barrio sin dato'} · ${this.hoverUpz || 'UPZ sin dato'}`
      : 'Toca o señala una zona para ver el barrio y la UPZ';
    this.statusEl.innerHTML =
      `<span class="mapa-status__txt">${this.esc(texto)}</span>`;
  }

  /** Control fijo abajo a la izquierda con el territorio bajo el cursor. */
  private agregarBarraEstado(): void {
    if (!this.map) return;
    const ctl = new L.Control({ position: 'bottomleft' });
    ctl.onAdd = () => {
      const div = L.DomUtil.create('div', 'mapa-status');
      this.statusEl = div;
      // Sin esto, un clic sobre la barra se propaga al mapa (zoom/arrastre).
      L.DomEvent.disableClickPropagation(div);
      this.refrescarStatus();
      return div;
    };
    ctl.addTo(this.map);
  }

  /**
   * Etiqueta permanente (nombre suelto sobre el polígono). `interactive:false`
   * es obligatorio: si no, el texto se come el clic de lo que tenga debajo.
   */
  private etiquetaDivIcon(texto: string, clase: string, latlng: L.LatLng): L.Marker {
    return L.marker(latlng, {
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: `mapa-etiqueta ${clase}`,
        html: `<span>${this.esc(texto)}</span>`,
        iconSize: undefined as any,
      }),
    });
  }

  /**
   * Muestra/esconde las etiquetas según el zoom: UPZ desde 13, barrio desde 15.
   * Antes de esos umbrales el mapa queda ilegible de tanto texto encimado.
   */
  private actualizarEtiquetas(): void {
    if (!this.map) return;
    const z = this.map.getZoom();
    const aplicar = (capa: L.LayerGroup | undefined, visible: boolean) => {
      if (!capa || !this.map) return;
      const puesta = this.map.hasLayer(capa);
      if (visible && !puesta) capa.addTo(this.map);
      else if (!visible && puesta) capa.remove();
    };
    aplicar(this.upzLabelsLayer, this.capas.upz && z >= 13);
    aplicar(this.barriosLabelsLayer, this.capas.barrios && z >= 15);
  }

  /**
   * Manda los polígonos al fondo del panel de overlays. Los marcadores de
   * eventos son `circleMarker` (SVG, mismo panel que los polígonos): sin esto
   * el barrio queda encima y se COME el clic del marcador — el bug que hoy
   * impide abrir los popups con las capas prendidas.
   *
   * El orden importa: cada llamada manda esa capa más atrás que la anterior,
   * así que se listan de adelante hacia atrás. Barrio va adelante de UPZ (es
   * el más específico: si el cursor está sobre un barrio, la respuesta útil es
   * el barrio, y su tooltip ya nombra la UPZ) y adelante de parques, que no
   * tienen interacción y taparían el hover del territorio.
   */
  private ordenarPoligonos(): void {
    this.barriosLayer?.bringToBack();
    this.parquesLayer?.bringToBack();
    this.upzLayer?.bringToBack();
    this.estratificacionLayer?.bringToBack();
  }

  private cargarUpzLazy(): void {
    if (this.upzLayer) return;
    this.setEstadoCapa('upz', 'cargando');
    this.geo.upzKennedy().subscribe({
      next: (fc) => {
      const etiquetas = L.layerGroup();
      const capa = L.geoJSON(fc as any, {
        style: () => ({ ...this.estiloUpz }),
        onEachFeature: (feat: any, lyr: any) => {
          const props = feat?.properties ?? {};
          const nombre = this.primerTexto(props, ['NOMBRE', 'UPlNombre', 'nombre'])
            || 'UPZ sin nombre';
          const cod = this.normalizarCodigo(this.primerTexto(props, [
            'CODIGO_UPZ', 'UPlCodigo', 'codigo', 'upz_codigo',
          ]));
          const texto = cod ? `UPZ ${cod} · ${nombre}` : `UPZ · ${nombre}`;
          // sticky: la etiqueta persigue al cursor en vez de quedarse fija en
          // el centro del polígono, que en una UPZ entera queda lejísimos.
          lyr.bindTooltip(texto, { sticky: true, direction: 'top', className: 'mapa-tip mapa-tip--upz' });
          lyr.on('mouseover', () => {
            lyr.setStyle(this.estiloUpzHover);
            this.hoverUpz = texto;
            this.refrescarStatus();
          });
          lyr.on('mouseout', () => {
            capa.resetStyle(lyr);
            this.hoverUpz = '';
            this.refrescarStatus();
          });
          // Toque: en un celular no hay hover. Sin esto el nombre de la UPZ era
          // sencillamente inalcanzable desde un teléfono, que es como se abre la
          // mayoría de los enlaces que reparte la Alcaldía.
          lyr.on('click', (ev: L.LeafletMouseEvent) => {
            this.hoverUpz = texto;
            this.refrescarStatus();
            lyr.openTooltip(ev.latlng);
          });
          try {
            const centro = lyr.getBounds?.()?.getCenter?.();
            if (centro) etiquetas.addLayer(this.etiquetaDivIcon(nombre, 'mapa-etiqueta--upz', centro));
          } catch { /* sin bounds, sin etiqueta */ }
        },
      });
      this.upzLayer = capa;
      this.upzLabelsLayer = etiquetas;
      this.setEstadoCapa('upz', capa.getLayers().length ? 'ok' : 'vacia');
      if (this.capas.upz && this.map) {
        capa.addTo(this.map);
        this.ordenarPoligonos();
        this.actualizarEtiquetas();
      }
      },
      error: (e) => this.errorDeCapa('upz', e),
    });
  }

  private cargarBarriosLazy(): void {
    if (this.barriosLayer) return;
    this.setEstadoCapa('barrios', 'cargando');
    this.geo.barriosKennedy().subscribe({
      next: (fc) => {
      const etiquetas = L.layerGroup();
      const capa = L.geoJSON(fc as any, {
        style: () => ({ ...this.estiloBarrio }),
        onEachFeature: (feat: any, lyr: any) => {
          const props = feat?.properties ?? {};
          const nombre = this.primerTexto(props, ['NOMBRE', 'nombre', 'SCANOMBRE'])
            || 'Barrio sin nombre';
          const upz = this.upzDeBarrio(props, nombre);
          lyr.bindTooltip(
            `<strong>${this.esc(nombre)}</strong><br><small>${this.esc(upz)}</small>`,
            { sticky: true, direction: 'top', className: 'mapa-tip mapa-tip--barrio' },
          );
          lyr.on('mouseover', () => {
            lyr.setStyle(this.estiloBarrioHover);
            this.hoverBarrio = nombre;
            this.hoverUpz = upz;
            this.refrescarStatus();
          });
          lyr.on('mouseout', () => {
            capa.resetStyle(lyr);
            this.hoverBarrio = '';
            this.refrescarStatus();
          });
          // Toque: sin esto el nombre del barrio no existe en móvil (ver UPZ).
          lyr.on('click', (ev: L.LeafletMouseEvent) => {
            this.hoverBarrio = nombre;
            this.hoverUpz = upz;
            this.refrescarStatus();
            lyr.openTooltip(ev.latlng);
          });
          try {
            const centro = lyr.getBounds?.()?.getCenter?.();
            if (centro) etiquetas.addLayer(this.etiquetaDivIcon(nombre, 'mapa-etiqueta--barrio', centro));
          } catch { /* sin bounds, sin etiqueta */ }
        },
      });
      this.barriosLayer = capa;
      this.barriosLabelsLayer = etiquetas;
      this.setEstadoCapa('barrios', capa.getLayers().length ? 'ok' : 'vacia');
      if (this.capas.barrios && this.map) {
        capa.addTo(this.map);
        this.ordenarPoligonos();
        this.actualizarEtiquetas();
      }
      },
      error: (e) => this.errorDeCapa('barrios', e),
    });
  }

  private cargarEstratificacionLazy(): void {
    if (this.estratificacionLayer || this.estratificacionCargando) return;
    // 4.966 manzanas recortadas a Kennedy, ~1 MB gzip: se siente. Sin avisar que
    // está cargando, el usuario prende el check, no ve nada y cree que está roto.
    this.estratificacionCargando = true;
    // Sin filtro (todos los estratos) no se manda el parámetro: el servidor
    // sirve la capa completa y su caché de 1 h se aprovecha entera.
    const filtro = this.todosLosEstratos() ? undefined : this.estratosVisibles();
    this.geo.estratificacionKennedy(filtro).subscribe({
      next: (fc) => {
        this.estratificacionCargando = false;
        if (!this.map) return;
        // Una capa vacía no es un caso normal: la tabla tiene ~19k manzanas y el
        // endpoint recorta a las de Kennedy. Cero features = algo está mal, y hay
        // que decirlo en vez de dejar el check prendido sin dibujar nada.
        if (!fc?.features?.length) {
          if (filtro) {
            // Con filtro puesto, cero manzanas es una respuesta legítima: en
            // Kennedy hay estratos que casi no existen. Apagar la capa acá sería
            // castigar al usuario por haber filtrado bien.
            this.setEstadoCapa('estratificacion', 'vacia');
            return;
          }
          this.errorMsg.set('Estratificación: el servidor no devolvió manzanas.');
          this.capas.estratificacion = false;
          return;
        }
        this.setEstadoCapa('estratificacion', 'ok');
        // Misma receta que las capas que SÍ se ven (parques/UPZ/barrios):
        // renderer SVG por defecto en el overlayPane, encima del basemap. El
        // intento anterior con `L.canvas()` caía por debajo de las teselas
        // (regla `.leaflet-map-pane canvas { z-index: 100 }` de leaflet.css).
        this.estratificacionLayer = L.geoJSON(fc as any, {
          style: (f: any) => {
            const color = this.colorEstrato(f?.properties?.estrato);
            return { color, weight: 0.3, fillColor: color, fillOpacity: 0.55 };
          },
          onEachFeature: (f: any, layer) => {
            const e = f?.properties?.estrato;
            const cod = f?.properties?.codigo_manzana;
            // El estrato primero, que es lo que la persona vino a ver. El
            // código catastral de la manzana es un identificador interno: sirve
            // para reportar un error, no para informar, así que va debajo y
            // rotulado como lo que es.
            layer.bindPopup(
              `<b>Estrato ${e ?? 'sin registrar'}</b>`
              + (cod ? `<br><small>Manzana catastral ${this.esc(String(cod))}</small>` : ''),
            );
          },
        });
        if (this.capas.estratificacion) this.estratificacionLayer.addTo(this.map);
      },
      error: (e) => {
        // Antes esto se tragaba el error entero: el check quedaba prendido, el
        // mapa vacío y ni una pista de por qué.
        this.estratificacionCargando = false;
        this.capas.estratificacion = false;
        this.errorDeCapa('estratificacion', e);
        this.errorMsg.set('No se pudo cargar la estratificación. Reintenta en un momento.');
      },
    });
  }

  cargarEventos(): void {
    const filtros: EventoFiltros = {
      tipo_evento: this.selectedTipos.length ? this.selectedTipos : undefined,
      subgrupo_id: this.selectedSubgrupos.length
        ? this.selectedSubgrupos.map(Number) : undefined,
      dependencia_id: this.selectedDependencia ?? undefined,
    };
    this.loading.set(true);
    this.geo.eventos(filtros).subscribe({
      next: (fc) => {
        // Un banner que nunca se limpia miente en cuanto la causa desaparece:
        // antes NO había ni un solo errorMsg.set('') en el archivo, así que el
        // aviso quedaba hasta recargar la página.
        this.errorMsg.set('');
        this.eventos.set(fc);
        this.renderEventos();
        this.loading.set(false);
      },
      error: (e) => {
        this.errorMsg.set(
          (e as { status?: number })?.status === 401
            ? 'No se pudieron cargar las actividades.'
            : 'No se pudieron cargar las actividades. Reintenta en un momento.',
        );
        this.loading.set(false);
      },
    });
  }

  /** Separación del abanico al desapilar, en grados (~44 m). */
  private readonly RADIO_DESAPILADO = 0.0004;

  renderEventos(): void {
    if (!this.map || !this.eventoLayer) return;
    this.eventoLayer.clearLayers();

    // Lee los FILTRADOS, no todos.
    //
    // Antes iteraba `this.eventos().features` mientras la tabla y los KPIs
    // usaban `eventosFiltrados()`: escribir en "Buscar" cambiaba la tabla y el
    // contador pero NO los marcadores, así que la página se contradecía a sí
    // misma en pantalla.
    const feats = this.eventosFiltrados();

    // Agrupar por coordenada para desapilar.
    //
    // Todo evento creado sin coordenadas queda en la sede de la Alcaldía (es la
    // ubicación de respaldo del backend). El resultado es que N actividades se
    // pintan en el MISMO píxel: se ve un punto solo, el popup que abre es el
    // del marcador que quedó encima, y al filtrar por subgrupo el punto no
    // desaparece porque abajo sigue habiendo otros. Se lee como si el filtro
    // estuviera roto y no lo está.
    const grupos = new Map<string, { lat: number; lng: number; items: GeoFeature[] }>();
    for (const f of feats) {
      const geom = f.geometry;
      if (geom?.type !== 'Point' || !Array.isArray(geom.coordinates)) continue;
      const lng = Number(geom.coordinates[0]);
      const lat = Number(geom.coordinates[1]);
      if (isNaN(lat) || isNaN(lng)) continue;

      const clave = `${lat.toFixed(6)},${lng.toFixed(6)}`;
      const g = grupos.get(clave);
      if (g) g.items.push(f);
      else grupos.set(clave, { lat, lng, items: [f] });
    }

    for (const { lat, lng, items } of grupos.values()) {
      const n = items.length;
      items.forEach((f, i) => {
        const p = f.properties;
        let mLat = lat;
        let mLng = lng;

        // Abanico alrededor del punto real. Se abre en anillos de 8 para que
        // 30 marcadores no queden pegados; la corrección por coseno evita que
        // el círculo se vea ovalado en la latitud de Bogotá.
        if (n > 1) {
          const anillo = Math.floor(i / 8);
          const enAnillo = Math.min(n - anillo * 8, 8);
          const ang = (2 * Math.PI * (i % 8)) / enAnillo;
          const r = this.RADIO_DESAPILADO * (1 + anillo);
          mLat = lat + r * Math.cos(ang);
          mLng = lng + (r * Math.sin(ang)) / Math.cos((lat * Math.PI) / 180);
        }

        const aprox = !!p['ubicacion_aproximada'];
        const marker = L.circleMarker([mLat, mLng], {
          radius: 7,
          weight: 2,
          // Borde punteado y relleno más pálido = "no sabemos dónde fue".
          // La diferencia se ve sin leer el popup y sin depender del color,
          // que ya está ocupado por el tipo de evento.
          color: aprox ? '#6B7280' : '#fff',
          dashArray: aprox ? '3,3' : undefined,
          fillColor: this.colorTipo(p.tipo_evento_codigo),
          fillOpacity: aprox ? 0.55 : 0.95,
        });
        marker.bindPopup(this.popupHtml(p));
        marker.addTo(this.eventoLayer!);
      });
    }
  }

  private popupHtml(p: Record<string, any>): string {
    const fila = (label: string, value: any) =>
      value ? `<div><strong>${label}:</strong> ${value}</div>` : '';
    // El aviso va ARRIBA, antes que la dirección: si el punto no es dónde pasó
    // la actividad, eso es lo primero que hay que saber. Ponerlo al final
    // equivale a esconderlo.
    const avisoAprox = p['ubicacion_aproximada']
      ? `<p class="mapa-popup__aviso">
           <strong>Ubicación no registrada.</strong> Esta actividad se muestra
           en la sede de la Alcaldía porque no tiene dirección propia en el
           sistema. No ocurrió necesariamente en este punto.
         </p>`
      : '';

    return `
      <div class="mapa-popup">
        <h4>${p['nombre'] || 'Evento'}</h4>
        ${avisoAprox}
        ${fila('Tipo', this.tipoNombre(p['tipo_evento_codigo']))}
        ${p['fecha_inicio'] ? fila('Fecha', this.fechaLegible(p['fecha_inicio'])) : ''}
        ${fila('Dependencia', p['dependencia'])}
        ${fila('Subgrupo', p['subgrupo'])}
        ${fila('Funcionario', p['funcionario'])}
        ${fila('Dirección', p['direccion'])}
        ${fila('Meta a la que aporta', p['indicador'])}
        ${fila('Cantidad aportada', p['magnitud_aportada'])}
        ${p['caracterizaciones'] ? fila('Caracterizaciones', p['caracterizaciones'].total + (p['caracterizaciones'].sector ? ' · ' + p['caracterizaciones'].sector : '')) : ''}
      </div>
    `;
  }

  // ── UI handlers ─────────────────────────────────────────────────
  onFiltrosChange(): void {
    this.cargarEventos();
  }

  /** Multi-selección por clic simple (sin Ctrl) para Tipo de evento. */
  toggleTipo(codigo: string): void {
    const i = this.selectedTipos.indexOf(codigo);
    this.selectedTipos = i === -1
      ? [...this.selectedTipos, codigo]
      : this.selectedTipos.filter(c => c !== codigo);
    this.cargarEventos();
    this.urlSync$.next();
  }

  /** Multi-selección por clic simple (sin Ctrl) para Subgrupo. */
  toggleSubgrupo(id: number): void {
    const i = this.selectedSubgrupos.indexOf(id);
    this.selectedSubgrupos = i === -1
      ? [...this.selectedSubgrupos, id]
      : this.selectedSubgrupos.filter(s => s !== id);
    this.cargarEventos();
    this.urlSync$.next();
  }
  onDependenciaChange(): void {
    // limpia subgrupos al cambiar dependencia
    this.selectedSubgrupos = [];
    this.cargarEventos();
    this.urlSync$.next();
  }
  onBuscar(): void {
    // El filtro es client-side (computed); acá solo se refleja en la URL. El
    // debounce de 350 ms absorbe el tecleo → un solo navigate.
    this.urlSync$.next();
  }

  limpiarFiltros(): void {
    this.query = '';
    this.selectedTipos = [];
    this.selectedSubgrupos = [];
    this.selectedDependencia = null;
    this.subgrupoTab.set(null);
    this.cargarEventos();
    this.urlSync$.next();
  }

  setSubgrupoTab(id: number | null): void {
    this.subgrupoTab.set(id);
    this.selectedSubgrupos = id ? [id] : [];
    // El equipamiento es propio de cada subgrupo (decisión Alex 2026-06-03):
    //   Cultura → solo Escuelas de Cultura.
    //   Deporte → solo Escuelas de Deporte.
    //   Otros / Todos → sin equipamiento (cada subgrupo es distinto).
    const nombre = id
      ? (this.subgruposInversion().find(s => s.id === id)?.nombre || '').toLowerCase()
      : '';
    this.capas.escuelasCultura = nombre === 'cultura';
    this.capas.escuelasDeporte = nombre === 'deporte';
    this.toggleCapa('escuelasCultura');
    this.toggleCapa('escuelasDeporte');
    this.cargarEventos();
  }

  toggleCapa(
    nombre: 'parques' | 'barrios' | 'upz' | 'localidad'
          | 'escuelasCultura' | 'escuelasDeporte'
          | 'festivales' | 'tramosViales' | 'parquesObras' | 'estratificacion'
          | 'banco' | 'colegios' | 'cai',
  ): void {
    if (!this.map) return;
    // C1: cualquier cambio de capa se refleja en la URL (el objeto `capas` no es
    // signal, por eso el disparo va aquí y no en el effect).
    this.urlSync$.next();
    const on = (this.capas as any)[nombre];
    if (nombre === 'estratificacion') {
      if (on) {
        this.cargarEstratificacionLazy();
        this.estratificacionLayer?.addTo(this.map);
        this.ordenarPoligonos();
      } else this.estratificacionLayer?.remove();
      return;
    }
    if (nombre === 'festivales') {
      if (on) { this.cargarFestivales(); this.festivalesLayer?.addTo(this.map); }
      else this.festivalesLayer?.remove();
      return;
    }
    if (nombre === 'tramosViales') {
      if (on) { this.cargarTramos(); this.tramosLayer?.addTo(this.map); }
      else this.tramosLayer?.remove();
      return;
    }
    if (nombre === 'parquesObras') {
      if (on) { this.cargarParquesObras(); this.parquesObrasLayer?.addTo(this.map); }
      else this.parquesObrasLayer?.remove();
      return;
    }
    if (nombre === 'banco') {
      if (on) { this.cargarBanco(); this.bancoLayer?.addTo(this.map); }
      else this.bancoLayer?.remove();
      return;
    }
    if (nombre === 'colegios') {
      if (on) { this.cargarColegios(); this.colegiosLayer?.addTo(this.map); }
      else this.colegiosLayer?.remove();
      return;
    }
    if (nombre === 'cai') {
      if (on) { this.cargarCai(); this.caiLayer?.addTo(this.map); }
      else this.caiLayer?.remove();
      return;
    }
    if (nombre === 'parques') {
      if (on) {
        this.cargarParquesLazy();
        this.parquesLayer?.addTo(this.map);
        this.ordenarPoligonos();
      } else this.parquesLayer?.remove();
    } else if (nombre === 'barrios') {
      if (on) {
        this.cargarBarriosLazy();
        this.barriosLayer?.addTo(this.map);
        this.ordenarPoligonos();
      } else {
        this.barriosLayer?.remove();
        this.hoverBarrio = '';
        this.refrescarStatus();
      }
      this.actualizarEtiquetas();
    } else if (nombre === 'upz') {
      if (on) {
        this.cargarUpzLazy();
        this.upzLayer?.addTo(this.map);
        this.ordenarPoligonos();
      } else {
        this.upzLayer?.remove();
        this.hoverUpz = '';
        this.refrescarStatus();
      }
      this.actualizarEtiquetas();
    } else if (nombre === 'localidad') {
      if (on && this.contornoLayer) this.contornoLayer.addTo(this.map);
      else this.contornoLayer?.remove();
    } else if (nombre === 'escuelasCultura') {
      if (on && this.escuelasCulturaLayer) this.escuelasCulturaLayer.addTo(this.map);
      else this.escuelasCulturaLayer?.remove();
    } else if (nombre === 'escuelasDeporte') {
      if (on && this.escuelasDeporteLayer) this.escuelasDeporteLayer.addTo(this.map);
      else this.escuelasDeporteLayer?.remove();
    }
  }

  centrar(f: GeoFeature): void {
    if (!this.map) return;
    const g = f.geometry;
    if (g?.type === 'Point' && Array.isArray(g.coordinates)) {
      this.map.setView([Number(g.coordinates[1]), Number(g.coordinates[0])], 16);
    }
  }

  colorTipo(codigo: string): string {
    const t = this.catalogos()?.tipos_evento.find(x => x.codigo === codigo);
    return t?.color_hex || '#6B7280';
  }

  /**
   * Color de texto legible sobre `fondo`: negro o blanco, el que contraste.
   *
   * La píldora de tipo en la tabla llevaba `color: white` fijo sobre un fondo
   * que sale de la BD (`tipo_evento.color_hex`). Basta con que un administrador
   * cargue un amarillo o un celeste para que el texto quede ilegible, y nadie
   * lo notaría al guardarlo: el fallo aparece en una tabla del mapa público,
   * lejos del formulario donde se eligió el color.
   *
   * Umbral 0.6 sobre luminancia relativa (WCAG 2.x): por encima, negro; por
   * debajo, blanco. Con los colores del catálogo actual da ≥ 4.5:1 en los dos
   * sentidos.
   */
  textoSobre(fondo: string): string {
    const hex = (fondo || '').replace('#', '').trim();
    const full = hex.length === 3
      ? hex.split('').map(c => c + c).join('')
      : hex;
    if (full.length !== 6 || /[^0-9a-fA-F]/.test(full)) return '#fff';

    const canal = (i: number) => {
      const v = parseInt(full.slice(i, i + 2), 16) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    const lum = 0.2126 * canal(0) + 0.7152 * canal(2) + 0.0722 * canal(4);
    return lum > 0.6 ? '#111827' : '#fff';
  }

  /**
   * Nombre de display de un tipo de evento.
   *
   * El catálogo del backend manda. El fallback ANTES era `codigo`, así que
   * mientras los catálogos no habían cargado —o si llegaba un código que no
   * empareja— la tabla y los popups pintaban literales internos como
   * `BANCO_INICIATIVAS` o `ESTIMULO_CULTURAL` a un ciudadano. Ahora cae en el
   * catálogo compartido, que además traduce SNAKE_CASE a texto legible.
   */
  tipoNombre(codigo: string): string {
    const t = this.catalogos()?.tipos_evento.find(x => x.codigo === codigo);
    return t?.nombre || tipoEventoNombre(codigo);
  }

  /** Fecha ISO → "15 de julio de 2026". */
  fechaLegible(iso: unknown): string {
    return formatFecha(iso);
  }
}

// Cast local porque el modelo del backend tiene optional fields
type MapaCatalogosLocal = {
  upz: any[];
  barrios: any[];
  tipos_evento: TipoEventoLite[];
  dependencias: any[];
  subgrupos: SubgrupoLite[];
  subgrupos_inversion_local: SubgrupoLite[];
  conteos_subgrupo: Record<number, ConteoSubgrupo>;
};
