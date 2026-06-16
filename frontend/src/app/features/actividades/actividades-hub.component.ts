import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { ActividadesService, HubTiposResponse } from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Hub principal de Actividades — Angular nativo.
 *
 * Reemplaza el iframe al hub Django. Consume
 * `GET /api/actividades/tipos/` que ya filtra por módulos del usuario.
 */
@Component({
  standalone: true,
  selector: 'app-actividades-hub',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="hub">
      <header class="hub__header">
        <h1>
          <i class="fa fa-calendar-check" aria-hidden="true"></i>
          Actividades
        </h1>
        <p class="hub__subtitle">
          Eventos, capacitaciones, cursos, inscripciones, caracterizaciones
          y entregas del territorio. Selecciona un tipo de actividad para
          operar.
        </p>
      </header>

      @if (loading()) {
        <div class="hub__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="hub__error">⚠ {{ errorMsg() }}</div>
      } @else {
        @if (data()?.resumen_sector?.length) {
          <div class="sector-filtro" role="group" aria-label="Filtrar por sector">
            <button class="sector-pill" [class.sector-pill--active]="sectorFiltro() === null"
                    (click)="filtrarSector(null)">Todos</button>
            @for (s of data()!.resumen_sector!; track s.subgrupo_id) {
              <button class="sector-pill"
                      [class.sector-pill--active]="sectorFiltro() === s.subgrupo_id"
                      (click)="filtrarSector(s.subgrupo_id)">
                <span class="sector-pill__dot" [style.background]="s.color"></span>
                {{ s.nombre }}
              </button>
            }
          </div>

          <section class="hub-section">
            <h2 class="hub-section__title">Resumen por sector</h2>
            <div class="sector-grid">
              @for (s of data()!.resumen_sector!; track s.subgrupo_id) {
                <div class="sector-card" [style.border-left-color]="s.color">
                  <h3 class="sector-card__name">{{ s.nombre }}</h3>
                  <div class="sector-card__stats">
                    <span class="sector-card__stat"><strong>{{ s.num_proyectos }}</strong> proyecto{{ s.num_proyectos === 1 ? '' : 's' }}</span>
                    <span class="sector-card__stat"><strong>{{ s.num_eventos }}</strong> evento{{ s.num_eventos === 1 ? '' : 's' }}</span>
                  </div>
                </div>
              }
            </div>
          </section>
        }

        @if (data()?.cards_admin?.length) {
          <section class="hub-section">
            <h2 class="hub-section__title">Administrativo</h2>
            <div class="hub-grid">
              @for (c of data()!.cards_admin; track c.codigo) {
                <a [routerLink]="c.ruta"
                   class="ui-card ui-card--interactive"
                   [class]="'ui-card--' + c.color">
                  <div class="hub-card__icon">
                    <i class="fa" [class]="c.icono"></i>
                  </div>
                  <div class="ui-card__body">
                    <h3 class="ui-card__title">{{ c.nombre }}</h3>
                    <p class="ui-card__subtitle">{{ c.subtitulo }}</p>
                  </div>
                </a>
              }
            </div>
          </section>
        }

        <section class="hub-section">
          <h2 class="hub-section__title">Tipos de actividad</h2>
          @if (data()?.tipos?.length) {
            <div class="hub-grid">
              @for (t of data()!.tipos; track t.codigo) {
                <a [routerLink]="rutaTipo(t.codigo)"
                   class="ui-card ui-card--interactive ui-card--info">
                  <div class="hub-card__icon"
                       [style.color]="t.color_hex">
                    <i class="fa" [class]="t.icono"></i>
                  </div>
                  <div class="ui-card__body">
                    <h3 class="ui-card__title">{{ t.nombre }}</h3>
                    <p class="ui-card__subtitle">
                      {{ t.descripcion || ('Actividades de tipo ' + t.codigo) }}
                    </p>
                    <small class="hub-card__meta">
                      {{ t.num_eventos }} evento{{ t.num_eventos === 1 ? '' : 's' }}
                    </small>
                    @if (t.por_sector?.length) {
                      <div class="tipo-chips">
                        @for (c of t.por_sector!; track c.subgrupo_id) {
                          <span class="tipo-chip" [style.background]="c.color"
                                [attr.title]="c.nombre + ': ' + c.count">
                            {{ c.nombre }} {{ c.count }}
                          </span>
                        }
                      </div>
                    }
                  </div>
                </a>
              }
            </div>
          } @else {
            <div class="ui-empty-state">
              <i class="fa fa-info-circle"></i>
              <p>Tu rol no tiene acceso a ningún tipo de actividad.
                 Contacta al administrador.</p>
            </div>
          }
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .hub { max-width: 1200px; margin: 0 auto; }
    .hub__header { margin-bottom: $space-6; }
    .hub__header h1 {
      margin: 0;
      color: $color-primary;
      i { margin-right: $space-2; }
    }
    .hub__subtitle {
      color: $color-text-muted;
      margin: $space-2 0 0;
      max-width: 720px;
    }
    .hub__loading, .hub__error {
      padding: $space-4;
      text-align: center;
      color: $color-text-muted;
    }
    .hub__error { color: $color-danger; }
    .hub-section { margin-top: $space-5; }
    .hub-section__title {
      font-size: $font-size-md;
      color: $color-text-muted;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: 0 0 $space-3;
    }
    .hub-card__meta {
      display: block;
      margin-top: $space-1;
      color: $color-text-muted;
      font-size: $font-size-xs;
    }

    /* ── Capa de sector (solo admin) ── */
    .sector-filtro {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
      margin-bottom: $space-4;
    }
    .sector-pill {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      padding: $space-1 $space-3;
      min-height: 36px;
      border: 1.5px solid $color-border;
      border-radius: $radius-pill;
      background: $color-bg;
      color: $color-text;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      cursor: pointer;
      transition: border-color $transition-base, background $transition-base;
      &:hover { border-color: $color-text-muted; }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
      &--active { border-color: $color-primary; background: $color-bg-muted; }
    }
    .sector-pill__dot {
      width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
    }
    .sector-grid {
      display: grid;
      gap: $space-3;
      grid-template-columns: repeat(2, 1fr);
      @media (min-width: #{$bp-md}) { grid-template-columns: repeat(4, 1fr); }
    }
    .sector-card {
      background: $color-bg;
      border: 1px solid $color-border;
      border-left: 4px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-3 $space-4;
    }
    .sector-card__name {
      margin: 0 0 $space-2;
      font-size: $font-size-sm;
      color: $color-text;
    }
    .sector-card__stats { display: flex; flex-direction: column; gap: 2px; }
    .sector-card__stat {
      font-size: $font-size-xs;
      color: $color-text-muted;
      strong { color: $color-text; font-size: $font-size-md; }
    }
    .tipo-chips {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-top: $space-2;
      width: 100%;
    }
    .tipo-chip {
      display: block;
      width: 100%;
      box-sizing: border-box;
      padding: 3px $space-2;
      border-radius: $radius-md;
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      color: #fff;
      white-space: normal;
      overflow-wrap: anywhere;
    }
  `],
})
export class ActividadesHubComponent implements OnInit {
  private svc = inject(ActividadesService);
  private layout = inject(LayoutService);

  data = signal<HubTiposResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');

  /** Filtro de sector activo (subgrupo_id). Solo aplica a admin. */
  sectorFiltro = signal<number | null>(null);

  /** Las cards admin (Lista/Crear/Tipos) siguen apuntando al CRUD
   * Django mientras no haya editor de evento nativo. */
  djangoBase = '';

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Actividades' },
    ]);
    this.cargar();
  }

  private cargar(): void {
    this.loading.set(true);
    this.svc.tipos(this.sectorFiltro()).subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg.set('No se pudieron cargar los tipos de actividad.');
        this.loading.set(false);
      },
    });
  }

  /** Pulsar una pill: alterna el filtro por ese sector y recarga. */
  filtrarSector(id: number | null): void {
    this.sectorFiltro.set(this.sectorFiltro() === id ? null : id);
    this.cargar();
  }

  /** Caracterización tiene su hub propio; el resto va por /actividades/tipo. */
  rutaTipo(codigo: string): string[] {
    return codigo.toUpperCase() === 'CARACTERIZACION'
      ? ['/caracterizacion']
      : ['/actividades/tipo', codigo];
  }
}
