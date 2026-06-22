import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CursosApi } from './cursos.api';
import { LayoutService } from '../../core/layout/layout.service';
import { ToastService } from '../../shared/ui/toast.service';
import { ConfirmService } from '../../shared/ui/confirm.service';
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
        <div class="page__header-row">
          <h1>
            <i class="fa fa-chalkboard-teacher"></i>
            Mis cursos
          </h1>
          <a routerLink="/cursos/insights" class="ui-btn ui-btn--outline ui-btn--sm">
            <i class="fa fa-chart-line"></i> Insights
          </a>
        </div>
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
                      <tr [class.fila--archivable]="esAntiguo(c)">
                        <td>{{ c.id }}</td>
                        <td>
                          <strong>{{ c.nombre || '—' }}</strong>
                          @if (!c.funcionario_nombre) {
                            <span class="warn-badge" title="Este curso no tiene docente asignado">
                              <i class="fa fa-triangle-exclamation"></i> Sin docente
                            </span>
                          }
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
                          @if (!c.fecha_fin) {
                            <br><span class="alerta-badge" title="El curso no tiene fecha de fin">Sin fecha fin</span>
                          }
                          @if (esAnioAnterior(c)) {
                            <span class="alerta-badge alerta-badge--year" title="El curso inició en un año anterior">Año anterior</span>
                          }
                        </td>
                        <td>
                          <strong>{{ c.inscritos }}</strong>@if (c.cupo_maximo != null) { <span class="muted"> / {{ c.cupo_maximo }}</span> }
                          @if (c.cupo_maximo != null && c.inscritos >= c.cupo_maximo) {
                            <span class="pill pill--full">Lleno</span>
                          }
                          @if (c.en_espera > 0) {
                            <small class="muted d-block">{{ c.en_espera }} en espera</small>
                          }
                        </td>
                        <td>{{ c.pasadas }} / {{ c.sesiones }} <small class="muted d-block">pasadas</small></td>
                        <td>
                          <a [routerLink]="['/cursos', c.id]" class="ui-btn ui-btn--sm ui-btn--primary">
                            <i class="fa fa-eye"></i> <span>Panel</span>
                          </a>
                          <button type="button" class="ui-btn ui-btn--sm ui-btn--outline"
                                  [disabled]="archivandoId() === c.id"
                                  (click)="archivar(c)"
                                  title="Archivar el curso (lo oculta de la lista; no borra nada)">
                            <i class="fa fa-box-archive"></i>
                            <span>{{ archivandoId() === c.id ? 'Archivando…' : 'Archivar' }}</span>
                          </button>
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
    .page__header-row { display: flex; align-items: center; justify-content: space-between; gap: $space-3; flex-wrap: wrap; }
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
    .pill { border-radius: $radius-pill; padding: 1px 8px; font-size: .7rem; font-weight: 600; margin-left: 4px; }
    .pill--full { background: #FEE2E2; color: #991B1B; }
    .warn-badge {
      display: inline-flex; align-items: center; gap: 4px; margin-left: 6px;
      background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;
      border-radius: $radius-pill; padding: 1px 8px; font-size: .7rem; font-weight: 600;
      i { color: #D97706; }
    }
    .alerta-badge {
      display: inline-block; margin: 2px 4px 0 0;
      background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;
      border-radius: $radius-pill; padding: 1px 8px; font-size: .68rem; font-weight: 600;
    }
    .alerta-badge--year { background: #FEE2E2; color: #991B1B; border-color: #FECACA; }
    .fila--archivable { background: #FFFBEB; }
  `],
})
export class CursosListComponent implements OnInit {
  private api = inject(CursosApi);
  private layout = inject(LayoutService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);

  data = signal<MisCursosResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  filtro = signal<string | null>(null);
  archivandoId = signal<number | null>(null);

  /** Año actual para detectar cursos de vigencias pasadas (CC-05). */
  private readonly anioActual = new Date().getFullYear();

  /** Curso sin fecha de fin: candidato a archivar (contamina listas/insights). */
  esSinFechaFin(c: CursoLite): boolean {
    return !c.fecha_fin;
  }

  /** Curso iniciado en un año anterior al actual. */
  esAnioAnterior(c: CursoLite): boolean {
    if (!c.fecha_inicio) return false;
    const anio = Number(c.fecha_inicio.slice(0, 4));
    return Number.isFinite(anio) && anio < this.anioActual;
  }

  /** Fila a resaltar como candidata a archivar (CC-05). */
  esAntiguo(c: CursoLite): boolean {
    return this.esSinFechaFin(c) || this.esAnioAnterior(c);
  }

  async archivar(c: CursoLite): Promise<void> {
    const ok = await this.confirm.ask({
      title: 'Archivar curso',
      message: `¿Archivar "${c.nombre || ('Curso #' + c.id)}"? Se ocultará de la lista `
        + 'y de los insights. No se borra nada; puedes reactivarlo después.',
      danger: true,
      confirmText: 'Archivar',
      cancelText: 'Cancelar',
    });
    if (!ok) return;
    this.archivandoId.set(c.id);
    this.api.setActivo(c.id, false).subscribe({
      next: () => {
        // Lo sacamos de la lista al instante (el backend ya solo lista activos).
        const d = this.data();
        if (d) {
          const results = d.results.filter((x) => x.id !== c.id);
          this.data.set({ count: results.length, results });
        }
        this.archivandoId.set(null);
        this.toast.success('Curso archivado.');
      },
      error: () => {
        this.archivandoId.set(null);
        this.toast.error('No se pudo archivar el curso.');
      },
    });
  }

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
