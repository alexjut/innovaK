import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, ChangeDetectionStrategy, Component, ElementRef,
  OnDestroy, OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { DireccionPickerComponent, DireccionElegida }
  from '../../shared/direccion/direccion-picker.component';
import { ConfigService } from '../../core/config/config.service';
import {
  DependenciaLite, GeoService, SubgrupoLite, TipoEventoLite,
} from '../../core/geo/geo.service';
import { LayoutService } from '../../core/layout/layout.service';
import {
  camposVacios, enfocarPrimerInvalido, erroresObligatorios,
  limpiarCampo, mapearErroresBackend,
} from '../../shared/forms/form-validation';
import { EventoDetalle, EventosApi } from './eventos.api';

interface Linea { id: number; nombre: string; }
interface Funcionario { id: number; nombre: string; }
interface ProyectoLite { id: number; codigo: string; nombre: string; }
interface ActPlanLite { id: number; nombre: string; }
interface IndicadorLite { id: number; nombre: string; unidad_medida: string; meta_magnitud: number; }
interface ContratoLite { id: number; numero: string; valor: number; }

@Component({
  standalone: true,
  selector: 'app-evento-form',
  imports: [CommonModule, FormsModule, RouterLink, DireccionPickerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <div class="page__title-row">
            <span class="page__title-icon"><i class="fa" [class]="modoEdit() ? 'fa-edit' : 'fa-plus-circle'"></i></span>
            <h1>
              @if (modoEdit()) { Editar actividad #{{ eventoId() }} }
              @else { Crear nueva actividad }
            </h1>
          </div>
          <p class="page__subtitle">
            Cuatro bloques: básicos · responsable · ubicación · plan presupuestal.
          </p>
        </div>
      </header>
      <div class="page__divider"></div>

      @if (loading()) { <div class="page__loading">Cargando…</div> }
      @else if (errorMsg()) { <div class="page__error">⚠ {{ errorMsg() }}</div> }
      @else {
        <form class="form" (ngSubmit)="guardar()">

          <!-- ▷ Bloque 1 — Básicos -->
          <fieldset class="bloque">
            <legend><i class="fa fa-circle-info" aria-hidden="true"></i> 1. Datos básicos</legend>
            <div class="form-grid">
              <label class="field field--full">
                <span>Nombre *</span>
                <input type="text" [(ngModel)]="form.nombre" name="nombre" data-field="nombre" required
                       [class.is-invalid]="campoErrores()['nombre']"
                       (input)="limpiarError('nombre')"
                       placeholder="Nombre de la actividad">
                @if (campoErrores()['nombre']) { <span class="field-error">{{ campoErrores()['nombre'] }}</span> }
              </label>

              <label class="field">
                <span>Tipo de actividad *</span>
                <select [(ngModel)]="form.tipo_evento_id" name="tipo" data-field="tipo_evento_id" required
                        [class.is-invalid]="campoErrores()['tipo_evento_id']"
                        (change)="onTipoChange(); limpiarError('tipo_evento_id')">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (t of tipos(); track t.codigo) {
                    <option [ngValue]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
                @if (campoErrores()['tipo_evento_id']) { <span class="field-error">{{ campoErrores()['tipo_evento_id'] }}</span> }
              </label>

              <label class="field">
                <span>Fecha *</span>
                <input type="date" [(ngModel)]="form.fecha_inicio" name="fini" data-field="fecha_inicio" required
                       [class.is-invalid]="campoErrores()['fecha_inicio']"
                       (input)="limpiarError('fecha_inicio')">
                @if (campoErrores()['fecha_inicio']) { <span class="field-error">{{ campoErrores()['fecha_inicio'] }}</span> }
              </label>

              <label class="field">
                <span>Fecha fin (opcional)</span>
                <input type="date" [(ngModel)]="form.fecha_fin" name="ffin">
              </label>

              @if (tipoActual()?.requiere_horario) {
                <label class="field">
                  <span>Hora inicio</span>
                  <input type="time" [(ngModel)]="form.hora_inicio" name="hini">
                </label>
                <label class="field">
                  <span>Hora fin</span>
                  <input type="time" [(ngModel)]="form.hora_fin" name="hfin">
                </label>
              }

              @if (tipoActual()?.permite_caracterizacion) {
                <label class="field">
                  <span>Sector caracterización *</span>
                  <select [(ngModel)]="form.sector_caracterizacion" name="sec" required>
                    <option [ngValue]="null">— Selecciona —</option>
                    <option value="cultura">Cultura</option>
                    <option value="deporte">Deporte</option>
                    <option value="mujer">Mujer</option>
                    <option value="salud">Salud</option>
                    <option value="poblacional">Poblacional</option>
                    <option value="participacion_ciudadana">Participación Ciudadana</option>
                  </select>
                </label>
              }

              <label class="field field--full">
                <span>Descripción</span>
                <textarea [(ngModel)]="form.descripcion" name="descripcion"
                          rows="2" placeholder="Detalle adicional…"></textarea>
              </label>
            </div>
          </fieldset>

          <!-- ▷ Bloque 2 — Responsable (cascada A) -->
          <fieldset class="bloque">
            <legend><i class="fa fa-user-tie" aria-hidden="true"></i> 2. Responsable de la actividad</legend>
            <div class="form-grid">
              <label class="field">
                <span>Dependencia *</span>
                <select [(ngModel)]="form.dependencia_id" name="dep" data-field="dependencia_id" required
                        [class.is-invalid]="campoErrores()['dependencia_id']"
                        (change)="onDepChange(); limpiarError('dependencia_id')">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (d of dependencias(); track d.id) {
                    <option [ngValue]="d.id">{{ d.nombre }}</option>
                  }
                </select>
                @if (campoErrores()['dependencia_id']) { <span class="field-error">{{ campoErrores()['dependencia_id'] }}</span> }
              </label>

              <label class="field">
                <span>Subgrupo *</span>
                <select [(ngModel)]="form.subgrupo_id" name="sub" data-field="subgrupo_id" required
                        [class.is-invalid]="campoErrores()['subgrupo_id']"
                        (change)="onSubChange(); limpiarError('subgrupo_id')">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (s of subgruposFiltrados(); track s.id) {
                    <option [ngValue]="s.id">{{ s.nombre }}</option>
                  }
                </select>
                @if (campoErrores()['subgrupo_id']) { <span class="field-error">{{ campoErrores()['subgrupo_id'] }}</span> }
              </label>

              <label class="field">
                <span>Línea (opcional)</span>
                <select [(ngModel)]="form.linea_id" name="lin">
                  <option [ngValue]="null">— Sin línea —</option>
                  @for (l of lineas(); track l.id) {
                    <option [ngValue]="l.id">{{ l.nombre }}</option>
                  }
                </select>
              </label>

              <label class="field">
                <span>Funcionario *</span>
                <select [(ngModel)]="form.funcionario_id" name="func" data-field="funcionario_id" required
                        [disabled]="sinFuncionarios()"
                        [class.is-invalid]="campoErrores()['funcionario_id']"
                        (change)="limpiarError('funcionario_id')">
                  <!-- La opción vacía DICE por qué está vacía. «— Selecciona —»
                       sobre una lista sin nada manda a abrirla para descubrir
                       que no hay nada. -->
                  @if (sinFuncionarios()) {
                    <option [ngValue]="null">— Este subgrupo no tiene funcionarios —</option>
                  } @else if (funcionariosCargando()) {
                    <option [ngValue]="null">Cargando…</option>
                  } @else {
                    <option [ngValue]="null">— Selecciona —</option>
                  }
                  @for (f of funcionarios(); track f.id) {
                    <option [ngValue]="f.id">{{ f.nombre }}</option>
                  }
                </select>
                @if (sinFuncionarios()) {
                  <span class="field-aviso" role="status">
                    Nadie está registrado como funcionario de
                    <b>{{ subgrupoElegido() }}</b>, así que no hay a quién asignarle
                    la actividad. Se registran en
                    <a routerLink="/admin/org" target="_blank" rel="noopener">Organización
                    → Funcionarios</a>; después vuelve y recarga esta página.
                  </span>
                }
                @if (campoErrores()['funcionario_id']) { <span class="field-error">{{ campoErrores()['funcionario_id'] }}</span> }
              </label>
            </div>
          </fieldset>

          <!-- ▷ Bloque 3 — Ubicación (dirección + mapa) -->
          <fieldset class="bloque">
            <legend><i class="fa fa-map-location-dot" aria-hidden="true"></i> 3. Ubicación</legend>
            <div class="form-grid">
              <div class="field field--full">
                <!-- La dirección se elige de la lista de Catastro: así existe y
                     cae en el mapa sola. El mapa de abajo queda para ajustar el
                     punto, o para ubicar algo que no tiene dirección exacta. -->
                <app-direccion-picker
                  label="Dirección *"
                  placeholder="Escribe y elige: Cl. 38 Sur # 78K-58"
                  [valor]="direccion"
                  [conMapa]="false"
                  (direccionElegida)="onDireccionElegida($event)" />
              </div>
              <label class="field">
                <span>Latitud *</span>
                <input type="number" step="0.000001" [(ngModel)]="latitud"
                       name="lat" required readonly>
              </label>
              <label class="field">
                <span>Longitud *</span>
                <input type="number" step="0.000001" [(ngModel)]="longitud"
                       name="lon" required readonly>
              </label>
              <div class="field field--full">
                <span class="muted">Click en el mapa si no hay dirección exacta (un parque, un lote)</span>
                <div #mapEl class="mini-mapa"></div>
                @if (campoErrores()['ubicacion']) {
                  <span class="field-error" role="alert">{{ campoErrores()['ubicacion'] }}</span>
                }
              </div>
            </div>
          </fieldset>

          <!-- ▷ Bloque 4 — Plan presupuestal (cascada B). Solo para tipos que
               aportan al plan (requiere_actividad_plan); GENERICO no lo muestra. -->
          @if (tipoActual()?.requiere_actividad_plan) {
          <fieldset class="bloque">
            <legend><i class="fa fa-coins" aria-hidden="true"></i> 4. Aporte al plan presupuestal</legend>
            <div class="form-grid">
              <label class="field">
                <span>Proyecto *</span>
                <select [(ngModel)]="proyectoId" name="proy" required
                        (change)="onProyectoChange()">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (p of proyectos(); track p.id) {
                    <option [ngValue]="p.id">{{ p.codigo }} · {{ p.nombre }}</option>
                  }
                </select>
              </label>

              <label class="field">
                <span>Actividad del plan *</span>
                <select [(ngModel)]="form.actividad_plan_id" name="ap" data-field="actividad_plan_id" required
                        [disabled]="!proyectoId"
                        [class.is-invalid]="campoErrores()['actividad_plan_id']"
                        (change)="onActividadChange(); limpiarError('actividad_plan_id')">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (a of actividadesPlan(); track a.id) {
                    <option [ngValue]="a.id">#{{ a.id }} · {{ a.nombre }}</option>
                  }
                </select>
                @if (!proyectoId) { <span class="field-hint">Selecciona primero un proyecto</span> }
                @if (campoErrores()['actividad_plan_id']) { <span class="field-error">{{ campoErrores()['actividad_plan_id'] }}</span> }
              </label>

              <label class="field">
                <span>Indicador / KPI *</span>
                <select [(ngModel)]="form.indicador_id" name="ind" data-field="indicador_id" required
                        [disabled]="!form.actividad_plan_id"
                        [class.is-invalid]="campoErrores()['indicador_id']"
                        (change)="limpiarError('indicador_id')">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (k of indicadores(); track k.id) {
                    <option [ngValue]="k.id">
                      {{ k.nombre }} ({{ k.unidad_medida }}, meta {{ k.meta_magnitud }})
                    </option>
                  }
                </select>
                @if (!proyectoId) { <span class="field-hint">Selecciona primero un proyecto</span> }
                @else if (!form.actividad_plan_id) { <span class="field-hint">Selecciona primero una actividad del plan</span> }
                @if (campoErrores()['indicador_id']) { <span class="field-error">{{ campoErrores()['indicador_id'] }}</span> }
              </label>

              <label class="field">
                <span>Magnitud aportada *</span>
                <input type="number" step="0.01" [(ngModel)]="form.magnitud_aportada"
                       name="mag" data-field="magnitud_aportada" placeholder="0.00" required
                       [class.is-invalid]="campoErrores()['magnitud_aportada']"
                       (input)="limpiarError('magnitud_aportada')">
                @if (campoErrores()['magnitud_aportada']) { <span class="field-error">{{ campoErrores()['magnitud_aportada'] }}</span> }
              </label>

              <label class="field field--full">
                <span>Contrato que financia (opcional)</span>
                <select [(ngModel)]="contratoFinanciaId" name="cf">
                  <option [ngValue]="null">— Sin contrato —</option>
                  @for (c of contratos(); track c.id) {
                    <option [ngValue]="c.id">{{ c.numero }} · \${{ c.valor }}</option>
                  }
                </select>
              </label>
            </div>
          </fieldset>
          }

          <!-- ▷ Bloque 5 — Solo INFO_TERRENO -->
          @if (tipoActual()?.codigo === 'INFO_TERRENO') {
            <fieldset class="bloque">
              <legend><i class="fa fa-map-pin" aria-hidden="true"></i> 5. Información de terreno</legend>
              <div class="form-grid">
                <label class="field field--full">
                  <span>Hallazgos</span>
                  <textarea [(ngModel)]="hallazgos" name="hall" rows="2"></textarea>
                </label>
                <label class="field field--full">
                  <span>Recorrido</span>
                  <textarea [(ngModel)]="recorrido" name="rec" rows="2"></textarea>
                </label>
                <label class="field field--full">
                  <span>Observaciones</span>
                  <textarea [(ngModel)]="observaciones" name="obs" rows="2"></textarea>
                </label>
              </div>
            </fieldset>
          }

          <!-- ▷ Campos extra DATA-DRIVEN según el tipo (evento_creacion_schema) -->
          @if (schemaExtra().fields.length) {
            <fieldset class="bloque">
              <legend><i class="fa fa-sliders" aria-hidden="true"></i> Datos de «{{ tipoActual()?.nombre }}»</legend>
              <div class="form-grid">
                @for (f of schemaExtra().fields; track f.name) {
                  <label class="field" [class.field--full]="f.type === 'textarea'">
                    <span>{{ f.label }}@if (f.required) { * }</span>
                    @switch (f.type) {
                      @case ('number') {
                        <input type="number" [(ngModel)]="extras[f.name]" [name]="'ex_' + f.name"
                               [required]="f.required">
                      }
                      @case ('select') {
                        <select [(ngModel)]="extras[f.name]" [name]="'ex_' + f.name" [required]="f.required">
                          <option [ngValue]="null">— Seleccionar —</option>
                          @for (opt of schemaExtra().catalogos[f.catalogo] || []; track opt.value) {
                            <option [ngValue]="opt.value">{{ opt.label }}</option>
                          }
                        </select>
                      }
                      @case ('checkbox') {
                        <input type="checkbox" [(ngModel)]="extras[f.name]" [name]="'ex_' + f.name">
                      }
                      @case ('date') {
                        <input type="date" [(ngModel)]="extras[f.name]" [name]="'ex_' + f.name" [required]="f.required">
                      }
                      @default {
                        <input type="text" [(ngModel)]="extras[f.name]" [name]="'ex_' + f.name" [required]="f.required">
                      }
                    }
                  </label>
                }
              </div>
            </fieldset>
          }

          @if (modoEdit()) {
            <label class="field field--check">
              <input type="checkbox" [(ngModel)]="form.activo" name="act">
              <span>Activo</span>
            </label>
          }

          <div class="form-actions">
            <a routerLink="/eventos" class="ui-btn ui-btn--ghost">Cancelar</a>
            <button type="submit" class="ui-btn ui-btn--primary"
                    [disabled]="guardando()">
              @if (guardando()) { Guardando… }
              @else if (modoEdit()) { Guardar cambios }
              @else { Crear actividad }
            </button>
          </div>

          @if (msg()) {
            <div class="ui-info-bar"
                 [class.ui-info-bar--success]="!errorGuardar()"
                 [class.ui-info-bar--danger]="errorGuardar()">
              {{ msg() }}
            </div>
          }
        </form>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
  .page__header { align-items: flex-start; }
  .page__title-row { display: flex; align-items: center; gap: $space-3; }
  .page__title-icon { display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: $radius-md; background: $color-primary; color: #fff; flex-shrink: 0; }
  .page__divider { height: 1px; background: $color-border; margin: $space-3 0; }
    .page__header h1 { margin: 0; color: $color-text; font-size: 32px; font-weight: $font-weight-semibold; &::after { content: ''; display: block; width: 48px; height: 4px; border-radius: $radius-pill; background: $color-secondary; margin-top: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading, .page__error { padding: $space-4; text-align: center; color: $color-text-muted; }
    .page__error { color: $color-danger; }
    .form { margin-top: $space-3; }
    .bloque {
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-3 $space-4;
      margin-bottom: $space-3;
      legend {
        color: $color-primary;
        font-weight: $font-weight-bold;
        padding: 0 $space-2;
        i { margin-right: $space-2; }
      }
    }
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: $space-3;
      @media (max-width: 720px) { grid-template-columns: 1fr; }
    }
    .field {
      display: block;
      span {
        display: block;
        font-size: $font-size-xs;
        color: $color-text-muted;
        margin-bottom: $space-1;
      }
      input, select, textarea {
        width: 100%;
        padding: $space-2;
        border: 1px solid $color-border;
        border-radius: $radius-md;
        font-family: inherit;
        font-size: $font-size-sm;
        &:focus {
          outline: none;
          border-color: $color-primary;
          box-shadow: 0 0 0 3px rgba(214,0,28,0.15);
        }
      }
      textarea { min-height: 70px; }
      &--full { grid-column: 1 / -1; }
      &--check {
        display: flex; align-items: center; gap: $space-2;
        input { width: auto; }
        span { margin: 0; }
      }
    }
    .mini-mapa {
      height: 280px;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      margin-top: $space-1;
    }
    .form-actions {
      margin-top: $space-4;
      display: flex;
      gap: $space-2;
      justify-content: flex-end;
    }
    .muted { color: $color-text-muted; font-size: $font-size-xs; }
  `],
})
export class EventoFormComponent implements OnInit, AfterViewInit, OnDestroy {
  private api = inject(EventosApi);
  private geo = inject(GeoService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private layout = inject(LayoutService);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private host = inject(ElementRef) as ElementRef<HTMLElement>;

  @ViewChild('mapEl', { static: false }) mapEl!: ElementRef<HTMLDivElement>;

  eventoId = signal<number | null>(null);
  modoEdit = computed(() => this.eventoId() !== null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  guardando = signal<boolean>(false);
  msg = signal<string>('');
  errorGuardar = signal<boolean>(false);
  /** Errores por campo (clave = nombre de campo backend). */
  campoErrores = signal<Record<string, string>>({});

  tipos = signal<TipoEventoLite[]>([]);
  dependencias = signal<DependenciaLite[]>([]);
  subgrupos = signal<SubgrupoLite[]>([]);
  lineas = signal<Linea[]>([]);
  funcionarios = signal<Funcionario[]>([]);
  /**
   * Estado de la consulta de funcionarios, no solo su resultado.
   *
   * Hace falta porque «todavía no han llegado» y «llegaron y no hay ninguno»
   * se veían igual —la lista vacía— y significan cosas opuestas. El desplegable
   * mostraba «— Selecciona —» sobre la nada en los dos casos y el funcionario
   * solo se enteraba al guardar, con un «Este campo es obligatorio» señalando
   * un campo que no tenía nada que elegir.
   */
  funcionariosCargando = signal<boolean>(false);
  funcionariosPedidos = signal<boolean>(false);
  proyectos = signal<ProyectoLite[]>([]);
  actividadesPlan = signal<ActPlanLite[]>([]);
  indicadores = signal<IndicadorLite[]>([]);
  contratos = signal<ContratoLite[]>([]);

  // Campos NO modelo evento pero del form Django.
  direccion = '';
  latitud: number | null = null;
  longitud: number | null = null;
  hallazgos = '';
  recorrido = '';
  observaciones = '';
  proyectoId: number | null = null;
  contratoFinanciaId: number | null = null;

  form: Partial<EventoDetalle> & { activo?: boolean } = {
    nombre: '',
    descripcion: '',
    tipo_evento_id: null,
    dependencia_id: null,
    subgrupo_id: null,
    linea_id: null,
    funcionario_id: null,
    fecha_inicio: null,
    fecha_fin: null,
    hora_inicio: null,
    hora_fin: null,
    actividad_plan_id: null,
    indicador_id: null,
    magnitud_aportada: null,
    lugar_incidencia_id: null,
    sector_caracterizacion: null,
    activo: true,
  };

  subgruposFiltrados = computed<SubgrupoLite[]>(() => {
    const all = this.subgrupos();
    const dep = this.form.dependencia_id;
    if (dep == null) return all;
    return all.filter(s => s.dependencia_id === dep);
  });

  /**
   * El subgrupo elegido no tiene NINGÚN funcionario registrado.
   *
   * No es un caso raro: al 2026-08-26 son 31 de los 46 subgrupos. Un área
   * recién creada empieza siempre así, porque el subgrupo se crea en una
   * pantalla y las personas en otra.
   */
  sinFuncionarios = computed<boolean>(() =>
    this.form.subgrupo_id != null
    && this.funcionariosPedidos()
    && !this.funcionariosCargando()
    && this.funcionarios().length === 0);

  /** El nombre del subgrupo elegido, para poder nombrarlo en el aviso. */
  subgrupoElegido = computed<string>(() =>
    this.subgrupos().find(sg => sg.id === this.form.subgrupo_id)?.nombre ?? '');

  tipoActual = computed<TipoEventoLite | undefined>(() =>
    this.tipos().find(t => t.codigo === this.form.tipo_evento_id));

  // Campos extra data-driven del tipo (evento_creacion_schema) + sus valores.
  schemaExtra = signal<{ fields: any[]; catalogos: Record<string, any[]> }>(
    { fields: [], catalogos: {} });
  extras: Record<string, any> = {};

  // ── Leaflet mini-mapa ────────────────────────────────────────
  private map?: L.Map;
  private marker?: L.Marker;

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      const id = p.get('id');
      this.eventoId.set(id ? Number(id) : null);
      this.boot();
    });
  }

  ngAfterViewInit(): void {
    // Mapa se inicializa cuando loading()=false. Watch via setTimeout.
    const tryInit = () => {
      if (!this.loading() && this.mapEl?.nativeElement && !this.map) {
        this.initMap();
      } else if (this.loading()) {
        setTimeout(tryInit, 150);
      }
    };
    setTimeout(tryInit, 200);
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }

  /** La dirección quedó elegida de Catastro: mueve el pin y llena lat/lon.
   *
   * `null` = el usuario reescribió y ya no hay dirección válida. NO se borra el
   * punto: puede haberlo puesto a mano con click (un parque no tiene placa).
   * Lo que se invalida es la dirección, no la ubicación.
   */
  onDireccionElegida(d: DireccionElegida | null): void {
    this.direccion = d?.direccion ?? '';
    if (!d) { return; }
    this.latitud = d.lat;
    this.longitud = d.lon;
    if (this.map) {
      this.map.setView([d.lat, d.lon], 17);
      if (this.marker) {
        this.marker.setLatLng([d.lat, d.lon]);
      } else {
        this.marker = L.marker([d.lat, d.lon]).addTo(this.map);
      }
    }
  }

  private initMap(): void {
    const lat = this.latitud ?? 4.628;
    const lng = this.longitud ?? -74.153;
    this.map = L.map(this.mapEl.nativeElement, {
      center: [lat, lng], zoom: 13,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap © CARTO',
      subdomains: 'abcd', maxZoom: 19,
    }).addTo(this.map);
    if (this.latitud && this.longitud) {
      this.marker = L.marker([this.latitud, this.longitud]).addTo(this.map);
      this.map.setView([this.latitud, this.longitud], 15);
    }
    this.map.on('click', (e: any) => {
      const { lat, lng } = e.latlng;
      this.latitud = Math.round(lat * 1e6) / 1e6;
      this.longitud = Math.round(lng * 1e6) / 1e6;
      if (this.marker) {
        this.marker.setLatLng([lat, lng]);
      } else {
        this.marker = L.marker([lat, lng]).addTo(this.map!);
      }
    });
  }

  private boot(): void {
    this.loading.set(true);
    this.geo.catalogos().subscribe({
      next: c => {
        this.tipos.set(c.tipos_evento);
        this.dependencias.set(c.dependencias);
        this.subgrupos.set(c.subgrupos);
      },
    });

    // proyectos (paginado primer page solo)
    this.http.get<any>(this.cfg.url('/presupuesto/api/proyectos/')).subscribe(r => {
      const list = r?.results || r;
      this.proyectos.set((list as any[]).map(p => ({
        id: p.id, codigo: p.codigo, nombre: p.nombre,
      })));
    });

    if (this.modoEdit()) {
      this.api.detalle(this.eventoId()!).subscribe({
        next: ev => {
          Object.assign(this.form, ev);
          this.form.tipo_evento_id = ev.tipo_codigo;
          // Ubicación → propiedades del mapa (el marcador se coloca al
          // iniciar el mapa, cuando loading pasa a false).
          const e = ev as any;
          if (e.latitud != null) this.latitud = e.latitud;
          if (e.longitud != null) this.longitud = e.longitud;
          if (e.direccion) this.direccion = e.direccion;
          // Cascada presupuestal: precarga proyecto → actividad → KPI.
          if (e.proyecto_id) {
            this.proyectoId = e.proyecto_id;
            this.precargarPlan(e.proyecto_id, ev.actividad_plan_id, ev.indicador_id);
          }
          this.loading.set(false);
          this.layout.setBreadcrumb([
            { label: 'Inicio', url: '/' },
            { label: 'Lista de actividades', url: '/eventos' },
            { label: `Editar #${ev.id}` },
          ]);
          if (ev.subgrupo_id) {
            this.cargarLineas(ev.subgrupo_id);
            this.cargarFuncionarios(ev.subgrupo_id);
          }
        },
        error: () => {
          this.errorMsg.set('No se pudo cargar el evento.');
          this.loading.set(false);
        },
      });
    } else {
      // Preselección del tipo cuando se llega desde el hub de Actividades
      // (/eventos/nueva?tipo=CURSO).
      const tipoPreset = this.route.snapshot.queryParamMap.get('tipo');
      if (tipoPreset) {
        this.form.tipo_evento_id = tipoPreset;
        this.onTipoChange();
      }
      this.loading.set(false);
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Lista de actividades', url: '/eventos' },
        { label: 'Crear actividad' },
      ]);
    }
  }

  onTipoChange(): void {
    const t = this.tipoActual();
    if (!t?.permite_caracterizacion) this.form.sector_caracterizacion = null;
    this.cargarSchemaExtra();
  }

  /** Trae los campos extra del tipo (data-driven) y resetea sus valores. */
  cargarSchemaExtra(): void {
    const codigo = this.form.tipo_evento_id;
    if (!codigo) { this.schemaExtra.set({ fields: [], catalogos: {} }); return; }
    this.http
      .get<{ fields: any[]; catalogos: Record<string, any[]> }>(
        this.cfg.url(`/api/eventos/creacion-schema/?tipo=${encodeURIComponent(codigo)}`))
      .subscribe({
        next: (s) => {
          this.schemaExtra.set(s);
          // Conserva valores ya cargados (edición); inicializa los nuevos.
          for (const f of s.fields) {
            if (!(f.name in this.extras)) {
              this.extras[f.name] = (this.form as any)[f.name] ?? null;
            }
          }
        },
        error: () => this.schemaExtra.set({ fields: [], catalogos: {} }),
      });
  }

  onDepChange(): void {
    const dep = this.form.dependencia_id;
    const sub = this.subgrupos().find(s => s.id === this.form.subgrupo_id);
    if (sub && sub.dependencia_id !== dep) {
      this.form.subgrupo_id = null;
      this.form.linea_id = null;
      this.form.funcionario_id = null;
      this.funcionariosPedidos.set(false);
      this.lineas.set([]);
      this.funcionarios.set([]);
    }
  }

  onSubChange(): void {
    this.form.linea_id = null;
    this.form.funcionario_id = null;
    this.funcionariosPedidos.set(false);
    if (this.form.subgrupo_id) {
      this.cargarLineas(this.form.subgrupo_id);
      this.cargarFuncionarios(this.form.subgrupo_id);
    } else {
      this.lineas.set([]);
      this.funcionarios.set([]);
    }
  }

  onProyectoChange(): void {
    this.form.actividad_plan_id = null;
    this.form.indicador_id = null;
    this.contratoFinanciaId = null;
    this.actividadesPlan.set([]);
    this.indicadores.set([]);
    this.contratos.set([]);
    if (!this.proyectoId) return;
    // actividades_plan por proyecto
    this.http.get<{ items: ActPlanLite[] }>(
      this.cfg.url(`/presupuesto/api/plan-actividades-por-proyecto/${this.proyectoId}/`),
    ).subscribe(r => this.actividadesPlan.set(r.items || []));
    // contratos por proyecto
    this.http.get<any>(
      this.cfg.url(`/presupuesto/api/contratos-por-proyecto/${this.proyectoId}/`),
    ).subscribe(r => {
      const arr: any[] = r?.items || r?.results || r || [];
      this.contratos.set(arr.map((c: any) => ({
        id: c.id, numero: c.numero || c.contrato_numero,
        valor: Number(c.valor || 0),
      })));
    });
  }

  /** Precarga la cascada presupuestal al editar, conservando los valores. */
  private precargarPlan(proyId: number, actId: number | null, indId: number | null): void {
    this.http.get<{ items: ActPlanLite[] }>(
      this.cfg.url(`/presupuesto/api/plan-actividades-por-proyecto/${proyId}/`),
    ).subscribe(r => {
      this.actividadesPlan.set(r.items || []);
      if (actId) {
        this.form.actividad_plan_id = actId;
        this.http.get<any>(
          this.cfg.url(`/presupuesto/api/indicadores-por-actividad/${actId}/`),
        ).subscribe(rr => {
          const arr: any[] = rr?.indicadores || rr?.items || rr?.results || [];
          this.indicadores.set(arr.map((k: any) => ({
            id: k.id, nombre: k.nombre,
            unidad_medida: k.unidad_medida || k.unidad || '',
            meta_magnitud: Number(k.meta_magnitud || 0),
          })));
          if (indId) this.form.indicador_id = indId;
        });
      }
    });
    this.http.get<any>(
      this.cfg.url(`/presupuesto/api/contratos-por-proyecto/${proyId}/`),
    ).subscribe(r => {
      const arr: any[] = r?.items || r?.results || r || [];
      this.contratos.set(arr.map((c: any) => ({
        id: c.id, numero: c.numero || c.contrato_numero,
        valor: Number(c.valor || 0),
      })));
    });
  }

  onActividadChange(): void {
    this.form.indicador_id = null;
    this.indicadores.set([]);
    if (!this.form.actividad_plan_id) return;
    this.http.get<any>(
      this.cfg.url(`/presupuesto/api/indicadores-por-actividad/${this.form.actividad_plan_id}/`),
    ).subscribe(r => {
      const arr: any[] = r?.indicadores || r?.items || r?.results || [];
      this.indicadores.set(arr.map((k: any) => ({
        id: k.id, nombre: k.nombre,
        unidad_medida: k.unidad_medida || k.unidad || '',
        meta_magnitud: Number(k.meta_magnitud || 0),
      })));
    });
  }

  private cargarLineas(subId: number): void {
    this.http.get<any>(
      this.cfg.url(`/api/lineas-por-subgrupo/?subgrupo_id=${subId}`),
    ).subscribe(r => {
      const arr: any[] = Array.isArray(r) ? r : (r.results || r.lineas || []);
      this.lineas.set(arr);
    });
  }

  private cargarFuncionarios(subId: number): void {
    this.funcionariosCargando.set(true);
    this.funcionariosPedidos.set(true);
    this.http.get<any>(
      this.cfg.url(`/api/funcionarios/?subgrupo_id=${subId}`),
    ).subscribe({
      next: r => {
        const arr: any[] = Array.isArray(r) ? r : (r.results || r.funcionarios || []);
        this.funcionarios.set(arr.map((f: any) => ({
          id: f.id,
          nombre: f.nombre || f.nombre_completo || (`${f.nombre1 || ''} ${f.apellido1 || ''}`).trim(),
        })));
        this.funcionariosCargando.set(false);
      },
      // Si la consulta FALLA, `funcionariosPedidos` vuelve a false: una lista
      // vacía por un error de red no es lo mismo que un subgrupo sin gente, y
      // decirle al funcionario que registre personas que sí existen lo manda a
      // crear duplicados.
      error: () => {
        this.funcionariosCargando.set(false);
        this.funcionariosPedidos.set(false);
        this.funcionarios.set([]);
      },
    });
  }

  /** Limpia el realce de un campo cuando el usuario lo corrige. */
  limpiarError(campo: string): void {
    this.campoErrores.update((e) => limpiarCampo(e, campo));
  }

  /** Campos obligatorios reales (mismos que valida el backend). */
  private camposRequeridos(): string[] {
    const base = [
      'nombre', 'tipo_evento_id', 'dependencia_id',
      'subgrupo_id', 'funcionario_id', 'fecha_inicio',
    ];
    if (this.tipoActual()?.requiere_actividad_plan) {
      base.push('actividad_plan_id', 'indicador_id', 'magnitud_aportada');
    }
    return base;
  }

  guardar(): void {
    // Validación cliente de los obligatorios reales (espejo del backend).
    const faltan = camposVacios(
      this.form as Record<string, unknown>,
      this.camposRequeridos(),
    );
    const errores: Record<string, string> = faltan.length ? erroresObligatorios(faltan) : {};
    // «Este campo es obligatorio» sobre un desplegable que no tenía ninguna
    // opción culpa al funcionario de no llenar algo que el sistema no le dejó
    // llenar. Cuando el subgrupo no tiene gente, el mensaje dice eso.
    if (errores['funcionario_id'] && this.sinFuncionarios()) {
      errores['funcionario_id'] =
        `${this.subgrupoElegido() || 'Este subgrupo'} todavía no tiene funcionarios `
        + 'registrados. Regístralos en Organización → Funcionarios, o elige otro subgrupo.';
    }
    // La ubicación no está en `this.form` —lat/lng son campos aparte— así que
    // `camposVacios` no la ve. Es obligatoria desde el 2026-08-05: mientras no
    // lo fue, la actividad sin punto se anclaba sola en la sede de la Alcaldía
    // y el mapa terminó con 18 actividades apiladas ahí.
    if (this.latitud == null || this.longitud == null) {
      errores['ubicacion'] = 'Elige la dirección de la lista o marca el punto en el mapa.';
    }
    if (Object.keys(errores).length) {
      this.campoErrores.set(errores);
      this.errorGuardar.set(true);
      this.msg.set('Faltan campos obligatorios. Revisa los marcados en rojo.');
      if (faltan.length) enfocarPrimerInvalido(this.host, faltan);
      else this.mapEl?.nativeElement?.scrollIntoView({ block: 'center' });
      return;
    }

    this.guardando.set(true);
    this.msg.set('');
    this.errorGuardar.set(false);
    this.campoErrores.set({});

    const payload: any = {};
    for (const k of Object.keys(this.form)) {
      const v = (this.form as any)[k];
      if (v !== null && v !== undefined && v !== '') payload[k] = v;
    }
    // Direccion y lat/lng se mandan también — backend puede manejar
    // creando LugarIncidencia (en deuda: backend Angular CRUD aún no
    // crea LugarIncidencia, sólo persiste lugar_incidencia_id si llega).
    if (this.direccion) payload.direccion = this.direccion;
    if (this.latitud != null) payload.latitud = this.latitud;
    if (this.longitud != null) payload.longitud = this.longitud;
    if (this.hallazgos) payload.hallazgos = this.hallazgos;
    if (this.recorrido) payload.recorrido = this.recorrido;
    if (this.observaciones) payload.observaciones = this.observaciones;
    if (this.contratoFinanciaId) payload.contrato_financia = this.contratoFinanciaId;

    // Campos extra data-driven del tipo (cupo, festival, …). Solo los del
    // esquema vigente; el backend los acota a _CAMPOS_EDITABLES.
    for (const f of this.schemaExtra().fields) {
      const v = this.extras[f.name];
      payload[f.name] = (v === '' || v === undefined) ? null : v;
    }

    const obs = this.modoEdit()
      ? this.api.actualizar(this.eventoId()!, payload)
      : this.api.crear(payload);

    obs.subscribe({
      next: (r) => {
        this.msg.set('✓ ' + r.detail);
        this.guardando.set(false);
        setTimeout(() => this.router.navigate(['/eventos']), 600);
      },
      error: (err) => {
        this.errorGuardar.set(true);
        const campoErrs = mapearErroresBackend(err);
        const generales = campoErrs['__all__'];
        delete campoErrs['__all__'];
        this.campoErrores.set(campoErrs);
        const claves = Object.keys(campoErrs);
        if (claves.length) {
          this.msg.set(generales || 'Hay campos con errores. Revisa los marcados en rojo.');
          enfocarPrimerInvalido(this.host, claves);
        } else {
          this.msg.set(generales || err?.error?.detail || 'Error guardando.');
        }
        this.guardando.set(false);
      },
    });
  }
}
