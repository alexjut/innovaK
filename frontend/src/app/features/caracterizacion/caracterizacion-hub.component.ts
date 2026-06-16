import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { CaracterizacionApi } from './caracterizacion.api';
import { CaractInsights, SECTORES } from './caracterizacion.types';

/**
 * Hub de caracterización: 6 cards (un sector cada una) + KPIs globales.
 */
@Component({
  standalone: true,
  selector: 'app-caracterizacion-hub',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page caract-hub">

      <!-- Encabezado de página -->
      <header class="caract-hub__header">
        <div class="caract-hub__header-text">
          <h1 class="caract-hub__title">
            <span class="caract-hub__title-icon" aria-hidden="true">
              <i class="fa fa-clipboard-list"></i>
            </span>
            Caracterización ciudadana
          </h1>
          <p class="caract-hub__subtitle">
            Registro diferenciado por sector. Selecciona un sector para consultar o registrar.
          </p>
        </div>

        <!-- Tile KPI total -->
        @if (insights(); as ins) {
          <div class="caract-hub__kpi" [attr.aria-label]="'Total de caracterizaciones registradas: ' + ins.total">
            <span class="caract-hub__kpi-value">{{ ins.total }}</span>
            <span class="caract-hub__kpi-label">Total<br>caracterizaciones</span>
          </div>
        } @else {
          <div class="caract-hub__kpi caract-hub__kpi--loading" aria-busy="true" aria-label="Cargando totales">
            <span class="caract-hub__kpi-value skeleton" style="width:64px;height:2.25rem;display:inline-block;border-radius:4px;"></span>
            <span class="caract-hub__kpi-label">Total<br>caracterizaciones</span>
          </div>
        }
      </header>

      <!-- Grid de sectores -->
      <div class="caract-sectors"
           role="list"
           aria-label="Sectores de caracterización">

        @for (s of sectores; track s.codigo) {
          <a [routerLink]="['/caracterizacion', s.codigo]"
             class="caract-card"
             [class]="'caract-card--' + s.color"
             role="listitem"
             [attr.aria-label]="ariaLabel(s.codigo, s.label)">

            <!-- Ícono con fondo de color por sector -->
            <div class="caract-card__icon-wrap" aria-hidden="true">
              <i class="fa" [class]="s.icon"></i>
            </div>

            <!-- Texto -->
            <div class="caract-card__body">
              <h3 class="caract-card__title">{{ s.label }}</h3>
              <p class="caract-card__count">
                @if (countOf(s.codigo) !== null) {
                  {{ countOf(s.codigo) }} {{ countOf(s.codigo) === 1 ? 'registro' : 'registros' }}
                } @else {
                  <span aria-hidden="true" class="skeleton" style="width:80px;height:0.875rem;display:inline-block;border-radius:4px;"></span>
                  <span class="ui-sr-only">Cargando…</span>
                }
              </p>
            </div>

            <!-- Badge especial para Cultura (3 fichas de captura) -->
            @if (s.codigo === 'cultura') {
              <span class="caract-card__badge" aria-label="3 tipos de ficha disponibles">3 fichas</span>
            }

            <!-- Flecha decorativa -->
            <span class="caract-card__arrow" aria-hidden="true">
              <i class="fa fa-chevron-right"></i>
            </span>
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    /* ---- Host ---- */
    :host { display: block; }

    /* ---- Wrapper de página ---- */
    .caract-hub {
      max-width: 1100px;
      margin: 0 auto;
      padding: $space-6 $space-4 $space-12;

      @media (min-width: $bp-md) { padding: $space-8 $space-6 $space-16; }
    }

    /* ---- Encabezado con KPI tile lateral ---- */
    .caract-hub__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: $space-6;
      margin-bottom: $space-8;
      padding-bottom: $space-6;
      border-bottom: 2px solid $color-border;

      @media (max-width: #{$bp-sm - 1px}) {
        flex-direction: column;
        align-items: stretch;
      }
    }

    .caract-hub__header-text {
      flex: 1;
      min-width: 0;
    }

    .caract-hub__title {
      margin: 0 0 $space-2;
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-text;
      line-height: $line-height-tight;
      display: flex;
      align-items: center;
      gap: $space-3;

      @media (min-width: $bp-md) { font-size: $font-size-3xl; }
    }

    .caract-hub__title-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      background: $color-primary;
      color: $color-text-inverse;
      border-radius: $radius-lg;
      font-size: $font-size-xl;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(214, 0, 28, 0.30);

      @media (min-width: $bp-md) {
        width: 56px;
        height: 56px;
        font-size: $font-size-2xl;
      }
    }

    .caract-hub__subtitle {
      margin: 0;
      font-size: $font-size-sm;
      color: $color-text-muted;
      line-height: $line-height-relaxed;
      max-width: 520px;

      @media (min-width: $bp-md) { font-size: $font-size-base; }
    }

    /* ---- Tile KPI ---- */
    .caract-hub__kpi {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: $space-1;
      min-width: 120px;
      padding: $space-4 $space-5;
      background: linear-gradient(135deg, $color-primary 0%, $color-primary-dark 100%);
      color: $color-text-inverse;
      border-radius: $radius-xl;
      box-shadow: 0 8px 24px rgba(214, 0, 28, 0.25);
      text-align: center;
      flex-shrink: 0;

      @media (max-width: #{$bp-sm - 1px}) {
        flex-direction: row;
        align-items: center;
        gap: $space-4;
        min-width: 0;
      }

      &--loading {
        background: linear-gradient(135deg, $color-neutral-200 0%, $color-neutral-100 100%);
        box-shadow: none;
      }
    }

    .caract-hub__kpi-value {
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;
      line-height: 1;
      letter-spacing: -0.02em;
    }

    .caract-hub__kpi-label {
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      opacity: 0.85;
      line-height: $line-height-snug;
    }

    /* ---- Grid de cards ---- */
    .caract-sectors {
      display: grid;
      grid-template-columns: 1fr;
      gap: $space-4;

      @media (min-width: $bp-sm) { grid-template-columns: repeat(2, 1fr); }
      @media (min-width: $bp-lg) { grid-template-columns: repeat(3, 1fr); }
    }

    /* ---- Card base ---- */
    .caract-card {
      display: flex;
      align-items: center;
      gap: $space-4;
      padding: $space-5 $space-5;
      background: $color-bg;
      border: 1px solid $color-border;
      border-radius: $radius-xl;
      box-shadow: $shadow-sm;
      color: $color-text;
      text-decoration: none;
      position: relative;
      overflow: hidden;
      min-height: $touch-target-min;
      transition:
        transform 200ms ease-out,
        box-shadow 200ms ease-out,
        border-color 200ms ease-out;

      /* Franja de color a la izquierda */
      &::before {
        content: '';
        position: absolute;
        inset: 0 auto 0 0;
        width: 4px;
        border-radius: $radius-xl 0 0 $radius-xl;
        transition: width 200ms ease-out;
      }

      /* Gradiente sutil al fondo */
      &::after {
        content: '';
        position: absolute;
        inset: 0;
        opacity: 0;
        border-radius: inherit;
        transition: opacity 200ms ease-out;
        pointer-events: none;
      }

      &:hover,
      &:focus-visible {
        transform: translateY(-3px);
        box-shadow: $shadow-xl;
        border-color: $color-border-strong;
        z-index: 1;

        &::before { width: 6px; }
        &::after  { opacity: 0.04; }

        .caract-card__icon-wrap { transform: scale(1.1) rotate(-5deg); }
        .caract-card__title     { color: inherit; }
        .caract-card__arrow     { transform: translateX(4px); opacity: 1; }
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &:active {
        transform: translateY(-1px);
        box-shadow: $shadow-md;
      }
    }

    /* ---- Ícono circular con fondo de color ---- */
    .caract-card__icon-wrap {
      flex-shrink: 0;
      width: 52px;
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: $radius-lg;
      font-size: $font-size-xl;
      color: $color-text-inverse;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
      transition: transform 200ms ease-out;
    }

    /* ---- Texto ---- */
    .caract-card__body {
      flex: 1;
      min-width: 0;
    }

    .caract-card__title {
      margin: 0 0 $space-1;
      font-size: $font-size-md;
      font-weight: $font-weight-semibold;
      color: $color-text;
      line-height: $line-height-snug;
      transition: color $transition-fast;
    }

    .caract-card__count {
      margin: 0;
      font-size: $font-size-sm;
      color: $color-text-muted;
      line-height: $line-height-snug;
    }

    /* ---- Badge "3 fichas" (Cultura) ---- */
    .caract-card__badge {
      flex-shrink: 0;
      padding: 2px $space-2;
      font-size: $font-size-xs;
      font-weight: $font-weight-bold;
      line-height: $line-height-tight;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      color: $color-primary;
      background: $color-primary-bg;
      border: 1px solid rgba(214, 0, 28, 0.25);
      border-radius: $radius-pill;
      white-space: nowrap;
      align-self: flex-start;
    }

    /* ---- Flecha ---- */
    .caract-card__arrow {
      flex-shrink: 0;
      color: $color-neutral-300;
      font-size: $font-size-sm;
      opacity: 0.6;
      transition: transform 200ms ease-out, opacity 200ms ease-out;
    }

    /* ====================================================================
     * Variantes de color por sector
     * El color de fondo del ícono y la franja izquierda varían.
     * Los tonos de fondo del gradiente ::after también.
     * ==================================================================== */

    /* Cultura — primario (rojo) */
    .caract-card--primary {
      &::before { background: $color-primary; }
      &::after  { background: $color-primary; }
      .caract-card__icon-wrap { background: $color-primary; box-shadow: 0 4px 14px rgba(214, 0, 28, 0.35); }
      &:hover, &:focus-visible {
        .caract-card__title { color: $color-primary-dark; }
        .caract-card__arrow { color: $color-primary; opacity: 1; }
      }
    }

    /* Deporte — verde éxito */
    .caract-card--success {
      &::before { background: $color-success; }
      &::after  { background: $color-success; }
      .caract-card__icon-wrap { background: $color-success; box-shadow: 0 4px 14px rgba(22, 163, 74, 0.30); }
      &:hover, &:focus-visible {
        .caract-card__title { color: $color-success; }
        .caract-card__arrow { color: $color-success; opacity: 1; }
      }
    }

    /* Mujer — teal (accent) */
    .caract-card--accent {
      &::before { background: #0D9488; }
      &::after  { background: #0D9488; }
      .caract-card__icon-wrap { background: #0D9488; box-shadow: 0 4px 14px rgba(13, 148, 136, 0.30); }
      &:hover, &:focus-visible {
        .caract-card__title { color: #0F766E; }
        .caract-card__arrow { color: #0D9488; opacity: 1; }
      }
    }

    /* Salud — peligro (rojo suave) */
    .caract-card--danger {
      &::before { background: $color-danger; }
      &::after  { background: $color-danger; }
      .caract-card__icon-wrap { background: $color-danger; box-shadow: 0 4px 14px rgba(220, 38, 38, 0.30); }
      &:hover, &:focus-visible {
        .caract-card__title { color: $color-danger; }
        .caract-card__arrow { color: $color-danger; opacity: 1; }
      }
    }

    /* Poblacional — info (azul) */
    .caract-card--info {
      &::before { background: $color-info; }
      &::after  { background: $color-info; }
      .caract-card__icon-wrap { background: $color-info; box-shadow: 0 4px 14px rgba(59, 130, 246, 0.30); }
      &:hover, &:focus-visible {
        .caract-card__title { color: $color-info; }
        .caract-card__arrow { color: $color-info; opacity: 1; }
      }
    }

    /* Participación — warning (naranja/amarillo) */
    .caract-card--warning {
      &::before { background: $color-warning; }
      &::after  { background: $color-warning; }
      /* Ícono: texto oscuro para contraste sobre amarillo (ratio 10.7:1 sobre #F59E0B) */
      .caract-card__icon-wrap { background: $color-warning; color: $color-neutral-900; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.30); }
      &:hover, &:focus-visible {
        .caract-card__title { color: #92400E; }  /* amber-800: 4.9:1 sobre blanco */
        .caract-card__arrow { color: $color-warning; opacity: 1; }
      }
    }

    /* ====================================================================
     * Accesibilidad: prefers-reduced-motion
     * ==================================================================== */
    @media (prefers-reduced-motion: reduce) {
      .caract-card,
      .caract-card__icon-wrap,
      .caract-card__arrow,
      .caract-card::before,
      .caract-card::after {
        transition: none !important;
        transform: none !important;
        animation: none !important;
      }
    }
  `],
})
export class CaracterizacionHubComponent implements OnInit {
  private api = inject(CaracterizacionApi);
  private layout = inject(LayoutService);

  // Seguridad se oculta hasta tener su tabla dedicada + Form (sin captura
  // ni listado todavía). Vuelve al catálogo cuando se construya su sector.
  sectores = SECTORES.filter((s) => s.codigo !== 'seguridad');
  insights = signal<CaractInsights | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Caracterización' },
    ]);
    this.api.insights().subscribe({
      next: (i) => this.insights.set(i),
      error: () => this.insights.set(null),
    });
  }

  countOf(codigo: string): number | null {
    const ins = this.insights();
    if (!ins?.por_sector) return null;
    return ins.por_sector[codigo] ?? 0;
  }

  ariaLabel(codigo: string, label: string): string {
    const count = this.countOf(codigo);
    const suffix = count !== null
      ? `, ${count} ${count === 1 ? 'registro' : 'registros'}`
      : '';
    return `Caracterización de ${label}${suffix}`;
  }
}
