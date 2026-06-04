import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ActividadesService, EventosResponse } from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';

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
  imports: [CommonModule, FormsModule, RouterLink],
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
          <h1>{{ d.tipo.nombre }} · {{ d.subgrupo.nombre }}</h1>
          <p class="page__subtitle">
            Actividades del área {{ d.subgrupo.nombre }} en {{ d.tipo.nombre }}.
            <strong>{{ d.total }} evento{{ d.total === 1 ? '' : 's' }}</strong>
          </p>
        </header>

        @if (d.lineas_disponibles.length) {
          <div class="ui-filter-bar">
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
                @for (ev of d.eventos; track ev.id) {
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
                        @if (d.tipo.permite_inscripcion || esEntrega()) {
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
                        @if (d.tipo.permite_inscripcion || d.tipo.permite_caracterizacion || esEntrega()) {
                          <a [href]="ev.url_publica" target="_blank" rel="noopener"
                             class="ui-btn ui-btn--sm ui-btn--outline" title="Abrir el formulario público (el que se llena por QR)">
                            <i class="fa fa-file-lines"></i> Formulario
                          </a>
                          <a [routerLink]="['/eventos', ev.id, 'qr']"
                             class="ui-btn ui-btn--sm ui-btn--ghost" title="Ver/descargar el QR para compartir">
                            <i class="fa fa-qrcode"></i> QR
                          </a>
                        }
                        <a [routerLink]="['/eventos', ev.id, 'editar']"
                           class="ui-btn ui-btn--sm ui-btn--ghost">
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
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; }
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

  /** Ruta nativa del botón "Beneficiarios" según tipo_evento. */
  rutaBeneficiarios(): string {
    const c = this.codigo();
    if (c === 'JOVENES_BECA') return '/jovenes';
    if (c === 'ENTREGA') return '/entregas';
    return '/banco';
  }
  queryBeneficiarios(eventoId: number): Record<string, number> {
    return this.codigo() === 'JOVENES_BECA'
      ? { evento_id: eventoId } : { evento: eventoId };
  }

  labelBeneficiarios(): string {
    const c = this.codigo();
    if (c === 'JOVENES_BECA') return 'Entregas';
    if (c === 'ENTREGA') return 'Beneficiarios';
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
