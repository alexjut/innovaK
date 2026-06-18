import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CursosApi } from './cursos.api';
import { LayoutService } from '../../core/layout/layout.service';
import { CursoLite, MisCursosResponse } from './cursos.types';

interface GrupoCursos {
  subgrupo: string;
  cursos: CursoLite[];
}

@Component({
  standalone: true,
  selector: 'app-cursos-list',
  imports: [CommonModule, FormsModule, RouterLink],
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
        @if (data()!.results.length) {
          <!-- Filtro por subgrupo -->
          @if (subgrupos().length > 1) {
            <div class="filtro">
              <span class="filtro__label">Subgrupo:</span>
              <button class="chip" [class.chip--on]="filtro() === null" (click)="filtro.set(null)">
                Todos
              </button>
              @for (s of subgrupos(); track s) {
                <button class="chip" [class.chip--on]="filtro() === s" (click)="filtro.set(s)">
                  {{ s }}
                </button>
              }
            </div>
          }

          <!-- Una sección por subgrupo -->
          @for (g of grupos(); track g.subgrupo) {
            <section class="grupo">
              <h2 class="grupo__titulo">
                <i class="fa fa-layer-group" aria-hidden="true"></i>
                {{ g.subgrupo }}
                <span class="grupo__n">{{ g.cursos.length }}</span>
              </h2>
              <div class="ui-table-responsive">
                <table class="ui-table">
                  <thead>
                    <tr>
                      <th>#</th><th>Curso</th><th>Tipo</th><th>Fechas</th>
                      <th>Inscritos</th><th>Sesiones</th><th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (c of g.cursos; track c.id) {
                      <tr>
                        <td>{{ c.id }}</td>
                        <td>
                          <strong>{{ c.nombre || '—' }}</strong>
                          @if (c.funcionario_nombre) {
                            <br><small class="muted">{{ c.funcionario_nombre }}</small>
                          } @else {
                            <br><small class="muted sin-doc">Sin docente asignado</small>
                          }
                        </td>
                        <td><span class="ui-badge ui-badge--info">{{ c.tipo_nombre || c.tipo_codigo }}</span></td>
                        <td>
                          <small>
                            @if (c.fecha_inicio) { {{ c.fecha_inicio }} → {{ c.fecha_fin || '—' }} }
                            @else { — }
                          </small>
                        </td>
                        <td><strong>{{ c.inscritos }}</strong></td>
                        <td>{{ c.pasadas }} / {{ c.sesiones }} <small class="muted d-block">pasadas</small></td>
                        <td>
                          <a [routerLink]="['/cursos', c.id]" class="ui-btn ui-btn--sm ui-btn--primary">
                            <i class="fa fa-eye"></i> <span>Panel</span>
                          </a>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </section>
          }
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
    .sin-doc { font-style: italic; }
    .d-block { display: block; }
    .filtro { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; margin-bottom: $space-3; }
    .filtro__label { color: $color-text-muted; font-size: $font-size-sm; }
    .chip {
      border: 1px solid $color-border; background: #fff; border-radius: $radius-pill;
      padding: 4px 14px; font-size: $font-size-sm; cursor: pointer; color: $color-text;
      transition: background .15s, border-color .15s;
    }
    .chip:hover { border-color: $color-primary; }
    .chip--on { background: $color-primary; color: #fff; border-color: $color-primary; }
    .grupo { margin-bottom: $space-5; }
    .grupo__titulo {
      display: flex; align-items: center; gap: $space-2;
      font-size: $font-size-md; color: $color-text; margin: 0 0 $space-2;
      i { color: $color-text-muted; }
    }
    .grupo__n {
      background: $color-bg-muted; color: $color-text-muted;
      border-radius: $radius-pill; padding: 1px 10px; font-size: $font-size-sm;
    }
  `],
})
export class CursosListComponent implements OnInit {
  private api = inject(CursosApi);
  private layout = inject(LayoutService);

  data = signal<MisCursosResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  filtro = signal<string | null>(null);

  subgrupos = computed<string[]>(() => {
    const set = new Set((this.data()?.results ?? []).map((c) => c.subgrupo || 'Sin subgrupo'));
    return [...set].sort((a, b) => a.localeCompare(b));
  });

  grupos = computed<GrupoCursos[]>(() => {
    const rows = this.data()?.results ?? [];
    const f = this.filtro();
    const map = new Map<string, CursoLite[]>();
    for (const c of rows) {
      const sg = c.subgrupo || 'Sin subgrupo';
      if (f && sg !== f) continue;
      (map.get(sg) ?? map.set(sg, []).get(sg)!).push(c);
    }
    return [...map.entries()]
      .map(([subgrupo, cursos]) => ({ subgrupo, cursos }))
      .sort((a, b) => a.subgrupo.localeCompare(b.subgrupo));
  });

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
