import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ActividadesService, SubgruposResponse } from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';
import { LucideAngularModule } from 'lucide-angular';
import { areaIcono as areaIconoUtil, areaColor as areaColorUtil } from './area-visual.util';

/**
 * Pantalla 2 — dado un tipo, lista subgrupos con eventos vivos o (si caracterización) los 6 sectores.
 */
@Component({
  standalone: true,
  selector: 'app-actividades-tipo',
  imports: [CommonModule, RouterLink, LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loading()) {
        <div class="page__loading">Cargando...</div>
      } @else if (errorMsg()) {
        <div class="page__error">⚠ {{ errorMsg() }}</div>
      } @else if (data()) {
        @let d = data()!;
        <header class="page__header">
          <div class="page__header-row">
            <div class="page__icon-badge" [style.background]="d.tipo.color_hex || '#6B7280'">
              <i class="fa" [class]="d.tipo.icono || 'fa-folder'"></i>
            </div>
            <h1>{{ d.tipo.nombre }}</h1>
          </div>
          @if (d.tipo.permite_inscripcion) {
            <span class="page__badge" [style.color]="d.tipo.color_hex || '#3B82F6'">
              <span class="page__badge-dot" [style.background]="d.tipo.color_hex || '#3B82F6'"></span>
              Inscripción
            </span>
          }
          <p class="page__subtitle">
            {{ d.tipo.descripcion || 'Selecciona un área para ver las actividades disponibles.' }}
          </p>
        </header>

        @if (d.tipo.permite_caracterizacion) {
          <h2 class="page__section">Sectores</h2>
          <div class="hub-grid">
            @for (s of d.sectores; track s.codigo) {
              <a [routerLink]="['/caracterizacion', s.codigo]"
                class="ui-card ui-card--interactive ui-card--accent">
                <div class="hub-card__icon">
                  <i class="fa" [class]="s.icono"></i>
                </div>
                <div class="ui-card__body">
                  <h3 class="ui-card__title">{{ s.nombre }}</h3>
                  <p class="ui-card__subtitle">
                    {{ s.descripcion || ('Caracterizar persona — sector ' + s.codigo) }}
                  </p>
                </div>
              </a>
            }
          </div>
        } @else if (d.subgrupos.length) {
          <div class="kpi-strip">
            <div class="kpi-card">
              <div class="kpi-card__value">{{ totalActividades() }}</div>
              <div class="kpi-card__label">Actividad{{ totalActividades() === 1 ? '' : 'es' }} total{{ totalActividades() === 1 ? '' : 'es' }}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-card__value">{{ d.subgrupos.length }}</div>
              <div class="kpi-card__label">Área{{ d.subgrupos.length === 1 ? '' : 's' }} / Subgrupos</div>
            </div>
          </div>
          <h2 class="page__section">Áreas / Subgrupos</h2>
          <div class="hub-grid">
            @for (s of d.subgrupos; track s.id) {
              <a [routerLink]="['/actividades/tipo', codigo(), 'sub', s.id]"
                class="ui-card ui-card--interactive ui-card--info">
                <div class="hub-card__icon" [style.background]="areaColor(s.nombre)">
                  <lucide-icon [name]="areaIcono(s.nombre)" [size]="24"></lucide-icon>
                </div>
                <div class="ui-card__body">
                  <h3 class="ui-card__title">{{ s.nombre }}</h3>
                  <p class="ui-card__subtitle">
                    {{ s.num_eventos }} actividad{{ s.num_eventos === 1 ? '' : 'es' }}
                    @if (s.dependencia_nombre) {
                      · {{ s.dependencia_nombre }}
                    }
                  </p>
                </div>
              </a>
            }
          </div>
        } @else {
          <div class="ui-empty-state">
            <i class="fa fa-folder-open"></i>
            <p>Este tipo aún no tiene áreas con actividades registradas.</p>
            <a [routerLink]="['/eventos/nueva']" [queryParams]="{ tipo: codigo() }"
              class="ui-btn ui-btn--primary">
              <i class="fa fa-plus-circle"></i>
              <span>Crear actividad de tipo «{{ d.tipo.nombre }}»</span>
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
    .page__badge {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: $space-1;
      font-size: $font-size-xs;
      font-weight: $font-weight-bold;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      padding: $space-1 $space-3;
      border-radius: $radius-pill;
      background: $color-bg-muted;
      height: fit-content;
      margin-top: $space-1;
    }
    .page__badge-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
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
    .kpi-card:nth-child(2) {
      border-top-color: $color-secondary;
    }
    .kpi-card__value { font-size: $font-size-xl; font-weight: $font-weight-bold; color: $color-text; }
    .kpi-card__label {
      font-size: $font-size-xs;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .page__subtitle { flex-basis: 100%; color: $color-text-muted; margin: 0; }
    .page__section {
      font-size: $font-size-md;
      color: $color-text-muted;
      letter-spacing: 0.01em;
      margin: $space-4 0 $space-3;
    }
    .page__loading, .page__error {
      padding: $space-4;
      text-align: center;
      color: $color-text-muted;
    }
    .page__error { color: $color-danger; }
  `],
})
export class ActividadesTipoComponent implements OnInit {
  private svc = inject(ActividadesService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private layout = inject(LayoutService);

  data = signal<SubgruposResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  codigo = signal<string>('');
  totalActividades = computed(() =>
    (this.data()?.subgrupos ?? []).reduce((acc, s) => acc + s.num_eventos, 0)
  );

  /** Ícono/color de área para las tarjetas de subgrupo, mismo mapeo que usa el hub de Actividades. */
  areaIcono(nombre: string): string {
    return areaIconoUtil(nombre);
  }

  areaColor(nombre: string): string {
    return areaColorUtil(nombre);
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      const codigo = (p.get('codigo') || '').toUpperCase();
      // Caracterización tiene su hub propio en /caracterizacion (una sola puerta).
      if (codigo === 'CARACTERIZACION') {
        this.router.navigate(['/caracterizacion'], { replaceUrl: true });
        return;
      }
      // Cursos/capacitaciones: todo va al panel de cursos (una sola puerta).
      // Antes esta pantalla quedaba vacía porque CURSO permite_caracterizacion
      // y caía en la rama de "Sectores" (solo poblada para Admin).
      if (codigo === 'CURSO' || codigo === 'CAPACITACION') {
        this.router.navigate(['/cursos'], { replaceUrl: true });
        return;
      }
      // Festivales: panel propio (proyecto 2780, Meta 4). El código real
      // en BD es FESTIVAL; aceptamos también el alias FESTIVAL_CULTURAL.
      if (codigo === 'FESTIVAL' || codigo === 'FESTIVAL_CULTURAL') {
        this.router.navigate(['/festivales'], { replaceUrl: true });
        return;
      }
      this.codigo.set(codigo);
      this.cargar(codigo);
    });
  }

  private cargar(codigo: string): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.svc.subgrupos(codigo).subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Actividades', url: '/actividades' },
          { label: r.tipo.nombre },
        ]);
      },
      error: (err) => {
        if (err.status === 404) {
          this.errorMsg.set('Tipo de actividad no encontrado.');
        } else {
          this.errorMsg.set('No se pudo cargar la información.');
        }
        this.loading.set(false);
      },
    });
  }
}
