import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  AfterViewInit, ChangeDetectionStrategy, Component, ElementRef,
  OnDestroy, OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import * as L from 'leaflet';
import { ConfigService } from '../../core/config/config.service';
import {
  DependenciaLite, GeoService, SubgrupoLite, TipoEventoLite,
} from '../../core/geo/geo.service';
import { LayoutService } from '../../core/layout/layout.service';
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
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <h1>
          <i class="fa" [class]="modoEdit() ? 'fa-edit' : 'fa-plus-circle'"></i>
          @if (modoEdit()) { Editar actividad #{{ eventoId() }} }
          @else { Crear nueva actividad }
        </h1>
        <p class="page__subtitle">
          Cuatro bloques: básicos · responsable · ubicación · plan presupuestal.
        </p>
      </header>

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
                <input type="text" [(ngModel)]="form.nombre" name="nombre" required
                       placeholder="Nombre de la actividad">
              </label>

              <label class="field">
                <span>Tipo de actividad *</span>
                <select [(ngModel)]="form.tipo_evento_id" name="tipo" required
                        (change)="onTipoChange()">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (t of tipos(); track t.codigo) {
                    <option [ngValue]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
              </label>

              <label class="field">
                <span>Fecha *</span>
                <input type="date" [(ngModel)]="form.fecha_inicio" name="fini" required>
              </label>

              <label class="field">
                <span>Fecha fin (opcional)</span>
                <input type="date" [(ngModel)]="form.fecha_fin" name="ffin">
              </label>

              <label class="field">
                <span>Hora inicio</span>
                <input type="time" [(ngModel)]="horaInicio" name="hini">
                <small class="muted">UI únicamente (no persistido)</small>
              </label>

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
                <select [(ngModel)]="form.dependencia_id" name="dep" required
                        (change)="onDepChange()">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (d of dependencias(); track d.id) {
                    <option [ngValue]="d.id">{{ d.nombre }}</option>
                  }
                </select>
              </label>

              <label class="field">
                <span>Subgrupo *</span>
                <select [(ngModel)]="form.subgrupo_id" name="sub" required
                        (change)="onSubChange()">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (s of subgruposFiltrados(); track s.id) {
                    <option [ngValue]="s.id">{{ s.nombre }}</option>
                  }
                </select>
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
                <select [(ngModel)]="form.funcionario_id" name="func" required>
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (f of funcionarios(); track f.id) {
                    <option [ngValue]="f.id">{{ f.nombre }}</option>
                  }
                </select>
              </label>
            </div>
          </fieldset>

          <!-- ▷ Bloque 3 — Ubicación (dirección + mapa) -->
          <fieldset class="bloque">
            <legend><i class="fa fa-map-location-dot" aria-hidden="true"></i> 3. Ubicación</legend>
            <div class="form-grid">
              <label class="field field--full">
                <span>Dirección *</span>
                <input type="text" [(ngModel)]="direccion" name="dir" required
                       placeholder="Cl. 38 Sur # 78K-58 (escribe y click en mapa)">
              </label>
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
                <span class="muted">Click en el mapa para marcar el punto exacto</span>
                <div #mapEl class="mini-mapa"></div>
              </div>
            </div>
          </fieldset>

          <!-- ▷ Bloque 4 — Plan presupuestal (cascada B) -->
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
                <select [(ngModel)]="form.actividad_plan_id" name="ap" required
                        (change)="onActividadChange()">
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (a of actividadesPlan(); track a.id) {
                    <option [ngValue]="a.id">#{{ a.id }} · {{ a.nombre }}</option>
                  }
                </select>
              </label>

              <label class="field">
                <span>Indicador / KPI *</span>
                <select [(ngModel)]="form.indicador_id" name="ind" required>
                  <option [ngValue]="null">— Selecciona —</option>
                  @for (k of indicadores(); track k.id) {
                    <option [ngValue]="k.id">
                      {{ k.nombre }} ({{ k.unidad_medida }}, meta {{ k.meta_magnitud }})
                    </option>
                  }
                </select>
              </label>

              <label class="field">
                <span>Magnitud aportada *</span>
                <input type="number" step="0.01" [(ngModel)]="form.magnitud_aportada"
                       name="mag" placeholder="0.00" required>
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
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
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

  @ViewChild('mapEl', { static: false }) mapEl!: ElementRef<HTMLDivElement>;

  eventoId = signal<number | null>(null);
  modoEdit = computed(() => this.eventoId() !== null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  guardando = signal<boolean>(false);
  msg = signal<string>('');
  errorGuardar = signal<boolean>(false);

  tipos = signal<TipoEventoLite[]>([]);
  dependencias = signal<DependenciaLite[]>([]);
  subgrupos = signal<SubgrupoLite[]>([]);
  lineas = signal<Linea[]>([]);
  funcionarios = signal<Funcionario[]>([]);
  proyectos = signal<ProyectoLite[]>([]);
  actividadesPlan = signal<ActPlanLite[]>([]);
  indicadores = signal<IndicadorLite[]>([]);
  contratos = signal<ContratoLite[]>([]);

  // Campos NO modelo evento pero del form Django.
  horaInicio = '';
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

  tipoActual = computed<TipoEventoLite | undefined>(() =>
    this.tipos().find(t => t.codigo === this.form.tipo_evento_id));

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
  }

  onDepChange(): void {
    const dep = this.form.dependencia_id;
    const sub = this.subgrupos().find(s => s.id === this.form.subgrupo_id);
    if (sub && sub.dependencia_id !== dep) {
      this.form.subgrupo_id = null;
      this.form.linea_id = null;
      this.form.funcionario_id = null;
      this.lineas.set([]);
      this.funcionarios.set([]);
    }
  }

  onSubChange(): void {
    this.form.linea_id = null;
    this.form.funcionario_id = null;
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
    this.http.get<any>(
      this.cfg.url(`/api/funcionarios/?subgrupo_id=${subId}`),
    ).subscribe(r => {
      const arr: any[] = Array.isArray(r) ? r : (r.results || r.funcionarios || []);
      this.funcionarios.set(arr.map((f: any) => ({
        id: f.id,
        nombre: f.nombre || f.nombre_completo || (`${f.nombre1 || ''} ${f.apellido1 || ''}`).trim(),
      })));
    });
  }

  guardar(): void {
    if (!this.form.nombre || !this.form.tipo_evento_id) {
      this.errorGuardar.set(true);
      this.msg.set('Nombre y tipo de actividad son obligatorios.');
      return;
    }
    this.guardando.set(true);
    this.msg.set('');
    this.errorGuardar.set(false);

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
        this.msg.set(err?.error?.detail || 'Error guardando.');
        this.guardando.set(false);
      },
    });
  }
}
