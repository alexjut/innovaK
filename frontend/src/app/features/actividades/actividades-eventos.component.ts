import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ActividadesService, EventosResponse } from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';
import { EventoQrFormComponent } from '../../shared/evento-qr-form/evento-qr-form.component';
import { LucideAngularModule } from 'lucide-angular';
import { areaIcono as areaIconoUtil, areaColor as areaColorUtil } from './area-visual.util';

/**
 * Pantalla 3 — tabla de eventos del par (tipo, subgrupo).
 *
 * Acciones contextuales por evento dependen del tipo:
 *   - permite_inscripcion (Banco)   → ver beneficiarios
 *   - permite_caracterizacion        → ver caracterizaciones
 *   - CURSO/CAPACITACION             → panel del curso
 *   - siempre                        → editar
 */
@Component({
  standalone: true,
  selector: 'app-actividades-eventos',
  imports: [CommonModule, FormsModule, RouterLink, EventoQrFormComponent, LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loading()) {
        <div class="page__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="page__error">⚠ {{ errorMsg() }}</div>
      } @else if (data()) {
        @let d = data()!;
        <header class="page__header">
          <div class="page__header-row">
            <div class="page__icon-badge" [style.background]="areaColor(d.subgrupo.nombre)">
              <lucide-icon [name]="areaIcono(d.subgrupo.nombre)" [size]="22"></lucide-icon>
            </div>
            <h1>{{ d.tipo.nombre }} · {{ d.subgrupo.nombre }}</h1>
          </div>
          <p class="page__subtitle">
            Actividades del área {{ d.subgrupo.nombre }} en {{ d.tipo.nombre }}.
            <strong>{{ d.total }} evento{{ d.total === 1 ? '' : 's' }}</strong>
          </p>
        </header>

        <div class="kpi-strip">
          <div class="kpi-card">
            <div class="kpi-card__value">{{ d.total }}</div>
            <div class="kpi-card__label">Evento{{ d.total === 1 ? '' : 's' }} total{{ d.total === 1 ? '' : 'es' }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-card__value">{{ activosCount() }}</div>
            <div class="kpi-card__label">Activo{{ activosCount() === 1 ? '' : 's' }}</div>
          </div>
        </div>

        @if (d.eventos.length) {
          <div class="ui-filter-bar">
            <label class="ui-search">
              <i class="fa fa-search"></i>
              <input type="search" [(ngModel)]="q" placeholder="Buscar por nombre...">
            </label>
            <label class="mapa-field" style="margin:0">
              <span>Línea</span>
              <select [(ngModel)]="lineaSel" (change)="recargar()">
                <option [ngValue]="null">— Todas —</option>
                @for (l of d.lineas_disponibles; track l.id) {
                  <option [ngValue]="l.id">{{ l.nombre }}</option>
                }
              </select>
            </label>
          </div>
        }

        @if (d.eventos.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Nombre</th>
                  <th>Línea</th>
                  <th>Fecha inicio</th>
                  <th>Fecha fin</th>
                  <th>Funcionario</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                @for (ev of eventosFiltrados(d.eventos); track ev.id) {
                  <tr>
                    <td>{{ ev.id }}</td>
                    <td>{{ ev.nombre || '—' }}</td>
                    <td>
                      @if (ev.linea) {
                        <span class="ui-badge ui-badge--info">{{ ev.linea }}</span>
                      } @else { — }
                    </td>
                    <td>{{ ev.fecha_inicio || '—' }}</td>
                    <td>{{ ev.fecha_fin || '—' }}</td>
                    <td>{{ ev.funcionario_nombre || '—' }}</td>
                    <td>
                      @if (ev.activo) {
                        <span class="ui-badge ui-badge--success">Activo</span>
                      } @else {
                        <span class="ui-badge ui-badge--muted">Inactivo</span>
                      }
                    </td>
                    <td>
                      <div class="acciones">
                        @if (d.tipo.permite_inscripcion || esEntrega() || esCaptura()) {
                          <a [routerLink]="rutaBeneficiarios()" [queryParams]="queryBeneficiarios(ev.id)"
                             class="ui-btn ui-btn--sm ui-btn--primary">
                            <i class="fa fa-users"></i> {{ labelBeneficiarios() }}
                          </a>
                        }
                        @if (d.tipo.permite_caracterizacion) {
                          <a [routerLink]="['/caracterizacion/evento', ev.id]"
                             class="ui-btn ui-btn--sm ui-btn--accent">
                            <i class="fa fa-clipboard-list"></i> Caracterizaciones
                          </a>
                        }
                        @if (esCurso()) {
                          <a [routerLink]="['/cursos', ev.id]"
                             class="ui-btn ui-btn--sm ui-btn--accent">
                            <i class="fa fa-chalkboard-teacher"></i> Panel del curso
                          </a>
                        }
                        @if (d.tipo.permite_inscripcion || d.tipo.permite_caracterizacion || esEntrega() || esCaptura() || esCurso()) {
                          <app-evento-qr-form [eventoId]="ev.id" [urlPublica]="ev.url_publica"
                                              [etiquetaForm]="esCurso() ? 'Inscripción' : 'Formulario'" />
                        }
                        <a [routerLink]="['/eventos', ev.id, 'editar']"
                           class="ui-btn ui-btn--sm ui-btn--ghost ui-btn--ghost-red">
                          <i class="fa fa-edit"></i> Editar
                        </a>
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <div class="ui-empty-state">
            <i class="fa fa-folder-open"></i>
            <p>No hay actividades registradas para
              <strong>{{ d.tipo.nombre }}</strong> en
              <strong>{{ d.subgrupo.nombre }}</strong>.</p>
            <a [routerLink]="['/eventos/nueva']" [queryParams]="{ tipo: codigo() }"
               class="ui-btn ui-btn--primary">
              <i class="fa fa-plus-circle"></i>
              <span>Crear nueva actividad</span>
            </a>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header {
      align-items: flex-start;
      padding-bottom: $space-4;
      border-bottom: 1px solid $color-border;
      margin-bottom: $space-4;
    }
    .page__header-row { display: flex; align-items: center; gap: $space-3; }
    .page__icon-badge {
      width: 44px; height: 44px; border-radius: $radius-md;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; color: #fff; font-size: $font-size-lg;
    }
    .page__header-row h1 {
      margin: 0;
      color: $color-text;
      font-size: 32px;
      font-weight: $font-weight-semibold;
    }
    .page__header-row h1::after {
      content: '';
      display: block;
      width: 48px;
      height: 4px;
      border-radius: $radius-pill;
      background: $color-secondary;
      margin-top: $space-2;
    }
    .kpi-strip {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      max-width: 420px;
      gap: $space-4;
      margin-bottom: $space-5;
    }
    .kpi-card {
      background: $color-bg-muted;
      border: 1px solid $color-border;
      border-top: 3px solid $color-info;
      border-radius: $radius-lg;
      padding: $space-4 $space-5;
    }
    .kpi-card:nth-child(2) { border-top-color: $color-secondary; }
    .kpi-card__value { font-size: $font-size-xl; font-weight: $font-weight-bold; color: $color-text; }
    .kpi-card__label {
      font-size: $font-size-xs;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading, .page__error {
      padding: $space-4;
      text-align: center;
      color: $color-text-muted;
    }
    .page__error { color: $color-danger; }
    .acciones {
      display: flex;
      gap: $space-1;
      flex-wrap: wrap;
    }
    .ui-btn--ghost-red { color: $color-primary; }
    .ui-btn--ghost-red:hover:not(:disabled) { color: $color-primary-dark; background: $color-bg-muted; }
  `],
})
export class ActividadesEventosComponent implements OnInit {
  private svc = inject(ActividadesService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  data = signal<EventosResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  codigo = signal<string>('');
  subId = signal<number>(0);
  lineaSel: number | null = null;
  q = '';

  activosCount = computed(() => (this.data()?.eventos ?? []).filter(e => e.activo).length);

  eventosFiltrados(eventos: EventosResponse['eventos']): EventosResponse['eventos'] {
    const term = this.q.trim().toLowerCase();
    if (!term) return eventos;
    return eventos.filter(e => (e.nombre || '').toLowerCase().includes(term));
  }

  /** Icono/color de area para la insignia del encabezado, mismo mapeo que usa el hub de Actividades. */
  areaIcono(nombre: string): string {
    return areaIconoUtil(nombre);
  }

  areaColor(nombre: string): string {
    return areaColorUtil(nombre);
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      const codigo = p.get('codigo') || '';
      const sub = Number(p.get('subgrupo') || '0');
      this.codigo.set(codigo);
      this.subId.set(sub);
      this.lineaSel = null;
      this.recargar();
    });
  }

  esCurso(): boolean {
    const c = this.codigo();
    return c === 'CURSO' || c === 'CAPACITACION';
  }

  esEntrega(): boolean {
    return this.codigo() === 'ENTREGA';
  }

  /** Tipos del motor genérico de captura (Cultura y futuros). */
  esCaptura(): boolean {
    return ['CULTURA_ORG', 'ESTIMULO_CULTURAL', 'PROYECTO_CULTURAL'].includes(this.codigo());
  }

  /** Ruta nativa del botón "Beneficiarios" según tipo_evento. */
  rutaBeneficiarios(): string {
    const c = this.codigo();
    if (c === 'JOVENES_BECA') return '/jovenes';
    if (c === 'ENTREGA') return '/entregas';
    if (this.esCaptura()) return '/captura';
    return '/banco';
  }
  queryBeneficiarios(eventoId: number): Record<string, any> {
    if (this.codigo() === 'JOVENES_BECA') return { evento_id: eventoId };
    if (this.esCaptura()) return { evento: eventoId, tipo: this.codigo() };
    return { evento: eventoId };
  }

  labelBeneficiarios(): string {
    const c = this.codigo();
    if (c === 'JOVENES_BECA') return 'Entregas';
    if (this.esCaptura()) return 'Registros';
    return 'Beneficiarios';
  }

  recargar(): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.svc.eventos(this.codigo(), this.subId(), this.lineaSel).subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Actividades', url: '/actividades' },
          { label: r.tipo.nombre, url: `/actividades/tipo/${r.tipo.codigo}` },
          { label: r.subgrupo.nombre },
        ]);
      },
      error: () => {
        this.errorMsg.set('No se pudieron cargar los eventos.');
        this.loading.set(false);
      },
    });
  }
}
