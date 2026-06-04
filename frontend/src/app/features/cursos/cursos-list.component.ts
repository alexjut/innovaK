import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { CursosApi } from './cursos.api';
import { LayoutService } from '../../core/layout/layout.service';
import { MisCursosResponse } from './cursos.types';

@Component({
  standalone: true,
  selector: 'app-cursos-list',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <h1>
          <i class="fa fa-chalkboard-teacher"></i>
          Mis cursos
        </h1>
        <p class="page__subtitle">
          Sesiones, asistencia, notas y reporte por curso.
          @if (data()) {
            <strong>{{ data()!.count }}</strong> curso{{ data()!.count === 1 ? '' : 's' }} a tu cargo.
          }
        </p>
      </header>

      @if (loading()) {
        <div class="page__loading">Cargando cursos…</div>
      } @else if (errorMsg()) {
        <div class="page__error">⚠ {{ errorMsg() }}</div>
      } @else if (data()) {
        @let d = data()!;
        @if (d.results.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Curso</th>
                  <th>Tipo</th>
                  <th>Subgrupo</th>
                  <th>Fechas</th>
                  <th>Inscritos</th>
                  <th>Sesiones</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                @for (c of d.results; track c.id) {
                  <tr>
                    <td>{{ c.id }}</td>
                    <td>
                      <strong>{{ c.nombre || '—' }}</strong>
                      @if (c.funcionario_nombre) {
                        <br><small class="muted">{{ c.funcionario_nombre }}</small>
                      }
                    </td>
                    <td>
                      <span class="ui-badge ui-badge--info">{{ c.tipo_nombre || c.tipo_codigo }}</span>
                    </td>
                    <td>{{ c.subgrupo || '—' }}</td>
                    <td>
                      <small>
                        @if (c.fecha_inicio) {
                          {{ c.fecha_inicio }} → {{ c.fecha_fin || '—' }}
                        } @else { — }
                      </small>
                    </td>
                    <td><strong>{{ c.inscritos }}</strong></td>
                    <td>
                      {{ c.pasadas }} / {{ c.sesiones }}
                      <small class="muted d-block">pasadas</small>
                    </td>
                    <td>
                      <a [routerLink]="['/cursos', c.id]"
                         class="ui-btn ui-btn--sm ui-btn--primary">
                        <i class="fa fa-eye"></i>
                        <span>Panel</span>
                      </a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <div class="ui-empty-state">
            <i class="fa fa-folder-open"></i>
            <p>No tienes cursos asignados como funcionario responsable.</p>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading, .page__error { padding: $space-4; text-align: center; color: $color-text-muted; }
    .page__error { color: $color-danger; }
    .muted { color: $color-text-muted; }
    .d-block { display: block; }
  `],
})
export class CursosListComponent implements OnInit {
  private api = inject(CursosApi);
  private layout = inject(LayoutService);

  data = signal<MisCursosResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mis cursos' },
    ]);
    this.api.misCursos().subscribe({
      next: (r) => { this.data.set(r); this.loading.set(false); },
      error: () => {
        this.errorMsg.set('No se pudieron cargar los cursos.');
        this.loading.set(false);
      },
    });
  }
}
