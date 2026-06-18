import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CursosApi } from './cursos.api';
import { LayoutService } from '../../core/layout/layout.service';
import { ConfigService } from '../../core/config/config.service';
import { DescargasService } from '../../core/descargas.service';
import {
  AsistenciaResponse, CursoDetalle, NotasResponse, ReporteResponse,
  Sesion, SesionesResponse, SesionCrearItem,
} from './cursos.types';

type TabId = 'sesiones' | 'asistencia' | 'notas' | 'reporte';

@Component({
  standalone: true,
  selector: 'app-curso-detalle',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loadingCurso()) {
        <div class="page__loading">Cargando curso…</div>
      } @else if (errorCurso()) {
        <div class="page__error">⚠ {{ errorCurso() }}</div>
      } @else if (curso()) {
        @let c = curso()!;
        <header class="curso-header">
          <h1><i class="fa fa-chalkboard-user" aria-hidden="true"></i> {{ c.nombre || ('Curso #' + c.id) }}</h1>
          <p class="curso-meta">
            <span class="ui-badge ui-badge--info">{{ c.tipo_nombre || c.tipo_codigo }}</span>
            @if (c.subgrupo) { · <strong>{{ c.subgrupo }}</strong> }
            @if (c.funcionario_nombre) { · {{ c.funcionario_nombre }} }
          </p>
          <div class="curso-kpis">
            <div class="curso-kpi">
              <span class="value">{{ c.resumen.inscritos_count }}</span>
              <span class="label">Inscritos</span>
            </div>
            <div class="curso-kpi">
              <span class="value">{{ c.resumen.sesiones_count }}</span>
              <span class="label">Sesiones</span>
            </div>
            <div class="curso-kpi">
              <span class="value">{{ c.resumen.sesiones_pasadas }}</span>
              <span class="label">Pasadas</span>
            </div>
          </div>
          <div class="curso-actions">
            @if (c.url_inscripcion) {
              <a [href]="c.url_inscripcion" target="_blank" rel="noopener"
                 class="ui-btn ui-btn--primary ui-btn--sm"
                 title="Abrir el formulario de inscripción / caracterización del curso (el que se llena por QR)">
                <i class="fa fa-user-plus"></i> Inscripción
              </a>
              <a [routerLink]="['/eventos', c.id, 'qr']"
                 class="ui-btn ui-btn--outline ui-btn--sm" title="Ver / descargar el QR para compartir">
                <i class="fa fa-qrcode"></i> QR
              </a>
            }
            <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="exportar('excel')">
              <i class="fa fa-file-excel"></i> Reporte Excel
            </button>
            <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="exportar('pdf')">
              <i class="fa fa-file-pdf"></i> Reporte PDF
            </button>
            <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="exportar('asistencia')">
              <i class="fa fa-list-check"></i> Asistencia PDF
            </button>
          </div>
        </header>

        <nav class="tabs" role="tablist">
          @for (t of TABS; track t.id) {
            <button type="button" class="tab"
                    [class.tab--active]="tab() === t.id"
                    (click)="setTab(t.id)" [attr.role]="'tab'">
              <i class="fa" [class]="t.icon"></i>
              {{ t.label }}
            </button>
          }
        </nav>

        <section class="tab-content">
          @switch (tab()) {

            <!-- SESIONES -->
            @case ('sesiones') {
              @let s = sesiones();
              @if (loadingSes()) { <p>Cargando…</p> }
              @else if (s) {
                @if (s.results.length) {
                  <table class="ui-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Fecha</th>
                        <th>Hora</th>
                        <th>Nombre</th>
                        <th>Lugar</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (ses of s.results; track ses.id) {
                        <tr>
                          <td>{{ ses.id }}</td>
                          <td>{{ ses.fecha }}</td>
                          <td>
                            @if (ses.hora_inicio) {
                              {{ ses.hora_inicio }}–{{ ses.hora_fin || '?' }}
                            } @else { — }
                          </td>
                          <td>{{ ses.nombre || '—' }}</td>
                          <td>{{ ses.lugar || '—' }}</td>
                          <td>
                            <button class="ui-btn ui-btn--sm ui-btn--primary"
                                    (click)="verAsistencia(ses)">
                              <i class="fa fa-clipboard-check"></i> Asistencia
                            </button>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <div class="ui-empty-state">
                    <i class="fa fa-calendar-times"></i>
                    <p>El curso aún no tiene sesiones planeadas.</p>
                  </div>
                }
                <details class="form-create" [open]="!s.results.length">
                  <summary>+ Crear sesiones bulk</summary>
                  <p class="muted">
                    Una sesión por línea, formato:
                    <code>YYYY-MM-DD HH:MM HH:MM Nombre opcional</code>
                  </p>
                  <textarea [(ngModel)]="textoSesiones" rows="5"
                            placeholder="2026-06-05 07:00 08:00 Sesión 1
2026-06-12 07:00 08:00 Sesión 2"></textarea>
                  <button class="ui-btn ui-btn--primary"
                          [disabled]="!textoSesiones.trim() || creandoSes()"
                          (click)="crearSesionesBulk()">
                    @if (creandoSes()) { Creando… }
                    @else { Crear sesiones }
                  </button>
                  @if (sesCrearMsg()) {
                    <p class="ui-info-bar ui-info-bar--success">{{ sesCrearMsg() }}</p>
                  }
                </details>
              }
            }

            <!-- ASISTENCIA -->
            @case ('asistencia') {
              @let a = asistencia();
              @if (!sesionSel()) {
                <div class="ui-empty-state">
                  <i class="fa fa-hand-pointer"></i>
                  <p>Selecciona una sesión desde la pestaña "Sesiones" para tomar lista.</p>
                </div>
              } @else if (a) {
                <div class="asist-header">
                  <h3>{{ a.nombre || ('Sesión #' + a.clase_id) }} — {{ a.fecha }}</h3>
                  <small>{{ a.total_inscritos }} inscritos</small>
                </div>
                <table class="ui-table">
                  <thead>
                    <tr><th>Participante</th><th>Presente</th><th>Observación</th></tr>
                  </thead>
                  <tbody>
                    @for (p of a.lista; track p.participante_id) {
                      <tr>
                        <td>{{ p.nombre }}</td>
                        <td>
                          <input type="checkbox"
                                 [checked]="!!marcasMap()[p.participante_id]?.presente"
                                 (change)="setPresente(p.participante_id, $any($event.target).checked)">
                        </td>
                        <td>
                          <input type="text"
                                 [value]="marcasMap()[p.participante_id]?.observacion || ''"
                                 (input)="setObs(p.participante_id, $any($event.target).value)"
                                 placeholder="Opcional">
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
                <div class="acciones">
                  <button class="ui-btn ui-btn--primary"
                          [disabled]="guardandoAsist()"
                          (click)="guardarAsistencia()">
                    @if (guardandoAsist()) { Guardando… }
                    @else { Guardar asistencia }
                  </button>
                  @if (asistMsg()) {
                    <span class="ui-info-bar ui-info-bar--success">{{ asistMsg() }}</span>
                  }
                </div>
              } @else { <p>Cargando…</p> }
            }

            <!-- NOTAS -->
            @case ('notas') {
              @let n = notas();
              @if (loadingNotas()) { <p>Cargando…</p> }
              @else if (n) {
                @if (n.results.length) {
                  <table class="ui-table">
                    <thead>
                      <tr><th>Participante</th><th>Nota</th><th>Etiqueta</th><th>Fecha</th></tr>
                    </thead>
                    <tbody>
                      @for (it of n.results; track it.id) {
                        <tr>
                          <td>{{ it.participante_id }}</td>
                          <td><strong>{{ it.nota }}</strong></td>
                          <td>{{ it.etiqueta || '—' }}</td>
                          <td>{{ it.fecha || '—' }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                  <div class="promedios">
                    <h4>Promedios por participante</h4>
                    @for (pair of objKeys(n.promedios); track pair) {
                      <div><strong>{{ pair }}:</strong> {{ n.promedios[pair] }}</div>
                    }
                  </div>
                } @else {
                  <div class="ui-empty-state">
                    <i class="fa fa-pen"></i>
                    <p>Aún no hay notas registradas.</p>
                  </div>
                }
                <details class="form-create">
                  <summary>+ Agregar nota</summary>
                  <div class="form-row">
                    <label>Participante ID
                      <input type="number" [(ngModel)]="nuevoPartId" min="1">
                    </label>
                    <label>Nota
                      <input type="number" [(ngModel)]="nuevaNota" step="0.1" min="0" max="5">
                    </label>
                    <label>Etiqueta
                      <input type="text" [(ngModel)]="nuevaEtiqueta">
                    </label>
                    <button class="ui-btn ui-btn--primary"
                            [disabled]="!nuevoPartId || nuevaNota == null"
                            (click)="agregarNota()">Agregar</button>
                  </div>
                  @if (notaMsg()) { <p class="ui-info-bar ui-info-bar--success">{{ notaMsg() }}</p> }
                </details>
              }
            }

            <!-- REPORTE -->
            @case ('reporte') {
              @let r = reporte();
              @if (loadingReporte()) { <p>Cargando…</p> }
              @else if (r) {
                <table class="ui-table">
                  <thead>
                    <tr>
                      <th>Participante</th>
                      <th>Documento</th>
                      <th>Asistencia</th>
                      <th>%</th>
                      <th>Notas</th>
                      <th>Promedio</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (it of r.results; track it.participante_id) {
                      <tr>
                        <td>{{ it.persona_nombre }}</td>
                        <td>{{ it.documento }}</td>
                        <td>{{ it.asistencias }} / {{ it.total_marcas }}</td>
                        <td>
                          @if (it.pct_asistencia != null) { {{ it.pct_asistencia }}% }
                          @else { — }
                        </td>
                        <td>{{ it.notas.join(', ') || '—' }}</td>
                        <td>{{ it.promedio ?? '—' }}</td>
                        <td>
                          @if (it.aprobado === true) {
                            <span class="ui-badge ui-badge--success">Aprobó</span>
                          } @else if (it.aprobado === false) {
                            <span class="ui-badge ui-badge--danger">Reprobó</span>
                          } @else {
                            <span class="ui-badge ui-badge--muted">Pendiente</span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
            }
          }
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .curso-header h1 { margin: 0 0 $space-1; color: $color-primary; i { margin-right: $space-2; } }
    .curso-meta { color: $color-text-muted; margin: 0 0 $space-3; }
    .curso-kpis { display: flex; gap: $space-2; flex-wrap: wrap; }
    .curso-actions { display: flex; gap: $space-2; flex-wrap: wrap; margin-top: $space-3; }
    .curso-kpi {
      background: $color-bg;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      padding: $space-2 $space-3;
      min-width: 96px;
      text-align: center;
      .value {
        display: block;
        font-size: $font-size-xl;
        font-weight: $font-weight-bold;
        color: $color-primary;
      }
      .label {
        display: block;
        font-size: $font-size-xs;
        letter-spacing: 0.01em;
        color: $color-text-muted;
      }
    }
    .tabs {
      display: flex;
      gap: 2px;
      margin-top: $space-4;
      border-bottom: 2px solid $color-border;
    }
    .tab {
      background: transparent;
      border: 0;
      padding: $space-2 $space-3;
      cursor: pointer;
      font-size: $font-size-sm;
      color: $color-text-muted;
      border-bottom: 3px solid transparent;
      margin-bottom: -2px;
      i { margin-right: $space-1; }
      &:hover { color: $color-primary; }
      &--active {
        color: $color-primary;
        border-bottom-color: $color-primary;
        font-weight: $font-weight-semibold;
      }
    }
    .tab-content { padding: $space-3 0; }
    .form-create {
      margin-top: $space-3;
      padding: $space-3;
      background: $color-bg-subtle;
      border-radius: $radius-md;
      summary { cursor: pointer; font-weight: $font-weight-semibold; }
      textarea, input[type=text], input[type=number] {
        width: 100%;
        padding: $space-1 $space-2;
        border: 1px solid $color-border;
        border-radius: $radius-sm;
        margin: $space-1 0;
        font-family: inherit;
      }
      textarea { min-height: 80px; }
    }
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr auto;
      gap: $space-2;
      align-items: end;
      label { display: block; font-size: $font-size-xs; color: $color-text-muted; }
    }
    .asist-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: $space-2;
      h3 { margin: 0; }
    }
    .acciones { margin-top: $space-3; display: flex; gap: $space-2; align-items: center; }
    .promedios { margin-top: $space-3; }
    .muted { color: $color-text-muted; }
    .page__loading, .page__error { padding: $space-4; text-align: center; color: $color-text-muted; }
    .page__error { color: $color-danger; }
  `],
})
export class CursoDetalleComponent implements OnInit {
  private api = inject(CursosApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private cfg = inject(ConfigService);
  private descargas = inject(DescargasService);

  /** Abre el reporte/asistencia del curso (endpoints Django con la sesión). */
  exportar(tipo: 'excel' | 'pdf' | 'asistencia'): void {
    const id = this.eventoId();
    const urls: Record<string, string> = {
      excel: `/cursos/${id}/reporte/excel/`,
      pdf: `/cursos/${id}/reporte/pdf/`,
      asistencia: `/evento/asistencia-pdf/${id}/`,
    };
    this.descargas.descargar(urls[tipo]);
  }

  readonly TABS = [
    { id: 'sesiones' as TabId, label: 'Sesiones', icon: 'fa-calendar' },
    { id: 'asistencia' as TabId, label: 'Asistencia', icon: 'fa-clipboard-check' },
    { id: 'notas' as TabId, label: 'Notas', icon: 'fa-pen' },
    { id: 'reporte' as TabId, label: 'Reporte', icon: 'fa-file-alt' },
  ];

  eventoId = signal<number>(0);
  curso = signal<CursoDetalle | null>(null);
  loadingCurso = signal<boolean>(true);
  errorCurso = signal<string>('');
  tab = signal<TabId>('sesiones');

  // Sesiones
  sesiones = signal<SesionesResponse | null>(null);
  loadingSes = signal<boolean>(false);
  textoSesiones = '';
  creandoSes = signal<boolean>(false);
  sesCrearMsg = signal<string>('');

  // Asistencia
  sesionSel = signal<Sesion | null>(null);
  asistencia = signal<AsistenciaResponse | null>(null);
  marcas: Record<number, { presente: boolean; observacion: string }> = {};
  marcasSig = signal(0);
  guardandoAsist = signal<boolean>(false);
  asistMsg = signal<string>('');
  marcasMap = computed(() => { this.marcasSig(); return this.marcas; });

  // Notas
  notas = signal<NotasResponse | null>(null);
  loadingNotas = signal<boolean>(false);
  nuevoPartId: number | null = null;
  nuevaNota: number | null = null;
  nuevaEtiqueta = '';
  notaMsg = signal<string>('');

  // Reporte
  reporte = signal<ReporteResponse | null>(null);
  loadingReporte = signal<boolean>(false);

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      const id = Number(p.get('id') || 0);
      this.eventoId.set(id);
      this.cargarCurso();
      this.cargarSesiones();
    });
  }

  private cargarCurso(): void {
    this.loadingCurso.set(true);
    this.api.detalle(this.eventoId()).subscribe({
      next: (c) => {
        this.curso.set(c);
        this.loadingCurso.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Mis cursos', url: '/cursos' },
          { label: c.nombre || `Curso #${c.id}` },
        ]);
      },
      error: () => {
        this.errorCurso.set('No se pudo cargar el curso.');
        this.loadingCurso.set(false);
      },
    });
  }

  setTab(t: TabId): void {
    this.tab.set(t);
    if (t === 'notas' && !this.notas()) this.cargarNotas();
    if (t === 'reporte' && !this.reporte()) this.cargarReporte();
  }

  // ── Sesiones ───────────────────────────────────────────────────
  private cargarSesiones(): void {
    this.loadingSes.set(true);
    this.api.sesiones(this.eventoId()).subscribe({
      next: (r) => { this.sesiones.set(r); this.loadingSes.set(false); },
      error: () => this.loadingSes.set(false),
    });
  }

  crearSesionesBulk(): void {
    const lines = this.textoSesiones.split('\n').map(l => l.trim()).filter(Boolean);
    const items: SesionCrearItem[] = [];
    for (const l of lines) {
      // formato: YYYY-MM-DD HH:MM HH:MM Nombre
      const m = l.match(/^(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?(?:\s+(\d{2}:\d{2}))?(?:\s+(.+))?$/);
      if (!m) continue;
      items.push({
        fecha: m[1],
        hora_inicio: m[2],
        hora_fin: m[3],
        nombre: m[4],
      });
    }
    if (!items.length) {
      this.sesCrearMsg.set('Formato inválido. Verifica el ejemplo.');
      return;
    }
    this.creandoSes.set(true);
    this.api.crearSesiones(this.eventoId(), items).subscribe({
      next: (r) => {
        this.sesCrearMsg.set(`✓ ${r.creadas} sesión(es) creada(s).`);
        this.creandoSes.set(false);
        this.textoSesiones = '';
        this.cargarSesiones();
      },
      error: () => {
        this.sesCrearMsg.set('Error creando sesiones.');
        this.creandoSes.set(false);
      },
    });
  }

  // ── Asistencia ─────────────────────────────────────────────────
  verAsistencia(s: Sesion): void {
    this.sesionSel.set(s);
    this.tab.set('asistencia');
    this.asistencia.set(null);
    this.marcas = {};
    this.api.asistencia(s.id).subscribe({
      next: (r) => {
        this.asistencia.set(r);
        for (const p of r.lista) {
          this.marcas[p.participante_id] = {
            presente: !!p.presente,
            observacion: p.observacion || '',
          };
        }
        this.marcasSig.update(v => v + 1);
      },
    });
  }

  setPresente(partId: number, val: boolean): void {
    this.marcas[partId] = { ...this.marcas[partId], presente: val };
    this.marcasSig.update(v => v + 1);
  }
  setObs(partId: number, val: string): void {
    this.marcas[partId] = { ...this.marcas[partId], observacion: val };
  }

  guardarAsistencia(): void {
    const s = this.sesionSel();
    if (!s) return;
    const marcas = Object.entries(this.marcas).map(([pid, v]) => ({
      participante_id: Number(pid),
      presente: !!v.presente,
      observacion: v.observacion || undefined,
    }));
    this.guardandoAsist.set(true);
    this.api.tomarLista(s.id, { marcas }).subscribe({
      next: (r) => {
        this.asistMsg.set(`✓ ${r.presentes} presentes / ${r.ausentes} ausentes`);
        this.guardandoAsist.set(false);
      },
      error: () => {
        this.asistMsg.set('Error guardando asistencia.');
        this.guardandoAsist.set(false);
      },
    });
  }

  // ── Notas ──────────────────────────────────────────────────────
  private cargarNotas(): void {
    this.loadingNotas.set(true);
    this.api.notas(this.eventoId()).subscribe({
      next: (r) => { this.notas.set(r); this.loadingNotas.set(false); },
      error: () => this.loadingNotas.set(false),
    });
  }

  agregarNota(): void {
    if (!this.nuevoPartId || this.nuevaNota == null) return;
    this.api.guardarNotas(this.eventoId(), [{
      participante_id: this.nuevoPartId,
      nota: this.nuevaNota,
      etiqueta: this.nuevaEtiqueta || undefined,
    }]).subscribe({
      next: (r) => {
        this.notaMsg.set(`✓ ${r.creadas} creada(s), ${r.actualizadas} actualizada(s).`);
        this.nuevoPartId = null;
        this.nuevaNota = null;
        this.nuevaEtiqueta = '';
        this.cargarNotas();
      },
      error: () => this.notaMsg.set('Error registrando nota.'),
    });
  }

  // ── Reporte ────────────────────────────────────────────────────
  private cargarReporte(): void {
    this.loadingReporte.set(true);
    this.api.reporte(this.eventoId()).subscribe({
      next: (r) => { this.reporte.set(r); this.loadingReporte.set(false); },
      error: () => this.loadingReporte.set(false),
    });
  }

  // util para iterar Record en template
  objKeys(o: Record<string, any>): string[] {
    return Object.keys(o || {});
  }
}
