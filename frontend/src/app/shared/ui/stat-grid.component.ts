import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

export interface StatItem {
  value: string | number;
  label: string;
  sublabel?: string;
  /** Denominador opcional: value/total, ej. 3 de 10 actividades con meta. */
  total?: string | number;
  /** Clase fa-* completa, ej. "fa-graduation-cap". Opcional. */
  icon?: string;
  /** Acento del borde izquierdo. Sin variant = neutral. */
  variant?: 'ok' | 'warn' | 'plan';
}

/**
 * Fila de indicadores compactos. Envuelve `.kpis`/`.kpi` (globales en
 * `_page.scss`, el mismo patrón que ya usan 20+ pantallas) — solo aporta
 * la API de datos, sin clases nuevas.
 */
@Component({
  standalone: true,
  selector: 'app-stat-grid',
  imports: [CommonModule],
  template: `
    <section class="kpis" [attr.aria-label]="ariaLabel ?? null">
      @for (s of stats; track s.label) {
        <div class="kpi"
             [class.kpi--ok]="s.variant === 'ok'"
             [class.kpi--warn]="s.variant === 'warn'"
             [class.kpi--plan]="s.variant === 'plan'">
          @if (s.icon) { <i class="fa" [class]="s.icon" aria-hidden="true"></i> }
          <span class="kpi__val">
            {{ s.value }}
            @if (s.total != null) { <small>/{{ s.total }}</small> }
          </span>
          <span class="kpi__lbl">
            {{ s.label }}
            @if (s.sublabel) { <small>· {{ s.sublabel }}</small> }
          </span>
        </div>
      }
    </section>
  `,
})
export class StatGridComponent {
  @Input({ required: true }) stats: StatItem[] = [];
  @Input() ariaLabel?: string;
}
