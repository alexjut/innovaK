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
    <div class="page">
      <header class="page__header">
        <h1>Caracterización ciudadana</h1>
        <p class="page__subtitle">6 sectores con wizards públicos. Datos consolidados aquí.</p>
      </header>

      @if (insights(); as ins) {
        <div class="ui-card ui-card--primary kpi-total">
          <div class="ui-card__body">
            <span class="kpi__label">Total caracterizaciones</span>
            <span class="kpi__value">{{ ins.total }}</span>
          </div>
        </div>
      }

      <div class="hub-grid">
        @for (s of sectores; track s.codigo) {
          <a [routerLink]="['/caracterizacion', s.codigo]"
             class="hub-card"
             [class]="'hub-card--' + s.color">
            <div class="hub-card__icon">
              <i class="fa" [class]="s.icon" aria-hidden="true"></i>
            </div>
            <h3 class="hub-card__title">{{ s.label }}</h3>
            <p class="hub-card__subtitle">
              @if (countOf(s.codigo) !== null) {
                {{ countOf(s.codigo) }} registro{{ countOf(s.codigo) === 1 ? '' : 's' }}
              } @else {
                Ver caracterizaciones
              }
            </p>
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header { margin-bottom: $space-6; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }
    .kpi-total { margin-bottom: $space-4; }
    .kpi-total .ui-card__body {
      display: flex;
      flex-direction: column;
    }
    .kpi__label {
      font-size: $font-size-xs;
      color: $color-text-muted;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: $font-weight-semibold;
    }
    .kpi__value {
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;
      color: $color-primary;
    }
  `],
})
export class CaracterizacionHubComponent implements OnInit {
  private api = inject(CaracterizacionApi);
  private layout = inject(LayoutService);

  sectores = SECTORES;
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
    if (!ins?.totales_por_sector) return null;
    return ins.totales_por_sector[codigo] ?? 0;
  }
}
