import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

export type AtencionSeveridad = 'critico' | 'alto' | 'medio' | 'neutral';

export interface AtencionItem {
  /** Identifica el item al emitir el click. Solo se necesita si `accionable`. */
  clave: string;
  etiqueta: string;
  cantidad: number;
  severidad: AtencionSeveridad;
  /** Si no hay una navegación real para este item, no se pinta como botón. */
  accionable?: boolean;
}

/**
 * Bandeja ejecutiva de "qué requiere atención". Agrupa items que YA se
 * calcularon en el componente padre (nunca inventa cifras propias) y los
 * pinta como una lista escaneable, color + palabra (WCAG 1.4.1), cada uno
 * clicable SOLO si el padre declaró una acción real para él.
 */
@Component({
  standalone: true,
  selector: 'app-attention-panel',
  imports: [CommonModule],
  template: `
    <div class="attn" role="region" [attr.aria-label]="titulo">
      <h3 class="attn__titulo">{{ titulo }}</h3>
      @if (!items.length) {
        <p class="attn__vacio">Nada pendiente de revisar por ahora.</p>
      } @else {
        <ul class="attn__lista">
          @for (it of items; track it.clave) {
            <li>
              @if (it.accionable) {
                <button type="button" class="attn__item attn__item--accion"
                        [class]="'attn__item attn__item--accion attn__item--' + it.severidad"
                        (click)="accion.emit(it.clave)">
                  <span class="attn__punto" aria-hidden="true"></span>
                  <span class="attn__texto">{{ it.cantidad }} {{ it.etiqueta }}</span>
                  <span class="attn__flecha" aria-hidden="true">→</span>
                </button>
              } @else {
                <span class="attn__item" [class]="'attn__item attn__item--' + it.severidad">
                  <span class="attn__punto" aria-hidden="true"></span>
                  <span class="attn__texto">{{ it.cantidad }} {{ it.etiqueta }}</span>
                </span>
              }
            </li>
          }
        </ul>
      }
      <ng-content />
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    .attn { display: flex; flex-direction: column; gap: $space-2; }
    .attn__titulo { margin: 0; font-size: $font-size-sm; font-weight: 700; color: $color-text; }
    .attn__vacio { margin: 0; font-size: $font-size-sm; color: $color-text-muted; }
    .attn__lista { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
    .attn__item {
      display: flex; align-items: center; gap: $space-2; width: 100%;
      padding: $space-2 $space-2; border: 0; background: transparent; border-radius: $radius-sm;
      font-size: $font-size-sm; color: $color-text; text-align: left;
    }
    .attn__item--accion { cursor: pointer; }
    .attn__item--accion:hover { background: $color-bg-subtle; }
    .attn__item--accion:focus-visible { outline: $focus-ring; outline-offset: -2px; }
    .attn__punto { width: 8px; height: 8px; border-radius: 50%; flex: none; }
    .attn__item--critico .attn__punto { background: $color-danger; }
    .attn__item--alto .attn__punto { background: $color-warning; }
    .attn__item--medio .attn__punto { background: $color-info; }
    .attn__item--neutral .attn__punto { background: $color-neutral-400; }
    .attn__texto { flex: 1; min-width: 0; }
    .attn__flecha { color: $color-text-muted; flex: none; }
  `],
})
export class AttentionPanelComponent {
  @Input() titulo = 'Requiere atención';
  @Input() items: AtencionItem[] = [];
  @Output() accion = new EventEmitter<string>();
}
