import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { ENTIDADES } from './presupuesto.types';

@Component({
  standalone: true,
  selector: 'app-presupuesto-hub',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Presupuesto</h1>
        <p class="page__subtitle">Proyectos, KPIs, CDPs y contratos del PDL.</p>
      </header>

      <div class="hub-grid">
        @for (e of entidades; track e.codigo) {
          <a [routerLink]="['/presupuesto', e.codigo]"
             class="hub-card" [class]="'hub-card--' + e.color">
            <div class="hub-card__icon">
              <i class="fa" [class]="e.icon" aria-hidden="true"></i>
            </div>
            <h3 class="hub-card__title">{{ e.label }}</h3>
            <p class="hub-card__subtitle">Ver listado y detalle</p>
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-6; }
  `],
})
export class PresupuestoHubComponent implements OnInit {
  private layout = inject(LayoutService);
  entidades = ENTIDADES;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto' },
    ]);
  }
}
