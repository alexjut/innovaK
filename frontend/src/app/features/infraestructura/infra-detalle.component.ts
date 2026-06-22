import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatMoneda } from '../../shared/format/format.util';
import { ConfirmService } from '../../shared/ui/confirm.service';
import { ToastService } from '../../shared/ui/toast.service';
import { InfraestructuraApi } from './infraestructura.api';
import {
  ContratoInfraDetalle,
  CorteAvance,
  CorteInput,
  EstadoAvance,
  InfraCatalogos,
  InfraFeatureCollection,
  ObjetoCorte,
  ParqueCatalogo,
  ParqueInput,
  ParqueIntervencion,
  TramoInput,
  TramoVial,
} from './infraestructura.types';

const ESTADO_LBL: Record<EstadoAvance, string> = {
  sin_iniciar: 'Sin iniciar', parcial: 'En ejecución', terminado: 'Terminado',
};

/** Color de avance: 🔴 0 / 🟠 parcial / 🟢 100. */
function colorAvance(pct: number): string {
  if (pct >= 100) return '#16a34a';
  if (pct > 0) return '#f59e0b';
  return '#dc2626';
}

/**
 * Detalle de un contrato de infraestructura. DATA-DRIVEN por categoría:
 *  - VIAS  → tabla de tramos (eje/desde/hasta/CIV/valor/avance), edición inline
 *            del % avance, estado geo, y form "Agregar vía" (geometría auto).
 *  - PARQUES → tabla de parques con selector de catálogo (554) que autocompleta
 *            nombre + dirección, edición inline del % avance.
 *  - INTERVENTORIA → solo seguimiento por cortes (no captura geo).
 *
 * SEGUIMIENTO POR CORTES (cómo el responsable "aumenta las cosas"):
 *  - Botón grande "Registrar avance" a nivel del contrato (única forma de
 *    avanzar una INTERVENTORÍA) + acción por cada vía/parque en su fila.
 *  - Cada corte queda en un historial (fecha, %, observación, foto cifrada).
 *  - Mini-mapa Leaflet con las geometrías coloreadas por % de avance.
 */
@Component({
  standalone: true,
  selector: 'app-infra-detalle',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando contrato…</div> }
      @if (!loading() && error()) {
        <div class="ui-info-bar ui-info-bar--danger"><strong>Error:</strong> {{ error() }}</div>
        <a routerLink="/infraestructura" class="ui-btn ui-btn--ghost"><i class="fa fa-arrow-left"></i> Volver</a>
      }

      @if (!loading() && !error() && contrato(); as c) {
        <header class="page__header">
          <div>
            <h1><i class="fa fa-file-contract" aria-hidden="true"></i> {{ c.numero }}</h1>
            <p class="page__sub">
              <span class="badge badge--{{ c.categoria }}">{{ catLabel(c.categoria) }}</span>
              @if (c.proyecto_codigo) {
                <a [routerLink]="['/presupuesto/proyectos']" class="chip chip--link">
                  <i class="fa fa-coins"></i> {{ c.proyecto_codigo }}
                </a>
              }
            </p>
          </div>
          <div class="actions">
            <a routerLink="/infraestructura" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left"></i> Listado
            </a>
            <a routerLink="/mapa" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-map-marked-alt"></i> Ver en el Mapa Kennedy
            </a>
          </div>
        </header>

        <!-- Cabecera del contrato -->
        <section class="cab">
          <dl>
            <div><dt>Objeto</dt><dd>{{ c.objeto || '—' }}</dd></div>
            <div><dt>Proyecto</dt><dd>{{ c.proyecto_nombre || '—' }}</dd></div>
            <div><dt>Valor</dt><dd>{{ moneda(c.valor) }}</dd></div>
            <div><dt>Vigencia</dt><dd>{{ c.fecha_inicio || '—' }} → {{ c.fecha_fin || '—' }}</dd></div>
            <div><dt>Interventoría</dt>
              <dd>
                {{ c.interventoria_contrato || '—' }}
                @if (c.interventoria_valor != null) { · {{ moneda(c.interventoria_valor) }} }
              </dd>
            </div>
            <div class="ejc-block"><dt>Ejecución</dt>
              <dd>
                <div class="ejc">
                  <div class="ejc__bar"><div class="ejc__fill" [class]="ejecClase(c.ejecucion)" [style.width.%]="c.ejecucion || 0"></div></div>
                  <b>{{ c.ejecucion || 0 }}%</b>
                </div>
              </dd>
            </div>
          </dl>

          <!-- Registrar avance del contrato: prominente, siempre visible -->
          <div class="cab__cta">
            <button class="ui-btn ui-btn--primary cta-avance" (click)="abrirCorteContrato(c)">
              <i class="fa fa-chart-line"></i> Registrar avance
            </button>
            <span class="cta-hint">
              @if (c.categoria === 'INTERVENTORIA') {
                Registra el seguimiento de la interventoría por cortes (fecha, % y evidencia).
              } @else {
                Avance global del contrato. También puedes registrar avance por cada vía o parque abajo.
              }
            </span>
          </div>
        </section>

        <!-- ── MINI-MAPA ─────────────────────────────────────────── -->
        @if (tieneGeometrias()) {
          <section class="block block--map">
            <div class="block__head">
              <h2><i class="fa fa-map-location-dot"></i> Ubicación de la intervención</h2>
            </div>
            <div #miniMapa class="mini-map"></div>
            <div class="leyenda">
              <span><i class="dot" style="background:#dc2626"></i> Sin iniciar (0%)</span>
              <span><i class="dot" style="background:#f59e0b"></i> En ejecución</span>
              <span><i class="dot" style="background:#16a34a"></i> Terminado (100%)</span>
            </div>
          </section>
        } @else if (c.categoria === 'INTERVENTORIA') {
          <section class="block">
            <div class="ui-info-bar ui-info-bar--info">
              <i class="fa fa-clipboard-check"></i>
              Este contrato no tiene vías ni parques (interventoría). Su avance se mide solo por cortes de seguimiento.
            </div>
          </section>
        }

        <!-- ── VIAS ──────────────────────────────────────────────── -->
        @if (c.categoria === 'VIAS') {
          <section class="block">
            <div class="block__head">
              <h2><i class="fa fa-road"></i> Tramos viales ({{ c.tramos.length }})</h2>
              @if (esAdmin()) {
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="abrirTramo()">
                  <i class="fa fa-plus"></i> Agregar vía
                </button>
              }
            </div>

            @if (c.tramos.length === 0) {
              <div class="ui-empty-state ui-empty-state--sm">
                <i class="fa fa-road"></i>
                @if (esAdmin()) {
                  <p>Este contrato aún no tiene tramos. Agrega una vía por su CIV; la geometría se ubica en el mapa automáticamente.</p>
                } @else {
                  <p>Este contrato aún no tiene tramos registrados.</p>
                }
              </div>
            } @else {
              <div class="tabla-wrap">
                <table class="tabla">
                  <thead>
                    <tr>
                      <th>Eje Vial</th><th>Desde</th><th>Hasta</th><th>CIV</th>
                      <th class="num">Valor Intervención</th>
                      <th class="avc">% Avance</th><th>Geo</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (t of c.tramos; track t.id) {
                      <tr>
                        <td><strong>{{ t.eje_vial || '—' }}</strong></td>
                        <td>{{ t.desde || '—' }}</td>
                        <td>{{ t.hasta || '—' }}</td>
                        <td>{{ t.civ }}</td>
                        <td class="num">{{ moneda(t.valor_intervencion) }}</td>
                        <td class="avc">
                          <div class="inline-edit">
                            @if (esAdmin()) {
                              <input type="number" min="0" max="100" class="ui-input ui-input--sm"
                                     [ngModel]="t.pct_avance"
                                     (ngModelChange)="setTramoAvance(t, $event)"
                                     (blur)="guardarTramoAvance(t)"
                                     (keyup.enter)="guardarTramoAvance(t)">
                            } @else {
                              <span class="pct-ro">{{ t.pct_avance }}%</span>
                            }
                            <span class="badge badge--{{ t.estado }}">{{ estadoLbl(t.estado) }}</span>
                          </div>
                        </td>
                        <td>
                          @if (t.geo_status === 'OK') {
                            <span class="geo geo--ok" title="Ubicado en el mapa"><i class="fa fa-map-pin"></i> en mapa</span>
                          } @else {
                            <span class="geo geo--no" title="Sin geometría resuelta"><i class="fa fa-triangle-exclamation"></i> sin geo</span>
                          }
                        </td>
                        <td class="acc">
                          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="abrirCorteTramo(t)" title="Registrar avance">
                            <i class="fa fa-chart-line"></i>
                          </button>
                          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="toggleHistorial('tramo', t.id)"
                                  [class.on]="esHistAbierto('tramo', t.id)" title="Ver historial de cortes">
                            <i class="fa fa-clock-rotate-left"></i>
                          </button>
                          @if (esAdmin()) {
                            <button class="ui-btn ui-btn--ghost ui-btn--sm danger" (click)="eliminarTramo(t)"
                                    [disabled]="eliminando() === 't' + t.id" title="Quitar tramo">
                              @if (eliminando() === 't' + t.id) { <i class="fa fa-spinner fa-spin"></i> }
                              @else { <i class="fa fa-trash"></i> }
                            </button>
                          }
                        </td>
                      </tr>
                      @if (esHistAbierto('tramo', t.id)) {
                        <tr class="hist-row">
                          <td colspan="8">
                            <ng-container [ngTemplateOutlet]="histTpl"
                              [ngTemplateOutletContext]="{ $implicit: histDe('tramo', t.id) }"></ng-container>
                          </td>
                        </tr>
                      }
                    }
                  </tbody>
                </table>
              </div>
            }
          </section>
        }

        <!-- ── PARQUES ───────────────────────────────────────────── -->
        @else if (c.categoria === 'PARQUES') {
          <section class="block">
            <div class="block__head">
              <h2><i class="fa fa-tree"></i> Parques intervenidos ({{ c.parques.length }})</h2>
              @if (esAdmin()) {
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="abrirParque()">
                  <i class="fa fa-plus"></i> Agregar parque
                </button>
              }
            </div>

            @if (c.parques.length === 0) {
              <div class="ui-empty-state ui-empty-state--sm">
                <i class="fa fa-tree"></i>
                @if (esAdmin()) {
                  <p>Este contrato aún no tiene parques. Vincula uno del catálogo; ya trae su ubicación para el mapa.</p>
                } @else {
                  <p>Este contrato aún no tiene parques registrados.</p>
                }
              </div>
            } @else {
              <div class="tabla-wrap">
                <table class="tabla">
                  <thead>
                    <tr><th>Código Parque</th><th>Nombre</th><th>Dirección</th><th class="avc">% Avance</th><th></th></tr>
                  </thead>
                  <tbody>
                    @for (p of c.parques; track p.id) {
                      <tr>
                        <td><strong>{{ p.codigo_parque ?? '—' }}</strong></td>
                        <td>{{ p.nombre || '—' }}</td>
                        <td class="dir">{{ p.direccion || '—' }}</td>
                        <td class="avc">
                          <div class="inline-edit">
                            @if (esAdmin()) {
                              <input type="number" min="0" max="100" class="ui-input ui-input--sm"
                                     [ngModel]="p.pct_avance"
                                     (ngModelChange)="setParqueAvance(p, $event)"
                                     (blur)="guardarParqueAvance(p)"
                                     (keyup.enter)="guardarParqueAvance(p)">
                            } @else {
                              <span class="pct-ro">{{ p.pct_avance }}%</span>
                            }
                            <span class="badge badge--{{ p.estado }}">{{ estadoLbl(p.estado) }}</span>
                          </div>
                        </td>
                        <td class="acc">
                          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="abrirCorteParque(p)" title="Registrar avance">
                            <i class="fa fa-chart-line"></i>
                          </button>
                          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="toggleHistorial('parque', p.id)"
                                  [class.on]="esHistAbierto('parque', p.id)" title="Ver historial de cortes">
                            <i class="fa fa-clock-rotate-left"></i>
                          </button>
                          @if (esAdmin()) {
                            <button class="ui-btn ui-btn--ghost ui-btn--sm danger" (click)="eliminarParque(p)"
                                    [disabled]="eliminando() === 'p' + p.id" title="Quitar parque">
                              @if (eliminando() === 'p' + p.id) { <i class="fa fa-spinner fa-spin"></i> }
                              @else { <i class="fa fa-trash"></i> }
                            </button>
                          }
                        </td>
                      </tr>
                      @if (esHistAbierto('parque', p.id)) {
                        <tr class="hist-row">
                          <td colspan="5">
                            <ng-container [ngTemplateOutlet]="histTpl"
                              [ngTemplateOutletContext]="{ $implicit: histDe('parque', p.id) }"></ng-container>
                          </td>
                        </tr>
                      }
                    }
                  </tbody>
                </table>
              </div>
            }
          </section>
        }

        <!-- ── Historial del contrato (cortes a nivel global) ────── -->
        <section class="block">
          <div class="block__head">
            <h2><i class="fa fa-clock-rotate-left"></i> Historial de cortes del contrato</h2>
            <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="toggleHistorial('contrato', 0)"
                    [class.on]="esHistAbierto('contrato', 0)">
              {{ esHistAbierto('contrato', 0) ? 'Ocultar' : 'Ver' }} historial
            </button>
          </div>
          @if (esHistAbierto('contrato', 0)) {
            <ng-container [ngTemplateOutlet]="histTpl"
              [ngTemplateOutletContext]="{ $implicit: histDe('contrato', 0) }"></ng-container>
          }
        </section>
      }
    </div>

    <!-- Template reusable: historial de cortes de un objeto -->
    <ng-template #histTpl let-cortes>
      @if (!cortes) {
        <div class="hist hist--load"><i class="fa fa-spinner fa-spin"></i> Cargando historial…</div>
      } @else if (cortes.length === 0) {
        <div class="hist hist--empty">Sin cortes registrados todavía.</div>
      } @else {
        <ul class="hist">
          @for (corte of cortes; track corte.id) {
            <li class="hist__item">
              <div class="hist__meta">
                <span class="hist__pct" [style.color]="colorPct(corte.pct)">{{ corte.pct }}%</span>
                <span class="hist__fecha"><i class="fa fa-calendar-day"></i> {{ corte.fecha }}</span>
              </div>
              @if (corte.observacion) { <p class="hist__obs">{{ corte.observacion }}</p> }
              @if (corte.tiene_foto_antes || corte.tiene_foto_despues) {
                <div class="hist__fotos">
                  @if (corte.tiene_foto_antes) {
                    <figure class="hist__foto-fig">
                      <figcaption class="hist__foto-cap">Antes</figcaption>
                      @if (fotoUrl(corte.id, 'antes'); as src) {
                        <img [src]="src" class="hist__foto" alt="Evidencia antes"
                             (click)="ampliarFoto(corte.id, 'antes')" title="Ver más grande">
                      } @else {
                        <button class="hist__foto-load" (click)="cargarFoto(corte.id, 'antes')">
                          <i class="fa fa-image"></i> Ver foto
                        </button>
                      }
                    </figure>
                  }
                  @if (corte.tiene_foto_despues) {
                    <figure class="hist__foto-fig">
                      <figcaption class="hist__foto-cap">Después</figcaption>
                      @if (fotoUrl(corte.id, 'despues'); as src) {
                        <img [src]="src" class="hist__foto" alt="Evidencia después"
                             (click)="ampliarFoto(corte.id, 'despues')" title="Ver más grande">
                      } @else {
                        <button class="hist__foto-load" (click)="cargarFoto(corte.id, 'despues')">
                          <i class="fa fa-image"></i> Ver foto
                        </button>
                      }
                    </figure>
                  }
                </div>
              }
            </li>
          }
        </ul>
      }
    </ng-template>

    <!-- Modal: registrar corte de avance (reusable) -->
    @if (corteForm(); as cf) {
      <div class="modal" (click)="cerrarCorte()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2><i class="fa fa-chart-line"></i> Registrar avance</h2>
          <p class="modal__hint">{{ corteAlcance() }}</p>
          @if (corteError()) { <div class="ui-info-bar ui-info-bar--danger">{{ corteError() }}</div> }

          <div class="row">
            <label>Fecha *
              <input type="date" class="ui-input" [(ngModel)]="cf.fecha">
            </label>
            <label>% Avance *
              <input type="number" min="0" max="100" class="ui-input" [(ngModel)]="cf.pct"
                     (ngModelChange)="setCortePct($event)">
            </label>
          </div>
          <input type="range" min="0" max="100" class="slider" [ngModel]="cf.pct"
                 (ngModelChange)="setCortePct($event)">

          <label>Observación
            <textarea class="ui-input" rows="3" [(ngModel)]="cf.observacion"
                      placeholder="¿Qué se ejecutó en este corte?"></textarea>
          </label>

          <div class="fotos-row">
            <div class="foto-block">
              <span class="foto-block__title">📷 Foto ANTES</span>
              <input #fotoAntesInput type="file" accept="image/*" capture="environment"
                     class="file-hidden" (change)="onFoto('antes', $event)">
              <button type="button" class="ui-btn ui-btn--ghost foto-btn" (click)="fotoAntesInput.click()">
                <i class="fa fa-camera"></i> {{ cf.foto_antes ? 'Cambiar foto' : 'Tomar/Subir foto' }}
              </button>
              @if (fotoAntesPreview()) {
                <div class="foto-preview">
                  <img [src]="fotoAntesPreview()!" alt="Vista previa antes">
                  <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" (click)="quitarFotoCorte('antes')">
                    <i class="fa fa-times"></i> Quitar
                  </button>
                </div>
              }
            </div>

            <div class="foto-block">
              <span class="foto-block__title">📷 Foto DESPUÉS</span>
              <input #fotoDespuesInput type="file" accept="image/*" capture="environment"
                     class="file-hidden" (change)="onFoto('despues', $event)">
              <button type="button" class="ui-btn ui-btn--ghost foto-btn" (click)="fotoDespuesInput.click()">
                <i class="fa fa-camera"></i> {{ cf.foto_despues ? 'Cambiar foto' : 'Tomar/Subir foto' }}
              </button>
              @if (fotoDespuesPreview()) {
                <div class="foto-preview">
                  <img [src]="fotoDespuesPreview()!" alt="Vista previa después">
                  <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" (click)="quitarFotoCorte('despues')">
                    <i class="fa fa-times"></i> Quitar
                  </button>
                </div>
              }
            </div>
          </div>

          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrarCorte()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardarCorte()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Registrar avance' }}
            </button>
          </div>
        </div>
      </div>
    }

    <!-- Lightbox de foto ampliada -->
    @if (fotoZoom(); as src) {
      <div class="lightbox" (click)="fotoZoom.set(null)">
        <img [src]="src" alt="Evidencia ampliada">
      </div>
    }

    <!-- Modal: agregar vía -->
    @if (esAdmin() && tramoForm()) {
      <div class="modal" (click)="cerrarTramo()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2><i class="fa fa-road"></i> Agregar vía (tramo)</h2>
          <p class="modal__hint">El sistema ubica la vía en el mapa automáticamente usando el CIV.</p>
          @if (tramoError()) { <div class="ui-info-bar ui-info-bar--danger">{{ tramoError() }}</div> }

          <label>Valor Intervención ($)
            <input type="number" min="0" class="ui-input" [(ngModel)]="tramoForm()!.valor_intervencion"
                   placeholder="Ej: 85000000">
          </label>
          <div class="row">
            <label>CIV *
              <input type="number" class="ui-input" [(ngModel)]="tramoForm()!.civ" placeholder="Ej: 8004567">
              <small class="hint">Código de Identificación Vial (malla vial de Bogotá).</small>
            </label>
            <label>PK ID
              <input type="number" class="ui-input" [(ngModel)]="tramoForm()!.pk_id" placeholder="Opcional">
            </label>
          </div>
          <label>Eje Vial
            <input class="ui-input" [(ngModel)]="tramoForm()!.eje_vial" placeholder="Ej: Carrera 80">
          </label>
          <div class="row">
            <label>Desde<input class="ui-input" [(ngModel)]="tramoForm()!.desde" placeholder="Ej: Calle 38 Sur"></label>
            <label>Hasta<input class="ui-input" [(ngModel)]="tramoForm()!.hasta" placeholder="Ej: Calle 42 Sur"></label>
          </div>
          <label>% Avance Intervención
            <input type="number" min="0" max="100" class="ui-input" [(ngModel)]="tramoForm()!.pct_avance" placeholder="0">
          </label>

          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrarTramo()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardarTramo()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Agregar vía' }}
            </button>
          </div>
        </div>
      </div>
    }

    <!-- Modal: agregar parque -->
    @if (esAdmin() && parqueForm()) {
      <div class="modal" (click)="cerrarParque()">
        <div class="modal__box" (click)="$event.stopPropagation()">
          <h2><i class="fa fa-tree"></i> Agregar parque</h2>
          <p class="modal__hint">El parque ya trae su ubicación; aparecerá en el mapa al guardar.</p>
          @if (parqueError()) { <div class="ui-info-bar ui-info-bar--danger">{{ parqueError() }}</div> }

          <label>Código Parque *
            <input class="ui-input" [(ngModel)]="busquedaParque" (ngModelChange)="filtrarParques($event)"
                   placeholder="Busca por código o nombre… (ej. 08-001 o Cayetano)">
          </label>
          @if (busquedaParque && parquesFiltrados().length > 0) {
            <ul class="picker">
              @for (p of parquesFiltrados(); track p.id) {
                <li class="picker__opt" [class.picker__opt--on]="parqueForm()!.parque_id === p.id"
                    role="button" tabindex="0"
                    (click)="elegirParque(p)" (keyup.enter)="elegirParque(p)">
                  <strong>{{ p.codigo_parque }}</strong> · {{ p.nombre }}
                </li>
              }
            </ul>
          } @else if (busquedaParque && parqueForm()!.parque_id === null) {
            <small class="hint">Sin coincidencias. Escribe parte del código o nombre del parque.</small>
          }

          <label>Nombre del parque
            <input class="ui-input" [ngModel]="parqueNombre()" readonly placeholder="Se autocompleta al elegir">
          </label>
          <label>Dirección
            <input class="ui-input" [(ngModel)]="parqueForm()!.direccion" placeholder="Ej: Calle 40 Sur # 79-20">
          </label>
          <label>% Avance Intervención
            <input type="number" min="0" max="100" class="ui-input" [(ngModel)]="parqueForm()!.pct_avance" placeholder="0">
          </label>

          <div class="modal__acc">
            <button class="ui-btn ui-btn--ghost" (click)="cerrarParque()">Cancelar</button>
            <button class="ui-btn ui-btn--primary" (click)="guardarParque()" [disabled]="saving()">
              {{ saving() ? 'Guardando…' : 'Vincular parque' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { margin: $space-1 0 $space-3; display: flex; gap: $space-2; align-items: center; flex-wrap: wrap; }
    .actions { display: flex; gap: $space-2; flex-wrap: wrap; }
    .chip { background: #F3F4F6; color: #374151; border-radius: 99px; padding: 3px 12px; font-size: .75rem; }
    .chip--link { text-decoration: none; background: #EEF2FF; color: #4338CA; font-weight: 600; }

    .cab { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; }
    .cab dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; margin: 0; }
    @media (max-width: 760px) { .cab dl { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 480px) { .cab dl { grid-template-columns: 1fr; } }
    .cab dt { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; letter-spacing: .03em; margin-bottom: 2px; }
    .cab dd { margin: 0; color: $color-text; font-weight: 600; }
    .ejc-block dd { font-weight: 400; }
    .cab__cta { display: flex; align-items: center; gap: $space-3; margin-top: $space-4; padding-top: $space-3; border-top: 1px dashed $color-border; flex-wrap: wrap; }
    .cta-avance { font-size: 1rem; padding: 10px 20px; }
    .cta-avance i { margin-right: $space-2; }
    .cta-hint { color: $color-text-muted; font-size: $font-size-sm; flex: 1; min-width: 220px; }

    .block { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; }
    .block__head { display: flex; justify-content: space-between; align-items: center; gap: $space-3; margin-bottom: $space-3; flex-wrap: wrap; }
    .block__head h2 { margin: 0; color: $color-primary; font-size: 1.05rem; }
    .block__head h2 i { margin-right: $space-2; }

    .block--map { padding-bottom: $space-3; }
    .mini-map { height: 320px; width: 100%; border-radius: $radius-md; border: 1px solid $color-border; z-index: 0; }
    .leyenda { display: flex; gap: $space-4; flex-wrap: wrap; margin-top: $space-2; font-size: .75rem; color: $color-text-muted; }
    .leyenda .dot { display: inline-block; width: 12px; height: 12px; border-radius: 99px; margin-right: 4px; vertical-align: middle; }

    .tabla-wrap { overflow: auto; border: 1px solid $color-border; border-radius: $radius-md; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla thead th { text-align: left; padding: $space-2 $space-3; color: $color-text-muted; font-weight: 600; border-bottom: 2px solid $color-border; white-space: nowrap; background: #F9FAFB; }
    .tabla th.num, .tabla td.num { text-align: right; }
    .tabla th.avc { width: 200px; }
    .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid $color-border; vertical-align: middle; }
    .tabla tbody tr:last-child td { border-bottom: none; }
    .dir { color: $color-text-muted; max-width: 220px; }
    .acc { text-align: right; white-space: nowrap; }
    .acc .ui-btn.on { background: #EEF2FF; color: #4338CA; }
    .danger { color: #DC2626; }

    .inline-edit { display: flex; align-items: center; gap: $space-2; }
    .ui-input--sm { width: 70px; padding: 4px 8px; }
    .pct-ro { width: 70px; font-weight: 700; color: $color-text; font-variant-numeric: tabular-nums; }

    .ejc { display: flex; align-items: center; gap: $space-2; }
    .ejc__bar { flex: 1; height: 8px; background: #eee; border-radius: 99px; overflow: hidden; min-width: 80px; max-width: 220px; }
    .ejc__fill { height: 100%; transition: width .4s; }
    .ejc__fill.ok { background: #16A34A; } .ejc__fill.warn { background: #F59E0B; } .ejc__fill.low { background: #DC2626; }

    .geo { font-size: .72rem; font-weight: 600; white-space: nowrap; }
    .geo--ok { color: #15803D; } .geo--no { color: #B45309; }
    .geo i { margin-right: 3px; }

    /* Historial de cortes */
    .hist-row td { background: #F9FAFB; padding: $space-2 $space-3 $space-3; }
    .hist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: $space-2; }
    .hist--load, .hist--empty { color: $color-text-muted; font-size: $font-size-sm; padding: $space-2 0; }
    .hist__item { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-2 $space-3; }
    .hist__meta { display: flex; align-items: center; gap: $space-3; }
    .hist__pct { font-weight: 700; font-size: 1rem; }
    .hist__fecha { color: $color-text-muted; font-size: .75rem; }
    .hist__fecha i { margin-right: 3px; }
    .hist__obs { margin: 4px 0 0; color: $color-text; font-size: $font-size-sm; }
    .hist__foto { height: 72px; border-radius: $radius-sm; border: 1px solid $color-border; cursor: pointer; object-fit: cover; }
    .hist__foto-load { background: none; border: 1px dashed $color-border; color: $color-text-muted; border-radius: $radius-sm; padding: 6px 12px; cursor: pointer; font-size: .75rem; }

    .badge { border-radius: 99px; padding: 3px 10px; font-size: .7rem; font-weight: 600; white-space: nowrap; }
    .badge--VIAS { background: #DBEAFE; color: #1E40AF; }
    .badge--PARQUES { background: #CCFBF1; color: #0F766E; }
    .badge--INTERVENTORIA { background: #FEF3C7; color: #92400E; }
    .badge--sin_iniciar { background: #FEE2E2; color: #991B1B; }
    .badge--parcial { background: #FEF3C7; color: #92400E; }
    .badge--terminado { background: #DCFCE7; color: #166534; }

    .hint { color: $color-text-muted; font-size: .72rem; font-weight: 400; margin-top: 2px; }
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; padding: $space-3; z-index: 1000; }
    .modal__box { background: #fff; border-radius: $radius-lg; padding: $space-4; width: 100%; max-width: 540px; max-height: 90vh; overflow: auto; display: flex; flex-direction: column; gap: $space-2; }
    .modal__box h2 { margin: 0 0 4px; color: $color-primary; }
    .modal__box h2 i { margin-right: $space-2; }
    .modal__hint { color: $color-text-muted; font-size: $font-size-sm; margin: 0 0 $space-2; }
    .modal__box label { display: flex; flex-direction: column; font-size: $font-size-sm; color: $color-text; gap: 4px; }
    .modal__box textarea.ui-input { resize: vertical; }
    .modal__box .row { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2; }
    @media (max-width: 600px) { .modal__box .row { grid-template-columns: 1fr; } }
    .modal__acc { display: flex; justify-content: flex-end; gap: $space-2; margin-top: $space-2; }

    .slider { width: 100%; }
    .file-hidden { display: none; }
    .foto-btn { align-self: flex-start; }
    .foto-btn i { margin-right: 6px; }
    .foto-preview { display: flex; align-items: center; gap: $space-3; margin-top: $space-2; }
    .foto-preview img { height: 90px; border-radius: $radius-md; border: 1px solid $color-border; object-fit: cover; }

    .fotos-row { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; }
    @media (max-width: 600px) { .fotos-row { grid-template-columns: 1fr; } }
    .foto-block { display: flex; flex-direction: column; gap: 6px; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-3; background: #F9FAFB; }
    .foto-block__title { font-size: $font-size-sm; font-weight: 700; color: $color-text; }

    .hist__fotos { display: flex; gap: $space-3; flex-wrap: wrap; margin-top: $space-2; }
    .hist__foto-fig { margin: 0; display: flex; flex-direction: column; gap: 3px; }
    .hist__foto-cap { font-size: .68rem; font-weight: 600; color: $color-text-muted; text-transform: uppercase; letter-spacing: .03em; }

    .lightbox { position: fixed; inset: 0; background: rgba(0,0,0,.8); display: flex; align-items: center; justify-content: center; padding: $space-4; z-index: 1100; cursor: zoom-out; }
    .lightbox img { max-width: 95vw; max-height: 90vh; border-radius: $radius-md; }

    .picker { list-style: none; margin: 0; padding: 0; max-height: 200px; overflow: auto; border: 1px solid $color-border; border-radius: $radius-md; }
    .picker__opt { padding: $space-2 $space-3; cursor: pointer; border-bottom: 1px solid $color-border; font-size: $font-size-sm; }
    .picker__opt:last-child { border-bottom: none; }
    .picker__opt:hover, .picker__opt--on { background: #EEF2FF; }
    .picker__opt:focus-visible { outline: 2px solid $color-primary; outline-offset: -2px; }
  `],
})
export class InfraDetalleComponent implements OnInit, AfterViewInit, OnDestroy {
  private api = inject(InfraestructuraApi);
  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private sanitizer = inject(DomSanitizer);

  @ViewChild('miniMapa') mapEl?: ElementRef<HTMLElement>;

  contratoId = 0;
  /** Acciones de administración (agregar/borrar vía-parque, edición inline %) solo para infraestructura_admin. */
  esAdmin = computed(() => this.auth.hasModule('infraestructura_admin'));
  loading = signal(false);
  error = signal('');
  contrato = signal<ContratoInfraDetalle | null>(null);
  catalogos = signal<InfraCatalogos | null>(null);

  // Form: agregar tramo.
  tramoForm = signal<TramoInput | null>(null);
  tramoError = signal('');

  // Form: agregar parque (con selector de catálogo).
  parqueForm = signal<ParqueInput | null>(null);
  parqueError = signal('');
  busquedaParque = '';
  parquesFiltrados = signal<ParqueCatalogo[]>([]);
  private parqueElegido = signal<ParqueCatalogo | null>(null);
  parqueNombre = computed(() => this.parqueElegido()?.nombre ?? '');

  saving = signal(false);
  /** Marcador del borrado en curso: 't<id>' tramo o 'p<id>' parque. */
  eliminando = signal<string | null>(null);

  // ── Cortes ──────────────────────────────────────────────────────
  corteForm = signal<CorteInput | null>(null);
  corteError = signal('');
  fotoAntesPreview = signal<string | null>(null);
  fotoDespuesPreview = signal<string | null>(null);
  /** Etiqueta del objeto sobre el que se registra el corte (en el modal). */
  private corteLabel = signal('');
  corteAlcance = computed(() => this.corteLabel());

  /** Historiales cargados: clave `<tipo>:<id>` → lista de cortes (o null=cargando). */
  private historiales = signal<Record<string, CorteAvance[] | null>>({});
  /** Qué historiales están abiertos en la UI. */
  private historialAbierto = signal<Set<string>>(new Set());

  /** Fotos cargadas como blob+Bearer: clave `<corte.id>:<antes|despues>` → SafeUrl. */
  private fotos = signal<Record<string, SafeUrl>>({});
  fotoZoom = signal<SafeUrl | null>(null);

  // ── Mini-mapa Leaflet ───────────────────────────────────────────
  private map?: L.Map;
  private geojson = signal<InfraFeatureCollection | null>(null);
  tieneGeometrias = computed(() => (this.geojson()?.features?.length ?? 0) > 0);

  ngOnInit(): void {
    this.contratoId = Number(this.route.snapshot.paramMap.get('id'));
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Infraestructura', url: '/infraestructura' },
      { label: 'Contrato' },
    ]);
    this.api.catalogos().subscribe({ next: (c) => this.catalogos.set(c) });
    this.cargar();
  }

  ngAfterViewInit(): void {
    // El contenedor del mapa solo existe cuando hay geometrías y loading()=false.
    const tryInit = () => {
      if (this.map) return;
      if (this.tieneGeometrias() && this.mapEl?.nativeElement) {
        this.initMap();
      } else if (this.loading() || (this.geojson() === null && !this.error())) {
        setTimeout(tryInit, 150);
      }
    };
    setTimeout(tryInit, 200);
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }

  moneda(v: unknown): string { return formatMoneda(v); }
  estadoLbl(e: EstadoAvance): string { return ESTADO_LBL[e] ?? e; }
  colorPct(pct: number): string { return colorAvance(pct); }
  catLabel(cod: string): string {
    return this.catalogos()?.categorias.find((c) => c.codigo === cod)?.label ?? cod;
  }
  ejecClase(ejec: number | null): string {
    const e = ejec || 0;
    return e >= 80 ? 'ok' : e >= 50 ? 'warn' : 'low';
  }

  cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.detalle(this.contratoId).subscribe({
      next: (c) => {
        this.contrato.set(c);
        this.loading.set(false);
        this.cargarGeojson();
        this.refrescarHistorialesAbiertos();
      },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  private cargarGeojson(): void {
    this.api.contratoGeojson(this.contratoId).subscribe({
      next: (fc) => { this.geojson.set(fc); this.pintarMapa(); },
      error: () => { this.geojson.set({ type: 'FeatureCollection', features: [] }); },
    });
  }

  // ── Mini-mapa ───────────────────────────────────────────────────
  private initMap(): void {
    if (this.map || !this.mapEl?.nativeElement) return;
    this.map = L.map(this.mapEl.nativeElement, { center: [4.628, -74.153], zoom: 13 });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap © CARTO', subdomains: 'abcd', maxZoom: 19,
    }).addTo(this.map);
    this.pintarMapa();
  }

  private pintarMapa(): void {
    if (!this.map) { setTimeout(() => this.initMap(), 100); return; }
    // Limpia capas previas (deja solo el tile base).
    this.map.eachLayer((layer) => {
      if (!(layer instanceof L.TileLayer)) this.map!.removeLayer(layer);
    });
    const fc = this.geojson();
    if (!fc) return;
    const bounds: L.LatLngExpression[] = [];
    for (const f of fc.features) {
      if (!f.geometry) continue;
      const color = colorAvance(f.properties.pct_avance ?? 0);
      if (f.geometry.type === 'LineString') {
        const coords = (f.geometry.coordinates as number[][])
          .map(([lng, lat]) => [lat, lng] as L.LatLngExpression);
        L.polyline(coords, { color, weight: 5, opacity: 0.85 })
          .bindPopup(this.popupTramo(f.properties)).addTo(this.map);
        bounds.push(...coords);
      } else if (f.geometry.type === 'Point') {
        const [lng, lat] = f.geometry.coordinates as number[];
        const pt = [lat, lng] as L.LatLngExpression;
        L.circleMarker(pt, { radius: 9, color: '#fff', weight: 2, fillColor: color, fillOpacity: 0.95 })
          .bindPopup(this.popupParque(f.properties)).addTo(this.map);
        bounds.push(pt);
      }
    }
    if (bounds.length) {
      this.map.fitBounds(L.latLngBounds(bounds).pad(0.2));
    }
    setTimeout(() => this.map?.invalidateSize(), 60);
  }

  private popupTramo(p: { eje_vial?: string | null; desde?: string | null; hasta?: string | null; civ?: number | null; pct_avance: number }): string {
    return `<b>${p.eje_vial || 'Tramo'}</b><br>${p.desde || '?'} → ${p.hasta || '?'}`
      + `<br>CIV ${p.civ ?? '—'} · <b>${p.pct_avance ?? 0}%</b>`;
  }
  private popupParque(p: { codigo_parque?: number | string | null; nombre?: string | null; pct_avance: number }): string {
    return `<b>${p.nombre || 'Parque'}</b><br>Cód. ${p.codigo_parque ?? '—'} · <b>${p.pct_avance ?? 0}%</b>`;
  }

  // ── Tramos: edición inline del avance ──────────────────────────
  setTramoAvance(t: TramoVial, val: number): void {
    t.pct_avance = Math.max(0, Math.min(100, Number(val) || 0));
  }

  guardarTramoAvance(t: TramoVial): void {
    this.api.actualizarTramo(t.id, t.pct_avance).subscribe({
      next: (r) => { this.aplicarEjecucion(r.ejecucion_contrato); this.cargar(); },
      error: (e) => this.toast.error(this.msg(e)),
    });
  }

  async eliminarTramo(t: TramoVial): Promise<void> {
    if (this.eliminando()) return;
    const ok = await this.confirm.ask({
      title: 'Quitar tramo', danger: true, confirmText: 'Quitar',
      message: `¿Quitar el tramo CIV ${t.civ}? Saldrá del mapa.`,
    });
    if (!ok) return;
    this.eliminando.set('t' + t.id);
    this.api.quitarTramo(t.id).subscribe({
      next: () => { this.eliminando.set(null); this.toast.success('Tramo quitado ✓'); this.cargar(); },
      error: (e) => { this.eliminando.set(null); this.toast.error(this.msg(e)); },
    });
  }

  // ── Parques: edición inline del avance ─────────────────────────
  setParqueAvance(p: ParqueIntervencion, val: number): void {
    p.pct_avance = Math.max(0, Math.min(100, Number(val) || 0));
  }

  guardarParqueAvance(p: ParqueIntervencion): void {
    this.api.actualizarParque(p.id, p.pct_avance).subscribe({
      next: (r) => { this.aplicarEjecucion(r.ejecucion_contrato); this.cargar(); },
      error: (e) => this.toast.error(this.msg(e)),
    });
  }

  async eliminarParque(p: ParqueIntervencion): Promise<void> {
    if (this.eliminando()) return;
    const ok = await this.confirm.ask({
      title: 'Quitar parque', danger: true, confirmText: 'Quitar',
      message: `¿Quitar el parque "${p.nombre || p.codigo_parque}" de este contrato?`,
    });
    if (!ok) return;
    this.eliminando.set('p' + p.id);
    this.api.quitarParque(p.id).subscribe({
      next: () => { this.eliminando.set(null); this.toast.success('Parque quitado ✓'); this.cargar(); },
      error: (e) => { this.eliminando.set(null); this.toast.error(this.msg(e)); },
    });
  }

  private aplicarEjecucion(ejec: number): void {
    this.contrato.update((c) => c ? { ...c, ejecucion: ejec } : c);
  }

  // ── Cortes de avance (modal reusable) ──────────────────────────
  abrirCorteContrato(c: ContratoInfraDetalle): void {
    this.abrirCorte('contrato', null,
      c.categoria === 'INTERVENTORIA'
        ? 'Corte de seguimiento de la interventoría (avance global del contrato).'
        : 'Avance global del contrato.');
  }
  abrirCorteTramo(t: TramoVial): void {
    this.abrirCorte('tramo', t.id, `Avance de la vía ${t.eje_vial || 'CIV ' + t.civ}.`, t.pct_avance);
  }
  abrirCorteParque(p: ParqueIntervencion): void {
    this.abrirCorte('parque', p.id, `Avance del parque ${p.nombre || p.codigo_parque}.`, p.pct_avance);
  }

  private abrirCorte(tipo: ObjetoCorte, objetoId: number | null, label: string, pctActual = 0): void {
    this.corteError.set('');
    this.fotoAntesPreview.set(null);
    this.fotoDespuesPreview.set(null);
    this.corteLabel.set(label);
    this.corteForm.set({
      contrato_id: this.contratoId,
      objeto_tipo: tipo,
      objeto_id: objetoId,
      fecha: new Date().toISOString().slice(0, 10),
      pct: pctActual,
      observacion: '',
      foto_antes: null,
      foto_despues: null,
    });
  }
  cerrarCorte(): void {
    this.corteForm.set(null);
    this.fotoAntesPreview.set(null);
    this.fotoDespuesPreview.set(null);
  }

  setCortePct(val: number): void {
    this.corteForm.update((f) =>
      f ? { ...f, pct: Math.max(0, Math.min(100, Number(val) || 0)) } : f);
  }

  onFoto(cual: 'antes' | 'despues', ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    const preview = cual === 'antes' ? this.fotoAntesPreview : this.fotoDespuesPreview;
    this.corteForm.update((f) =>
      f ? { ...f, [cual === 'antes' ? 'foto_antes' : 'foto_despues']: file } : f);
    preview.set(file ? URL.createObjectURL(file) : null);
  }
  quitarFotoCorte(cual: 'antes' | 'despues'): void {
    const preview = cual === 'antes' ? this.fotoAntesPreview : this.fotoDespuesPreview;
    this.corteForm.update((f) =>
      f ? { ...f, [cual === 'antes' ? 'foto_antes' : 'foto_despues']: null } : f);
    preview.set(null);
  }

  guardarCorte(): void {
    const data = this.corteForm();
    if (!data) return;
    if (!data.fecha) { this.corteError.set('La fecha es obligatoria.'); return; }
    if (data.pct == null || data.pct < 0 || data.pct > 100) {
      this.corteError.set('El % de avance debe estar entre 0 y 100.'); return;
    }
    const fd = new FormData();
    fd.append('contrato_id', String(data.contrato_id));
    fd.append('objeto_tipo', data.objeto_tipo);
    if (data.objeto_id != null) fd.append('objeto_id', String(data.objeto_id));
    fd.append('fecha', data.fecha);
    fd.append('pct', String(data.pct));
    fd.append('observacion', data.observacion || '');
    if (data.foto_antes) fd.append('foto_antes', data.foto_antes, data.foto_antes.name);
    if (data.foto_despues) fd.append('foto_despues', data.foto_despues, data.foto_despues.name);

    const objeto = data.objeto_tipo;
    const objetoId = data.objeto_id;
    this.saving.set(true);
    this.corteError.set('');
    this.api.registrarCorte(fd).subscribe({
      next: () => {
        this.saving.set(false);
        this.cerrarCorte();
        this.toast.success('Avance registrado ✓');
        if (objeto !== 'contrato') {
          this.toast.info('El mapa y la ejecución del contrato se actualizan.');
        }
        // Refresca detalle (% del ítem + ejecución) + historial de ese objeto.
        this.cargar();
        this.recargarHistorial(objeto, objetoId ?? 0, true);
      },
      error: (e) => { this.saving.set(false); this.corteError.set(this.msg(e)); },
    });
  }

  // ── Historial de cortes ────────────────────────────────────────
  private clave(tipo: ObjetoCorte, id: number): string { return `${tipo}:${id}`; }

  esHistAbierto(tipo: ObjetoCorte, id: number): boolean {
    return this.historialAbierto().has(this.clave(tipo, id));
  }

  histDe(tipo: ObjetoCorte, id: number): CorteAvance[] | null {
    return this.historiales()[this.clave(tipo, id)] ?? null;
  }

  toggleHistorial(tipo: ObjetoCorte, id: number): void {
    const k = this.clave(tipo, id);
    const abiertos = new Set(this.historialAbierto());
    if (abiertos.has(k)) {
      abiertos.delete(k);
    } else {
      abiertos.add(k);
      if (this.historiales()[k] === undefined) this.recargarHistorial(tipo, id, false);
    }
    this.historialAbierto.set(abiertos);
  }

  private recargarHistorial(tipo: ObjetoCorte, id: number, abrir: boolean): void {
    const k = this.clave(tipo, id);
    this.historiales.update((h) => ({ ...h, [k]: null }));
    if (abrir) {
      const abiertos = new Set(this.historialAbierto());
      abiertos.add(k);
      this.historialAbierto.set(abiertos);
    }
    const filtros = tipo === 'contrato'
      ? { contrato_id: this.contratoId, objeto_tipo: 'contrato' as ObjetoCorte }
      : { contrato_id: this.contratoId, objeto_tipo: tipo, objeto_id: id };
    this.api.cortes(filtros).subscribe({
      next: (lista) => this.historiales.update((h) => ({ ...h, [k]: lista })),
      error: () => this.historiales.update((h) => ({ ...h, [k]: [] })),
    });
  }

  private refrescarHistorialesAbiertos(): void {
    for (const k of this.historialAbierto()) {
      const [tipo, id] = k.split(':') as [ObjetoCorte, string];
      this.recargarHistorial(tipo, Number(id), false);
    }
  }

  // ── Fotos de evidencia (blob + Bearer) ─────────────────────────
  private fotoKey(corteId: number, cual: 'antes' | 'despues'): string { return `${corteId}:${cual}`; }

  fotoUrl(corteId: number, cual: 'antes' | 'despues'): SafeUrl | null {
    return this.fotos()[this.fotoKey(corteId, cual)] ?? null;
  }

  cargarFoto(corteId: number, cual: 'antes' | 'despues'): void {
    const key = this.fotoKey(corteId, cual);
    if (this.fotos()[key]) { this.ampliarFoto(corteId, cual); return; }
    this.http.get(this.cfg.url(this.api.fotoCortePath(corteId, cual)), { responseType: 'blob' })
      .subscribe({
        next: (b) => {
          const url = this.sanitizer.bypassSecurityTrustUrl(URL.createObjectURL(b));
          this.fotos.update((f) => ({ ...f, [key]: url }));
        },
        error: () => this.toast.error('No se pudo cargar la evidencia.'),
      });
  }

  ampliarFoto(corteId: number, cual: 'antes' | 'despues'): void {
    const url = this.fotos()[this.fotoKey(corteId, cual)];
    if (url) this.fotoZoom.set(url);
    else this.cargarFoto(corteId, cual);
  }

  // ── Agregar tramo ──────────────────────────────────────────────
  abrirTramo(): void {
    this.tramoError.set('');
    this.tramoForm.set({
      valor_intervencion: null, civ: null, pk_id: null,
      eje_vial: null, desde: null, hasta: null, pct_avance: 0,
    });
  }
  cerrarTramo(): void { this.tramoForm.set(null); }

  guardarTramo(): void {
    const data = this.tramoForm();
    if (!data) return;
    if (!data.civ) { this.tramoError.set('El CIV es obligatorio.'); return; }
    this.saving.set(true);
    this.tramoError.set('');
    this.api.agregarTramo(this.contratoId, data).subscribe({
      next: (r) => {
        this.saving.set(false);
        this.cerrarTramo();
        if (r.en_mapa) {
          this.toast.success('Tramo agregado y ubicado en el mapa ✓ Refresca la capa del Mapa Kennedy.');
        } else {
          this.toast.info('Tramo agregado. La geometría no se resolvió aún (revisión).');
        }
        this.cargar();
      },
      error: (e) => { this.saving.set(false); this.tramoError.set(this.msg(e)); },
    });
  }

  // ── Agregar parque ─────────────────────────────────────────────
  abrirParque(): void {
    this.parqueError.set('');
    this.busquedaParque = '';
    this.parquesFiltrados.set([]);
    this.parqueElegido.set(null);
    this.parqueForm.set({ parque_id: null, direccion: null, pct_avance: 0 });
  }
  cerrarParque(): void { this.parqueForm.set(null); }

  filtrarParques(q: string): void {
    this.parqueForm.update((f) => f ? { ...f, parque_id: null } : f);
    this.parqueElegido.set(null);
    const term = (q || '').trim().toLowerCase();
    if (term.length < 2) { this.parquesFiltrados.set([]); return; }
    const todos = this.catalogos()?.parques ?? [];
    this.parquesFiltrados.set(
      todos.filter((p) =>
        String(p.codigo_parque).toLowerCase().includes(term)
        || (p.nombre || '').toLowerCase().includes(term),
      ).slice(0, 30),
    );
  }

  elegirParque(p: ParqueCatalogo): void {
    this.parqueElegido.set(p);
    this.busquedaParque = `${p.codigo_parque} · ${p.nombre}`;
    this.parquesFiltrados.set([]);
    this.parqueForm.update((f) => f ? { ...f, parque_id: p.id } : f);
  }

  guardarParque(): void {
    const data = this.parqueForm();
    if (!data) return;
    if (!data.parque_id) { this.parqueError.set('Selecciona un parque del catálogo.'); return; }
    this.saving.set(true);
    this.parqueError.set('');
    this.api.vincularParque(this.contratoId, data).subscribe({
      next: () => {
        this.saving.set(false);
        this.cerrarParque();
        this.toast.success('Parque vinculado ✓ Refresca la capa del Mapa Kennedy.');
        this.cargar();
      },
      error: (e) => { this.saving.set(false); this.parqueError.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    const b = e?.error;
    if (b?.detail) return b.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para gestionar infraestructura.';
    return e?.message || 'Error inesperado.';
  }
}
